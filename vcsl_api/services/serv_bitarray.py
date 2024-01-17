import random
from kink import inject
from services.abstractClasses.serv_cache_i import ICacheService
from services.abstractClasses.serv_lock_i import ILockService
from persistance.dao_bitarray import BitArrayDAO
from models.bitarray import BitArray
from uuid import uuid4


@inject
class BitArrayService:
    def __init__(self, cache_service: ICacheService, lock_service: ILockService, bitarray_dao: BitArrayDAO):
        self.bitarray_dao: BitArrayDAO = bitarray_dao
        self.cache_service: ICacheService = cache_service
        self.lock_service: ILockService = lock_service

    async def create_bit_array(self) -> str:
        bit_array_uuid = str(uuid4())
        bit_array = BitArray(id=bit_array_uuid)
        await self.lock_service.acquire_lock(bit_array_uuid)
        self.bitarray_dao.set_bitarray(bit_array)
        self.bitarray_dao.set_mask(bit_array)
        # await self.cache_service.set(f'mask:{bit_array_uuid}', bit_array.compress())
        # await self.cache_service.set(bit_array_uuid, bit_array.compress())
        await self.lock_service.release_lock(bit_array_uuid)
        return bit_array_uuid

    async def get_bit_array(self, bit_array_uuid: str, cached=True) -> (BitArray, BitArray):
        compressed_bit_array = self.bitarray_dao.get_bitarray(bit_array_uuid)
        compressed_mask = self.bitarray_dao.get_mask(bit_array_uuid)
        return compressed_bit_array, compressed_mask

    async def acquire_bit_array_index(self, bit_array_uuid: str) -> int:
        lock = await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        if lock is None:
            return -1
        bit_array: BitArray = None
        mask: BitArray = None
        try:
            bit_array. mask = await self.get_bit_array(bit_array_uuid)
        except Exception:
            return -1

        if bit_array.free == 0:
            await self.lock_service.release_lock(bit_array_uuid)
            return -1

        index = random.randint(0, bit_array.size - 1)
        while bit_array[index] == 1:
            index = random.randint(0, bit_array.size - 1)

        mask[index] = 1
        self.bitarray_dao.set_mask(mask)
        await self.lock_service.release_lock(bit_array_uuid)
        return index

    async def flip_bit(self, bit_array_uuid: str, index: int) -> bool:
        lock = await self.redis_service.acquire_lock(bit_array_uuid, blocking=True)
        if lock is None:
            return False
        bit_array: BitArray = None
        mask: BitArray = None
        try:
            bit_array, mask = await self.get_bit_array(bit_array_uuid)
        except Exception:
            return False
        if mask[index] == 0:
            return False
        bit_array[index] = not bit_array[index]

        self.bitarray_dao.set_bitarray(bit_array)
        await self.redis_service.release_lock(bit_array_uuid)
        return True  # TODO: Check if there was an error and return false

    async def get_free_bits(self, bit_array_uuid: str) -> int:
        try:
            bit_array, mask = await self.get_bit_array(bit_array_uuid)
        except Exception:
            return -1
        return bit_array.free
