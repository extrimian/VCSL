from kink import di
from os import environ
from services.serv_health import HealthCheckService
from services.serv_redis import RedisService
from services.serv_bitarray import BitArrayService
from redis import Redis

from routers.rout_health import HealthCheckRouter
from routers.rout_bitarray import BitArrayRouter


def init_di() -> None:
    di['redis_host'] = environ.get('REDIS_HOST', '127.0.0.1')
    di['redis_port'] = environ.get('REDIS_PORT', 6379)
    di[Redis] = Redis(host=di['redis_host'], port=di['redis_port'], db=0)

    di[HealthCheckService] = HealthCheckService()
    di[RedisService] = RedisService()
    di[HealthCheckRouter] = HealthCheckRouter()
    di[BitArrayService] = BitArrayService()
    di[BitArrayRouter] = BitArrayRouter()

    pass
