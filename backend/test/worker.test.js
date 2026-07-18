import assert from "node:assert/strict";
import test from "node:test";

import {
  ProxyError,
  authorizeAccount,
  buildMatchData,
  normalizeAccountId,
  platformRoute,
  sha256Hex
} from "../src/worker.js";

test("normalizes Riot IDs without changing their structure", () => {
  assert.equal(normalizeAccountId(" Test Player ", " EUW "), "test player#euw");
});

test("maps platforms to Riot regional routes", () => {
  assert.deepEqual(platformRoute("euw1"), { platform: "EUW1", region: "europe" });
  assert.throws(() => platformRoute("invalid"), ProxyError);
});

test("allows a token only for assigned Riot IDs", async () => {
  const token = "test-token-with-more-than-24-characters";
  const hash = await sha256Hex(token);
  const rules = JSON.stringify({ [hash]: ["Test Player#EUW"] });
  await authorizeAccount(`Bearer ${token}`, rules, "test player", "euw");
  await assert.rejects(
    authorizeAccount(`Bearer ${token}`, rules, "Another Player", "EUW"),
    (error) => error instanceof ProxyError && error.status === 403
  );
});

test("rejects unknown access tokens", async () => {
  await assert.rejects(
    authorizeAccount(
      "Bearer unknown-token-with-more-than-24-characters",
      "{}",
      "Test Player",
      "EUW"
    ),
    (error) => error instanceof ProxyError && error.status === 401
  );
});

test("returns only the tracked participant match fields", () => {
  const match = {
    metadata: { matchId: "EUW1_123" },
    info: {
      gameCreation: 1_700_000_000_000,
      gameDuration: 1800,
      queueId: 420,
      participants: [
        {
          puuid: "p1",
          championName: "Lux",
          teamPosition: "MIDDLE",
          win: true,
          kills: 5,
          deaths: 2,
          assists: 9,
          totalMinionsKilled: 150,
          neutralMinionsKilled: 10,
          totalDamageDealtToChampions: 21000,
          goldEarned: 12345,
          visionScore: 18,
          champLevel: 17
        },
        { puuid: "another-player", championName: "Hidden" }
      ]
    }
  };
  const parsed = buildMatchData(match, "p1");
  assert.equal(parsed.match_id, "EUW1_123");
  assert.equal(parsed.champion, "Lux");
  assert.equal(parsed.cs, 160);
  assert.equal(Object.hasOwn(parsed, "participants"), false);
});
