import {
  ProxyError,
  jsonBody,
  jsonResponse,
  normalizeAccountId,
  platformRoute,
  sha256Hex
} from "./core.js";
import {
  addFriendAccount,
  adminOverview,
  authorizeAccount,
  authorizeRequest,
  cleanupLogs,
  createFriend,
  deleteDevice,
  deleteFriend,
  deleteFriendAccount,
  recordActivity,
  reviewFriendAccount,
  requireAdmin,
  rotateFriendCode,
  updateDevice,
  updateFriend
} from "./access.js";
import { adminPageResponse } from "./admin_page.js";

export { ProxyError, normalizeAccountId, platformRoute, sha256Hex, authorizeAccount };

async function riotJson(url, riotApiKey) {
  if (!riotApiKey) {
    throw new ProxyError(
      503,
      "riot_key_expired",
      "Właściciel nie skonfigurował jeszcze klucza Riot na serwerze."
    );
  }
  let response;
  try {
    response = await fetch(url, {
      headers: {
        "X-Riot-Token": riotApiKey,
        "User-Agent": "LoL-XP-Tracker-Private/0.10"
      }
    });
  } catch {
    throw new ProxyError(502, "riot_unavailable", "Nie udało się połączyć z Riot API.");
  }
  if (response.status === 401 || response.status === 403) {
    throw new ProxyError(
      503,
      "riot_key_expired",
      "Klucz Riot na serwerze wygasł albo został odrzucony. Właściciel musi go wymienić."
    );
  }
  if (response.status === 429) {
    throw new ProxyError(
      429,
      "riot_rate_limited",
      "Limit zapytań Riot został chwilowo przekroczony.",
      response.headers.get("retry-after")
    );
  }
  if (response.status === 404) {
    throw new ProxyError(404, "riot_not_found", "Nie znaleziono konta lub meczu.");
  }
  if (!response.ok) {
    throw new ProxyError(502, "riot_error", `Riot API zwróciło błąd ${response.status}.`);
  }
  return response.json();
}

export function buildMatchData(match, puuid) {
  const info = match?.info || {};
  const participant = (info.participants || []).find((item) => item.puuid === puuid);
  if (!participant) {
    throw new ProxyError(404, "participant_not_found", "Nie znaleziono gracza w meczu.");
  }
  const creation = Number(info.gameCreation || 0);
  return {
    match_id: match?.metadata?.matchId || null,
    played_at: creation ? new Date(creation).toISOString() : new Date().toISOString(),
    queue_id: Number(info.queueId || 0),
    champion: participant.championName || "Nieznany",
    role: participant.teamPosition || participant.role || "",
    win: Boolean(participant.win),
    kills: Number(participant.kills || 0),
    deaths: Number(participant.deaths || 0),
    assists: Number(participant.assists || 0),
    cs: Number(participant.totalMinionsKilled || 0) + Number(participant.neutralMinionsKilled || 0),
    damage: Number(participant.totalDamageDealtToChampions || 0),
    gold: Number(participant.goldEarned || 0),
    vision_score: Number(participant.visionScore || 0),
    champion_level: Number(participant.champLevel || 0),
    duration_seconds: Number(info.gameDuration || 0)
  };
}

function requiredQuery(url, name, maxLength) {
  const value = String(url.searchParams.get(name) || "").trim();
  if (!value || value.length > maxLength) {
    throw new ProxyError(400, "invalid_request", `Nieprawidłowe pole ${name}.`);
  }
  return value;
}

async function accountPuuid(region, gameName, tagLine, riotApiKey) {
  const account = await riotJson(
    `https://${region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/` +
      `${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`,
    riotApiKey
  );
  if (!account?.puuid) {
    throw new ProxyError(404, "riot_not_found", "Nie znaleziono konta Riot.");
  }
  return account.puuid;
}

function inBackground(context, promise) {
  const safePromise = promise.catch(() => undefined);
  if (context && typeof context.waitUntil === "function") {
    context.waitUntil(safePromise);
  }
}

async function handleMatchRequest(request, env, context, explicitMatchId = null) {
  const url = new URL(request.url);
  const gameName = requiredQuery(url, "game_name", 64);
  const tagLine = requiredQuery(url, "tag_line", 16);
  const { platform, region } = platformRoute(requiredQuery(url, "platform", 8));
  const access = await authorizeRequest(request, env, gameName, tagLine, context, platform);

  const puuid = await accountPuuid(region, gameName, tagLine, env.RIOT_API_KEY);
  let matchId = explicitMatchId;
  if (!matchId) {
    const ids = await riotJson(
      `https://${region}.api.riotgames.com/lol/match/v5/matches/by-puuid/` +
        `${encodeURIComponent(puuid)}/ids?start=0&count=1`,
      env.RIOT_API_KEY
    );
    if (!Array.isArray(ids) || !ids.length) {
      throw new ProxyError(404, "match_not_found", "Konto nie ma dostępnych meczów.");
    }
    matchId = ids[0];
  }
  if (!/^[A-Za-z0-9]+_[0-9]+$/.test(matchId)) {
    throw new ProxyError(400, "invalid_match_id", "Nieprawidłowy identyfikator meczu.");
  }
  const match = await riotJson(
    `https://${region}.api.riotgames.com/lol/match/v5/matches/${encodeURIComponent(matchId)}`,
    env.RIOT_API_KEY
  );
  const result = buildMatchData(match, puuid);
  if (access.friendId) {
    inBackground(
      context,
      recordActivity(env, {
        friendId: access.friendId,
        deviceId: access.deviceId,
        eventType: "request_ok",
        requestedAccount: access.requestedAccount,
        endpoint: url.pathname,
        country: access.country,
        networkHash: access.networkHash,
        result: "allowed",
        details: result.match_id
      })
    );
  }
  return result;
}

