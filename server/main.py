"""Cognitive Exocortex - FastAPI Server

Main server entry point for all cognitive enhancement features.
"""
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_databases, close_databases, db, vector_db
from models import (
    FileOperation,
    FileOperationResponse,
    PredictionRequest,
    PredictionResponse,
    SearchRequest,
    SearchResponse,
    UndoRequest,
    UndoResponse,
    FileHistoryRequest,
    FileHistoryResponse,
    NLCommandRequest,
    NLCommandResponse,
    HealthResponse,
)
from services import prediction_service, search_service, undo_service, nl_service

settings = get_settings()
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🧠 Starting Cognitive Exocortex Server...")
    await init_databases()
    print("✅ Databases connected")
    yield
    # Shutdown
    print("👋 Shutting down...")
    await close_databases()


app = FastAPI(
    title="Cognitive Exocortex",
    description="AI-powered cognitive enhancement system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for desktop/mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================
# HEALTH & STATUS
# ===========================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check server and database health"""
    postgres_ok = False
    qdrant_ok = False

    try:
        await db.fetchval("SELECT 1")
        postgres_ok = True
    except Exception:
        pass

    try:
        vector_db.client.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if (postgres_ok and qdrant_ok) else "degraded",
        postgres_connected=postgres_ok,
        qdrant_connected=qdrant_ok,
        uptime_seconds=time.time() - start_time,
    )


@app.get("/stats", tags=["Health"])
async def get_stats():
    """Get system statistics"""
    prediction_stats = await prediction_service.get_prediction_stats()
    search_stats = await search_service.get_index_stats()
    undo_stats = await undo_service.get_storage_stats()

    return {
        "predictions": prediction_stats,
        "search": search_stats,
        "undo": undo_stats,
    }


# ===========================================
# PREDICTIVE INTELLIGENCE (Tier 1, Feature 1)
# ===========================================

@app.post("/operations", response_model=FileOperationResponse, tags=["Predictions"])
async def record_operation(operation: FileOperation):
    """Record a file operation for learning patterns"""
    op_id = await prediction_service.record_operation(operation)

    # Get immediate predictions
    predictions = await prediction_service.get_predictions(
        current_directory=operation.directory_path,
        recent_files=[operation.file_path],
        device_id=operation.device_id,
    )

    return FileOperationResponse(
        id=op_id,
        timestamp=datetime.now(),
        predictions=predictions,
    )


@app.post("/predictions", response_model=PredictionResponse, tags=["Predictions"])
async def get_predictions(request: PredictionRequest):
    """Get file predictions based on current context"""
    predictions = await prediction_service.get_predictions(
        current_directory=request.current_directory,
        recent_files=request.recent_files,
        device_id=request.device_id,
        max_results=request.max_results,
    )

    return PredictionResponse(
        predictions=predictions,
        generated_at=datetime.now(),
        expires_at=datetime.now() + timedelta(seconds=settings.prediction_cache_ttl),
    )


# ===========================================
# SEMANTIC SEARCH (Tier 1, Feature 2)
# ===========================================

@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def semantic_search(request: SearchRequest):
    """Search files using natural language"""
    start = time.time()

    results = await search_service.search(
        query=request.query,
        max_results=request.max_results,
        file_types=request.file_types,
        directory=request.directory,
    )

    search_time_ms = int((time.time() - start) * 1000)

    return SearchResponse(
        results=results,
        query=request.query,
        total_results=len(results),
        search_time_ms=search_time_ms,
    )


@app.post("/index", tags=["Search"])
async def index_file(
    file_path: str,
    content: Optional[str] = None,
):
    """Index a file for semantic search"""
    success = await search_service.index_file(file_path, content)
    return {"success": success, "file_path": file_path}


@app.get("/search/similar", tags=["Search"])
async def find_similar(
    file_path: str = Query(...),
    max_results: int = Query(default=5, ge=1, le=50),
):
    """Find files similar to a given file"""
    results = await search_service.search_similar(file_path, max_results)
    return {"file_path": file_path, "similar_files": results}


# ===========================================
# INFINITE UNDO (Tier 1, Feature 3)
# ===========================================

@app.post("/versions", tags=["Undo"])
async def record_version(
    file_path: str,
    operation: str,
):
    """Record a new version of a file"""
    version_id = await undo_service.record_version(file_path, operation)
    return {"version_id": version_id, "file_path": file_path}


@app.get("/versions/{file_path:path}", response_model=FileHistoryResponse, tags=["Undo"])
async def get_file_history(
    file_path: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Get version history for a file"""
    versions, total = await undo_service.get_history(file_path, limit, offset)
    return FileHistoryResponse(
        file_path=file_path,
        versions=versions,
        total_versions=total,
    )


@app.post("/undo", response_model=UndoResponse, tags=["Undo"])
async def undo_file(request: UndoRequest):
    """Restore a file to a previous version"""
    return await undo_service.restore_version(
        file_path=request.file_path,
        target_version=request.target_version,
        target_timestamp=request.target_timestamp,
    )


@app.get("/timetravel", tags=["Undo"])
async def time_travel(
    directory: str = Query(...),
    timestamp: datetime = Query(...),
):
    """Show what a directory looked like at a specific time"""
    return await undo_service.time_travel(directory, timestamp)


# ===========================================
# NATURAL LANGUAGE (Tier 1, Feature 4)
# ===========================================

@app.post("/command", response_model=NLCommandResponse, tags=["Natural Language"])
async def execute_command(request: NLCommandRequest):
    """Execute a natural language command"""
    return await nl_service.process_command(
        command=request.command,
        context=request.context,
        dry_run=request.dry_run,
    )


@app.post("/command/confirm", response_model=NLCommandResponse, tags=["Natural Language"])
async def confirm_command(request: NLCommandRequest):
    """Execute a natural language command with confirmation"""
    return await nl_service.process_command(
        command=request.command,
        context=request.context,
        dry_run=False,
        confirmed=True,
    )


@app.get("/command/suggest", tags=["Natural Language"])
async def suggest_commands(
    partial: str = Query(..., min_length=2),
):
    """Get command suggestions based on history"""
    suggestions = await nl_service.get_command_suggestions(partial)
    return {"suggestions": suggestions}


# ===========================================
# MAIN ENTRY POINT
# ===========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
