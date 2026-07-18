import {
  ProxyError,
  bearerToken,
  normalizeAccountId,
  platformRoute,
  randomId,
  randomToken,
  sha256Hex,
  utcNow
} from "./core.js";

const TOKEN_MINIMUM = 24;
const TOKEN_MAXIMUM = 256;
const LOG_RETENTION_DAYS = 30;

function parseAccessRules(rawRules) {
  try {
    const parsed = JSON.parse(rawRules || "{}");
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("ACCESS_RULES must be an object");
    }
    return parsed;
  } catch {
    throw new ProxyError(
      503,
      "access_rules_invalid",
      "Właściciel musi poprawić konfigurację dostępu na serwerze."
    );
  }
}

function validateAccessToken(token) {
  if (token.length < TOKEN_MINIMUM || token.length > TOKEN_MAXIMUM) {
    throw new ProxyError(401, "access_denied", "Kod dostępu jest nieprawidłowy.");
  }
}

function accountAllowed(accounts, gameName, tagLine) {
  const requestedAccount = normalizeAccountId(gameName, tagLine);
  return accounts.some((account) => {
    const separator = String(account).lastIndexOf("#");
    if (separator < 1) return false;
    return normalizeAccountId(
      String(account).slice(0, separator),
      String(account).slice(separator + 1)
    ) === requestedAccount;
  });
}

export async function authorizeAccount(authorization, rawRules, gameName, tagLine) {
  if (!authorization || !authorization.startsWith("Bearer ")) {
    throw new ProxyError(401, "access_denied", "Brak kodu dostępu do prywatnego serwera.");
  }
  const token = authorization.slice(7).trim();
  validateAccessToken(token);
  const tokenHash = await sha256Hex(token);
  const rules = parseAccessRules(rawRules);
  const allowedAccounts = rules[tokenHash];
  if (!Array.isArray(allowedAccounts)) {
    throw new ProxyError(401, "access_denied", "Kod dostępu jest nieprawidłowy.");
  }
  if (!accountAllowed(allowedAccounts, gameName, tagLine)) {
    throw new ProxyError(403, "access_denied", "Ten kod nie ma dostępu do wybranego konta Riot.");
  }
}

function hasDatabase(env) {
  return Boolean(env.ACCESS_DB && typeof env.ACCESS_DB.prepare === "function");
}

export function requireDatabase(env) {
  if (!hasDatabase(env)) {
    throw new ProxyError(
      503,
      "database_not_configured",
      "Panel znajomych wymaga dokończenia konfiguracji bazy D1."
    );
  }
  return env.ACCESS_DB;
}

function rows(result) {
  return Array.isArray(result?.results) ? result.results : [];
}

function cleanCountry(request) {
  const raw = String(request.cf?.country || request.headers.get("cf-ipcountry") || "").toUpperCase();
  return /^[A-Z]{2}$/.test(raw) ? raw : null;
}

function cleanAppVersion(request) {
  const raw = String(request.headers.get("x-tracker-version") || "").trim();
  return /^[0-9A-Za-z._-]{1,24}$/.test(raw) ? raw : null;
}

function cleanClientInstance(request) {
  const raw = String(request.headers.get("x-client-instance") || "").trim();
  return /^[0-9A-Za-z._~-]{16,256}$/.test(raw) ? raw : "legacy-client";
}

async function networkHash(request, env) {
  const address = String(request.headers.get("cf-connecting-ip") || "").trim();
  if (!address || !env.ADMIN_TOKEN) return null;
  return (await sha256Hex(`${env.ADMIN_TOKEN}:network:${address}`)).slice(0, 20);
}