async function handleAdminRequest(request, env) {
  await requireAdmin(request, env);
  const url = new URL(request.url);
  const origin = url.origin;

  if (request.method === "GET" && url.pathname === "/v1/admin/overview") {
    return jsonResponse(await adminOverview(env));
  }
  if (request.method === "POST" && url.pathname === "/v1/admin/friends") {
    return jsonResponse(await createFriend(env, await jsonBody(request), origin), 201);
  }
  const rotateRoute = url.pathname.match(/^\/v1\/admin\/friends\/([^/]+)\/rotate$/);
  if (request.method === "POST" && rotateRoute) {
    return jsonResponse(await rotateFriendCode(env, rotateRoute[1], origin));
  }
  const accountRoute = url.pathname.match(
    /^\/v1\/admin\/friends\/([^/]+)\/accounts(?:\/([^/]+))?$/
  );
  if (request.method === "POST" && accountRoute && !accountRoute[2]) {
    return jsonResponse(
      await addFriendAccount(env, accountRoute[1], await jsonBody(request)),
      201
    );
  }
  if (request.method === "DELETE" && accountRoute?.[2]) {
    await deleteFriendAccount(env, accountRoute[1], accountRoute[2]);
    return jsonResponse({ status: "ok" });
  }
  if (request.method === "PATCH" && accountRoute?.[2]) {
    return jsonResponse(await reviewFriendAccount(env, accountRoute[1], accountRoute[2]));
  }
  const friendRoute = url.pathname.match(/^\/v1\/admin\/friends\/([^/]+)$/);
  if (request.method === "PATCH" && friendRoute) {
    return jsonResponse(await updateFriend(env, friendRoute[1], await jsonBody(request)));
  }
  if (request.method === "DELETE" && friendRoute) {
    await deleteFriend(env, friendRoute[1]);
    return jsonResponse({ status: "ok" });
  }
  const deviceRoute = url.pathname.match(/^\/v1\/admin\/devices\/([^/]+)$/);
  if (request.method === "PATCH" && deviceRoute) {
    return jsonResponse(await updateDevice(env, deviceRoute[1], await jsonBody(request)));
  }
  if (request.method === "DELETE" && deviceRoute) {
    await deleteDevice(env, deviceRoute[1]);
    return jsonResponse({ status: "ok" });
  }
  throw new ProxyError(404, "route_not_found", "Nie znaleziono endpointu panelu.");
}

async function routeRequest(request, env, context) {
  const url = new URL(request.url);
  if (request.method === "GET" && (url.pathname === "/admin" || url.pathname === "/admin/")) {
    return adminPageResponse();
  }
  if (url.pathname.startsWith("/v1/admin/")) {
    return handleAdminRequest(request, env);
  }
  if (request.method !== "GET") {
    throw new ProxyError(405, "method_not_allowed", "Ta metoda nie jest dozwolona.");
  }
  if (url.pathname === "/health") {
    return jsonResponse({
      status: "ok",
      version: env.SERVICE_VERSION || "unknown",
      friend_profiles: Boolean(env.ACCESS_DB),
      riot_api_configured: Boolean(env.RIOT_API_KEY),
      admin_configured: Boolean(env.ADMIN_TOKEN)
    });
  }
  if (url.pathname === "/v1/latest-match") {
    return jsonResponse(await handleMatchRequest(request, env, context));
  }
  const matchRoute = url.pathname.match(/^\/v1\/matches\/([^/]+)$/);
  if (matchRoute) {
    let matchId;
    try {
      matchId = decodeURIComponent(matchRoute[1]);
    } catch {
      throw new ProxyError(400, "invalid_match_id", "Nieprawidłowy identyfikator meczu.");
    }
    return jsonResponse(await handleMatchRequest(request, env, context, matchId));
  }
  throw new ProxyError(404, "route_not_found", "Nie znaleziono endpointu.");
}

export default {
  async fetch(request, env, context) {
    try {
      return await routeRequest(request, env, context);
    } catch (error) {
      const known = error instanceof ProxyError;
      const status = known ? error.status : 500;
      const headers = known && error.retryAfter ? { "retry-after": error.retryAfter } : {};
      return jsonResponse(
        {
          error: {
            code: known ? error.code : "internal_error",
            message: known ? error.message : "Wewnętrzny błąd prywatnego serwera."
          }
        },
        status,
        headers
      );
    }
  },

  async scheduled(_controller, env, context) {
    context.waitUntil(cleanupLogs(env));
  }
};
