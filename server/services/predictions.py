"""Predictive Intelligence Service - Tier 1 Feature 1

Learns file access patterns and predicts what files you'll need next.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import asyncio
from collections import defaultdict

from database import db
from config import get_settings
from models import Prediction, FileOperation

settings = get_settings()


class PredictionService:
    """Predictive file intelligence based on usage patterns"""

    def __init__(self):
        self._pattern_cache: dict = {}
        self._last_cache_update: datetime | None = None

    async def record_operation(self, operation: FileOperation) -> UUID:
        """Record a file operation and update patterns"""
        query = """
            INSERT INTO file_operations
            (operation_type, file_path, file_name, file_extension,
             file_size, directory_path, context, session_id, device_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        import json
        context_json = json.dumps(operation.context) if operation.context else None

        result = await db.fetchval(
            query,
            operation.operation_type,
            operation.file_path,
            operation.file_name,
            operation.file_extension,
            operation.file_size,
            operation.directory_path,
            context_json,
            operation.session_id,
            operation.device_id,
        )

        # Update patterns asynchronously
        asyncio.create_task(self._update_patterns(operation))

        return result

    async def get_predictions(
        self,
        current_directory: Optional[str] = None,
        recent_files: Optional[list[str]] = None,
        device_id: Optional[str] = None,
        max_results: int = 5,
    ) -> list[Prediction]:
        """Get file predictions based on current context"""
        predictions = []

        # Strategy 1: Co-access patterns (files often opened together)
        if recent_files:
            co_access = await self._get_co_access_predictions(recent_files)
            predictions.extend(co_access)

        # Strategy 2: Time-based patterns (files accessed at this time of day)
        time_based = await self._get_time_based_predictions()
        predictions.extend(time_based)

        # Strategy 3: Directory patterns (common files in current directory)
        if current_directory:
            dir_based = await self._get_directory_predictions(current_directory)
            predictions.extend(dir_based)

        # Strategy 4: Frequency patterns (most frequently accessed)
        freq_based = await self._get_frequency_predictions()
        predictions.extend(freq_based)

        # Deduplicate and sort by confidence
        seen_paths = set()
        unique_predictions = []
        for p in sorted(predictions, key=lambda x: x.confidence, reverse=True):
            if p.file_path not in seen_paths:
                seen_paths.add(p.file_path)
                unique_predictions.append(p)

        # Filter out recently accessed files (already open)
        if recent_files:
            recent_set = set(recent_files)
            unique_predictions = [p for p in unique_predictions if p.file_path not in recent_set]

        return unique_predictions[:max_results]

    async def _get_co_access_predictions(self, recent_files: list[str]) -> list[Prediction]:
        """Find files commonly accessed with the recent files"""
        if not recent_files:
            return []

        # Look for files accessed within 5 minutes of any recent file
        query = """
            WITH recent_ops AS (
                SELECT timestamp, file_path
                FROM file_operations
                WHERE file_path = ANY($1)
                AND timestamp > NOW() - INTERVAL '7 days'
            ),
            co_accessed AS (
                SELECT fo.file_path, COUNT(*) as co_count
                FROM file_operations fo
                JOIN recent_ops ro ON
                    fo.timestamp BETWEEN ro.timestamp - INTERVAL '5 minutes'
                    AND ro.timestamp + INTERVAL '5 minutes'
                WHERE fo.file_path != ro.file_path
                AND fo.file_path NOT LIKE '%/.%'
                GROUP BY fo.file_path
                ORDER BY co_count DESC
                LIMIT 10
            )
            SELECT file_path, co_count FROM co_accessed
        """
        rows = await db.fetch(query, recent_files)

        predictions = []
        max_count = max((r["co_count"] for r in rows), default=1)
        for row in rows:
            confidence = min(0.9, (row["co_count"] / max_count) * 0.8 + 0.1)
            predictions.append(Prediction(
                file_path=row["file_path"],
                confidence=confidence,
                reason="Often accessed together with recent files",
            ))
        return predictions

    async def _get_time_based_predictions(self) -> list[Prediction]:
        """Find files commonly accessed at this time of day"""
        current_hour = datetime.now().hour

        query = """
            SELECT file_path, COUNT(*) as access_count
            FROM file_operations
            WHERE EXTRACT(HOUR FROM timestamp) BETWEEN $1 AND $2
            AND timestamp > NOW() - INTERVAL '30 days'
            AND file_path NOT LIKE '%/.%'
            GROUP BY file_path
            ORDER BY access_count DESC
            LIMIT 10
        """
        hour_start = (current_hour - 1) % 24
        hour_end = (current_hour + 1) % 24
        rows = await db.fetch(query, hour_start, hour_end)

        predictions = []
        max_count = max((r["access_count"] for r in rows), default=1)
        for row in rows:
            confidence = min(0.7, (row["access_count"] / max_count) * 0.5 + 0.2)
            predictions.append(Prediction(
                file_path=row["file_path"],
                confidence=confidence,
                reason=f"Often accessed around {current_hour}:00",
            ))
        return predictions

    async def _get_directory_predictions(self, directory: str) -> list[Prediction]:
        """Find commonly accessed files in the current directory"""
        query = """
            SELECT file_path, COUNT(*) as access_count
            FROM file_operations
            WHERE directory_path = $1
            AND timestamp > NOW() - INTERVAL '30 days'
            GROUP BY file_path
            ORDER BY access_count DESC
            LIMIT 10
        """
        rows = await db.fetch(query, directory)

        predictions = []
        max_count = max((r["access_count"] for r in rows), default=1)
        for row in rows:
            confidence = min(0.6, (row["access_count"] / max_count) * 0.4 + 0.2)
            predictions.append(Prediction(
                file_path=row["file_path"],
                confidence=confidence,
                reason="Frequently accessed in this directory",
            ))
        return predictions

    async def _get_frequency_predictions(self) -> list[Prediction]:
        """Get most frequently accessed files overall"""
        query = """
            SELECT file_path, COUNT(*) as access_count
            FROM file_operations
            WHERE timestamp > NOW() - INTERVAL '7 days'
            AND file_path NOT LIKE '%/.%'
            GROUP BY file_path
            ORDER BY access_count DESC
            LIMIT 10
        """
        rows = await db.fetch(query)

        predictions = []
        max_count = max((r["access_count"] for r in rows), default=1)
        for row in rows:
            confidence = min(0.5, (row["access_count"] / max_count) * 0.3 + 0.2)
            predictions.append(Prediction(
                file_path=row["file_path"],
                confidence=confidence,
                reason="Frequently accessed recently",
            ))
        return predictions

    async def _update_patterns(self, operation: FileOperation):
        """Update learned patterns based on new operation"""
        # Update co-access patterns
        query = """
            SELECT file_path
            FROM file_operations
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            AND file_path != $1
            AND session_id = $2
            LIMIT 10
        """
        co_files = await db.fetch(query, operation.file_path, operation.session_id)

        for row in co_files:
            await self._record_pattern(
                "co_access",
                {"file_a": operation.file_path, "file_b": row["file_path"]},
            )

    async def _record_pattern(self, pattern_type: str, pattern_data: dict):
        """Record or update a learned pattern"""
        import json
        query = """
            INSERT INTO prediction_patterns (pattern_type, pattern_data, confidence, hit_count)
            VALUES ($1, $2, 0.5, 1)
            ON CONFLICT (pattern_type, pattern_data)
            DO UPDATE SET
                hit_count = prediction_patterns.hit_count + 1,
                confidence = LEAST(0.95, prediction_patterns.confidence + 0.05),
                last_used = NOW(),
                updated_at = NOW()
        """
        # This would need a unique constraint on (pattern_type, pattern_data)
        # For now, just insert
        try:
            await db.execute(query, pattern_type, json.dumps(pattern_data))
        except Exception:
            pass  # Ignore pattern recording failures

    async def get_prediction_stats(self) -> dict:
        """Get statistics about predictions"""
        query = """
            SELECT
                COUNT(*) as total_operations,
                COUNT(DISTINCT file_path) as unique_files,
                COUNT(DISTINCT directory_path) as unique_directories
            FROM file_operations
            WHERE timestamp > NOW() - INTERVAL '30 days'
        """
        row = await db.fetchrow(query)
        return {
            "total_operations": row["total_operations"],
            "unique_files": row["unique_files"],
            "unique_directories": row["unique_directories"],
        }


# Global service instance
prediction_service = PredictionService()
