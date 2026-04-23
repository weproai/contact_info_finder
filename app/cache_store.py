import hashlib
import json
import os
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Optional

from app.config import settings
from app.models import ExtractedContact


class LocalExtractionCache:
    """In-memory plus exact-match SQLite cache for extraction results."""

    def __init__(self):
        self.enabled = settings.local_cache_enabled
        self._lock = threading.Lock()
        self._memory: "OrderedDict[str, Dict]" = OrderedDict()
        self._max_entries = max(1, settings.local_cache_memory_entries)
        self._hits = 0
        self._misses = 0
        self._connection: Optional[sqlite3.Connection] = None

        if not self.enabled:
            return

        db_path = settings.local_cache_db_path
        db_directory = os.path.dirname(db_path)
        if db_directory:
            os.makedirs(db_directory, exist_ok=True)
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_cache (
                cache_key TEXT PRIMARY KEY,
                normalized_text TEXT NOT NULL,
                extraction_json TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL,
                hit_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._connection.commit()

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.split())

    def _cache_key(self, text: str) -> str:
        normalized = self._normalize_text(text)
        payload = f"{settings.cache_normalization_version}:{normalized}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _remember(self, cache_key: str, extraction_data: Dict):
        self._memory[cache_key] = extraction_data
        self._memory.move_to_end(cache_key)
        while len(self._memory) > self._max_entries:
            self._memory.popitem(last=False)

    def get(self, text: str) -> Optional[Dict]:
        if not self.enabled:
            return None

        cache_key = self._cache_key(text)

        with self._lock:
            memory_hit = self._memory.get(cache_key)
            if memory_hit is not None:
                self._hits += 1
                self._memory.move_to_end(cache_key)
                return memory_hit

            if not self._connection:
                self._misses += 1
                return None

            row = self._connection.execute(
                """
                SELECT extraction_json
                FROM extraction_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

            if not row:
                self._misses += 1
                return None

            extraction_data = json.loads(row[0])
            self._connection.execute(
                """
                UPDATE extraction_cache
                SET hit_count = hit_count + 1,
                    last_accessed_at = ?
                WHERE cache_key = ?
                """,
                (datetime.utcnow().isoformat(), cache_key),
            )
            self._connection.commit()
            self._remember(cache_key, extraction_data)
            self._hits += 1
            return extraction_data

    def set(self, text: str, extraction: ExtractedContact, provider: str, model: str) -> bool:
        if not self.enabled:
            return False

        cache_key = self._cache_key(text)
        normalized = self._normalize_text(text)
        extraction_data = extraction.model_dump(mode="json")
        now = datetime.utcnow().isoformat()

        with self._lock:
            self._remember(cache_key, extraction_data)

            if not self._connection:
                return True

            self._connection.execute(
                """
                INSERT INTO extraction_cache (
                    cache_key,
                    normalized_text,
                    extraction_json,
                    provider,
                    model,
                    schema_version,
                    created_at,
                    last_accessed_at,
                    hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    normalized_text = excluded.normalized_text,
                    extraction_json = excluded.extraction_json,
                    provider = excluded.provider,
                    model = excluded.model,
                    schema_version = excluded.schema_version,
                    last_accessed_at = excluded.last_accessed_at
                """,
                (
                    cache_key,
                    normalized,
                    json.dumps(extraction_data),
                    provider,
                    model,
                    settings.cache_normalization_version,
                    now,
                    now,
                ),
            )
            self._connection.commit()
            return True

    def get_stats(self) -> Dict:
        if not self.enabled:
            return {
                "enabled": False,
                "memory_entries": 0,
                "persistent_entries": 0,
                "hits": 0,
                "misses": 0,
            }

        persistent_entries = 0
        if self._connection:
            row = self._connection.execute(
                "SELECT COUNT(*) FROM extraction_cache"
            ).fetchone()
            persistent_entries = int(row[0]) if row else 0

        return {
            "enabled": True,
            "memory_entries": len(self._memory),
            "persistent_entries": persistent_entries,
            "hits": self._hits,
            "misses": self._misses,
        }


local_cache = LocalExtractionCache()
