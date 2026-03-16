import aiosqlite
import os
from contextlib import asynccontextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "prompts.db")

# Returns a new DB connection as an async context manager
@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt        TEXT    NOT NULL,
                platform      TEXT    NOT NULL,
                url           TEXT,
                captured_at   TEXT    NOT NULL,
                was_filtered  INTEGER DEFAULT 0,
                filter_reason TEXT,
                category      TEXT,
                rating        INTEGER DEFAULT 0,
                rating_note   TEXT,
                score         INTEGER DEFAULT 0,
                session_id    TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                category    TEXT NOT NULL,
                template    TEXT NOT NULL,
                variables   TEXT,
                source_id   INTEGER,
                use_count   INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            )
        """)
        await db.commit()
