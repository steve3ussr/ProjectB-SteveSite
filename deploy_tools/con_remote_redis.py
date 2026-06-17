import redis
from sshtunnel import SSHTunnelForwarder
import msgspec
import paramiko
import dotenv
import os


dotenv.load_dotenv()
decoder = msgspec.msgpack.Decoder()

class MockDSSKey: pass
paramiko.DSSKey = MockDSSKey


SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT"))
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")


REMOTE_REDIS_HOST = os.getenv("REMOTE_REDIS_HOST")
REMOTE_REDIS_PORT = int(os.getenv("REMOTE_REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASSWORD,
        remote_bind_address=(REMOTE_REDIS_HOST, REMOTE_REDIS_PORT)
) as tunnel:
    print(f"本地映射端口: 127.0.0.1:{tunnel.local_bind_port}")
    try:
        r = redis.Redis(
            host="127.0.0.1",
            port=tunnel.local_bind_port,  # 核心：使用隧道动态生成的本地端口
            password=REDIS_PASSWORD
        )

        for key in r.scan_iter("*"):
            key_type = r.type(key).decode()

            if key_type == 'string':
                v = r.get(key)
                print(f"{key.decode()}: {decoder.decode(v)}")
            elif key_type == 'set':
                v = r.smembers(key)
                print(f"{key.decode()}: {v}")



    except redis.exceptions.ConnectionError as e:
        print(f"Redis 连接失败: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

print("SSH 隧道已断开，释放资源。")