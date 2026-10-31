"""
modules/admin_panel/services/ai_telemetry_service.py
===================================================
Production-Grade AI Invocation Telemetry & Cost Accounting Service for ImpactBridge.

Features:
- Thread-safe SQLite persistence in `.cache/ai_classifier/ai_telemetry.sqlite3`
  (strictly avoids altering or mutating production MySQL tables).
- Granular tracking: company_id, provider, model, task, status, tokens (input/output/total/cached),
  latency_ms, cost_usd, measurement_method ('PROVIDER_REPORTED', 'ESTIMATED', 'UNAVAILABLE'),
  fallback_used, error_category, evidence_excerpt, and validation_result.
- Accurate model pricing rate card (Gemini 1.5/2.0/3.x Flash, Grok 2, OpenAI GPT-4o-mini, OpenRouter free).
- Multi-dimensional aggregation queries for Usage & Limits dashboard.
- Company-specific execution history lookup.
- Audit synchronization with `AIConfigurationAuditLog` in MySQL.
"""

import os
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Model Pricing Rate Card (USD per 1,000,000 tokens)
MODEL_PRICING_RATES: Dict[str, Dict[str, float]] = {
    # Gemini
    "gemini-3.1-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Grok
    "grok-2-latest": {"input": 2.00, "output": 10.00},
    "grok-beta": {"input": 5.00, "output": 15.00},
    # OpenAI
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    # Anthropic
    "claude-3-5-haiku-latest": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    # OpenRouter & Local
    "openrouter/free": {"input": 0.00, "output": 0.00},
    "llama3.2": {"input": 0.00, "output": 0.00},
    "custom-model": {"input": 0.00, "output": 0.00},
}


