from kink import di
from os import environ
from services.serv_health import HealthCheckService
from services.serv_redis import RedisService
from redis import Redis

from routers.rout_health import HealthCheckRouter


def init_di() -> None:
    di['redis_host'] = environ.get('REDIS_HOST', 'localhost')
    di['redis_port'] = environ.get('REDIS_PORT', 6379)
    di[Redis] = Redis(host=di['redis_host'], port=di['redis_port'], db=0)

    di[HealthCheckService] = HealthCheckService()
    di[RedisService] = RedisService()
    di[HealthCheckRouter] = HealthCheckRouter()

    pass