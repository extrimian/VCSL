from kink import di
from os import environ
from persistance.datastore_postgres import PostgresDataStore
from services.abstractClasses.serv_cache_i import ICacheService
from services.abstractClasses.serv_lock_i import ILockService
from services.serv_web3 import Web3Service
from services.serv_lock import LockService
from services.serv_cache import CacheService
from redis import Redis


def init_di() -> None:
    di['redis_host'] = environ.get('REDIS_HOST', '127.0.0.1')
    di['redis_port'] = environ.get('REDIS_PORT', 6379)
    di[Redis] = Redis(host=di['redis_host'], port=di['redis_port'], db=0)

    di['psql_host'] = environ.get('PSQL_HOST', '127.0.0.1')
    di['psql_port'] = environ.get('PSQL_PORT', 5432)
    di['psql_user'] = environ.get('PSQL_USER', 'postgres')
    di['psql_pass'] = environ.get('PSQL_PASS', '12345')
    di['psql_db'] = environ.get('PSQL_DB', 'vcsl')
    di[PostgresDataStore] = PostgresDataStore(dbname=di['psql_db'], dbuser=di['psql_user'], dbpassword=di['psql_pass'], dbhost=di['psql_host'], dbport=di['psql_port'])
    connected = di[PostgresDataStore].init_connections()
    if not connected:
        raise Exception("Unable to connect to postgres")

    di['web3_url'] = environ.get('WEB3_URL', 'http://localhost:7545')
    di['web3_wallet_priv_key'] = environ.get('WEB3_PRIVATE_KEY', '0x78f20d29b9ff7226d40fd408d6a991aac2af4364b5e1a31b5a96035dcf68f44b')  # This is a development only key
    di['web3_contract_addr'] = environ.get('WEB3_CONTRACT_ADDR', '0x8ceBE8333A85Faed0e55EB2c07607A491cdA66f9')
    di['web3_abi_path'] = environ.get('WEB3_ABI_PATH', './resources/smart_contracts/vcsl_abi.json')
    with open(di['web3_abi_path'], 'r') as abi_definition:
        di['web3_abi'] = abi_definition.read()

    di[Web3Service] = Web3Service(url=di['web3_url'], wallet_priv_key=di['web3_wallet_priv_key'], contract_addr=di['web3_contract_addr'], abi=di['web3_abi'])

    di[ICacheService] = CacheService()
    di[ILockService] = LockService()
    # di[HealthCheckService] = HealthCheckService()
    # di[RedisService] = RedisService()
    # di[HealthCheckRouter] = HealthCheckRouter()
    # di[BitArrayService] = BitArrayService()
    # di[BitArrayRouter] = BitArrayRouter()
    # di[BitArrayDAO] = BitArrayDAO()
