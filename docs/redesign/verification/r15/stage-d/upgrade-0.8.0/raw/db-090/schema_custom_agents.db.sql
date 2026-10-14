CREATE TABLE custom_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    philosophy TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    tools_json TEXT NOT NULL DEFAULT '[]',
    default_provider TEXT NOT NULL,
    default_model TEXT,
    icon TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
