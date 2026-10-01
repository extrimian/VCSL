import random
import sys
from kink import inject
from services.abstractClasses.serv_cache_i import ICacheService
from services.abstractClasses.serv_lock_i import ILockService
from services.serv_web3 import Web3Service
from services.serv_ipfs import IPFSService
from persistance.dao_bitarray import BitArrayDAO
from models.bitarray import BitArray
from models.ipfs_dto import IPFSDto
from misc.scheduler import Scheduler
from uuid import uuid4
from datetime import datetime


class BitArrayNotFoundError(Exception):
    pass


class BitArrayFullError(Exception):
    pass


class LockNotAcquiredError(Exception):
    pass


class IndexNotAssignedError(Exception):
    pass


class IndexOutOfRangeError(Exception):
    pass


# Random tries before falling back to a linear scan for a free index
MAX_RANDOM_TRIES = 64


@inject
class BitArrayService:
    def __init__(self,
                 cache_service: ICacheService,
                 lock_service: ILockService,
                 bitarray_dao: BitArrayDAO,
                 web3_service: Web3Service,
                 ipfs_service: IPFSService,
                 scheduler: Scheduler
                 ):

        self.bitarray_dao: BitArrayDAO = bitarray_dao
        self.cache_service: ICacheService = cache_service
        self.lock_service: ILockService = lock_service
        self.ipfs_service: IPFSService = ipfs_service
        self.web3_service: Web3Service = web3_service
        self.scheduler: Scheduler = scheduler

        print(f"All bitarrays: {self.bitarray_dao.get_all_bitarrays()}")
        print(f"Total: {len(self.bitarray_dao.get_all_bitarrays())}")

        self.scheduler.add_job(self.update_bitarrays_in_ipfs, 'interval', hours=5, next_run_time=datetime.now())

    async def create_bit_array(self) -> (str, BitArray):
        bit_array_uuid = str(uuid4())
        bit_array = BitArray(id=bit_array_uuid)
        await self.lock_service.acquire_lock(bit_array_uuid)
        self.bitarray_dao.set_bitarray(bit_array)
        self.bitarray_dao.set_mask(bit_array)
        await self.lock_service.release_lock(bit_array_uuid)
        return bit_array_uuid, bit_array

    def upload_bit_array(self, id: str, bitarray: BitArray) -> None:
        keyCreated = self.ipfs_service.create_key(key_name=id)
        if not keyCreated:
            raise Exception("IPFS Key creation failed")
        try:
            ipfs_dto: IPFSDto = self.ipfs_service.add_vcsl(bit_array=bitarray, bit_array_id=id, key_name=id)
        except Exception as e:
            print(e, file=sys.stderr)
            return

        # Now, upload it to the smart contract
        result = self.web3_service.add_vcsl(id=id, ipns=ipfs_dto.get_ipns())
        if not result:
            raise Exception("VCSL upload failed")

    async def get_bit_array(self, bit_array_uuid: str, cached=True) -> (BitArray, BitArray):
        compressed_bit_array = self.bitarray_dao.get_bitarray(bit_array_uuid)
        compressed_mask = self.bitarray_dao.get_mask(bit_array_uuid)
        return compressed_bit_array, compressed_mask

    @staticmethod
    def _pick_free_index(mask: BitArray) -> int:
        # The mask holds every index ever handed out; only mask == 0 is free
        for _ in range(MAX_RANDOM_TRIES):
            index = random.randint(0, mask.size - 1)
            if mask[index] == 0:
                return index
        # Almost full list: scan for the first byte with a free bit
        for byte_index, byte in enumerate(mask.array):
            if byte != 0xFF:
                for bit in range(8):
                    if not byte & (1 << bit):
                        return byte_index * 8 + bit
        raise BitArrayFullError()

    async def acquire_bit_array_index(self, bit_array_uuid: str) -> int:
        lock = await self.lock_service.acquire_lock(bit_array_uuid, blocking=True)
        if lock is None:
            raise LockNotAcquiredError(bit_array_uuid)
        try:
            bit_array, mask = await self.get_bit_array(bit_array_uuid)
            if bit_array is None or mask is None:
                raise BitArrayNotFoundError(bit_array_uuid)
            if mask.free == 0:
                raise BitArrayFullError(bit_array_uuid)

            index = self._pick_free_index(mask)
            mask[index] = 1
            self.bitarray_dao.set_mask(mask)
            return index
        finally:
            await self.lock_service.release_lock(bit_array_uuid)

    async def set_bit(self, bit_array_uuid: str, index: int, value: int = None) -> int:
        """Sets the status bit to `value` (0/1). With value=None it toggles (legacy behaviour).
        Returns the resulting bit."""
        lock = await self.lock_service.acquire_lock(bit_array_uuid, blocking=True)
        if lock is None:
            raise LockNotAcquiredError(bit_array_uuid)
        try:
            bit_array, mask = await self.get_bit_array(bit_array_uuid)
            if bit_array is None or mask is None:
                raise BitArrayNotFoundError(bit_array_uuid)
            if index < 0 or index >= bit_array.size:
                raise IndexOutOfRangeError(index)
            if mask[index] == 0:
                raise IndexNotAssignedError(index)

            new_value = (1 - bit_array[index]) if value is None else value
            if bit_array[index] != new_value:
                bit_array[index] = new_value
                self.bitarray_dao.set_bitarray(bit_array)
            return new_value
        finally:
            await self.lock_service.release_lock(bit_array_uuid)

    async def flip_bit(self, bit_array_uuid: str, index: int) -> bool:
        # Kept for backwards compatibility; prefer set_bit with an explicit value
        await self.set_bit(bit_array_uuid, index)
        return True

    async def get_free_bits(self, bit_array_uuid: str) -> int:
        try:
            bit_array, mask = await self.get_bit_array(bit_array_uuid)
        except Exception:
            return -1
        if mask is None:
            return -1
        return mask.free

    def update_bitarrays_in_ipfs(self):
        bitarrays = self.bitarray_dao.get_all_bitarrays()
        for bitarray in bitarrays:
            try:
                dto: IPFSDto = self.ipfs_service.update_vcsl(bitarray)
                print(f"Result: {dto}")
            except Exception as e:
                print(f"Error updating bitarray {bitarray.id} in IPFS")
                print(e, file=sys.stderr)
                break
