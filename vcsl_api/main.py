from fastapi import FastAPI
from kink import di

from di_init import init_di
from routers.rout_health import HealthCheckRouter
from routers.rout_bitarray import BitArrayRouter

app = FastAPI()


@app.on_event("startup")
def startup_event():
    init_di()
    health_router = di[HealthCheckRouter]
    bit_array_router = di[BitArrayRouter]
    app.include_router(health_router.router)
    app.include_router(bit_array_router.router)
