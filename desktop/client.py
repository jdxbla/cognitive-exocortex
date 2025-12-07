"""Cognitive Exocortex Desktop Client

Connects to the server and provides local file monitoring.
"""
import os
import sys
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

import httpx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


@dataclass
class ExocortexConfig:
    """Client configuration"""
    server_url: str = "http://100.91.15.124:8000"  # Tailscale IP
    watch_directories: list[str] = None
    ignored_patterns: list[str] = None
    device_id: str = None

    def __post_init__(self):
        if self.watch_directories is None:
            self.watch_directories = [
                str(Path.home() / "Documents"),
                str(Path.home() / "Desktop"),
            ]
        if self.ignored_patterns is None:
            self.ignored_patterns = [
                "*.tmp", "*.temp", "~*", ".git/*", "__pycache__/*",
                "*.pyc", ".DS_Store", "Thumbs.db", "*.log",
            ]
        if self.device_id is None:
            self.device_id = hashlib.md5(
                f"{os.name}-{os.getlogin()}".encode()
            ).hexdigest()[:12]


class ExocortexClient:
    """Main client for Cognitive Exocortex"""

    def __init__(self, config: Optional[ExocortexConfig] = None):
        self.config = config or ExocortexConfig()
        self.http = httpx.Client(base_url=self.config.server_url, timeout=30.0)
        self.session_id = None
        self._observers: list[Observer] = []

    def connect(self) -> bool:
        """Test connection to server"""
        try:
            response = self.http.get("/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected to Cognitive Exocortex")
                print(f"   Server status: {data['status']}")
                print(f"   PostgreSQL: {'✓' if data['postgres_connected'] else '✗'}")
                print(f"   Qdrant: {'✓' if data['qdrant_connected'] else '✗'}")
                return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
        return False

    def record_operation(
        self,
        operation_type: str,
        file_path: str,
        context: Optional[dict] = None,
    ) -> dict:
        """Record a file operation"""
        file_path = str(Path(file_path).resolve())
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        dir_path = os.path.dirname(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        payload = {
            "operation_type": operation_type,
            "file_path": file_path,
            "file_name": file_name,
            "file_extension": file_ext,
            "file_size": file_size,
            "directory_path": dir_path,
            "context": context,
            "device_id": self.config.device_id,
        }

        try:
            response = self.http.post("/operations", json=payload)
            return response.json()
        except Exception as e:
            print(f"Error recording operation: {e}")
            return {}

    def get_predictions(
        self,
        current_directory: Optional[str] = None,
        recent_files: Optional[list[str]] = None,
        max_results: int = 5,
    ) -> list[dict]:
        """Get file predictions"""
        payload = {
            "current_directory": current_directory,
            "recent_files": recent_files,
            "device_id": self.config.device_id,
            "max_results": max_results,
        }

        try:
            response = self.http.post("/predictions", json=payload)
            data = response.json()
            return data.get("predictions", [])
        except Exception as e:
            print(f"Error getting predictions: {e}")
            return []

    def search(
        self,
        query: str,
        max_results: int = 10,
        file_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search files semantically"""
        payload = {
            "query": query,
            "max_results": max_results,
            "file_types": file_types,
        }

        try:
            response = self.http.post("/search", json=payload)
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def index_file(self, file_path: str) -> bool:
        """Index a file for search"""
        try:
            # Read file content for indexing (text files only)
            content = None
            if os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                text_extensions = {
                    ".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
                    ".h", ".css", ".html", ".json", ".yaml", ".yml", ".xml",
                    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
                }
                if ext in text_extensions:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()[:10000]  # First 10KB
                    except Exception:
                        pass

            response = self.http.post(
                "/index",
                params={"file_path": file_path},
                json={"content": content},
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error indexing file: {e}")
            return False

    def get_file_history(
        self, file_path: str, limit: int = 50
    ) -> list[dict]:
        """Get version history for a file"""
        try:
            response = self.http.get(
                f"/versions/{file_path}",
                params={"limit": limit},
            )
            data = response.json()
            return data.get("versions", [])
        except Exception as e:
            print(f"Error getting history: {e}")
            return []

    def undo_file(
        self,
        file_path: str,
        version: Optional[int] = None,
    ) -> dict:
        """Restore a file to a previous version"""
        payload = {
            "file_path": file_path,
            "target_version": version,
        }

        try:
            response = self.http.post("/undo", json=payload)
            return response.json()
        except Exception as e:
            print(f"Error undoing: {e}")
            return {"success": False, "message": str(e)}

    def command(
        self,
        command: str,
        dry_run: bool = True,
    ) -> dict:
        """Execute a natural language command"""
        payload = {
            "command": command,
            "dry_run": dry_run,
            "context": {
                "cwd": os.getcwd(),
                "device_id": self.config.device_id,
            },
        }

        try:
            response = self.http.post("/command", json=payload)
            return response.json()
        except Exception as e:
            print(f"Error executing command: {e}")
            return {"error": str(e)}

    def start_watching(self):
        """Start watching directories for file changes"""
        handler = ExocortexFileHandler(self)

        for directory in self.config.watch_directories:
            if os.path.exists(directory):
                observer = Observer()
                observer.schedule(handler, directory, recursive=True)
                observer.start()
                self._observers.append(observer)
                print(f"👁 Watching: {directory}")

    def stop_watching(self):
        """Stop watching directories"""
        for observer in self._observers:
            observer.stop()
            observer.join()
        self._observers.clear()

    def close(self):
        """Clean up resources"""
        self.stop_watching()
        self.http.close()


class ExocortexFileHandler(FileSystemEventHandler):
    """Handles file system events"""

    def __init__(self, client: ExocortexClient):
        self.client = client
        self._last_events: dict[str, float] = {}  # Debouncing

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        from fnmatch import fnmatch
        for pattern in self.client.config.ignored_patterns:
            if fnmatch(path, pattern) or fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def _debounce(self, path: str, timeout: float = 1.0) -> bool:
        """Debounce rapid events on same file"""
        now = time.time()
        if path in self._last_events:
            if now - self._last_events[path] < timeout:
                return True
        self._last_events[path] = now
        return False

    def on_created(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        if self._debounce(event.src_path):
            return
        self.client.record_operation("create", event.src_path)
        self.client.index_file(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        if self._debounce(event.src_path):
            return
        self.client.record_operation("modify", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self.client.record_operation("delete", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path) or self._should_ignore(event.dest_path):
            return
        self.client.record_operation("move", event.dest_path, {
            "source": event.src_path,
        })


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Cognitive Exocortex Client")
    parser.add_argument("--server", default="http://100.91.15.124:8000",
                        help="Server URL")
    parser.add_argument("--watch", nargs="*", help="Directories to watch")
    parser.add_argument("--command", "-c", help="Execute a command")
    parser.add_argument("--search", "-s", help="Search for files")
    parser.add_argument("--predict", "-p", help="Get predictions for directory")

    args = parser.parse_args()

    config = ExocortexConfig(server_url=args.server)
    if args.watch:
        config.watch_directories = args.watch

    client = ExocortexClient(config)

    if not client.connect():
        sys.exit(1)

    if args.command:
        result = client.command(args.command)
        print(json.dumps(result, indent=2))
    elif args.search:
        results = client.search(args.search)
        for r in results:
            print(f"  {r['score']:.2f}  {r['file_path']}")
    elif args.predict:
        predictions = client.get_predictions(current_directory=args.predict)
        print("\n🔮 Predictions:")
        for p in predictions:
            print(f"  {p['confidence']:.0%}  {p['file_path']}")
            if p.get("reason"):
                print(f"       └─ {p['reason']}")
    else:
        # Start watching
        print("\n🧠 Cognitive Exocortex running...")
        print("   Watching for file changes. Press Ctrl+C to stop.\n")
        client.start_watching()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
            client.close()


if __name__ == "__main__":
    main()
