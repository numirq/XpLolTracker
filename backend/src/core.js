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
  const bytes = new TextEncoder().encode(String(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function bearerToken(request) {
  const authorization = request.headers.get("authorization") || "";
  if (!authorization.startsWith("Bearer ")) {
    return "";
  }
  return authorization.slice(7).trim();
}

export function jsonResponse(payload, status = 200, extraHeaders = {}) {
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

export async function jsonBody(request, maximumBytes = 8192) {
  const declaredLength = Number(request.headers.get("content-length") || 0);
  if (declaredLength > maximumBytes) {
    throw new ProxyError(413, "payload_too_large", "Przesłane dane są zbyt duże.");
  }
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > maximumBytes) {
    throw new ProxyError(413, "payload_too_large", "Przesłane dane są zbyt duże.");
  }
  try {
    const parsed = raw ? JSON.parse(raw) : {};
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("expected object");
    }
    return parsed;
  } catch {
    throw new ProxyError(400, "invalid_json", "Przesłano nieprawidłowe dane JSON.");
  }
}

export function randomToken(bytes = 32) {
  const buffer = new Uint8Array(bytes);
  crypto.getRandomValues(buffer);
  const binary = Array.from(buffer, (byte) => String.fromCharCode(byte)).join("");
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

export function randomId() {
  return crypto.randomUUID();
}

export function utcNow() {
  return new Date().toISOString();
}
