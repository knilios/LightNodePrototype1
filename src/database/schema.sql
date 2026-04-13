CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_folder_id TEXT NULL,
    full_path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY(parent_folder_id) REFERENCES folders(id)
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    folder_id TEXT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    sha256_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(folder_id) REFERENCES folders(id)
);

CREATE INDEX IF NOT EXISTS idx_files_folder_id ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
CREATE INDEX IF NOT EXISTS idx_files_sha256_hash ON files(sha256_hash);
