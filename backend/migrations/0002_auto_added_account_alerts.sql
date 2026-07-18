ALTER TABLE friend_accounts
ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 1 CHECK (reviewed IN (0, 1));

CREATE INDEX IF NOT EXISTS idx_friend_accounts_reviewed
ON friend_accounts(reviewed, created_at DESC);
