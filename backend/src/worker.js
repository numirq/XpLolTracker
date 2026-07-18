const PLATFORM_ROUTES = Object.freeze({
  EUW1: "europe",
  EUN1: "europe",
  TR1: "europe",
  RU: "europe",
  NA1: "americas",
  BR1: "americas",
  LA1: "americas",
  LA2: "americas",
  KR: "asia",
  JP1: "asia",
  OC1: "sea",
  PH2: "sea",
  SG2: "sea",
  TH2: "sea",
  TW2: "sea",
  VN2: "sea"
});

export class ProxyError extends Error {
  constructor(status, code, message, retryAfter = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

export function normalizeAccountId(gameName, tagLine) {
  return `${String(gameName).normalize("NFKC").trim()}#${String(tagLine).normalize("NFKC").trim()}`
    .toLocaleLowerCase("en-US");
}

export function platformRoute(platform) {
  const normalized = String(platform || "").toUpperCase();
  const region = PLATFORM_ROUTES[normalized];
  if (!region) {
    throw new ProxyError(400, "invalid_platform", "Nieobsługiwany serwer Riot.");
  }
  return { platform: normalized, region };
}

export async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

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

export async function authorizeAccount(authorization, rawRules, gameName, tagLine) {
  if (!authorization || !authorization.startsWith("Bearer ")) {
    throw new ProxyError(401, "access_denied", "Brak kodu dostępu do prywatnego serwera.");
  }
  const token = authorization.slice(7).trim();
  if (token.length < 24 || token.length > 256) {
    throw new ProxyError(401, "access_denied", "Kod dostępu jest nieprawidłowy.");
  }
  const tokenHash = await sha256Hex(token);
  const rules = parseAccessRules(rawRules);
  const allowedAccounts = rules[tokenHash];
  if (!Array.isArray(allowedAccounts)) {
    throw new ProxyError(401, "access_denied", "Kod dostępu jest nieprawidłowy.");
  }
  const requestedAccount = normalizeAccountId(gameName, tagLine);
  const allowed = allowedAccounts.some((account) => {
    const separator = String(account).lastIndexOf("#");
    if (separator < 1) return false;
    return normalizeAccountId(
      String(account).slice(0, separator),
      String(account).slice(separator + 1)
    ) === requestedAccount;
  });
  if (!allowed) {
    throw new ProxyError(403, "access_denied", "Ten kod nie ma dostępu do wybranego konta Riot.");
  }
}

function jsonResponse(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer",
      ...extraHeaders
    }
  });
}

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
        "User-Agent": "LoL-XP-Tracker-Private/0.7"
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

async function handleMatchRequest(request, env, explicitMatchId = null) {
  const url = new URL(request.url);
  const gameName = requiredQuery(url, "game_name", 64);
  const tagLine = requiredQuery(url, "tag_line", 16);
  const { platform, region } = platformRoute(requiredQuery(url, "platform", 8));
  await authorizeAccount(request.headers.get("authorization"), env.ACCESS_RULES, gameName, tagLine);

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
  return buildMatchData(match, puuid);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (request.method !== "GET") {
        throw new ProxyError(405, "method_not_allowed", "Dozwolone są wyłącznie zapytania GET.");
      }
      if (url.pathname === "/health") {
        return jsonResponse({ status: "ok", version: env.SERVICE_VERSION || "unknown" });
      }
      if (url.pathname === "/v1/latest-match") {
        return jsonResponse(await handleMatchRequest(request, env));
      }
      const matchRoute = url.pathname.match(/^\/v1\/matches\/([^/]+)$/);
      if (matchRoute) {
        return jsonResponse(
          await handleMatchRequest(request, env, decodeURIComponent(matchRoute[1]))
        );
      }
      throw new ProxyError(404, "route_not_found", "Nie znaleziono endpointu.");
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
  }
};
