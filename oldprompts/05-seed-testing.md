# 05 - Seed Script and Testing

## Task Information

| Field | Value |
|-------|-------|
| **Project** | MAI PostgreSQL + Qdrant Implementation |
| **Archon Project ID** | `42e538a6-9b44-4e9c-9a8a-2a8bcb6e2983` |
| **Archon Task ID** | `aeeb1c7f-25dc-4567-828d-4e253f26614d` |
| **Sequence** | 5 of 5 (Final) |
| **Depends On** | 04-service-integration.md completed |

---

## Archon Task Management

**Mark task as in-progress when starting:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/aeeb1c7f-25dc-4567-828d-4e253f26614d" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Mark task as done when complete:**
```bash
curl -X PUT "http://localhost:8181/api/tasks/aeeb1c7f-25dc-4567-828d-4e253f26614d" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

Steps 01-04 set up the complete infrastructure:
- PostgreSQL 18 with pgvector extension available
- Qdrant with API key authentication
- Database migrations applied (tables created)
- Service initialization with health checks

Now we need a seed script to populate test data for development and verification.

---

## Requirements

### 1. Create Seed Script

Create `scripts/seed_database.py`:

```python
#!/usr/bin/env python3
"""Seed script for MAI Framework development database.

Creates test data:
- Test users with hashed passwords
- Sample conversations and messages
- Memory entries with Qdrant vectors

Usage:
    poetry run python scripts/seed_database.py
    # or inside Docker:
    docker exec mai-api python scripts/seed_database.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy import select

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.utils.config import get_settings
from src.infrastructure.database.session import init_db, get_session, close_db
from src.infrastructure.database.models import User, Conversation, Message, Memory
from src.infrastructure.vector_store.qdrant_client import get_qdrant_client


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed_users(session) -> list[User]:
    """Create test users."""
    users_data = [
        {
            "username": "admin",
            "email": "admin@mai.local",
            "hashed_password": hash_password("admin123"),
            "is_active": True,
            "is_superuser": True,
            "full_name": "Admin User",
        },
        {
            "username": "testuser",
            "email": "test@mai.local",
            "hashed_password": hash_password("test123"),
            "is_active": True,
            "is_superuser": False,
            "full_name": "Test User",
        },
        {
            "username": "demo",
            "email": "demo@mai.local",
            "hashed_password": hash_password("demo123"),
            "is_active": True,
            "is_superuser": False,
            "full_name": "Demo User",
        },
    ]

    users = []
    for data in users_data:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.username == data["username"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  User '{data['username']}' already exists, skipping")
            users.append(existing)
        else:
            user = User(**data)
            session.add(user)
            users.append(user)
            print(f"  Created user: {data['username']}")

    await session.commit()
    return users


async def seed_conversations(session, users: list[User]) -> list[Conversation]:
    """Create sample conversations."""
    conversations = []

    for user in users[:2]:  # First two users get conversations
        conv_data = [
            {
                "user_id": user.id,
                "agent_name": "ChatAgent",
                "title": f"Welcome conversation for {user.username}",
                "is_archived": False,
            },
            {
                "user_id": user.id,
                "agent_name": "ChatAgent",
                "title": f"Test conversation for {user.username}",
                "is_archived": False,
            },
        ]

        for data in conv_data:
            conv = Conversation(**data)
            session.add(conv)
            conversations.append(conv)
            print(f"  Created conversation: {data['title']}")

    await session.commit()
    return conversations


async def seed_messages(session, conversations: list[Conversation]) -> list[Message]:
    """Create sample messages in conversations."""
    messages = []

    sample_exchanges = [
        ("user", "Hello! Can you help me understand how this system works?"),
        ("assistant", "Of course! I'm the MAI Framework assistant. I can help you with various tasks including answering questions, having conversations, and more. What would you like to know?"),
        ("user", "What kind of memory do you have?"),
        ("assistant", "I have multiple types of memory:\n\n1. **Short-term memory** - Stored in Redis for fast access during our conversation\n2. **Long-term memory** - Persisted in PostgreSQL for important information\n3. **Semantic memory** - Vector embeddings in Qdrant for similarity search\n\nThis allows me to remember context and find relevant information from past interactions."),
    ]

    for conv in conversations:
        for role, content in sample_exchanges:
            msg = Message(
                conversation_id=conv.id,
                role=role,
                content=content,
            )
            session.add(msg)
            messages.append(msg)

        print(f"  Added {len(sample_exchanges)} messages to conversation: {conv.title}")

    await session.commit()
    return messages


async def seed_memories_and_vectors(session, users: list[User]) -> None:
    """Create memory entries and corresponding Qdrant vectors."""
    settings = get_settings()
    qdrant = await get_qdrant_client()
    await qdrant.connect()

    # Sample memories with fake embeddings (in production, use actual embedding model)
    sample_memories = [
        "User prefers detailed technical explanations",
        "User is interested in AI and machine learning topics",
        "User works on a personal NotebookLM-like project",
        "User uses Docker for local development",
        "User prefers Python for backend development",
    ]

    # Generate fake embeddings (1536 dimensions, normalized)
    import random
    def fake_embedding():
        vec = [random.gauss(0, 1) for _ in range(settings.qdrant.vector_size)]
        norm = sum(x**2 for x in vec) ** 0.5
        return [x / norm for x in vec]

    for user in users[:2]:
        for i, content in enumerate(sample_memories):
            # Create memory in PostgreSQL
            qdrant_id = uuid.uuid4()
            memory = Memory(
                user_id=user.id,
                agent_name="ChatAgent",
                content=content,
                memory_type="semantic",
                importance=50 + i * 10,  # 50, 60, 70, 80, 90
                qdrant_id=qdrant_id,
            )
            session.add(memory)

            # Create vector in Qdrant
            embedding = fake_embedding()
            await qdrant.upsert(
                collection_name=settings.qdrant.collection_name,
                vectors=[embedding],
                payloads=[{
                    "user_id": str(user.id),
                    "agent_name": "ChatAgent",
                    "content": content,
                    "memory_type": "semantic",
                    "importance": memory.importance,
                }],
                ids=[str(qdrant_id)],
            )

        print(f"  Created {len(sample_memories)} memories for user: {user.username}")

    await session.commit()
    await qdrant.disconnect()


async def verify_seed_data() -> dict:
    """Verify all seed data was created correctly."""
    settings = get_settings()
    results = {}

    async with get_session() as session:
        # Count users
        result = await session.execute(select(User))
        results["users"] = len(result.scalars().all())

        # Count conversations
        result = await session.execute(select(Conversation))
        results["conversations"] = len(result.scalars().all())

        # Count messages
        result = await session.execute(select(Message))
        results["messages"] = len(result.scalars().all())

        # Count memories
        result = await session.execute(select(Memory))
        results["memories"] = len(result.scalars().all())

    # Count Qdrant vectors
    qdrant = await get_qdrant_client()
    await qdrant.connect()
    info = await qdrant.get_collection_info(settings.qdrant.collection_name)
    results["qdrant_vectors"] = info.get("points_count", 0)
    await qdrant.disconnect()

    return results


async def main():
    """Main seed function."""
    print("=" * 60)
    print("MAI Framework Database Seeder")
    print("=" * 60)

    # Initialize database
    print("\n[1/6] Initializing database connection...")
    await init_db()

    async with get_session() as session:
        # Seed users
        print("\n[2/6] Creating test users...")
        users = await seed_users(session)

        # Seed conversations
        print("\n[3/6] Creating sample conversations...")
        conversations = await seed_conversations(session, users)

        # Seed messages
        print("\n[4/6] Creating sample messages...")
        messages = await seed_messages(session, conversations)

        # Seed memories and vectors
        print("\n[5/6] Creating memories and Qdrant vectors...")
        await seed_memories_and_vectors(session, users)

    # Verify
    print("\n[6/6] Verifying seed data...")
    counts = await verify_seed_data()

    print("\n" + "=" * 60)
    print("Seed Complete!")
    print("=" * 60)
    print(f"  Users:        {counts['users']}")
    print(f"  Conversations: {counts['conversations']}")
    print(f"  Messages:     {counts['messages']}")
    print(f"  Memories:     {counts['memories']}")
    print(f"  Qdrant vectors: {counts['qdrant_vectors']}")
    print("=" * 60)

    # Cleanup
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Create Scripts Directory

```bash
mkdir -p /Users/maxwell/Projects/MAI/scripts
```

### 3. Add bcrypt to Dependencies (if missing)

Check `pyproject.toml` for bcrypt:

```bash
poetry add bcrypt
```

### 4. Run Seed Script

```bash
# Option A: Run locally (with local DATABASE__URL and QDRANT__URL)
cd /Users/maxwell/Projects/MAI
DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework \
QDRANT__URL=http://localhost:6333 \
QDRANT__API_KEY=mai-qdrant-secret-key \
poetry run python scripts/seed_database.py

# Option B: Run inside Docker
docker exec mai-api python scripts/seed_database.py
```

---

## Files to Create

| File | Action |
|------|--------|
| `/Users/maxwell/Projects/MAI/scripts/seed_database.py` | Create seed script |

---

## Success Criteria

```bash
cd /Users/maxwell/Projects/MAI

# 1. Run seed script (should complete without errors)
docker exec mai-api python scripts/seed_database.py
# Expected: Shows creation of users, conversations, messages, memories

# 2. Verify users in PostgreSQL
docker exec mai-postgres psql -U postgres -d mai_framework -c "SELECT username, email, is_superuser FROM users"
# Expected: admin, testuser, demo users

# 3. Verify conversations
docker exec mai-postgres psql -U postgres -d mai_framework -c "SELECT title, agent_name FROM conversations LIMIT 5"
# Expected: Sample conversations for admin and testuser

# 4. Verify messages
docker exec mai-postgres psql -U postgres -d mai_framework -c "SELECT role, LEFT(content, 50) as content FROM messages LIMIT 5"
# Expected: user and assistant messages

# 5. Verify memories
docker exec mai-postgres psql -U postgres -d mai_framework -c "SELECT content, importance FROM memories LIMIT 5"
# Expected: Sample memory content

# 6. Verify Qdrant vectors
curl -H "api-key: mai-qdrant-secret-key" http://localhost:6333/collections/mai_embeddings
# Expected: "points_count" should be > 0 (10 vectors for 2 users x 5 memories)

# 7. Test vector search in Qdrant
curl -X POST -H "api-key: mai-qdrant-secret-key" -H "Content-Type: application/json" \
  http://localhost:6333/collections/mai_embeddings/points/scroll \
  -d '{"limit": 5, "with_payload": true}'
# Expected: Returns points with user_id, content, importance in payload

# 8. Full health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","services":{"redis":true,"postgresql":true,"qdrant":true},...}
```

---

## Technical Notes

- **Fake Embeddings:** The seed script uses random normalized vectors. In production, use a real embedding model (e.g., LM Studio's embedding endpoint or sentence-transformers).
- **Idempotent:** The seed script checks for existing users before creating, so it can be run multiple times safely.
- **Password Hashing:** Uses bcrypt for secure password hashing. Default test passwords are weak - don't use in production.
- **Memory-Qdrant Link:** Each Memory record has a `qdrant_id` UUID that links to the corresponding vector in Qdrant.

---

## On Completion

### Mark Final Task Done
```bash
curl -X PUT "http://localhost:8181/api/tasks/aeeb1c7f-25dc-4567-828d-4e253f26614d" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

### Create Completion Document in Archon
```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI PostgreSQL + Qdrant Implementation - Complete",
    "content": "# MAI Framework Infrastructure Complete\n\n## What Was Implemented\n\n1. **PostgreSQL 18** - Primary database with pgvector extension available\n2. **Qdrant** - Vector database with API key authentication\n3. **Alembic Migrations** - Database schema management\n4. **Service Integration** - Health checks and graceful degradation\n5. **Seed Data** - Test users, conversations, and vector embeddings\n\n## Services Running\n\n- mai-redis: Redis for caching\n- mai-postgres: PostgreSQL 18 with pgvector\n- mai-qdrant: Qdrant vector database\n- mai-api: FastAPI application\n- mai-gui: Gradio interface\n\n## Test Credentials\n\n| User | Password | Role |\n|------|----------|------|\n| admin | admin123 | superuser |\n| testuser | test123 | user |\n| demo | demo123 | user |\n\n## Next Steps\n\n- Implement document ingestion pipeline\n- Add notebook abstraction\n- Create grounded RAG chat agent\n- Build studio output generators",
    "project_id": "42e538a6-9b44-4e9c-9a8a-2a8bcb6e2983"
  }'
```

---

## Summary

You have now completed the MAI PostgreSQL + Qdrant Implementation:

| Component | Status |
|-----------|--------|
| PostgreSQL 18 Docker service | Configured |
| Qdrant Docker service | Configured |
| Environment configuration | Complete |
| Database migrations | Applied |
| Service integration | Working |
| Seed data | Created |

The MAI Framework now has full database and vector store infrastructure ready for building your private NotebookLM features.
