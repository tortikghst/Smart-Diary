import redis.asyncio as aioredis
from scr.config import settings

redis_client = aioredis.from_url(
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True
)


class RedisOTPService:
    # сохраняет код в памяти на определенное время (сек)
    @staticmethod
    async def save_code(email: str, code: str) -> None:
        key = f"otp:{email}"
        await redis_client.set(key, code, ex=300)

    # проверка одноразового кода
    @staticmethod
    async def verify_code(email: str, input_code: str) -> bool:
        key = f"otp:{email}"
        saved_code = await redis_client.get(key)

        if saved_code and saved_code == input_code:
            await redis_client.delete(key)
            return True
        return False
