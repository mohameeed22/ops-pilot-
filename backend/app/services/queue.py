import json
import logging
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger("queue")

class RedisQueue:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            logger.info(f"Connecting to Redis at {self.redis_url}")
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def push_task(self, queue_name: str, payload: dict) -> None:
        client = await self.get_redis()
        logger.info(f"Pushing task to queue '{queue_name}'")
        await client.lpush(queue_name, json.dumps(payload))

    async def pop_task(self, queue_name: str, timeout: int = 0) -> dict | None:
        client = await self.get_redis()
        # brpop blocks and returns a tuple (queue, data) or None if timeout
        result = await client.brpop(queue_name, timeout=timeout)
        if result:
            _, val = result
            return json.loads(val)
        return None

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("Closed Redis connection")

# Singleton instance
redis_queue = RedisQueue(settings.REDIS_URL)
