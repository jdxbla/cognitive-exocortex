"""Semantic Search Service - Tier 1 Feature 2

Natural language file search using vector embeddings.
"""
from datetime import datetime
from typing import Optional
import hashlib
import os

from sentence_transformers import SentenceTransformer
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from database import db, vector_db
from config import get_settings
from models import SearchResult

settings = get_settings()


class SemanticSearchService:
    """Semantic file search using embeddings"""

    def __init__(self):
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the embedding model"""
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text"""
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _file_id(self, file_path: str) -> str:
        """Generate unique ID for a file"""
        return hashlib.md5(file_path.encode()).hexdigest()

    async def index_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Index a file for semantic search"""
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()

            # Build searchable text
            searchable_text = f"{file_name} "
            if content:
                # Take first 5000 chars for embedding
                searchable_text += content[:5000]

            # Generate embedding
            embedding = self._generate_embedding(searchable_text)

            # Store in Qdrant
            point_id = self._file_id(file_path)
            payload = {
                "file_path": file_path,
                "file_name": file_name,
                "file_extension": file_ext,
                "indexed_at": datetime.now().isoformat(),
                **(metadata or {}),
            }

            vector_db.client.upsert(
                collection_name=settings.qdrant_collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )

            # Update PostgreSQL file_nodes
            await self._upsert_file_node(file_path, file_name, file_ext, point_id)

            return True
        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
            return False

    async def _upsert_file_node(
        self, file_path: str, file_name: str, file_ext: str, embedding_id: str
    ):
        """Update or insert file node in PostgreSQL"""
        query = """
            INSERT INTO file_nodes (file_path, file_name, file_type, embedding_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (file_path) DO UPDATE SET
                embedding_id = $4,
                updated_at = NOW()
        """
        await db.execute(query, file_path, file_name, file_ext, embedding_id)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        file_types: Optional[list[str]] = None,
        directory: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search files using natural language query"""
        start_time = datetime.now()

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build filter conditions
        filter_conditions = []
        if file_types:
            # Normalize extensions
            normalized_types = [
                f".{t.lower().lstrip('.')}" for t in file_types
            ]
            filter_conditions.append(
                FieldCondition(
                    key="file_extension",
                    match=MatchValue(value=normalized_types[0]),  # Simplified
                )
            )

        search_filter = None
        if filter_conditions:
            search_filter = Filter(must=filter_conditions)

        # Search in Qdrant
        results = vector_db.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_embedding,
            limit=max_results,
            query_filter=search_filter,
        )

        # Convert to SearchResult
        search_results = []
        for hit in results:
            payload = hit.payload or {}
            search_results.append(SearchResult(
                file_path=payload.get("file_path", ""),
                file_name=payload.get("file_name", ""),
                score=hit.score,
                metadata=payload,
            ))

        return search_results

    async def search_similar(
        self, file_path: str, max_results: int = 5
    ) -> list[SearchResult]:
        """Find files similar to a given file"""
        point_id = self._file_id(file_path)

        try:
            # Get the file's embedding from Qdrant
            point = vector_db.client.retrieve(
                collection_name=settings.qdrant_collection,
                ids=[point_id],
            )

            if not point:
                return []

            # Search for similar
            results = vector_db.client.search(
                collection_name=settings.qdrant_collection,
                query_vector=point[0].vector,
                limit=max_results + 1,  # +1 to exclude self
            )

            # Convert and exclude self
            search_results = []
            for hit in results:
                if hit.id == point_id:
                    continue
                payload = hit.payload or {}
                search_results.append(SearchResult(
                    file_path=payload.get("file_path", ""),
                    file_name=payload.get("file_name", ""),
                    score=hit.score,
                    metadata=payload,
                ))

            return search_results[:max_results]
        except Exception as e:
            print(f"Error finding similar files: {e}")
            return []

    async def remove_file(self, file_path: str) -> bool:
        """Remove a file from the search index"""
        try:
            point_id = self._file_id(file_path)
            vector_db.client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=[point_id],
            )

            # Remove from PostgreSQL
            await db.execute(
                "DELETE FROM file_nodes WHERE file_path = $1",
                file_path,
            )
            return True
        except Exception as e:
            print(f"Error removing file from index: {e}")
            return False

    async def get_index_stats(self) -> dict:
        """Get indexing statistics"""
        try:
            collection_info = vector_db.client.get_collection(
                collection_name=settings.qdrant_collection
            )
            return {
                "indexed_files": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
            }
        except Exception:
            return {"indexed_files": 0, "vectors_count": 0}


# Global service instance
search_service = SemanticSearchService()
