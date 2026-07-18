import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import {
  adminOverview,
  authorizeRequest,
  createFriend,
  rotateFriendCode
} from "../src/access.js";
import { adminPageResponse } from "../src/admin_page.js";
import worker from "../src/worker.js";

class D1Statement {
  constructor(database, sql) {
    this.database = database;
    this.sql = sql;
    this.values = [];
  }

  bind(...values) {
    this.values = values;
    return this;
  }

  async first() {
    return this.database.database.prepare(this.sql).get(...this.values) || null;
  }

  async all() {
    return { results: this.database.database.prepare(this.sql).all(...this.values) };
  }

  async run() {
    const result = this.database.database.prepare(this.sql).run(...this.values);
    return { success: true, meta: { changes: Number(result.changes) } };
  }
}

class TestD1 {
  constructor() {
    this.database = new DatabaseSync(":memory:");
    this.database.exec(
      readFileSync(new URL("../migrations/0001_friend_profiles.sql", import.meta.url), "utf8")
    );
  }

  prepare(sql) {
    return new D1Statement(this, sql);
  }

  async batch(statements) {
    this.database.exec("BEGIN");
    try {
      const results = [];
      for (const statement of statements) results.push(await statement.run());
      this.database.exec("COMMIT");
      return results;
    } catch (error) {
      this.database.exec("ROLLBACK");
      throw error;
    }
  }
}

function context() {
  const pending = [];
  return {
    pending,
    waitUntil(promise) {
      pending.push(promise);
    }
  };
}

function matchRequest(token, instance, gameName = "Razorblade", tagLine = "Kiss") {
  const parameters = new URLSearchParams({ game_name: gameName, tag_line: tagLine, platform: "EUW1" });
  return new Request(`https://tracker.example/v1/latest-match?${parameters}`, {
    headers: {
      authorization: `Bearer ${token}`,
      "x-client-instance": instance,
      "x-tracker-version": "0.8.0",
      "cf-ipcountry": "PL"
    }
  });
}

