import aiomysql
from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE
)


class Database:
    pool: aiomysql.Pool = None

    @classmethod
    async def connect(cls):
        cls.pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            autocommit=True
        )

        await cls.init_tables()

    @classmethod
    async def init_tables(cls):
        query = """
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticket_number INT NOT NULL,
            ticket_type VARCHAR(32) NOT NULL,
            ticket_letter CHAR(1) NOT NULL,
            user_id BIGINT NOT NULL,
            channel_id BIGINT,
            status ENUM('open', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await cls.execute(query)
        print("✅ Tables checked / created")

    @classmethod
    async def fetchrow(cls, query, args=None):
        async with cls.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchone()

    @classmethod
    async def execute(cls, query, args=None):
        async with cls.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)

    @classmethod
    async def close(cls):
        if cls.pool:
            cls.pool.close()
            await cls.pool.wait_closed()
            print("🛑 MySQL pool closed")
