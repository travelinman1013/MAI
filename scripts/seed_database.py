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
import random
import sys
import uuid
from pathlib import Path

import bcrypt
from sqlalchemy import select

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.utils.config import get_settings
from src.infrastructure.database.models import Conversation, Memory, Message, User
from src.infrastructure.database.session import close_db, get_session, init_db
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

    # Refresh users to get their IDs
    for user in users:
        await session.refresh(user)

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
            # Check if conversation exists
            result = await session.execute(
                select(Conversation).where(
                    Conversation.user_id == data["user_id"],
                    Conversation.title == data["title"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  Conversation '{data['title']}' already exists, skipping")
                conversations.append(existing)
            else:
                conv = Conversation(**data)
                session.add(conv)
                conversations.append(conv)
                print(f"  Created conversation: {data['title']}")

    await session.commit()

    # Refresh conversations to get their IDs
    for conv in conversations:
        await session.refresh(conv)

    return conversations


async def seed_messages(session, conversations: list[Conversation]) -> list[Message]:
    """Create sample messages in conversations."""
    messages = []

    sample_exchanges = [
        ("user", "Hello! Can you help me understand how this system works?"),
        (
            "assistant",
            "Of course! I'm the MAI Framework assistant. I can help you with various tasks including answering questions, having conversations, and more. What would you like to know?",
        ),
        ("user", "What kind of memory do you have?"),
        (
            "assistant",
            "I have multiple types of memory:\n\n1. **Short-term memory** - Stored in Redis for fast access during our conversation\n2. **Long-term memory** - Persisted in PostgreSQL for important information\n3. **Semantic memory** - Vector embeddings in Qdrant for similarity search\n\nThis allows me to remember context and find relevant information from past interactions.",
        ),
    ]

    for conv in conversations:
        # Check if this conversation already has messages
        result = await session.execute(
            select(Message).where(Message.conversation_id == conv.id).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Messages already exist for conversation: {conv.title}, skipping")
            continue

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

    # Ensure collection exists
    await qdrant.create_collection()

    # Sample memories with fake embeddings (in production, use actual embedding model)
    sample_memories = [
        "User prefers detailed technical explanations",
        "User is interested in AI and machine learning topics",
        "User works on a personal NotebookLM-like project",
        "User uses Docker for local development",
        "User prefers Python for backend development",
    ]

    # Generate fake embeddings (1536 dimensions, normalized)
    def fake_embedding():
        vec = [random.gauss(0, 1) for _ in range(settings.qdrant.vector_size)]
        norm = sum(x**2 for x in vec) ** 0.5
        return [x / norm for x in vec]

    for user in users[:2]:
        # Check if user already has memories
        result = await session.execute(
            select(Memory).where(Memory.user_id == user.id).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Memories already exist for user: {user.username}, skipping")
            continue

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
                payloads=[
                    {
                        "user_id": str(user.id),
                        "agent_name": "ChatAgent",
                        "content": content,
                        "memory_type": "semantic",
                        "importance": memory.importance,
                    }
                ],
                ids=[str(qdrant_id)],
            )

        print(f"  Created {len(sample_memories)} memories for user: {user.username}")

    await session.commit()


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
    try:
        info = await qdrant.get_collection_info(settings.qdrant.collection_name)
        results["qdrant_vectors"] = info.get("points_count", 0)
    except Exception as e:
        print(f"  Warning: Could not get Qdrant collection info: {e}")
        results["qdrant_vectors"] = "unknown"

    return results


async def main():
    """Main seed function."""
    print("=" * 60)
    print("MAI Framework Database Seeder")
    print("=" * 60)

    # Initialize database
    print("\n[1/6] Initializing database connection...")
    init_db()

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
    print(f"  Users:          {counts['users']}")
    print(f"  Conversations:  {counts['conversations']}")
    print(f"  Messages:       {counts['messages']}")
    print(f"  Memories:       {counts['memories']}")
    print(f"  Qdrant vectors: {counts['qdrant_vectors']}")
    print("=" * 60)

    # Cleanup
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
