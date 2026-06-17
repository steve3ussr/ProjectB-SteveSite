import paramiko
import json
import os
import dotenv


dotenv.load_dotenv()


remote_path = os.getenv("REMOTE_SQL_PATH")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv("SSH_HOST"),
            username=os.getenv("SSH_USER"),
            password=os.getenv("SSH_PASSWORD"))

sql_query = "SELECT * FROM blog"

stdin, stdout, stderr = ssh.exec_command(f"sqlite3 -json {remote_path} '{sql_query}'")
res = stdout.read().decode("utf-8")
err = stderr.read().decode("utf-8")
if not err:
    res = json.loads(res)
else:
    res = json.loads(err)
print(res)
ssh.close()
quit(0)
