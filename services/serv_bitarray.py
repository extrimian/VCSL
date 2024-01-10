import random
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
        await self.redis_service.set(f'mask:{bit_array_uuid}', bit_array.compress())
        await self.redis_service.set(bit_array_uuid, bit_array.compress())
        return bit_array_uuid

    async def get_bit_array(self, bit_array_uuid: str) -> BitArray:
        await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        try:
            compressed_bit_array = await self.redis_service.get(bit_array_uuid)
        except Exception:
            return None
        await self.redis_service.release_lock(bit_array_uuid)
        return BitArray.decompress(compressed_bit_array)

    async def acquire_bit_array_index(self, bit_array_uuid: str) -> int:
        await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        try:
            bit_array = await self.get_bit_array(f'mask:{bit_array_uuid}')
        except Exception:
            return -1

        if bit_array.free == 0:
            await self.redis_service.release_lock(bit_array_uuid)
            return -1

        index = random.randint(0, bit_array.size - 1)
        while bit_array[index] == 1:
            index = random.randint(0, bit_array.size - 1)

        await self.redis_service.set(f'mask:{bit_array_uuid}', bit_array.compress())
        await self.redis_service.release_lock(bit_array_uuid)
        return index

    async def flip_bit(self, bit_array_uuid: str, index: int) -> bool:
        await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        try:
            bit_array = await self.get_bit_array(bit_array_uuid)
        except Exception:
            return False
        bit_array[index] = not bit_array[index]
        await self.redis_service.set(bit_array_uuid, bit_array.compress())
        await self.redis_service.release_lock(bit_array_uuid)
        return True  # TODO: Check if there was an error and return false
