from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services import settings


class SQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS runs (
                  run_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  completed_at TEXT,
                  model_runtime TEXT NOT NULL,
                  disease_track TEXT NOT NULL,
                  error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS patients (
                  run_id TEXT PRIMARY KEY,
                  patient_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS evidence (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  source_id TEXT NOT NULL,
                  chunk_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS protocols (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  rank_seed REAL,
                  protocol_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS coarse_results (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  summary_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS daily_states (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  day INTEGER NOT NULL,
                  state_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS safety_flags (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  day INTEGER NOT NULL,
                  severity TEXT NOT NULL,
                  code TEXT NOT NULL,
                  message TEXT NOT NULL,
                  disqualifying INTEGER NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS scores (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  total_score REAL NOT NULL,
                  component_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS citations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  protocol_id TEXT NOT NULL,
                  source_id TEXT NOT NULL,
                  source_url TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS chat_logs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  question TEXT NOT NULL,
                  answer TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS run_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  timestamp TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS run_results (
                  run_id TEXT PRIMARY KEY,
                  result_json TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def create_run(self, run_id: str, model_runtime: str, disease_track: str = "type-2-diabetes") -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO runs(run_id, status, created_at, model_runtime, disease_track) VALUES (?, ?, ?, ?, ?)",
                (run_id, "queued", now, model_runtime, disease_track),
            )

    def update_run_status(self, run_id: str, status: str, error_message: str | None = None) -> None:
        with self._lock, self._conn() as conn:
            completed_at = datetime.now(UTC).isoformat() if status in {"completed", "failed"} else None
            conn.execute(
                "UPDATE runs SET status = ?, completed_at = COALESCE(?, completed_at), error_message = ? WHERE run_id = ?",
                (status, completed_at, error_message, run_id),
            )

    def save_patient(self, run_id: str, patient: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO patients(run_id, patient_json) VALUES (?, ?)",
                (run_id, json.dumps(patient)),
            )

    def save_evidence(self, run_id: str, chunks: list[dict[str, Any]]) -> None:
        with self._lock, self._conn() as conn:
            conn.executemany(
                "INSERT INTO evidence(run_id, source_id, chunk_json) VALUES (?, ?, ?)",
                [(run_id, chunk["source_id"], json.dumps(chunk)) for chunk in chunks],
            )

    def save_protocols(self, run_id: str, protocols: list[dict[str, Any]]) -> None:
        with self._lock, self._conn() as conn:
            conn.executemany(
                "INSERT INTO protocols(run_id, protocol_id, rank_seed, protocol_json) VALUES (?, ?, ?, ?)",
                [
                    (run_id, protocol["protocol_id"], float(index + 1), json.dumps(protocol))
                    for index, protocol in enumerate(protocols)
                ],
            )

    def save_coarse_result(self, run_id: str, protocol_id: str, coarse_summary: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO coarse_results(run_id, protocol_id, summary_json) VALUES (?, ?, ?)",
                (run_id, protocol_id, json.dumps(coarse_summary)),
            )

    def save_daily_states(self, run_id: str, protocol_id: str, daily_states: list[dict[str, Any]]) -> None:
        with self._lock, self._conn() as conn:
            conn.executemany(
                "INSERT INTO daily_states(run_id, protocol_id, day, state_json) VALUES (?, ?, ?, ?)",
                [(run_id, protocol_id, state["day"], json.dumps(state)) for state in daily_states],
            )

    def save_safety_flags(self, run_id: str, flags: list[dict[str, Any]]) -> None:
        if not flags:
            return
        with self._lock, self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO safety_flags(run_id, protocol_id, day, severity, code, message, disqualifying)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        flag["protocol_id"],
                        flag["day"],
                        flag["severity"],
                        flag["code"],
                        flag["message"],
                        int(bool(flag.get("disqualifying", False))),
                    )
                    for flag in flags
                ],
            )

    def save_score(self, run_id: str, protocol_id: str, score: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO scores(run_id, protocol_id, total_score, component_json) VALUES (?, ?, ?, ?)",
                (run_id, protocol_id, score["total_score"], json.dumps(score)),
            )

    def save_citations(self, run_id: str, protocol_id: str, citations: list[dict[str, str]]) -> None:
        with self._lock, self._conn() as conn:
            conn.executemany(
                "INSERT INTO citations(run_id, protocol_id, source_id, source_url) VALUES (?, ?, ?, ?)",
                [(run_id, protocol_id, citation["source_id"], citation["source_url"]) for citation in citations],
            )

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> int:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO run_events(run_id, event_type, payload_json, timestamp) VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(payload), now),
            )
            return int(cursor.lastrowid)

    def get_events_after(self, run_id: str, last_event_id: int) -> list[dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT id, run_id, event_type, payload_json, timestamp FROM run_events WHERE run_id = ? AND id > ? ORDER BY id ASC",
                (run_id, last_event_id),
            ).fetchall()
        return [
            {
                "event_id": int(row["id"]),
                "run_id": row["run_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def save_run_result(self, run_id: str, result: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_results(run_id, result_json) VALUES (?, ?)",
                (run_id, json.dumps(result)),
            )

    def get_run_result(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT result_json FROM run_results WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["result_json"])

    def get_run_status(self, run_id: str) -> str | None:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return str(row["status"])

    def get_run_error(self, run_id: str) -> str | None:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT error_message FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return row["error_message"]

    def save_chat_log(self, run_id: str, question: str, answer: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_logs(run_id, question, answer, created_at) VALUES (?, ?, ?, ?)",
                (run_id, question, answer, now),
            )


repository = SQLiteRepository(settings.DB_PATH)

