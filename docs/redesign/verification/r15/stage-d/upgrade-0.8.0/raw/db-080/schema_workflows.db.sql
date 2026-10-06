CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX idx_workflows_updated ON workflows(updated_at DESC);
