from fastapi import FastAPI
from kink import di

from di_init import init_di
from routers.rout_health import HealthCheckRouter
from routers.rout_bitarray import BitArrayRouter

from persistance.datastore_postgres import PostgresDataStore


from services.serv_bitarray import BitArrayService
# import asyncio


async def test():
    bit_array_service = di[BitArrayService]
    uuid = await bit_array_service.create_bit_array()
    # await bit_array_service.flip_bit(uuid, 10)
    index = await bit_array_service.acquire_bit_array_index(uuid)
    if index == -1:
        print("No free bits")
        return

    await bit_array_service.flip_bit(uuid, index)
    bit_array = await bit_array_service.get_bit_array(uuid)
    bits = []
    for i in range(index - 5, index + 5):
        bits.append((i, bit_array[i]))

# asyncio.run(test())


app = FastAPI()


@app.on_event("startup")
def startup_event():
    init_di()
    health_router = di[HealthCheckRouter]
    bit_array_router = di[BitArrayRouter]
    app.include_router(health_router.router)
    app.include_router(bit_array_router.router)
