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

    def acquire_lock(self, lock_name: str, acquire_timeout: int = 10, blocking: bool = True) -> bool:
        """
        Acquire lock for lock_name.
        :param lock_name: name of lock
        :param acquire_timeout: timeout for acquire lock
        :return: True if lock acquired, False if not
        """
        lock = self.redis.lock(lock_name, timeout=acquire_timeout)
        return lock.acquire(blocking=blocking)

    def release_lock(self, lock_name: str) -> None:
        """
        Release lock for lock_name.
        :param lock_name: name of lock
        :return: None
        """
        lock = self.redis.lock(lock_name)
        lock.release()
