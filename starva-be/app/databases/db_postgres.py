# Handles pgvector schema setup, table management, and similarity search operations for CFOBuddy.

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# =========================
# CONFIG (EDIT HERE)
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 5))

TABLE_NAME = "CFOBuddy"
EMBEDDING_DIM = 384

# =========================
# GLOBAL POOL (SAFE)
# =========================

_pool = None
_lock = asyncio.Lock()


async def get_pool():
    global _pool

    if _pool is None:
        async with _lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=DB_POOL_MIN,
                    max_size=DB_POOL_MAX,
                )

    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# =========================
# SQL DEFINITIONS
# =========================

CREATE_EXTENSION_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS "{TABLE_NAME}" (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT,
    metadata JSONB,
    agent_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding VECTOR({EMBEDDING_DIM})
);
"""

CREATE_INDEX_SQL = f"""
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_embedding
ON "{TABLE_NAME}"
USING ivfflat (embedding vector_cosine_ops);
"""

# =========================
# INIT DB (SAFE TO RUN MANY TIMES)
# =========================

async def init_db():
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(CREATE_EXTENSION_SQL)
        await conn.execute(CREATE_TABLE_SQL)
        await conn.execute(CREATE_INDEX_SQL)

    print("✅ Database initialized")


# =========================
# INSERT DOCUMENT
# =========================

async def insert_document(content, embedding, metadata=None, source=None, agent_type=None):
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO "{TABLE_NAME}" (content, embedding, metadata, source, agent_type)
            VALUES ($1, $2, $3, $4, $5)
            """,
            content,
            embedding,
            metadata,
            source,
            agent_type,
        )


# =========================
# SIMILARITY SEARCH
# =========================

async def similarity_search(query_embedding, limit=5):
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT content, metadata, source,
                   embedding <-> $1 AS distance
            FROM "{TABLE_NAME}"
            ORDER BY embedding <-> $1
            LIMIT {limit}
            """,
            query_embedding,
        )

    return rows