test("permanent friend code allows multiple assigned accounts", async () => {
  const database = new TestD1();
  const env = { ACCESS_DB: database, ACCESS_RULES: "{}", ADMIN_TOKEN: "admin-secret-with-32-or-more-characters" };
  const created = await createFriend(
    env,
    { name: "Znajomy", game_name: "Razorblade", tag_line: "Kiss", platform: "EUW1" },
    "https://tracker.example"
  );
  const friendId = created.friend.id;
  await database
    .prepare(
      `INSERT INTO friend_accounts
       (id, friend_id, game_name, tag_line, normalized_account, platform, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .bind("a2", friendId, "Second", "EUW", "second#euw", "EUW1", new Date().toISOString())
    .run();

  const firstContext = context();
  const first = await authorizeRequest(
    matchRequest(created.code, "installation-one-123456"),
    env,
    "Razorblade",
    "Kiss",
    firstContext
  );
  await Promise.all(firstContext.pending);
  const second = await authorizeRequest(
    matchRequest(created.code, "installation-one-123456", "Second", "EUW"),
    env,
    "Second",
    "EUW",
    context()
  );
  assert.equal(first.friendId, friendId);
  assert.equal(second.friendId, friendId);
  assert.equal(created.invitation.startsWith("LOLXP1."), true);
  assert.equal(Object.hasOwn(created.friend, "expires_at"), false);
});

test("the first used account claims an empty friend profile but a second one does not", async () => {
  const database = new TestD1();
  const env = {
    ACCESS_DB: database,
    ACCESS_RULES: "{}",
    ADMIN_TOKEN: "admin-secret-with-32-or-more-characters"
  };
  const created = await createFriend(env, { name: "Znajomy" }, "https://tracker.example");
  const firstContext = context();

  const accepted = await authorizeRequest(
    matchRequest(created.code, "first-installation-12345"),
    env,
    "Razorblade",
    "Kiss",
    firstContext,
    "EUW1"
  );
  await Promise.all(firstContext.pending);

  assert.equal(accepted.friendId, created.friend.id);
  const overview = await adminOverview(env);
  assert.equal(overview.accounts.length, 1);
  assert.equal(overview.accounts[0].normalized_account, "razorblade#kiss");
  assert.equal(overview.accounts[0].platform, "EUW1");
  assert.equal(
    overview.activity.some((item) => item.event_type === "first_account_claimed"),
    true
  );

  const secondContext = context();
  await assert.rejects(
    authorizeRequest(
      matchRequest(created.code, "first-installation-12345", "Second", "EUW"),
      env,
      "Second",
      "EUW",
      secondContext,
      "EUW1"
    ),
    (error) => error.status === 403
  );
  await Promise.all(secondContext.pending);
  assert.equal((await adminOverview(env)).accounts.length, 1);
});

test("a new device is allowed and creates a visible alert instead of a block", async () => {
  const database = new TestD1();
  const env = { ACCESS_DB: database, ACCESS_RULES: "{}", ADMIN_TOKEN: "admin-secret-with-32-or-more-characters" };
  const created = await createFriend(
    env,
    { name: "Znajomy", game_name: "Razorblade", tag_line: "Kiss" },
    "https://tracker.example"
  );

  for (const instance of ["first-installation-12345", "second-installation-1234"]) {
    const workerContext = context();
    const authorization = await authorizeRequest(
      matchRequest(created.code, instance),
      env,
      "Razorblade",
      "Kiss",
      workerContext
    );
    assert.equal(authorization.source, "friend_profile");
    await Promise.all(workerContext.pending);
  }

  const overview = await adminOverview(env);
  assert.equal(overview.devices.length, 2);
  assert.equal(overview.alerts, 2);
  assert.equal(overview.devices.every((device) => device.trusted === 0), true);
  assert.equal(overview.activity.filter((item) => item.event_type === "new_device").length, 2);
});

test("rotating a permanent code revokes only the old code", async () => {
  const database = new TestD1();
  const env = { ACCESS_DB: database, ACCESS_RULES: "{}", ADMIN_TOKEN: "admin-secret-with-32-or-more-characters" };
  const created = await createFriend(
    env,
    { name: "Znajomy", game_name: "Razorblade", tag_line: "Kiss" },
    "https://tracker.example"
  );
  const rotated = await rotateFriendCode(env, created.friend.id, "https://tracker.example");
  await assert.rejects(
    authorizeRequest(
      matchRequest(created.code, "installation-one-123456"),
      env,
      "Razorblade",
      "Kiss",
      context()
    ),
    (error) => error.status === 401
  );
  const accepted = await authorizeRequest(
    matchRequest(rotated.code, "installation-one-123456"),
    env,
    "Razorblade",
    "Kiss",
    context()
  );
  assert.equal(accepted.friendId, created.friend.id);
});

test("raw friend tokens are never stored in D1", async () => {
  const database = new TestD1();
  const env = { ACCESS_DB: database, ACCESS_RULES: "{}" };
  const created = await createFriend(env, { name: "Znajomy" }, "https://tracker.example");
  const stored = await database.prepare("SELECT * FROM friends WHERE id = ?").bind(created.friend.id).first();
  assert.notEqual(stored.token_hash, created.code);
  assert.equal(stored.token_hash.length, 64);
  assert.equal(JSON.stringify(stored).includes(created.code), false);
});

test("admin HTTP routes require the owner token and create profiles", async () => {
  const database = new TestD1();
  const env = {
    ACCESS_DB: database,
    ACCESS_RULES: "{}",
    ADMIN_TOKEN: "admin-secret-with-32-or-more-characters",
    SERVICE_VERSION: "0.8.0"
  };
  const denied = await worker.fetch(
    new Request("https://tracker.example/v1/admin/overview"),
    env,
    context()
  );
  assert.equal(denied.status, 401);

  const created = await worker.fetch(
    new Request("https://tracker.example/v1/admin/friends", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.ADMIN_TOKEN}`,
        "content-type": "application/json"
      },
      body: JSON.stringify({ name: "Kacper", game_name: "Player", tag_line: "EUW" })
    }),
    env,
    context()
  );
  assert.equal(created.status, 201);
  const payload = await created.json();
  assert.equal(payload.friend.name, "Kacper");
  assert.equal(payload.code.startsWith("lxpf_"), true);

  const overview = await worker.fetch(
    new Request("https://tracker.example/v1/admin/overview", {
      headers: { authorization: `Bearer ${env.ADMIN_TOKEN}` }
    }),
    env,
    context()
  );
  assert.equal(overview.status, 200);
  assert.equal((await overview.json()).friends.length, 1);
});

test("admin page has strict browser headers and valid inline JavaScript", async () => {
  const response = adminPageResponse();
  const html = await response.text();
  assert.match(response.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  const script = html.match(/<script>([\s\S]+)<\/script>/)?.[1];
  assert.ok(script);
  assert.doesNotThrow(() => new Function(script));
  assert.match(script, /const formElement=event\.currentTarget/);
  assert.match(html, /Pierwsze konto przypisze się automatycznie/);
  assert.match(script, /first_account_claimed:'Przypisano pierwsze konto'/);
  assert.doesNotMatch(script, /await api\([^;]+\);event\.currentTarget\.reset/);
});
