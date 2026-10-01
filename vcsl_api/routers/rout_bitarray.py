import sys
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel
from kink import inject
from services.serv_bitarray import (
    BitArrayService,
    BitArrayNotFoundError,
    BitArrayFullError,
    LockNotAcquiredError,
    IndexNotAssignedError,
    IndexOutOfRangeError,
)


class BitValue(BaseModel):
    # `bit` is the documented field; `value` is accepted because existing clients already send it
    bit: Optional[Literal[0, 1]] = None
    value: Optional[Literal[0, 1]] = None

    def resolved(self) -> Optional[int]:
        return self.bit if self.bit is not None else self.value


def to_http_exception(e: Exception) -> HTTPException:
    if isinstance(e, BitArrayNotFoundError):
        return HTTPException(status_code=404, detail="Bit array not found")
    if isinstance(e, BitArrayFullError):
        return HTTPException(status_code=409, detail="No free bits")
    if isinstance(e, LockNotAcquiredError):
        return HTTPException(status_code=503, detail="Bit array busy, retry later")
    if isinstance(e, IndexOutOfRangeError):
        return HTTPException(status_code=400, detail="Index out of bounds")
    if isinstance(e, IndexNotAssignedError):
        return HTTPException(status_code=400, detail="Index not assigned")
    return HTTPException(status_code=500, detail="Internal error")


@inject
class BitArrayRouter:
    def __init__(self, bit_array_service: BitArrayService):
        self.bit_array_service: BitArrayService = bit_array_service
        self.router = APIRouter()
        self.router.add_api_route(path="/bit-array", endpoint=self.create_bit_array, methods=["PUT"],)
        self.router.add_api_route(path="/bit-array/{uuid}", endpoint=self.get_compressed_bit_array, methods=["GET"])
        self.router.add_api_route(path="/bit-array/{uuid}/free", endpoint=self.get_free_bits, methods=["GET"])
        # Must be registered before /bit-array/{uuid}/{index} so the literal "index" wins
        self.router.add_api_route(path="/bit-array/{uuid}/index", endpoint=self.acquire_index, methods=["PUT"])
        self.router.add_api_route(path="/bit-array/{uuid}/{index}", endpoint=self.set_bit, methods=["PUT"])
        self.router.add_api_route(path="/bit-array/{uuid}/{index}", endpoint=self.flip_bit, methods=["POST"])
        self.router.add_api_route(path="/bit-array/{uuid}/{index}", endpoint=self.get_bit_array_element, methods=["GET"])

    async def create_bit_array(self, background_tasks: BackgroundTasks):
        bit_array_uuid, bit_array = await self.bit_array_service.create_bit_array()
        background_tasks.add_task(self.bit_array_service.upload_bit_array, bit_array_uuid, bit_array)
        return {"id": bit_array_uuid}

    async def acquire_index(self, uuid: str):
        try:
            new_index = await self.bit_array_service.acquire_bit_array_index(uuid)
        except Exception as e:
            print(f"[BitArrayRouter] acquire_index {uuid} failed: {e!r}", file=sys.stderr)
            raise to_http_exception(e)
        print(f"[BitArrayRouter] index assigned list={uuid} index={new_index}")
        return {"index": new_index}

    async def set_bit(self, uuid: str, index: int, body: BitValue):
        value = body.resolved()
        if value is None:
            raise HTTPException(status_code=422, detail='Body must be {"bit": 0} or {"bit": 1}')
        try:
            bit = await self.bit_array_service.set_bit(uuid, index, value)
        except Exception as e:
            raise to_http_exception(e)
        print(f"[BitArrayRouter] bit set list={uuid} index={index} bit={bit}")
        return {"bit": bit}

    async def flip_bit(self, uuid: str, index: int, body: Optional[BitValue] = Body(None)):
        # With {"bit"} / {"value"} in the body the bit is set; without body it is toggled (deprecated)
        value = body.resolved() if body is not None else None
        try:
            bit = await self.bit_array_service.set_bit(uuid, index, value)
        except Exception as e:
            raise to_http_exception(e)
        if value is None:
            print(f"[BitArrayRouter] DEPRECATED toggle list={uuid} index={index} bit={bit}", file=sys.stderr)
        else:
            print(f"[BitArrayRouter] bit set list={uuid} index={index} bit={bit}")
        return {"message": "Bit flipped", "bit": bit}

    async def get_compressed_bit_array(self, uuid: str):
        bit_array, _ = await self.bit_array_service.get_bit_array(uuid)
        if (bit_array is None):
            raise HTTPException(status_code=404, detail="Bit array not found")
        return {"bit-array": bit_array.compress()}

    async def get_bit_array_element(self, uuid: str, index: int):
        bit_array, _ = await self.bit_array_service.get_bit_array(uuid)
        if bit_array is None:
            raise HTTPException(status_code=404, detail="Bit array not found")
        if index < 0 or index >= bit_array.size:
            raise HTTPException(status_code=404, detail="Index out of bounds")
        bit = bit_array[index]
        return {"bit": bit}

    async def get_free_bits(self, uuid: str):
        free_bits = await self.bit_array_service.get_free_bits(uuid)
        if free_bits == -1:
            raise HTTPException(status_code=404, detail="Bit array not found")
        return {"free": free_bits}
