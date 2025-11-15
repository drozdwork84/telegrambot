import aiosqlite
from datetime import datetime
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
DB_PATH = "matches.db"


async def init_db():
    """Initialize database and create tables if they don't exist"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                match_datetime TEXT NOT NULL,
                title TEXT NOT NULL,
                reminded INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def add_match(chat_id: int, match_datetime: datetime, title: str) -> None:
    """Add a new match to the database"""
    async with aiosqlite.connect(DB_PATH) as db:
        created_at = datetime.now(MOSCOW_TZ).isoformat()
        match_dt_str = match_datetime.isoformat()
        
        await db.execute(
            "INSERT INTO matches (chat_id, match_datetime, title, reminded, created_at) VALUES (?, ?, ?, 0, ?)",
            (chat_id, match_dt_str, title, created_at)
        )
        await db.commit()


async def get_today_matches(chat_id: int) -> List[Dict]:
    """Get all future matches for today in the specified chat"""
    now = datetime.now(MOSCOW_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, match_datetime, title FROM matches 
               WHERE chat_id = ? AND match_datetime >= ? AND match_datetime <= ?
               ORDER BY match_datetime ASC""",
            (chat_id, now.isoformat(), today_end.isoformat())
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_matches_for_reminders() -> List[Dict]:
    """Get all matches that need reminders (1 minute before match time, not yet reminded)"""
    now = datetime.now(MOSCOW_TZ)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, chat_id, match_datetime, title FROM matches 
               WHERE reminded = 0 AND match_datetime > ?
               ORDER BY match_datetime ASC""",
            (now.isoformat(),)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def mark_as_reminded(match_id: int) -> None:
    """Mark a match as reminded"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE matches SET reminded = 1 WHERE id = ?",
            (match_id,)
        )
        await db.commit()
