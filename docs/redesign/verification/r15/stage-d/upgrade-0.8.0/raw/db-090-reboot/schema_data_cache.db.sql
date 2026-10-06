CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX cache_updated_at ON cache(updated_at);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
