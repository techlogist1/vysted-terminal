CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX idx_workflows_updated ON workflows(updated_at DESC);
CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    last_fired_at INTEGER,
    last_seen TEXT,
    last_status TEXT,
    last_detail TEXT
);
