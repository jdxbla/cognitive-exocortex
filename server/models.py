"""Pydantic models for API requests and responses"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ===========================================
# FILE OPERATIONS
# ===========================================

class FileOperation(BaseModel):
    """A single file operation event"""
    operation_type: str = Field(..., description="Type: open, save, copy, move, delete, rename")
    file_path: str = Field(..., description="Full path to file")
    file_name: str = Field(..., description="File name only")
    file_extension: Optional[str] = None
    file_size: Optional[int] = None
    directory_path: str = Field(..., description="Parent directory")
    context: Optional[dict[str, Any]] = None
    session_id: Optional[UUID] = None
    device_id: Optional[str] = None


class FileOperationResponse(BaseModel):
    """Response after recording a file operation"""
    id: UUID
    timestamp: datetime
    predictions: list["Prediction"] = []


# ===========================================
# PREDICTIONS
# ===========================================

class Prediction(BaseModel):
    """A file access prediction"""
    file_path: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class PredictionRequest(BaseModel):
    """Request for predictions based on current context"""
    current_directory: Optional[str] = None
    recent_files: Optional[list[str]] = None
    time_of_day: Optional[str] = None
    device_id: Optional[str] = None
    max_results: int = 5


class PredictionResponse(BaseModel):
    """Response with file predictions"""
    predictions: list[Prediction]
    generated_at: datetime
    expires_at: datetime


# ===========================================
# SEMANTIC SEARCH
# ===========================================

class SearchRequest(BaseModel):
    """Semantic search request"""
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=100)
    file_types: Optional[list[str]] = None
    directory: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SearchResult(BaseModel):
    """A single search result"""
    file_path: str
    file_name: str
    score: float
    snippet: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Semantic search response"""
    results: list[SearchResult]
    query: str
    total_results: int
    search_time_ms: int


# ===========================================
# INFINITE UNDO
# ===========================================

class FileVersion(BaseModel):
    """A version of a file"""
    id: UUID
    file_path: str
    version_number: int
    operation: str
    content_hash: Optional[str] = None
    file_size: Optional[int] = None
    timestamp: datetime
    metadata: Optional[dict[str, Any]] = None


class UndoRequest(BaseModel):
    """Request to undo/restore a file"""
    file_path: str
    target_version: Optional[int] = None  # None = latest before current
    target_timestamp: Optional[datetime] = None


class UndoResponse(BaseModel):
    """Response after undo operation"""
    success: bool
    file_path: str
    restored_version: int
    message: str


class FileHistoryRequest(BaseModel):
    """Request file history"""
    file_path: str
    limit: int = 50
    offset: int = 0


class FileHistoryResponse(BaseModel):
    """File version history"""
    file_path: str
    versions: list[FileVersion]
    total_versions: int


# ===========================================
# NATURAL LANGUAGE
# ===========================================

class NLCommandRequest(BaseModel):
    """Natural language command request"""
    command: str = Field(..., min_length=1)
    context: Optional[dict[str, Any]] = None
    dry_run: bool = False  # If True, don't execute, just show what would happen


class ParsedCommand(BaseModel):
    """Parsed intent from natural language"""
    intent: str
    entities: dict[str, Any]
    confidence: float
    requires_confirmation: bool = False
    warning: Optional[str] = None


class NLCommandResponse(BaseModel):
    """Response after NL command processing"""
    original_command: str
    parsed: ParsedCommand
    executed: bool
    result: Optional[str] = None
    error: Optional[str] = None


# ===========================================
# KNOWLEDGE GRAPH
# ===========================================

class FileNode(BaseModel):
    """A file in the knowledge graph"""
    id: UUID
    file_path: str
    file_name: str
    file_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class FileRelationship(BaseModel):
    """Relationship between files"""
    source_file: str
    target_file: str
    relationship_type: str  # co-accessed, similar, references, parent, etc.
    strength: float = 1.0


class GraphQueryRequest(BaseModel):
    """Query the knowledge graph"""
    file_path: str
    relationship_types: Optional[list[str]] = None
    depth: int = 1
    max_results: int = 20


class GraphQueryResponse(BaseModel):
    """Knowledge graph query response"""
    center_node: FileNode
    related_files: list[FileNode]
    relationships: list[FileRelationship]


# ===========================================
# HEALTH & STATUS
# ===========================================

class HealthResponse(BaseModel):
    """Server health status"""
    status: str
    postgres_connected: bool
    qdrant_connected: bool
    uptime_seconds: float
    version: str = "0.1.0"


# Forward references for nested models
FileOperationResponse.model_rebuild()
