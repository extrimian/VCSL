from kink import inject

from services.serv_redis import RedisService
from models.bitarray import BitArray
from uuid import uuid4


@inject
class BitArrayService:
    def __init__(self, redis_service: RedisService):
        self.redis_service: RedisService = redis_service

    async def create_bit_array(self) -> str:
        bit_array = BitArray()
        bit_array_uuid = str(uuid4())
        await self.redis_service.set(bit_array_uuid, bit_array.compress())
        return bit_array_uuid

    async def get_bit_array(self, bit_array_uuid: str) -> BitArray:
        await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        compressed_bit_array = await self.redis_service.get(bit_array_uuid)
        await self.redis_service.release_lock(bit_array_uuid)
        return BitArray.decompress(compressed_bit_array)

    async def flip_bit(self, bit_array_uuid: str, index: int) -> None:
        await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        bit_array = await self.get_bit_array(bit_array_uuid)
        bit_array[index] = not bit_array[index]
        await self.redis_service.set(bit_array_uuid, bit_array.compress())
        await self.redis_service.release_lock(bit_array_uuid)