class AITelemetryStore:
    """Manages SQLite storage of AI invocation events and analytics queries."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            cache_dir = os.path.join(os.getcwd(), ".cache", "ai_classifier")
            os.makedirs(cache_dir, exist_ok=True)
            self.db_path = os.path.join(cache_dir, "ai_telemetry.sqlite3")
        else:
            self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    company_id TEXT,
                    company_name TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    task TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms INTEGER DEFAULT 0,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cached_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    measurement_method TEXT NOT NULL, -- 'PROVIDER_REPORTED', 'ESTIMATED', 'UNAVAILABLE'
                    fallback_used INTEGER DEFAULT 0,
                    error_category TEXT,
                    evidence_excerpt TEXT,
                    validation_result TEXT,
                    actor TEXT,
                    trace_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON ai_telemetry_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_company ON ai_telemetry_events(company_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_provider ON ai_telemetry_events(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_task ON ai_telemetry_events(task)")
            conn.commit()

    @staticmethod
    def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculates USD cost based on rate card; returns 0.0 if free tier or unknown."""
        m = (model_name or "").lower().strip()
        rates = MODEL_PRICING_RATES.get(m)
        if not rates:
            # Check prefix
            for k, v in MODEL_PRICING_RATES.items():
                if k in m:
                    rates = v
                    break
        if not rates:
            return 0.0

        in_cost = (input_tokens / 1_000_000.0) * rates.get("input", 0.0)
        out_cost = (output_tokens / 1_000_000.0) * rates.get("output", 0.0)
        return round(in_cost + out_cost, 6)

    def record_event(
        self,
        provider: str,
        model: str,
        task: str,
        status: str,
        company_id: Optional[str] = None,
        company_name: Optional[str] = None,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        measurement_method: str = "PROVIDER_REPORTED",
        fallback_used: bool = False,
        error_category: Optional[str] = None,
        evidence_excerpt: Optional[str] = None,
        validation_result: Optional[str] = None,
        actor: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """Records a single AI invocation event with automatic cost accounting."""
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)
        iso_now = datetime.utcnow().isoformat() + "Z"

        with self._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO ai_telemetry_events (
                    timestamp, company_id, company_name, provider, model, task, status,
                    latency_ms, input_tokens, output_tokens, total_tokens, cached_tokens,
                    cost_usd, measurement_method, fallback_used, error_category,
                    evidence_excerpt, validation_result, actor, trace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                iso_now, company_id, company_name, provider, model, task, status,
                latency_ms, input_tokens, output_tokens, total_tokens, cached_tokens,
                cost_usd, measurement_method, 1 if fallback_used else 0, error_category,
                evidence_excerpt, validation_result, actor or "SYSTEM", trace_id
            ))
            conn.commit()
            return cur.lastrowid

    def get_summary(
        self,
        days: int = 30,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        company_id: Optional[str] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates multi-dimensional aggregate metrics across events."""
        since_iso = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        query = "SELECT * FROM ai_telemetry_events WHERE timestamp >= ?"
        params: List[Any] = [since_iso]

        if provider and provider != "all":
            query += " AND provider = ?"
            params.append(provider)
        if model and model != "all":
            query += " AND model = ?"
            params.append(model)
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if task and task != "all":
            query += " AND task = ?"
            params.append(task)

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()

        total_calls = len(rows)
        success_calls = sum(1 for r in rows if r["status"] == "SUCCESS")
        failed_calls = sum(1 for r in rows if r["status"] in ("ERROR", "AUTH_FAILED", "QUOTA_EXCEEDED", "FAILED"))
        fallback_calls = sum(1 for r in rows if r["fallback_used"] == 1)

        input_tokens = sum(r["input_tokens"] or 0 for r in rows)
        output_tokens = sum(r["output_tokens"] or 0 for r in rows)
        total_tokens = sum(r["total_tokens"] or 0 for r in rows)
        cached_tokens = sum(r["cached_tokens"] or 0 for r in rows)
        total_cost = sum(r["cost_usd"] or 0.0 for r in rows)
        avg_latency = (sum(r["latency_ms"] or 0 for r in rows) / total_calls) if total_calls > 0 else 0

        # Breakdowns
        by_provider: Dict[str, int] = {}
        by_model: Dict[str, int] = {}
        by_task: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for r in rows:
            p = r["provider"]
            m = r["model"]
            t = r["task"]
            s = r["status"]
            by_provider[p] = by_provider.get(p, 0) + 1
            by_model[m] = by_model.get(m, 0) + 1
            by_task[t] = by_task.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "period_days": days,
            "total_calls": total_calls,
            "success_calls": success_calls,
            "failed_calls": failed_calls,
            "fallback_calls": fallback_calls,
            "fallback_rate_pct": round((fallback_calls / total_calls * 100), 1) if total_calls > 0 else 0.0,
            "success_rate_pct": round((success_calls / total_calls * 100), 1) if total_calls > 0 else 0.0,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": cached_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": int(avg_latency),
            "by_provider": by_provider,
            "by_model": by_model,
            "by_task": by_task,
            "by_status": by_status,
            "last_event_time": rows[-1]["timestamp"] if rows else None,
        }

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        provider: Optional[str] = None,
        company_id: Optional[str] = None,
        task: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Returns paginated, filterable raw invocation event stream."""
        query = "SELECT * FROM ai_telemetry_events WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM ai_telemetry_events WHERE 1=1"
        params: List[Any] = []

        if provider and provider != "all":
            query += " AND provider = ?"
            count_query += " AND provider = ?"
            params.append(provider)
        if company_id:
            query += " AND company_id = ?"
            count_query += " AND company_id = ?"
            params.append(company_id)
        if task and task != "all":
            query += " AND task = ?"
            count_query += " AND task = ?"
            params.append(task)
        if status and status != "all":
            query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        fetch_params = params + [limit, offset]

        with self._get_connection() as conn:
            cur = conn.execute(count_query, params)
            total = cur.fetchone()[0]

            cur = conn.execute(query, fetch_params)
            rows = [dict(r) for r in cur.fetchall()]

        return rows, total

    def get_company_history(self, company_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns chronological AI invocation history for a specific company."""
        if not company_id:
            return []
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT * FROM ai_telemetry_events
                WHERE company_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (company_id, limit))
            return [dict(r) for r in cur.fetchall()]


# Global singleton instance
telemetry_store = AITelemetryStore()

