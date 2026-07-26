ALTER TABLE friend_accounts
ADD COLUMN current_level INTEGER NOT NULL DEFAULT 0;

ALTER TABLE friend_accounts
ADD COLUMN current_xp INTEGER NOT NULL DEFAULT 0;

ALTER TABLE friend_accounts
ADD COLUMN xp_required INTEGER NOT NULL DEFAULT 0;

ALTER TABLE friend_accounts
ADD COLUMN goal_level INTEGER NOT NULL DEFAULT 30;

ALTER TABLE friend_accounts
ADD COLUMN progress_updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_friend_accounts_progress
ON friend_accounts(progress_updated_at DESC);
