"""Database connection and session management"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import get_settings

settings = get_settings()


class Database:
    """PostgreSQL async connection pool"""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            min_size=5,
            max_size=20,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        async with self.pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args):
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.connection() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)


class VectorDB:
    """Qdrant vector database client"""

    def __init__(self):
        self.client: QdrantClient | None = None

    def connect(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection not in collection_names:
            self.client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )

    def disconnect(self):
        if self.client:
            self.client.close()


# Global instances
db = Database()
vector_db = VectorDB()


async def init_databases():
    """Initialize all database connections"""
    await db.connect()
    vector_db.connect()


async def close_databases():
    """Close all database connections"""
    await db.disconnect()
    vector_db.disconnect()
