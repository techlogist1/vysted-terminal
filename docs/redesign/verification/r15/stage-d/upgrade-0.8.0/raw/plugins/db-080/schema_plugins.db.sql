CREATE TABLE plugin_configs (
    plugin_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    settings_json TEXT NOT NULL DEFAULT '{}',
    granted_secret_ids_json TEXT NOT NULL DEFAULT '[]'
);
