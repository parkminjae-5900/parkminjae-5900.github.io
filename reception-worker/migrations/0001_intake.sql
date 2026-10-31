CREATE TABLE IF NOT EXISTS requests (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
 contact_time TEXT NOT NULL CHECK(contact_time IN ('any','daytime','evening')),
 consent_version TEXT NOT NULL, payload_hash TEXT NOT NULL,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS requests_expiry ON requests(expires_at);
