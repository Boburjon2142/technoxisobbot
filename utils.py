"""Utility helpers for parsing and formatting expense records (minimal)."""

from __future__ import annotations

from typing import List, Sequence, Tuple


def parse_expense_message(text: str) -> tuple[str, int]:
    """Parse a user message like 'coffee 12000' -> ("coffee", 12000)."""
    s = (text or "").strip()
    if not s:
        raise ValueError("Matn bo'sh bo'lmasligi kerak.")

    parts = s.split()
    if len(parts) < 2:
        raise ValueError("Format: 'mahsulot summasi' (masalan: 'non 5000').")

    amount_str = parts[-1]
    item = " ".join(parts[:-1]).strip()
    if not amount_str.isdigit():
        raise ValueError("Summani butun son ko'rinishida yozing (masalan: 12000).")

    amount = int(amount_str)
    if amount < 0:
        raise ValueError("Summaning qiymati manfiy bo'lmasligi kerak.")
    if not item:
        raise ValueError("Mahsulot nomi ko'rsatilmagan.")

    return item, amount


def format_amount(amount: int) -> str:
    """Format amount in so'm with thousands separators."""
    return f"{amount:,} so'm".replace(",", " ")


def format_expenses_with_total(rows: Sequence[Tuple[str, int, str]]) -> str:
    """Format (item, amount, date) into a readable list plus total.

    - Item nomi va summa qalin ko'rinishda chiqadi.
    """
    lines: List[str] = []
    total = 0
    for item, amount, _date in rows:
        total += int(amount)
        lines.append(f"<b>{item}</b> — <b>{format_amount(int(amount))}</b>")
    lines.append(f"💰 Jami: <b>{format_amount(total)}</b>")
    return "\n".join(lines)
