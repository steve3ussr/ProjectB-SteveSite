import os
from datetime import timedelta
import redis
from dotenv import load_dotenv



class BaseConfig:
    load_dotenv()

    SECRET_OTP_ADMIN = os.getenv('SECRET_OTP_ADMIN')
    SECRET_OTP_OPERATOR = os.getenv('SECRET_OTP_OPERATOR')
    SECRET_OTP_USER = os.getenv('SECRET_OTP_USER')
    SECRET_KEY = os.getenv('SECRET_FLASK_SESSION')

    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_USE_SIGNER = True


class RedisConfig:
    SESSION_TYPE = 'redis'
    REDIS_DB_NUM = 0


class DevConfig(BaseConfig, RedisConfig):
    DB_FILENAME = 'inst_runtime.db'
    REDIS_BASE_URL = os.getenv('REDIS_URL_DEV')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)

class ProdConfig(BaseConfig, RedisConfig):
    DB_FILENAME = 'inst.db'
    REDIS_BASE_URL = os.getenv('REDIS_URL_PROD')


class TestConfig(BaseConfig, RedisConfig):
    # MISSING SQL DB: injected by pytest conftest
    REDIS_BASE_URL = os.getenv('REDIS_URL_TEST')
    # REDIS DB NUM: injected by pytest conftest
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=3)
