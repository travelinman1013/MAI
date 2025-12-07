import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import json
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import PointStruct, Filter, ScoredPoint, Batch
from qdrant_client.models import PointIdsList

from src.core.memory.long_term import LongTermMemory, LM_STUDIO_EMBEDDING_URL, QDRANT_COLLECTION_NAME, EMBEDDING_DIMENSION
from src.core.utils.exceptions import EmbeddingGenerationError
from src.infrastructure.database.models import Memory as DBMemory

# --- Fixtures ---

@pytest.fixture
def mock_db_session():
    """Mocks an SQLAlchemy AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    return session

@pytest.fixture
def mock_qdrant_client():
    """Mocks AsyncQdrantClient."""
    client = AsyncMock()
    client.recreate_collection.return_value = None
    client.upsert.return_value = None
    client.delete_points.return_value = None
    return client

@pytest.fixture
def mock_httpx_async_client():
    """Mocks httpx.AsyncClient for LM Studio calls."""
    with patch("httpx.AsyncClient") as mock:
        yield mock

@pytest.fixture
def long_term_memory(mock_db_session, mock_qdrant_client):
    """Provides an instance of LongTermMemory with mocked dependencies."""
    user_id = uuid.uuid4()
    agent_name = "TestAgent"
    return LongTermMemory(user_id=user_id, agent_name=agent_name, db_session=mock_db_session, qdrant_client=mock_qdrant_client)

# --- Helper for creating a mock DBMemory object ---
def create_mock_db_memory(
    user_id: uuid.UUID,
    agent_name: str,
    content: str,
    memory_type: str = "long_term",
    importance: int = 50,
    qdrant_id: Optional[uuid.UUID] = None,
    created_at: Optional[datetime] = None,
    last_accessed_at: Optional[datetime] = None,
    accessed_count: int = 0,
    id: Optional[uuid.UUID] = None
) -> DBMemory:
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    if last_accessed_at is None:
        last_accessed_at = created_at
    if id is None:
        id = uuid.uuid4()

    mock_memory = AsyncMock(spec=DBMemory)
    mock_memory.id = id
    mock_memory.user_id = user_id
    mock_memory.agent_name = agent_name
    mock_memory.content = content
    mock_memory.memory_type = memory_type
    mock_memory.importance = importance
    mock_memory.qdrant_id = qdrant_id if qdrant_id else uuid.uuid4()
    mock_memory.extra_metadata = "{}" # Renamed from metadata
    mock_memory.created_at = created_at
    mock_memory.last_accessed_at = last_accessed_at
    mock_memory.accessed_count = accessed_count
    return mock_memory


# --- Test Cases ---

@pytest.mark.asyncio
async def test_generate_embedding_success(long_term_memory, mock_httpx_async_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1] * EMBEDDING_DIMENSION}]
    }
    mock_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = mock_response

    text = "test text"
    embedding = await long_term_memory._generate_embedding(text)

    assert isinstance(embedding, list)
    assert len(embedding) == EMBEDDING_DIMENSION
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_called_once_with(
        LM_STUDIO_EMBEDDING_URL,
        headers={"Content-Type": "application/json"},
        json={"input": text, "model": "nomic-ai/nomic-embed-text-v1.5-GGUF"},
        timeout=60
    )

@pytest.mark.asyncio
async def test_generate_embedding_empty_text(long_term_memory):
    with pytest.raises(ValueError, match="Text for embedding generation cannot be empty."):
        await long_term_memory._generate_embedding("")

@pytest.mark.asyncio
async def test_generate_embedding_http_error(long_term_memory, mock_httpx_async_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"detail": "Bad request"}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = mock_response

    with pytest.raises(EmbeddingGenerationError, match="LM Studio embedding API error: 400"):
        await long_term_memory._generate_embedding("error text")

@pytest.mark.asyncio
async def test_generate_embedding_network_error(long_term_memory, mock_httpx_async_client):
    mock_httpx_async_client.return_value.__aenter__.return_value.post.side_effect = httpx.RequestError(
        "Network unreachable", request=MagicMock()
    )

    with pytest.raises(EmbeddingGenerationError, match="Network error while requesting LM Studio embedding"):
        await long_term_memory._generate_embedding("network error")

@pytest.mark.asyncio
async def test_store_success(long_term_memory, mock_db_session, mock_qdrant_client, mock_httpx_async_client):
    # Mock embedding generation
    mock_embedding = [0.2] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": mock_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    # Mock DB session commit and refresh
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', uuid.uuid4()) # Simulate ID generation

    content = "A new memory to store."
    memory_type = "declarative"
    importance = 75
    metadata = {"source": "test_source"}

    stored_memory = await long_term_memory.store(content, memory_type, importance, metadata)

    # Assertions for _generate_embedding
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_called_once()
    assert mock_httpx_async_client.return_value.__aenter__.return_value.post.call_args[1]["json"]["input"] == content

    # Assertions for Qdrant upsert
    mock_qdrant_client.recreate_collection.assert_awaited_once() # Called during _ensure_qdrant_collection_exists
    mock_qdrant_client.upsert.assert_awaited_once()
    upsert_args = mock_qdrant_client.upsert.call_args[1]
    assert upsert_args["collection_name"] == QDRANT_COLLECTION_NAME
    assert len(upsert_args["points"]) == 1
    point = upsert_args["points"][0]
    assert point.vector == mock_embedding
    assert point.payload["user_id"] == str(long_term_memory.user_id)
    assert point.payload["content_preview"] == content[:250]
    assert point.payload["importance"] == importance
    assert point.payload["metadata"] == json.dumps(metadata)
    assert point.id == str(stored_memory.qdrant_id) # Qdrant ID should match the one assigned to DBMemory

    # Assertions for DB operations
    mock_db_session.add.assert_called_once()
    added_db_memory = mock_db_session.add.call_args[0][0]
    assert added_db_memory.user_id == long_term_memory.user_id
    assert added_db_memory.agent_name == long_term_memory.agent_name
    assert added_db_memory.content == content
    assert added_db_memory.memory_type == memory_type
    assert added_db_memory.importance == importance
    assert added_db_memory.qdrant_id == stored_memory.qdrant_id
    assert added_db_memory.metadata == json.dumps(metadata)
    assert isinstance(added_db_memory.last_accessed_at, datetime)
    assert added_db_memory.last_accessed_at.tzinfo == timezone.utc

    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(added_db_memory)

    assert isinstance(stored_memory, DBMemory)
    assert stored_memory.id is not None
    assert stored_memory.qdrant_id is not None

@pytest.mark.asyncio
async def test_store_embedding_generation_failure(long_term_memory, mock_httpx_async_client):
    mock_httpx_async_client.return_value.__aenter__.return_value.post.side_effect = EmbeddingGenerationError("Test failure")

    with pytest.raises(EmbeddingGenerationError, match="Test failure"):
        await long_term_memory.store("content", "type")

@pytest.mark.asyncio
async def test_store_qdrant_upsert_failure(long_term_memory, mock_qdrant_client, mock_httpx_async_client):
    mock_embedding = [0.3] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": mock_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    mock_qdrant_client.upsert.side_effect = Exception("Qdrant error")

    with pytest.raises(Exception, match="Qdrant error"):
        await long_term_memory.store("content", "type")


@pytest.mark.asyncio
async def test_retrieve_success(long_term_memory, mock_db_session, mock_qdrant_client, mock_httpx_async_client):
    # Mock embedding generation for the query
    query_embedding = [0.4] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": query_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    # Mock Qdrant search result
    memory_qdrant_id = uuid.uuid4()
    mock_qdrant_client.search.return_value = [
        ScoredPoint(id=str(memory_qdrant_id), version=1, score=0.9, payload={}, vector=None)
    ]

    # Mock DB session to return a DBMemory object
    mock_db_memory = create_mock_db_memory(
        user_id=long_term_memory.user_id,
        agent_name=long_term_memory.agent_name,
        content="Retrieved content",
        qdrant_id=memory_qdrant_id
    )
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_db_memory]

    query = "test query"
    results = await long_term_memory.retrieve(query, limit=1)

    assert len(results) == 1
    assert results[0].content == "Retrieved content"
    
    # Assertions for _generate_embedding (query)
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_called_once_with(
        LM_STUDIO_EMBEDDING_URL,
        headers={"Content-Type": "application/json"},
        json={"input": query, "model": "nomic-ai/nomic-embed-text-v1.5-GGUF"},
        timeout=60
    )

    # Assertions for Qdrant search
    mock_qdrant_client.search.assert_awaited_once()
    search_args = mock_qdrant_client.search.call_args[1]
    assert search_args["collection_name"] == QDRANT_COLLECTION_NAME
    assert search_args["query_vector"] == query_embedding
    assert search_args["query_filter"].must[0].key == "user_id"
    assert search_args["query_filter"].must[0].match.value == str(long_term_memory.user_id)
    assert search_args["limit"] == 1

    # Assertions for DB retrieval
    mock_db_session.execute.assert_awaited_once()
    assert select(DBMemory).where(
                DBMemory.user_id == long_term_memory.user_id,
                DBMemory.qdrant_id.in_([memory_qdrant_id])
            ).compile().params == mock_db_session.execute.call_args[0][0].compile().params


@pytest.mark.asyncio
async def test_retrieve_empty_query(long_term_memory, mock_qdrant_client, mock_db_session, mock_httpx_async_client):
    results = await long_term_memory.retrieve("", limit=1)
    assert results == []
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_not_awaited()
    mock_qdrant_client.search.assert_not_awaited()
    mock_db_session.execute.assert_not_awaited()

@pytest.mark.asyncio
async def test_retrieve_embedding_generation_failure(long_term_memory, mock_httpx_async_client):
    mock_httpx_async_client.return_value.__aenter__.return_value.post.side_effect = EmbeddingGenerationError("Test failure")
    results = await long_term_memory.retrieve("query", limit=1)
    assert results == []

@pytest.mark.asyncio
async def test_retrieve_qdrant_search_failure(long_term_memory, mock_qdrant_client, mock_httpx_async_client):
    # Mock embedding generation for the query
    query_embedding = [0.4] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": query_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    mock_qdrant_client.search.side_effect = Exception("Qdrant search error")
    results = await long_term_memory.retrieve("query", limit=1)
    assert results == []

@pytest.mark.asyncio
async def test_retrieve_no_qdrant_results(long_term_memory, mock_qdrant_client, mock_httpx_async_client, mock_db_session):
    # Mock embedding generation for the query
    query_embedding = [0.4] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": query_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    mock_qdrant_client.search.return_value = [] # No results from Qdrant
    results = await long_term_memory.retrieve("query", limit=1)
    assert results == []
    mock_db_session.execute.assert_not_awaited() # Should not query DB if Qdrant has no results

@pytest.mark.asyncio
async def test_retrieve_qdrant_results_no_db_match(long_term_memory, mock_qdrant_client, mock_httpx_async_client, mock_db_session):
    # Mock embedding generation for the query
    query_embedding = [0.4] * EMBEDDING_DIMENSION
    embedding_response = MagicMock()
    embedding_response.status_code = 200
    embedding_response.json.return_value = {"data": [{"embedding": query_embedding}]}
    embedding_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = embedding_response

    # Mock Qdrant search result
    memory_qdrant_id = uuid.uuid4()
    mock_qdrant_client.search.return_value = [
        ScoredPoint(id=str(memory_qdrant_id), version=1, score=0.9, payload={}, vector=None)
    ]

    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [] # No DB match for the qdrant_id

    results = await long_term_memory.retrieve("query", limit=1)
    assert results == []
    mock_db_session.execute.assert_awaited_once() # Should still try to query DB


@pytest.mark.asyncio
async def test_get_recent_success(long_term_memory, mock_db_session):
    user_id = long_term_memory.user_id
    
    # Create some mock memories
    now = datetime.now(timezone.utc)
    memories = [
        create_mock_db_memory(user_id, "Agent1", "content 1", created_at=now - timedelta(days=2)),
        create_mock_db_memory(user_id, "Agent1", "content 2", created_at=now - timedelta(days=1)),
        create_mock_db_memory(user_id, "Agent1", "content 3", created_at=now),
    ]
    
    # Mock DB session to return sorted memories
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = sorted(memories, key=lambda m: m.created_at, reverse=True)

    # Test with default limit (5)
    recent_memories = await long_term_memory.get_recent()
    assert len(recent_memories) == 3
    assert recent_memories[0].content == "content 3"
    assert recent_memories[1].content == "content 2"
    assert recent_memories[2].content == "content 1"

    # Test with custom limit
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [memories[2], memories[1]] # Simulate limit 2
    recent_memories_limited = await long_term_memory.get_recent(limit=2)
    assert len(recent_memories_limited) == 2
    assert recent_memories_limited[0].content == "content 3"
    assert recent_memories_limited[1].content == "content 2"
    
    mock_db_session.execute.assert_awaited() # Ensure execute was called


@pytest.mark.asyncio
async def test_get_recent_no_memories(long_term_memory, mock_db_session):
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
    recent_memories = await long_term_memory.get_recent()
    assert len(recent_memories) == 0
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_recent_db_failure(long_term_memory, mock_db_session):
    mock_db_session.execute.side_effect = Exception("DB error")
    recent_memories = await long_term_memory.get_recent()
    assert recent_memories == []
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_access_success(long_term_memory, mock_db_session):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    original_accessed_count = 5
    original_last_accessed = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Mock DB session to return a memory
    mock_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="Test content",
        id=memory_id,
        accessed_count=original_accessed_count,
        last_accessed_at=original_last_accessed
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory
    
    await long_term_memory.update_access(memory_id)
    
    mock_db_session.execute.assert_awaited_once()
    # Check if the memory object was updated
    assert mock_memory.accessed_count == original_accessed_count + 1
    assert mock_memory.last_accessed_at > original_last_accessed # Ensure timestamp was updated
    assert mock_memory.last_accessed_at.tzinfo == timezone.utc # Check timezone awareness
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(mock_memory)


@pytest.mark.asyncio
async def test_update_access_memory_not_found(long_term_memory, mock_db_session):
    memory_id = uuid.uuid4()
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None # Memory not found
    
    await long_term_memory.update_access(memory_id)
    
    mock_db_session.execute.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_access_db_failure(long_term_memory, mock_db_session):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    
    mock_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="Test content",
        id=memory_id
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory
    mock_db_session.commit.side_effect = Exception("DB update error")
    
    await long_term_memory.update_access(memory_id)
    
    mock_db_session.execute.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_not_awaited() # Refresh won't be called if commit fails


@pytest.mark.asyncio
async def test_calculate_importance_success(long_term_memory, mock_db_session, mock_httpx_async_client):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    original_importance = 50
    llm_importance_score = 90
    
    # Mock DB session to return a memory
    mock_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="This is an important memory.",
        id=memory_id,
        importance=original_importance
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory

    # Mock LLM response
    llm_response = MagicMock()
    llm_response.status_code = 200
    llm_response.json.return_value = {
        "choices": [{"message": {"content": str(llm_importance_score)}}]
    }
    llm_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = llm_response

    importance = await long_term_memory.calculate_importance(memory_id)

    assert importance == llm_importance_score
    assert mock_memory.importance == llm_importance_score # Check if DBMemory object was updated
    
    mock_db_session.execute.assert_awaited_once() # For fetching memory
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(mock_memory)
    
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_called_once()
    post_args = mock_httpx_async_client.return_value.__aenter__.return_value.post.call_args[1]
    assert "Rate the importance" in post_args["json"]["messages"][0]["content"]
    assert str(memory_id) not in post_args["json"]["messages"][0]["content"] # Should use content, not ID


@pytest.mark.asyncio
async def test_calculate_importance_memory_not_found(long_term_memory, mock_db_session, mock_httpx_async_client):
    memory_id = uuid.uuid4()
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None # Memory not found
    
    importance = await long_term_memory.calculate_importance(memory_id)
    
    assert importance == 0
    mock_db_session.execute.assert_awaited_once()
    mock_httpx_async_client.return_value.__aenter__.return_value.post.assert_not_awaited() # LLM should not be called


@pytest.mark.asyncio
async def test_calculate_importance_llm_failure(long_term_memory, mock_db_session, mock_httpx_async_client):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    mock_memory = create_mock_db_memory(user_id=user_id, agent_name="Agent1", content="Test content", id=memory_id)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory

    mock_httpx_async_client.return_value.__aenter__.return_value.post.side_effect = httpx.RequestError(
        "LLM network error", request=MagicMock()
    )
    
    importance = await long_term_memory.calculate_importance(memory_id)
    assert importance == 0 # Should default to 0 on LLM failure
    assert mock_memory.importance == 0 # Importance in DB should also be 0
    mock_db_session.commit.assert_awaited_once() # Commit is called even if importance is 0
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_calculate_importance_db_update_failure(long_term_memory, mock_db_session, mock_httpx_async_client):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    mock_memory = create_mock_db_memory(user_id=user_id, agent_name="Agent1", content="Test content", id=memory_id)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory

    llm_response = MagicMock()
    llm_response.status_code = 200
    llm_response.json.return_value = {
        "choices": [{"message": {"content": "70"}}]
    }
    llm_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = llm_response

    mock_db_session.commit.side_effect = Exception("DB commit error")

    importance = await long_term_memory.calculate_importance(memory_id)
    assert importance == 70 # The calculated importance is returned
    assert mock_memory.importance == 70 # The memory object itself is updated
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_not_awaited() # Refresh not called due to commit failure

@pytest.mark.asyncio
async def test_calculate_importance_llm_returns_non_int(long_term_memory, mock_db_session, mock_httpx_async_client):
    user_id = long_term_memory.user_id
    memory_id = uuid.uuid4()
    mock_memory = create_mock_db_memory(user_id=user_id, agent_name="Agent1", content="Test content", id=memory_id)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_memory

    llm_response = MagicMock()
    llm_response.status_code = 200
    llm_response.json.return_value = {
        "choices": [{"message": {"content": "very important"}}]
    }
    llm_response.raise_for_status.return_value = None
    mock_httpx_async_client.return_value.__aenter__.return_value.post.return_value = llm_response

    importance = await long_term_memory.calculate_importance(memory_id)
    assert importance == 0 # Defaults to 0 if LLM returns non-int
    assert mock_memory.importance == 0
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_old_memories_success(long_term_memory, mock_db_session, mock_qdrant_client):
    user_id = long_term_memory.user_id
    
    # Create old and new memories
    now = datetime.now(timezone.utc)
    old_memory_qdrant_id = uuid.uuid4()
    old_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="Old content",
        qdrant_id=old_memory_qdrant_id,
        created_at=now - timedelta(days=10)
    )
    new_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="New content",
        created_at=now - timedelta(days=1)
    )
    
    # Mock DB session to return old memory
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [old_memory]
    
    # Mock Qdrant delete_points success
    mock_qdrant_client.delete_points.return_value = {"status": "ok"}
    
    await long_term_memory.cleanup_old_memories(max_age_days=5)
    
    # Assert DB query for old memories (select statement)
    first_execute_call_args = mock_db_session.execute.call_args_list[0][0][0]
    assert "FROM memories" in str(first_execute_call_args)
    assert "WHERE memories.user_id" in str(first_execute_call_args)
    assert "memories.created_at <" in str(first_execute_call_args)

    # Assert Qdrant delete_points call
    mock_qdrant_client.delete_points.assert_awaited_once_with(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector={"points": [str(old_memory_qdrant_id)]}
    )

    # Assert DB delete call (second execute call)
    second_execute_call_args = mock_db_session.execute.call_args_list[1][0][0]
    assert "DELETE FROM memories" in str(second_execute_call_args)
    assert "WHERE memories.id IN" in str(second_execute_call_args)
    assert mock_db_session.execute.call_count == 2 # Ensure both select and delete were called

    mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_old_memories_no_old_memories(long_term_memory, mock_db_session, mock_qdrant_client):
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [] # No old memories found
    
    await long_term_memory.cleanup_old_memories(max_age_days=5)
    
    mock_db_session.execute.assert_awaited_once()
    mock_qdrant_client.delete_points.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_old_memories_qdrant_failure(long_term_memory, mock_db_session, mock_qdrant_client):
    user_id = long_term_memory.user_id
    old_memory_qdrant_id = uuid.uuid4()
    old_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="Old content",
        qdrant_id=old_memory_qdrant_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=10)
    )
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [old_memory]
    
    mock_qdrant_client.delete_points.side_effect = Exception("Qdrant delete error")
    
    await long_term_memory.cleanup_old_memories(max_age_days=5)
    
    # Assert DB query for old memories (select statement)
    first_execute_call_args = mock_db_session.execute.call_args_list[0][0][0]
    assert "FROM memories" in str(first_execute_call_args)
    assert "WHERE memories.user_id" in str(first_execute_call_args)
    assert "memories.created_at <" in str(first_execute_call_args)

    # Assert Qdrant delete_points call
    mock_qdrant_client.delete_points.assert_awaited_once_with(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector={"points": [str(old_memory_qdrant_id)]}
    )

    # Assert DB delete call (second execute call)
    second_execute_call_args = mock_db_session.execute.call_args_list[1][0][0]
    assert "DELETE FROM memories" in str(second_execute_call_args)
    assert "WHERE memories.id IN" in str(second_execute_call_args)
    assert mock_db_session.execute.call_count == 2 # Ensure both select and delete were called

    # Even if Qdrant delete fails, DB delete should still be attempted for consistency
    mock_db_session.commit.assert_awaited_once() # Commit will be attempted after DB delete 


@pytest.mark.asyncio
async def test_cleanup_old_memories_db_delete_failure(long_term_memory, mock_db_session, mock_qdrant_client):
    user_id = long_term_memory.user_id
    old_memory_qdrant_id = uuid.uuid4()
    old_memory = create_mock_db_memory(
        user_id=user_id,
        agent_name="Agent1",
        content="Old content",
        qdrant_id=old_memory_qdrant_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=10)
    )
    # Mock DB session to return old memory for the initial select
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [old_memory]
    
    mock_qdrant_client.delete_points.return_value = {"status": "ok"}

    # Configure side_effect for the second call to execute (the delete statement)
    # The first call (select statement) will successfully return.
    # The second call (for the delete statement) should raise the exception.
    mock_db_session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[old_memory])))), # First call (select)
        Exception("DB delete error") # Second call (delete)
    ]
    
    await long_term_memory.cleanup_old_memories(max_age_days=5)
    
    assert mock_db_session.execute.call_count == 2 # One for select, one for delete
    mock_qdrant_client.delete_points.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited() # Commit should not happen if DB delete fails


