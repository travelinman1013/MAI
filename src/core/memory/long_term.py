import httpx
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter

from src.core.utils.logging import logger
from src.core.utils.exceptions import EmbeddingGenerationError
from src.infrastructure.database.models import Memory as DBMemory
from src.infrastructure.vector_store.qdrant_client import get_qdrant_client
from src.core.memory.models import Message # Re-using Message model for long-term memory content

LM_STUDIO_EMBEDDING_URL = "http://localhost:1234/v1/embeddings"
EMBEDDING_DIMENSION = 1536 # Assuming OpenAI compatible dimension
QDRANT_COLLECTION_NAME = "mai_memories"

class LongTermMemory:
    def __init__(
        self,
        user_id: UUID,
        agent_name: str,
        db_session: AsyncSession,
        qdrant_client: AsyncQdrantClient
    ):
        self.user_id = user_id
        self.agent_name = agent_name
        self.db_session = db_session
        self.qdrant_client = qdrant_client
        self._ensure_qdrant_collection_exists_task = None

    async def _ensure_qdrant_collection_exists(self):
        # This will be called once per instance to ensure the collection exists
        # Can be made more robust with retry mechanisms
        if not self._ensure_qdrant_collection_exists_task:
            self._ensure_qdrant_collection_exists_task = self.qdrant_client.recreate_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
            )
        await self._ensure_qdrant_collection_exists_task


    async def _generate_embedding(self, text: str) -> List[float]:
        if not text:
            raise ValueError("Text for embedding generation cannot be empty.")

        headers = {"Content-Type": "application/json"}
        payload = {
            "input": text,
            "model": "nomic-ai/nomic-embed-text-v1.5-GGUF" # Placeholder model, can be configured
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(LM_STUDIO_EMBEDDING_URL, headers=headers, json=payload, timeout=60)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            response_data = response.json()
            if not response_data or "data" not in response_data or not response_data["data"]:
                raise EmbeddingGenerationError("LM Studio embedding response missing 'data' field.")
            
            # LM Studio returns a list of embeddings, typically one for each input string
            # We expect a single embedding for a single input text
            embedding = response_data["data"][0]["embedding"]
            if not isinstance(embedding, list) or not all(isinstance(x, float) for x in embedding):
                raise EmbeddingGenerationError("LM Studio embedding response 'embedding' field is not a list of floats.")
            
            if len(embedding) != EMBEDDING_DIMENSION:
                logger.warning(f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}. This might cause issues with Qdrant.")
            
            logger.debug(f"Generated embedding for text snippet (first 30 chars): '{text[:30]}...'")
            return embedding

        except httpx.RequestError as exc:
            raise EmbeddingGenerationError(f"Network error while requesting LM Studio embedding: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"LM Studio embedding API returned an error: {exc.response.status_code} - {exc.response.text}")
            raise EmbeddingGenerationError(f"LM Studio embedding API error: {exc.response.status_code}")
        except json.JSONDecodeError as exc:
            raise EmbeddingGenerationError(f"Failed to decode LM Studio embedding response: {exc}")
        except Exception as exc:
            logger.error(f"An unexpected error occurred during embedding generation: {exc}")
            raise EmbeddingGenerationError(f"Unexpected error during embedding generation: {exc}")

    async def store(self, content: str, memory_type: str, importance: int = 0, metadata: Optional[Dict] = None) -> DBMemory:
        logger.info(f"Storing long-term memory for user {self.user_id}: '{content[:50]}...'")

        if not content:
            raise ValueError("Content for memory cannot be empty.")
        if not memory_type:
            raise ValueError("Memory type cannot be empty.")

        await self._ensure_qdrant_collection_exists()

        try:
            embedding = await self._generate_embedding(content)
        except EmbeddingGenerationError as e:
            logger.error(f"Failed to generate embedding for memory: {e}")
            raise

        # Generate a UUID for Qdrant point_id
        qdrant_point_id = uuid.uuid4()
        
        try:
            # Store embedding in Qdrant
            await self.qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                wait=True,
                points=[
                    PointStruct(
                        id=str(qdrant_point_id),
                        vector=embedding,
                        payload={
                            "user_id": str(self.user_id),
                            "agent_name": self.agent_name,
                            "memory_type": memory_type,
                            "content_preview": content[:250], # Store a preview in Qdrant payload
                            "importance": importance,
                            "metadata": json.dumps(metadata) if metadata else None
                        }
                    )
                ]
            )
            logger.debug(f"Memory embedding stored in Qdrant with ID: {qdrant_point_id}")
        except Exception as e:
            logger.error(f"Failed to store embedding in Qdrant for user {self.user_id}: {e}")
            raise

        # Store memory metadata in PostgreSQL
        db_memory = DBMemory(
            user_id=self.user_id,
            agent_name=self.agent_name,
            content=content,
            memory_type=memory_type,
            importance=importance,
            qdrant_id=qdrant_point_id,
            metadata=json.dumps(metadata) if metadata else None,
            last_accessed_at=datetime.now(timezone.utc) # Set initial access time
        )
        self.db_session.add(db_memory)
        await self.db_session.commit()
        await self.db_session.refresh(db_memory)
        logger.info(f"Memory metadata stored in PostgreSQL with ID: {db_memory.id}")

        return db_memory

    async def retrieve(self, query: str, limit: int = 5) -> List[DBMemory]:
        logger.info(f"Retrieving long-term memories for user {self.user_id} with query: '{query[:50]}...'")

        if not query:
            return []

        await self._ensure_qdrant_collection_exists()

        try:
            query_embedding = await self._generate_embedding(query)
        except EmbeddingGenerationError as e:
            logger.error(f"Failed to generate embedding for query: {e}")
            return []

        try:
            # Search in Qdrant
            search_result = await self.qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        {
                            "key": "user_id",
                            "match": {
                                "value": str(self.user_id)
                            }
                        }
                    ]
                ),
                limit=limit
            )
            logger.debug(f"Qdrant search returned {len(search_result)} results.")
        except Exception as e:
            logger.error(f"Failed to search Qdrant for user {self.user_id}: {e}")
            return []

        # Extract qdrant_ids from the search results
        qdrant_ids = [UUID(hit.id) for hit in search_result]
        if not qdrant_ids:
            return []

        # Retrieve corresponding memories from PostgreSQL
        try:
            stmt = select(DBMemory).where(
                DBMemory.user_id == self.user_id,
                DBMemory.qdrant_id.in_(qdrant_ids)
            ).order_by(
                # Order by Qdrant score - this requires getting scores and matching them
                # For simplicity, we'll order by creation date for now, or match order from qdrant_ids
                # A more robust solution would join or re-order based on Qdrant scores
                DBMemory.created_at.desc()
            )
            result = await self.db_session.execute(stmt)
            memories = result.scalars().all()
            logger.debug(f"Retrieved {len(memories)} memories from PostgreSQL.")
            return memories
        except Exception as e:
            logger.error(f"Failed to retrieve memories from PostgreSQL for user {self.user_id}: {e}")
            return []

    async def get_recent(self, limit: int = 5) -> List[DBMemory]:
        logger.info(f"Getting recent long-term memories for user {self.user_id}")
        try:
            stmt = select(DBMemory).where(DBMemory.user_id == self.user_id).order_by(DBMemory.created_at.desc()).limit(limit)
            result = await self.db_session.execute(stmt)
            memories = result.scalars().all()
            logger.debug(f"Retrieved {len(memories)} recent memories from PostgreSQL.")
            return memories
        except Exception as e:
            logger.error(f"Failed to retrieve recent memories from PostgreSQL for user {self.user_id}: {e}")
            return []

    async def update_access(self, memory_id: uuid.UUID):
        logger.info(f"Updating access for memory {memory_id} for user {self.user_id}")
        try:
            stmt = select(DBMemory).where(
                DBMemory.id == memory_id,
                DBMemory.user_id == self.user_id
            )
            result = await self.db_session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory:
                memory.last_accessed_at = datetime.now(timezone.utc)
                memory.accessed_count = (memory.accessed_count or 0) + 1
                await self.db_session.commit()
                await self.db_session.refresh(memory)
                logger.debug(f"Memory {memory_id} access updated.")
            else:
                logger.warning(f"Memory {memory_id} not found or does not belong to user {self.user_id}.")
        except Exception as e:
            logger.error(f"Failed to update access for memory {memory_id}: {e}")

    async def calculate_importance(self, memory_id: uuid.UUID) -> int:
        logger.info(f"Calculating importance for memory {memory_id} for user {self.user_id}")
        
        # 1. Fetch the memory from the database
        try:
            stmt = select(DBMemory).where(
                DBMemory.id == memory_id,
                DBMemory.user_id == self.user_id
            )
            result = await self.db_session.execute(stmt)
            memory = result.scalar_one_or_none()

            if not memory:
                logger.warning(f"Memory {memory_id} not found or does not belong to user {self.user_id}.")
                return 0 # Or raise an error
        except Exception as e:
            logger.error(f"Failed to fetch memory {memory_id} for importance calculation: {e}")
            return 0

        # 2. Construct a prompt for the LLM to score importance
        prompt = (
            f"Rate the importance of the following memory on a scale of 0 to 100. "
            f"A score of 0 means completely irrelevant, and 100 means critically important. "
            f"Provide only the numerical score. Memory: \"{memory.content}\""
        )
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "local-model",  # Assuming a local model is served by LM Studio for chat completions
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 10
        }

        importance_score = 0
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:1234/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
            
            response_data = response.json()
            if response_data and "choices" in response_data and response_data["choices"]:
                llm_response_content = response_data["choices"][0]["message"]["content"].strip()
                try:
                    importance_score = int(llm_response_content)
                    importance_score = max(0, min(100, importance_score)) # Clamp between 0 and 100
                except ValueError:
                    logger.warning(f"LLM returned non-integer importance score: '{llm_response_content}'. Defaulting to 0.")
        except httpx.RequestError as exc:
            logger.error(f"Network error during importance calculation LLM call: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"LLM API returned an error during importance calculation: {exc.response.status_code} - {exc.response.text}")
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to decode LLM response for importance calculation: {exc}")
        except Exception as exc:
            logger.error(f"An unexpected error occurred during importance calculation: {exc}")
        
        # 3. Update the importance score in the database
        if memory.importance != importance_score: # Only update if changed
            memory.importance = importance_score
            try:
                await self.db_session.commit()
                await self.db_session.refresh(memory)
                logger.debug(f"Memory {memory_id} importance updated to {importance_score}.")
            except Exception as e:
                logger.error(f"Failed to update importance for memory {memory_id} in DB: {e}")

        return importance_score

    async def cleanup_old_memories(self, max_age_days: int):
        logger.info(f"Cleaning up old memories for user {self.user_id} older than {max_age_days} days")

        if max_age_days <= 0:
            logger.warning("max_age_days must be positive for cleanup. No memories will be cleaned up.")
            return

        threshold_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        try:
            # 1. Query PostgreSQL for memories to delete
            stmt = select(DBMemory).where(
                DBMemory.user_id == self.user_id,
                DBMemory.created_at < threshold_date
            )
            result = await self.db_session.execute(stmt)
            memories_to_delete = result.scalars().all()

            if not memories_to_delete:
                logger.info(f"No old memories found for user {self.user_id} older than {max_age_days} days.")
                return

            qdrant_ids_to_delete = [str(m.qdrant_id) for m in memories_to_delete if m.qdrant_id]
            pg_memory_ids_to_delete = [m.id for m in memories_to_delete]

            # 2. Delete from Qdrant
            if qdrant_ids_to_delete:
                try:
                    await self.qdrant_client.delete_points(
                        collection_name=QDRANT_COLLECTION_NAME,
                        points_selector={"points": qdrant_ids_to_delete}
                    )
                    logger.debug(f"Deleted {len(qdrant_ids_to_delete)} embeddings from Qdrant.")
                except Exception as e:
                    logger.error(f"Failed to delete embeddings from Qdrant for user {self.user_id}: {e}")
            
            # 3. Delete from PostgreSQL
            if pg_memory_ids_to_delete:
                try:
                    stmt = delete(DBMemory).where(DBMemory.id.in_(pg_memory_ids_to_delete))
                    await self.db_session.execute(stmt)
                    await self.db_session.commit()
                    logger.info(f"Deleted {len(pg_memory_ids_to_delete)} old memories from PostgreSQL.")
                except Exception as e:
                    logger.error(f"Failed to delete memories from PostgreSQL for user {self.user_id}: {e}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during memory cleanup for user {self.user_id}: {e}")
