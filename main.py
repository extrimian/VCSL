from fastapi import FastAPI
from kink import di

from di_init import init_di
from routers.rout_health import HealthCheckRouter

from models.bitarray import BitArray

init_di()

bitArray = BitArray()
bitArray[1] = True
print(bitArray[1])
compressed = bitArray.compress()
print(f"Compressed: {compressed} - len: {len(compressed)}")

app = FastAPI()
health_router = di[HealthCheckRouter]
app.include_router(health_router.router)
