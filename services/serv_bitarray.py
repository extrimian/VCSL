from kink import inject

from services.serv_redis import RedisService


@inject
class BitArrayService:
    def __init__(self, redis_service: RedisService):
        self.redis_service: RedisService = redis_service
