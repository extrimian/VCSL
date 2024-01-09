from fastapi import FastAPI
from kink import di


from di_init import init_di
from routers.rout_health import HealthCheckRouter

print("Initializing dependency injection container...")

init_di()

app = FastAPI()
health_router = di[HealthCheckRouter]
app.include_router(health_router.router)
