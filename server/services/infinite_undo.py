"""Infinite Undo Service - Tier 1 Feature 3

Full version control for your entire file system.
Undo anything, anytime - time travel for files.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import hashlib
import os
import shutil

from database import db
from config import get_settings
from models import FileVersion, UndoResponse

settings = get_settings()


class InfiniteUndoService:
    """File versioning and time-travel capabilities"""

    def __init__(self):
        # Local storage for file versions (in production, use SeaweedFS)
        self.storage_path = os.path.expanduser("~/cognitive-exocortex/data/versions")
        os.makedirs(self.storage_path, exist_ok=True)

    def _compute_hash(self, file_path: str) -> Optional[str]:
        """Compute SHA-256 hash of file contents"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def _get_storage_path(self, content_hash: str) -> str:
        """Get storage path for a version (content-addressable)"""
        # Use first 2 chars as directory for better filesystem performance
        subdir = content_hash[:2]
        full_dir = os.path.join(self.storage_path, subdir)
        os.makedirs(full_dir, exist_ok=True)
        return os.path.join(full_dir, content_hash)

    async def record_version(
        self,
        file_path: str,
        operation: str,
        metadata: Optional[dict] = None,
    ) -> Optional[UUID]:
        """Record a new version of a file"""
        try:
            # Compute content hash
            content_hash = self._compute_hash(file_path)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            # Check if this exact version already exists (deduplication)
            existing = await db.fetchval(
                "SELECT id FROM file_versions WHERE file_path = $1 AND content_hash = $2 ORDER BY version_number DESC LIMIT 1",
                file_path,
                content_hash,
            )

            if existing and operation not in ("delete", "rename"):
                # Same content, no need to store again
                return existing

            # Get next version number
            current_version = await db.fetchval(
                "SELECT COALESCE(MAX(version_number), 0) FROM file_versions WHERE file_path = $1",
                file_path,
            )
            next_version = current_version + 1

            # Store the file content (if not already stored)
            storage_location = None
            if content_hash and os.path.exists(file_path):
                storage_location = self._get_storage_path(content_hash)
                if not os.path.exists(storage_location):
                    shutil.copy2(file_path, storage_location)

            # Record in database
            import json
            metadata_json = json.dumps(metadata) if metadata else None

            version_id = await db.fetchval(
                """
                INSERT INTO file_versions
                (file_path, version_number, operation, content_hash, storage_location, file_size, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                file_path,
                next_version,
                operation,
                content_hash,
                storage_location,
                file_size,
                metadata_json,
            )

            return version_id
        except Exception as e:
            print(f"Error recording version: {e}")
            return None

    async def get_history(
        self,
        file_path: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FileVersion], int]:
        """Get version history for a file"""
        # Get total count
        total = await db.fetchval(
            "SELECT COUNT(*) FROM file_versions WHERE file_path = $1",
            file_path,
        )

        # Get versions
        rows = await db.fetch(
            """
            SELECT id, file_path, version_number, operation, content_hash, file_size, timestamp, metadata
            FROM file_versions
            WHERE file_path = $1
            ORDER BY version_number DESC
            LIMIT $2 OFFSET $3
            """,
            file_path,
            limit,
            offset,
        )

        versions = []
        for row in rows:
            import json
            metadata = json.loads(row["metadata"]) if row["metadata"] else None
            versions.append(FileVersion(
                id=row["id"],
                file_path=row["file_path"],
                version_number=row["version_number"],
                operation=row["operation"],
                content_hash=row["content_hash"],
                file_size=row["file_size"],
                timestamp=row["timestamp"],
                metadata=metadata,
            ))

        return versions, total

    async def restore_version(
        self,
        file_path: str,
        target_version: Optional[int] = None,
        target_timestamp: Optional[datetime] = None,
    ) -> UndoResponse:
        """Restore a file to a previous version"""
        try:
            # Find the target version
            if target_version:
                row = await db.fetchrow(
                    "SELECT * FROM file_versions WHERE file_path = $1 AND version_number = $2",
                    file_path,
                    target_version,
                )
            elif target_timestamp:
                row = await db.fetchrow(
                    """
                    SELECT * FROM file_versions
                    WHERE file_path = $1 AND timestamp <= $2
                    ORDER BY timestamp DESC LIMIT 1
                    """,
                    file_path,
                    target_timestamp,
                )
            else:
                # Get previous version (not the latest)
                row = await db.fetchrow(
                    """
                    SELECT * FROM file_versions
                    WHERE file_path = $1
                    ORDER BY version_number DESC
                    OFFSET 1 LIMIT 1
                    """,
                    file_path,
                )

            if not row:
                return UndoResponse(
                    success=False,
                    file_path=file_path,
                    restored_version=0,
                    message="No version found to restore",
                )

            # Restore the file
            storage_location = row["storage_location"]
            if storage_location and os.path.exists(storage_location):
                # Create backup of current state first
                await self.record_version(file_path, "pre_restore")

                # Restore the file
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                shutil.copy2(storage_location, file_path)

                # Record the restore operation
                await self.record_version(file_path, "restore", {
                    "restored_from_version": row["version_number"],
                })

                return UndoResponse(
                    success=True,
                    file_path=file_path,
                    restored_version=row["version_number"],
                    message=f"Restored to version {row['version_number']}",
                )
            else:
                return UndoResponse(
                    success=False,
                    file_path=file_path,
                    restored_version=row["version_number"],
                    message="Version content not found in storage",
                )
        except Exception as e:
            return UndoResponse(
                success=False,
                file_path=file_path,
                restored_version=0,
                message=f"Error restoring: {str(e)}",
            )

    async def time_travel(
        self,
        directory: str,
        target_time: datetime,
    ) -> dict:
        """Show what a directory looked like at a specific time"""
        query = """
            WITH latest_versions AS (
                SELECT DISTINCT ON (file_path)
                    file_path, version_number, operation, file_size, timestamp
                FROM file_versions
                WHERE directory_path = $1 OR file_path LIKE $2
                AND timestamp <= $3
                ORDER BY file_path, timestamp DESC
            )
            SELECT * FROM latest_versions
            WHERE operation != 'delete'
            ORDER BY file_path
        """
        # This is a simplified implementation
        rows = await db.fetch(
            """
            SELECT DISTINCT ON (file_path) file_path, version_number, file_size, timestamp
            FROM file_versions
            WHERE file_path LIKE $1
            AND timestamp <= $2
            ORDER BY file_path, version_number DESC
            """,
            f"{directory}%",
            target_time,
        )

        files = []
        for row in rows:
            files.append({
                "file_path": row["file_path"],
                "version": row["version_number"],
                "size": row["file_size"],
                "timestamp": row["timestamp"].isoformat(),
            })

        return {
            "directory": directory,
            "as_of": target_time.isoformat(),
            "files": files,
            "file_count": len(files),
        }

    async def cleanup_old_versions(
        self,
        days_to_keep: int = 90,
        max_versions_per_file: int = 100,
    ) -> dict:
        """Clean up old versions to save space"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Delete old versions beyond the retention period
        deleted_count = await db.fetchval(
            """
            WITH to_delete AS (
                SELECT id, storage_location
                FROM file_versions
                WHERE timestamp < $1
                AND version_number < (
                    SELECT MAX(version_number) - $2
                    FROM file_versions v2
                    WHERE v2.file_path = file_versions.file_path
                )
            )
            DELETE FROM file_versions
            WHERE id IN (SELECT id FROM to_delete)
            RETURNING id
            """,
            cutoff_date,
            max_versions_per_file,
        )

        # TODO: Also clean up orphaned storage files

        return {
            "deleted_versions": deleted_count or 0,
            "cutoff_date": cutoff_date.isoformat(),
        }

    async def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        total_versions = await db.fetchval("SELECT COUNT(*) FROM file_versions")
        total_size = await db.fetchval("SELECT COALESCE(SUM(file_size), 0) FROM file_versions")
        unique_files = await db.fetchval("SELECT COUNT(DISTINCT file_path) FROM file_versions")

        return {
            "total_versions": total_versions,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
            "unique_files": unique_files,
        }


# Global service instance
undo_service = InfiniteUndoService()
