PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS friends (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    token_hint TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS friend_accounts (
    id TEXT PRIMARY KEY,
    friend_id TEXT NOT NULL REFERENCES friends(id) ON DELETE CASCADE,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    normalized_account TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'EUW1',
    created_at TEXT NOT NULL,
    UNIQUE(friend_id, normalized_account)
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    friend_id TEXT NOT NULL REFERENCES friends(id) ON DELETE CASCADE,
    instance_hash TEXT NOT NULL,
    name TEXT,
    trusted INTEGER NOT NULL DEFAULT 0 CHECK (trusted IN (0, 1)),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    first_country TEXT,
    last_country TEXT,
    app_version TEXT,
    UNIQUE(friend_id, instance_hash)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    friend_id TEXT REFERENCES friends(id) ON DELETE SET NULL,
    device_id TEXT REFERENCES devices(id) ON DELETE SET NULL,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    requested_account TEXT,
    endpoint TEXT,
    country TEXT,
    network_hash TEXT,
    result TEXT NOT NULL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_friend_accounts_friend ON friend_accounts(friend_id);
CREATE INDEX IF NOT EXISTS idx_devices_friend ON devices(friend_id);
CREATE INDEX IF NOT EXISTS idx_devices_untrusted ON devices(trusted, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_occurred ON activity_logs(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_friend ON activity_logs(friend_id, occurred_at DESC);
