from redis import Redis
from kink import inject


@inject
class RedisService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def get(self, key: str) -> str:
        return self.redis.get(key).decode('utf-8')

    def set(self, key: str, value: str) -> None:
        self.redis.set(key, value)
