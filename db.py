"""SQLite data access layer for the expense bot.

All public functions are async and internally offload blocking sqlite3
operations to a thread via asyncio.to_thread to keep the event loop responsive.
"""

from __future__ import annotations

import sqlite3
import os
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Sequence, Tuple

import asyncio


def _db_path() -> str:
    """Resolve the database path from env at call time.

    This ensures `.env`-loaded values are honored even if imported earlier.
    """
    return os.getenv("DB_PATH", "expenses.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            amount INTEGER NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    # Add optional columns if missing
    cur = conn.execute("PRAGMA table_info(expenses)")
    cols = {row[1] for row in cur.fetchall()}
    if "category" not in cols:
        conn.execute("ALTER TABLE expenses ADD COLUMN category TEXT")


def _init_db_sync() -> None:
    with closing(_connect()) as conn, conn:
        _ensure_schema(conn)


async def init_db() -> None:
    """Create the database/table if not present."""
    await asyncio.to_thread(_init_db_sync)


def _add_expense_sync(user_id: int, item: str, amount: int, date_str: str, category: str | None) -> None:
    with closing(_connect()) as conn, conn:
        _ensure_schema(conn)
        conn.execute(
            "INSERT INTO expenses (user_id, item, amount, date, category) VALUES (?, ?, ?, ?, ?)",
            (user_id, item, amount, date_str, category),
        )


async def add_expense(user_id: int, item: str, amount: int, date_str: str, category: str | None = None) -> None:
    """Add a single expense record to the database."""
    await asyncio.to_thread(_add_expense_sync, user_id, item, amount, date_str, category)


def _get_all_expenses_sync(user_id: int) -> List[Tuple[str, int, str]]:
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT item, amount, date FROM expenses WHERE user_id = ? ORDER BY id ASC",
            (user_id,),
        )
        return [(row["item"], int(row["amount"]), row["date"]) for row in cur.fetchall()]


async def get_all_expenses(user_id: int) -> List[Tuple[str, int, str]]:
    """Return all expenses as (item, amount, date)."""
    return await asyncio.to_thread(_get_all_expenses_sync, user_id)


def _get_expenses_by_date_sync(user_id: int, date_str: str) -> List[Tuple[str, int, str]]:
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            """
            SELECT item, amount, date
            FROM expenses
            WHERE user_id = ? AND date = ?
            ORDER BY id ASC
            """,
            (user_id, date_str),
        )
        return [(row["item"], int(row["amount"]), row["date"]) for row in cur.fetchall()]


async def get_expenses_by_date(user_id: int, date_str: str) -> List[Tuple[str, int, str]]:
    """Return expenses for a user for a specific YYYY-MM-DD date."""
    return await asyncio.to_thread(_get_expenses_by_date_sync, user_id, date_str)


def _get_month_total_sync(user_id: int, year: int, month: int) -> int:
    ym_prefix = f"{year:04d}-{month:02d}-"
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{ym_prefix}%"),
        )
        row = cur.fetchone()
        return int(row[0] or 0)


async def get_month_total(user_id: int, year: int, month: int) -> int:
    """Return total expenses for a user's given year-month."""
    return await asyncio.to_thread(_get_month_total_sync, user_id, year, month)


def _get_expenses_by_month_sync(user_id: int, year: int, month: int) -> List[Tuple[int, str, int, str, str | None]]:
    ym_prefix = f"{year:04d}-{month:02d}-"
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            """
            SELECT id, item, amount, date, category
            FROM expenses
            WHERE user_id = ? AND date LIKE ?
            ORDER BY date ASC, id ASC
            """,
            (user_id, f"{ym_prefix}%"),
        )
        return [
            (int(row["id"]), row["item"], int(row["amount"]), row["date"], row["category"])  # type: ignore[index]
            for row in cur.fetchall()
        ]


async def get_expenses_by_month(user_id: int, year: int, month: int) -> List[Tuple[int, str, int, str, str | None]]:
    """Return all expense rows for the given year-month."""
    return await asyncio.to_thread(_get_expenses_by_month_sync, user_id, year, month)


def _get_last_expense_sync(user_id: int) -> Tuple[int, str, int, str, str | None] | None:
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT id, item, amount, date, category FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return (int(row["id"]), row["item"], int(row["amount"]), row["date"], row["category"])  # type: ignore[index]


async def get_last_expense(user_id: int) -> Tuple[int, str, int, str, str | None] | None:
    return await asyncio.to_thread(_get_last_expense_sync, user_id)


def _delete_expense_sync(user_id: int, expense_id: int) -> int:
    with closing(_connect()) as conn, conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "DELETE FROM expenses WHERE user_id = ? AND id = ?",
            (user_id, expense_id),
        )
        return cur.rowcount or 0


async def delete_expense(user_id: int, expense_id: int) -> int:
    """Delete one expense for user by id. Returns number of rows removed (0 or 1)."""
    return await asyncio.to_thread(_delete_expense_sync, user_id, expense_id)


def _get_month_category_totals_sync(user_id: int, year: int, month: int) -> List[Tuple[str, int]]:
    ym_prefix = f"{year:04d}-{month:02d}-"
    with closing(_connect()) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            """
            SELECT COALESCE(NULLIF(category, ''), 'Boshqa') AS cat, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ? AND date LIKE ?
            GROUP BY cat
            ORDER BY total DESC
            """,
            (user_id, f"{ym_prefix}%"),
        )
        return [(row[0], int(row[1])) for row in cur.fetchall()]


async def get_month_category_totals(user_id: int, year: int, month: int) -> List[Tuple[str, int]]:
    return await asyncio.to_thread(_get_month_category_totals_sync, user_id, year, month)


def _delete_all_expenses_sync(user_id: int) -> int:
    with closing(_connect()) as conn, conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "DELETE FROM expenses WHERE user_id = ?",
            (user_id,),
        )
        return cur.rowcount or 0


async def delete_all_expenses(user_id: int) -> int:
    """Delete all expenses for a user. Returns number of rows removed."""
    return await asyncio.to_thread(_delete_all_expenses_sync, user_id)