export async function recordActivity(env, values) {
  if (!hasDatabase(env)) return;
  const now = utcNow();
  const details = values.details ? String(values.details).slice(0, 200) : null;
  await env.ACCESS_DB.prepare(
    `INSERT INTO activity_logs
      (friend_id, device_id, occurred_at, event_type, requested_account,
       endpoint, country, network_hash, result, details)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      values.friendId || null,
      values.deviceId || null,
      now,
      String(values.eventType || "request").slice(0, 40),
      values.requestedAccount ? String(values.requestedAccount).slice(0, 160) : null,
      values.endpoint ? String(values.endpoint).slice(0, 160) : null,
      values.country || null,
      values.networkHash || null,
      String(values.result || "ok").slice(0, 40),
      details
    )
    .run();
}

function background(context, promise) {
  const safePromise = promise.catch(() => undefined);
  if (context && typeof context.waitUntil === "function") {
    context.waitUntil(safePromise);
  }
}

async function registerDevice(request, env, friend, context) {
  const database = requireDatabase(env);
  const instance = cleanClientInstance(request);
  const instanceHash = await sha256Hex(`${friend.id}:device:${instance}`);
  const country = cleanCountry(request);
  const appVersion = cleanAppVersion(request);
  const now = utcNow();
  let device = await database
    .prepare("SELECT * FROM devices WHERE friend_id = ? AND instance_hash = ? LIMIT 1")
    .bind(friend.id, instanceHash)
    .first();

  if (device) {
    await database
      .prepare(
        `UPDATE devices
         SET last_seen_at = ?, last_country = ?, app_version = ?
         WHERE id = ?`
      )
      .bind(now, country, appVersion, device.id)
      .run();
    return { ...device, last_seen_at: now, last_country: country, app_version: appVersion };
  }

  const id = randomId();
  try {
    await database
      .prepare(
        `INSERT INTO devices
          (id, friend_id, instance_hash, name, trusted, first_seen_at, last_seen_at,
           first_country, last_country, app_version)
         VALUES (?, ?, ?, NULL, 0, ?, ?, ?, ?, ?)`
      )
      .bind(id, friend.id, instanceHash, now, now, country, country, appVersion)
      .run();
    device = {
      id,
      friend_id: friend.id,
      instance_hash: instanceHash,
      name: null,
      trusted: 0,
      first_seen_at: now,
      last_seen_at: now,
      first_country: country,
      last_country: country,
      app_version: appVersion
    };
    const requested = new URL(request.url);
    background(
      context,
      recordActivity(env, {
        friendId: friend.id,
        deviceId: id,
        eventType: "new_device",
        requestedAccount: normalizeAccountId(
          requested.searchParams.get("game_name") || "",
          requested.searchParams.get("tag_line") || ""
        ),
        endpoint: requested.pathname,
        country,
        networkHash: await networkHash(request, env),
        result: "allowed",
        details: instance === "legacy-client" ? "Aplikacja bez identyfikatora urządzenia" : null
      })
    );
    return device;
  } catch (error) {
    device = await database
      .prepare("SELECT * FROM devices WHERE friend_id = ? AND instance_hash = ? LIMIT 1")
      .bind(friend.id, instanceHash)
      .first();
    if (device) return device;
    throw error;
  }
}

async function authorizeLegacy(tokenHash, rawRules, gameName, tagLine) {
  const rules = parseAccessRules(rawRules);
  const allowedAccounts = rules[tokenHash];
  if (!Array.isArray(allowedAccounts)) return false;
  if (!accountAllowed(allowedAccounts, gameName, tagLine)) {
    throw new ProxyError(403, "access_denied", "Ten kod nie ma dostępu do wybranego konta Riot.");
  }
  return true;
}

export async function authorizeRequest(
  request,
  env,
  gameName,
  tagLine,
  context = null,
  requestedPlatform = "EUW1"
) {
  const token = bearerToken(request);
  if (!token) {
    throw new ProxyError(401, "access_denied", "Brak kodu dostępu do prywatnego serwera.");
  }
  validateAccessToken(token);
  const tokenHash = await sha256Hex(token);
  const requestedAccount = normalizeAccountId(gameName, tagLine);
  let databaseError = null;

  if (hasDatabase(env)) {
    try {
      const friend = await env.ACCESS_DB.prepare(
        "SELECT * FROM friends WHERE token_hash = ? LIMIT 1"
      )
        .bind(tokenHash)
        .first();
      if (friend) {
        if (!friend.enabled) {
          throw new ProxyError(401, "access_revoked", "Ten kod dostępu został wyłączony.");
        }
        const device = await registerDevice(request, env, friend, context);
        let account = await env.ACCESS_DB.prepare(
          `SELECT * FROM friend_accounts
           WHERE friend_id = ? AND normalized_account = ? LIMIT 1`
        )
          .bind(friend.id, requestedAccount)
          .first();
        if (!account) {
          const { platform } = platformRoute(requestedPlatform);
          const accountId = randomId();
          const createdAt = utcNow();
          let autoAdded = false;
          try {
            const created = await env.ACCESS_DB.prepare(
              `INSERT INTO friend_accounts
                (id, friend_id, game_name, tag_line, normalized_account, platform, created_at, reviewed)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)`
            )
              .bind(
                accountId,
                friend.id,
                gameName,
                tagLine,
                requestedAccount,
                platform,
                createdAt
              )
              .run();
            autoAdded = Boolean(created.meta?.changes);
          } catch (error) {
            account = await env.ACCESS_DB.prepare(
              `SELECT * FROM friend_accounts
               WHERE friend_id = ? AND normalized_account = ? LIMIT 1`
            )
              .bind(friend.id, requestedAccount)
              .first();
            if (!account) throw error;
          }

          account = await env.ACCESS_DB.prepare(
            `SELECT * FROM friend_accounts
             WHERE friend_id = ? AND normalized_account = ? LIMIT 1`
          )
            .bind(friend.id, requestedAccount)
            .first();

          if (autoAdded && account) {
            background(
              context,
              recordActivity(env, {
                friendId: friend.id,
                deviceId: device.id,
                eventType: "account_auto_added",
                requestedAccount,
                endpoint: new URL(request.url).pathname,
                country: cleanCountry(request),
                networkHash: await networkHash(request, env),
                result: "allowed",
                details: platform
              })
            );
          }
        }
        if (!account) throw new ProxyError(503, "account_registration_failed", "Nie udało się dopisać konta do profilu znajomego.");
        return {
          source: "friend_profile",
          friendId: friend.id,
          deviceId: device.id,
          requestedAccount,
          country: cleanCountry(request),
          networkHash: await networkHash(request, env)
        };
      }
    } catch (error) {
      if (error instanceof ProxyError) throw error;
      databaseError = error;
    }
  }

  if (await authorizeLegacy(tokenHash, env.ACCESS_RULES, gameName, tagLine)) {
    return { source: "legacy", friendId: null, deviceId: null, requestedAccount };
  }
  if (databaseError) {
    throw new ProxyError(
      503,
      "database_unavailable",
      "Baza profili znajomych jest chwilowo niedostępna."
    );
  }
  throw new ProxyError(401, "access_denied", "Kod dostępu jest nieprawidłowy.");
}

async function secureTokenEquals(provided, expected) {
  if (!provided || !expected) return false;
  const [left, right] = await Promise.all([sha256Hex(provided), sha256Hex(expected)]);
  let difference = left.length ^ right.length;
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return difference === 0;
}

export async function requireAdmin(request, env) {
  if (!env.ADMIN_TOKEN) {
    throw new ProxyError(
      503,
      "admin_not_configured",
      "Dodaj sekret ADMIN_TOKEN w ustawieniach Workera."
    );
  }
  if (!(await secureTokenEquals(bearerToken(request), String(env.ADMIN_TOKEN)))) {
    throw new ProxyError(401, "admin_denied", "Nieprawidłowy kod administratora.");
  }
  requireDatabase(env);
}

function requireName(value) {
  const name = String(value || "").normalize("NFKC").trim();
  if (!name || name.length > 60) {
    throw new ProxyError(400, "invalid_name", "Nazwa znajomego musi mieć od 1 do 60 znaków.");
  }
  return name;
}

function accountValues(body) {
  const gameName = String(body.game_name || "").normalize("NFKC").trim();
  const tagLine = String(body.tag_line || "").normalize("NFKC").trim().replace(/^#/, "");
  if (!gameName || gameName.length > 64 || !tagLine || tagLine.length > 16) {
    throw new ProxyError(400, "invalid_account", "Wpisz prawidłową nazwę Riot ID i tag.");
  }
  const { platform } = platformRoute(body.platform || "EUW1");
  return {
    gameName,
    tagLine,
    platform,
    normalized: normalizeAccountId(gameName, tagLine)
  };
}

function encodeInvitation(serverUrl, token) {
  const source = new TextEncoder().encode(JSON.stringify({ server: serverUrl, token }));
  const binary = Array.from(source, (byte) => String.fromCharCode(byte)).join("");
  return `LOLXP1.${btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "")}`;
}

function issueFriendCredentials(serverUrl) {
  const token = `lxpf_${randomToken(32)}`;
  return {
    token,
    tokenHint: token.slice(-6),
    invitation: encodeInvitation(serverUrl, token)
  };
}

export async function createFriend(env, body, serverUrl) {
  const database = requireDatabase(env);
  const name = requireName(body.name);
  const credentials = issueFriendCredentials(serverUrl);
  const friendId = randomId();
  const now = utcNow();
  const statements = [
    database
      .prepare(
        `INSERT INTO friends
          (id, name, token_hash, token_hint, enabled, created_at, updated_at)
         VALUES (?, ?, ?, ?, 1, ?, ?)`
      )
      .bind(
        friendId,
        name,
        await sha256Hex(credentials.token),
        credentials.tokenHint,
        now,
        now
      )
  ];
  if (body.game_name || body.tag_line) {
    const account = accountValues(body);
    statements.push(
      database
        .prepare(
          `INSERT INTO friend_accounts
            (id, friend_id, game_name, tag_line, normalized_account, platform, created_at, reviewed)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)`
        )
        .bind(
          randomId(),
          friendId,
          account.gameName,
          account.tagLine,
          account.normalized,
          account.platform,
          now
        )
    );
  }
  await database.batch(statements);
  return {
    friend: { id: friendId, name, token_hint: credentials.tokenHint, enabled: 1 },
    code: credentials.token,
    invitation: credentials.invitation
  };
}

export async function updateFriend(env, friendId, body) {
  const database = requireDatabase(env);
  const existing = await database.prepare("SELECT * FROM friends WHERE id = ?").bind(friendId).first();
  if (!existing) throw new ProxyError(404, "friend_not_found", "Nie znaleziono znajomego.");
  const name = body.name === undefined ? existing.name : requireName(body.name);
  const enabled = body.enabled === undefined ? Number(existing.enabled) : body.enabled ? 1 : 0;
  await database
    .prepare("UPDATE friends SET name = ?, enabled = ?, updated_at = ? WHERE id = ?")
    .bind(name, enabled, utcNow(), friendId)
    .run();
  return { id: friendId, name, enabled };
}

export async function deleteFriend(env, friendId) {
  const database = requireDatabase(env);
  const existing = await database
    .prepare("SELECT id FROM friends WHERE id = ?")
    .bind(friendId)
    .first();
  if (!existing) {
    throw new ProxyError(404, "friend_not_found", "Nie znaleziono znajomego.");
  }
  await database.batch([
    database.prepare("DELETE FROM activity_logs WHERE friend_id = ?").bind(friendId),
    database.prepare("DELETE FROM friends WHERE id = ?").bind(friendId)
  ]);
}

export async function rotateFriendCode(env, friendId, serverUrl) {
  const database = requireDatabase(env);
  const existing = await database.prepare("SELECT id FROM friends WHERE id = ?").bind(friendId).first();
  if (!existing) throw new ProxyError(404, "friend_not_found", "Nie znaleziono znajomego.");
  const credentials = issueFriendCredentials(serverUrl);
  await database
    .prepare(
      "UPDATE friends SET token_hash = ?, token_hint = ?, enabled = 1, updated_at = ? WHERE id = ?"
    )
    .bind(await sha256Hex(credentials.token), credentials.tokenHint, utcNow(), friendId)
    .run();
  await recordActivity(env, {
    friendId,
    eventType: "code_rotated",
    result: "admin"
  });
  return { code: credentials.token, invitation: credentials.invitation, token_hint: credentials.tokenHint };
}

export async function addFriendAccount(env, friendId, body) {
  const database = requireDatabase(env);
  const friend = await database.prepare("SELECT id FROM friends WHERE id = ?").bind(friendId).first();
  if (!friend) throw new ProxyError(404, "friend_not_found", "Nie znaleziono znajomego.");
  const account = accountValues(body);
  const id = randomId();
  try {
    await database
      .prepare(
        `INSERT INTO friend_accounts
          (id, friend_id, game_name, tag_line, normalized_account, platform, created_at, reviewed)
         VALUES (?, ?, ?, ?, ?, ?, ?, 1)`
      )
      .bind(
        id,
        friendId,
        account.gameName,
        account.tagLine,
        account.normalized,
        account.platform,
        utcNow()
      )
      .run();
  } catch {
    throw new ProxyError(409, "account_exists", "To konto jest już przypisane do znajomego.");
  }
  return { id, friend_id: friendId, game_name: account.gameName, tag_line: account.tagLine, platform: account.platform };
}

export async function deleteFriendAccount(env, friendId, accountId) {
  const result = await requireDatabase(env)
    .prepare("DELETE FROM friend_accounts WHERE id = ? AND friend_id = ?")
    .bind(accountId, friendId)
    .run();
  if (!result.meta?.changes) {
    throw new ProxyError(404, "account_not_found", "Nie znaleziono przypisanego konta.");
  }
}

export async function reviewFriendAccount(env, friendId, accountId) {
  const database = requireDatabase(env);
  const result = await database
    .prepare("UPDATE friend_accounts SET reviewed = 1 WHERE id = ? AND friend_id = ?")
    .bind(accountId, friendId)
    .run();
  if (!result.meta?.changes) {
    throw new ProxyError(404, "account_not_found", "Nie znaleziono przypisanego konta.");
  }
  await recordActivity(env, {
    friendId,
    eventType: "account_reviewed",
    result: "admin"
  });
  return { id: accountId, friend_id: friendId, reviewed: 1 };
}

export async function updateDevice(env, deviceId, body) {
  const database = requireDatabase(env);
  const existing = await database.prepare("SELECT * FROM devices WHERE id = ?").bind(deviceId).first();
  if (!existing) throw new ProxyError(404, "device_not_found", "Nie znaleziono urządzenia.");
  let name = existing.name;
  if (body.name !== undefined) {
    name = String(body.name || "").normalize("NFKC").trim().slice(0, 60) || null;
  }
  const trusted = body.trusted === undefined ? Number(existing.trusted) : body.trusted ? 1 : 0;
  await database
    .prepare("UPDATE devices SET name = ?, trusted = ? WHERE id = ?")
    .bind(name, trusted, deviceId)
    .run();
  return { id: deviceId, name, trusted };
}

export async function deleteDevice(env, deviceId) {
  const result = await requireDatabase(env).prepare("DELETE FROM devices WHERE id = ?").bind(deviceId).run();
  if (!result.meta?.changes) {
    throw new ProxyError(404, "device_not_found", "Nie znaleziono urządzenia.");
  }
}

export async function adminOverview(env) {
  const database = requireDatabase(env);
  const [friendResult, accountResult, deviceResult, activityResult] = await Promise.all([
    database.prepare("SELECT * FROM friends ORDER BY name COLLATE NOCASE").all(),
    database
      .prepare("SELECT * FROM friend_accounts ORDER BY game_name COLLATE NOCASE, tag_line COLLATE NOCASE")
      .all(),
    database
      .prepare(
        `SELECT d.*, f.name AS friend_name
         FROM devices d JOIN friends f ON f.id = d.friend_id
         ORDER BY d.trusted ASC, d.last_seen_at DESC LIMIT 200`
      )
      .all(),
    database
      .prepare(
        `SELECT l.*, f.name AS friend_name, d.name AS device_name
         FROM activity_logs l
         LEFT JOIN friends f ON f.id = l.friend_id
         LEFT JOIN devices d ON d.id = l.device_id
         ORDER BY l.occurred_at DESC LIMIT 250`
      )
      .all()
  ]);
  const accounts = rows(accountResult);
  const devices = rows(deviceResult);
  const accountAlerts = accounts.filter((account) => !account.reviewed).length;
  const deviceAlerts = devices.filter((device) => !device.trusted).length;
  return {
    friends: rows(friendResult),
    accounts,
    devices,
    activity: rows(activityResult),
    alerts: accountAlerts + deviceAlerts,
    account_alerts: accountAlerts,
    device_alerts: deviceAlerts,
    retention_days: LOG_RETENTION_DAYS
  };
}

export async function cleanupLogs(env) {
  if (!hasDatabase(env)) return;
  await env.ACCESS_DB.prepare(
    `DELETE FROM activity_logs
     WHERE datetime(occurred_at) < datetime('now', '-${LOG_RETENTION_DAYS} days')`
  )
    .run();
}
