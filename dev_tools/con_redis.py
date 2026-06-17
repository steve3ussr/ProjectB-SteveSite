import os
import redis
import dotenv
import msgspec


dotenv.load_dotenv()
url = os.environ['REDIS_URL']
r = redis.Redis.from_url(url)
decoder = msgspec.msgpack.Decoder()

for key in r.scan_iter("*"):
    key_type = r.type(key).decode()

    if key_type == 'string':
        v = r.get(key)
        print(f"{key.decode()}: {decoder.decode(v)}")
    elif key_type == 'set':
        v = r.smembers(key)
        print(f"{key.decode()}: {v}")



