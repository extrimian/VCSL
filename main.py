from fastapi import FastAPI
from kink import di

from di_init import init_di
from routers.rout_health import HealthCheckRouter


from services.serv_bitarray import BitArrayService
import asyncio

init_di()


async def test():
    bit_array_service = di[BitArrayService]
    uuid = await bit_array_service.create_bit_array()
    # await bit_array_service.flip_bit(uuid, 10)
    index = await bit_array_service.acquire_bit_array_index(uuid)
    if index == -1:
        print("No free bits")
        return

    print(f"About to flip bit {index}")
    await bit_array_service.flip_bit(uuid, index)
    print(f"Bit {index} flipped")
    bit_array = await bit_array_service.get_bit_array(uuid)
    bits = []
    for i in range(index - 5, index + 5):
        bits.append((i, bit_array[i]))
        print("Bit {} is {}".format(i, bit_array[i]))

asyncio.run(test())


app = FastAPI()
health_router = di[HealthCheckRouter]
app.include_router(health_router.router)
