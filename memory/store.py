"""Simple persistent fact store (SQLite) - long-term memory across sessions.

For a single-user home assistant the fact count will realistically stay in the
dozens, not thousands, so there's no need for embedding-based semantic search:
all facts are just loaded in full and injected into the system prompt.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "facts.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL UNIQUE)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reminders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "text TEXT NOT NULL, "
        "due_at TEXT NOT NULL, "
        "done INTEGER NOT NULL DEFAULT 0"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS automation_rules ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "time_of_day TEXT NOT NULL, "  # "HH:MM", daily trigger
        "action TEXT NOT NULL, "  # natural-language instruction fed to the LLM when triggered
        "enabled INTEGER NOT NULL DEFAULT 1, "
        "last_run_date TEXT"  # "YYYY-MM-DD" of the last day this fired, to fire at most once/day
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS interaction_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts TEXT NOT NULL, "
        "role TEXT NOT NULL, "
        "content TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS episodes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts TEXT NOT NULL, "
        "summary TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reflection_state (id INTEGER PRIMARY KEY CHECK (id = 1), last_run_date TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS shopping_list ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "item TEXT NOT NULL, "
        "done INTEGER NOT NULL DEFAULT 0"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts TEXT NOT NULL, "
        "text TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS speakers (name TEXT PRIMARY KEY, embedding BLOB NOT NULL)"
    )
    # Reminders/automations are delivered independently per channel (voice vs
    # Telegram) so one doesn't "steal" the delivery from the other - these
    # columns were added after the tables already existed, so ALTER TABLE
    # (ignoring the harmless "duplicate column" error on repeat runs).
    for statement in (
        "ALTER TABLE reminders ADD COLUMN telegram_sent INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE automation_rules ADD COLUMN telegram_last_run_date TEXT",
    ):
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass  # column already exists
    return conn


def add_fact(text: str) -> int:
    text = text.strip()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO facts (text) VALUES (?)", (text,)
        )
        conn.commit()
        row = conn.execute("SELECT id FROM facts WHERE text = ?", (text,)).fetchone()
        return row[0] if row else cursor.lastrowid


def list_facts() -> list[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT text FROM facts ORDER BY id").fetchall()
    return [row[0] for row in rows]


def delete_fact(fact_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_reminder(text: str, due_at_iso: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO reminders (text, due_at) VALUES (?, ?)", (text.strip(), due_at_iso)
        )
        conn.commit()
        return cursor.lastrowid


def list_pending_reminders() -> list[tuple[int, str, str]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, due_at FROM reminders WHERE done = 0 ORDER BY due_at"
        ).fetchall()
    return rows


def list_due_reminders(now_iso: str) -> list[tuple[int, str]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text FROM reminders WHERE done = 0 AND due_at <= ? ORDER BY due_at",
            (now_iso,),
        ).fetchall()
    return rows


def mark_reminder_done(reminder_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        conn.commit()


def list_due_reminders_telegram(now_iso: str) -> list[tuple[int, str]]:
    """Independent from list_due_reminders()/mark_reminder_done() (voice channel) -
    tracked via a separate telegram_sent flag so both channels reliably deliver."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text FROM reminders WHERE telegram_sent = 0 AND due_at <= ? ORDER BY due_at",
            (now_iso,),
        ).fetchall()
    return rows


