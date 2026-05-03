import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge_base.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin','Editor','Viewer')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
            tags TEXT DEFAULT '',
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id),
            updated_at TEXT NOT NULL,
            is_pinned INTEGER DEFAULT 0,
            is_private INTEGER DEFAULT 0,
            type TEXT DEFAULT 'article',
            language TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS article_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            tags TEXT DEFAULT '',
            saved_by INTEGER REFERENCES users(id),
            saved_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            reaction_type TEXT NOT NULL CHECK(reaction_type IN ('helpful','needs_update')),
            created_at TEXT NOT NULL,
            UNIQUE(article_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL,
            is_pinned INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            work_done TEXT NOT NULL,
            blockers TEXT DEFAULT '',
            remarks TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            login_time TEXT NOT NULL,
            logout_time TEXT NOT NULL,
            tasks_done TEXT NOT NULL,
            remarks TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS shared_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stored_name TEXT NOT NULL,
            original_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            uploaded_by INTEGER NOT NULL REFERENCES users(id),
            uploaded_at TEXT NOT NULL,
            visibility TEXT NOT NULL DEFAULT 'everyone' CHECK(visibility IN ('everyone','private'))
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            body,
            tags,
            content=articles,
            content_rowid=id
        );

        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, body, tags)
            VALUES (new.id, new.title, new.body, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, body, tags)
            VALUES ('delete', old.id, old.title, old.body, old.tags);
            INSERT INTO articles_fts(rowid, title, body, tags)
            VALUES (new.id, new.title, new.body, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, body, tags)
            VALUES ('delete', old.id, old.title, old.body, old.tags);
        END;
    ''')

    conn.commit()

    # Migrate existing DB: add columns that may not exist yet
    _migrate(conn)

    conn.close()


def _migrate(conn):
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(articles)")}
    for col, definition in [
        ('is_private', 'INTEGER DEFAULT 0'),
        ('type',       "TEXT DEFAULT 'article'"),
        ('language',   "TEXT DEFAULT ''"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE articles ADD COLUMN {col} {definition}")
    conn.commit()


def create_default_admin():
    from werkzeug.security import generate_password_hash
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        ts = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
            ('admin', generate_password_hash('admin123'), 'Admin', ts)
        )
        conn.commit()
        print("Default admin created: username=admin  password=admin123")
    conn.close()


def now():
    return datetime.utcnow().isoformat()
