CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    cost_basis REAL NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'equity',
    opened_at TEXT,
    note TEXT
);
CREATE TABLE sqlite_sequence(name,seq);