def mark_reminder_telegram_sent(reminder_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE reminders SET telegram_sent = 1 WHERE id = ?", (reminder_id,))
        conn.commit()


def add_automation_rule(time_of_day: str, action: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO automation_rules (time_of_day, action) VALUES (?, ?)",
            (time_of_day.strip(), action.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def list_automation_rules() -> list[tuple[int, str, str, bool]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, time_of_day, action, enabled FROM automation_rules ORDER BY time_of_day"
        ).fetchall()
    return [(rid, t, a, bool(e)) for rid, t, a, e in rows]


def delete_automation_rule(rule_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_due_automation_rules(current_time: str, today: str) -> list[tuple[int, str]]:
    """current_time: "HH:MM", today: "YYYY-MM-DD". Fires a rule at most once per day,
    as soon as current_time reaches its time_of_day."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, action FROM automation_rules "
            "WHERE enabled = 1 AND time_of_day <= ? "
            "AND (last_run_date IS NULL OR last_run_date != ?)",
            (current_time, today),
        ).fetchall()
    return rows


def mark_automation_rule_run(rule_id: int, today: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE automation_rules SET last_run_date = ? WHERE id = ?", (today, rule_id))
        conn.commit()


def get_due_automation_rules_telegram(current_time: str, today: str) -> list[tuple[int, str]]:
    """Independent from get_due_automation_rules()/mark_automation_rule_run() (voice
    channel) - tracked via a separate telegram_last_run_date column."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, action FROM automation_rules "
            "WHERE enabled = 1 AND time_of_day <= ? "
            "AND (telegram_last_run_date IS NULL OR telegram_last_run_date != ?)",
            (current_time, today),
        ).fetchall()
    return rows


def mark_automation_rule_telegram_run(rule_id: int, today: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE automation_rules SET telegram_last_run_date = ? WHERE id = ?", (today, rule_id))
        conn.commit()


def log_interaction(role: str, content: str, ts_iso: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO interaction_log (ts, role, content) VALUES (?, ?, ?)",
            (ts_iso, role, content.strip()),
        )
        conn.commit()


def get_interactions_since(since_iso: str) -> list[tuple[str, str, str]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, role, content FROM interaction_log WHERE ts >= ? ORDER BY ts", (since_iso,)
        ).fetchall()
    return rows


def add_episode(summary: str, ts_iso: str) -> int:
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO episodes (ts, summary) VALUES (?, ?)", (ts_iso, summary.strip()))
        conn.commit()
        return cursor.lastrowid


def list_recent_episodes(limit: int = 5) -> list[tuple[str, str]]:
    with _connect() as conn:
        rows = conn.execute("SELECT ts, summary FROM episodes ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return list(reversed(rows))


def get_reflection_last_run() -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT last_run_date FROM reflection_state WHERE id = 1").fetchone()
    return row[0] if row else None


def set_reflection_last_run(date_str: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reflection_state (id, last_run_date) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_run_date = excluded.last_run_date",
            (date_str,),
        )
        conn.commit()


def add_shopping_item(item: str) -> int:
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO shopping_list (item) VALUES (?)", (item.strip(),))
        conn.commit()
        return cursor.lastrowid


def list_shopping_items() -> list[tuple[int, str]]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, item FROM shopping_list WHERE done = 0 ORDER BY id").fetchall()
    return rows


def clear_shopping_list() -> None:
    with _connect() as conn:
        conn.execute("UPDATE shopping_list SET done = 1 WHERE done = 0")
        conn.commit()


def add_note(text: str, ts_iso: str) -> int:
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO notes (ts, text) VALUES (?, ?)", (ts_iso, text.strip()))
        conn.commit()
        return cursor.lastrowid


def list_notes(limit: int = 20) -> list[tuple[str, str]]:
    with _connect() as conn:
        rows = conn.execute("SELECT ts, text FROM notes ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return rows


def save_speaker_embedding(name: str, embedding: bytes) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO speakers (name, embedding) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET embedding = excluded.embedding",
            (name.strip(), embedding),
        )
        conn.commit()


def load_speaker_embeddings() -> dict[str, bytes]:
    with _connect() as conn:
        rows = conn.execute("SELECT name, embedding FROM speakers").fetchall()
    return {name: blob for name, blob in rows}


__all__ = [
    "add_fact",
    "list_facts",
    "delete_fact",
    "add_reminder",
    "list_pending_reminders",
    "list_due_reminders",
    "mark_reminder_done",
    "list_due_reminders_telegram",
    "mark_reminder_telegram_sent",
    "add_automation_rule",
    "list_automation_rules",
    "delete_automation_rule",
    "get_due_automation_rules",
    "mark_automation_rule_run",
    "get_due_automation_rules_telegram",
    "mark_automation_rule_telegram_run",
    "log_interaction",
    "get_interactions_since",
    "add_episode",
    "list_recent_episodes",
    "get_reflection_last_run",
    "set_reflection_last_run",
    "add_shopping_item",
    "list_shopping_items",
    "clear_shopping_list",
    "add_note",
    "list_notes",
    "save_speaker_embedding",
    "load_speaker_embeddings",
]
