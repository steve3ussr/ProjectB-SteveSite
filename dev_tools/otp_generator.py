import time
import os
import dotenv
import pyotp


dotenv.load_dotenv()
secret_admin    = os.getenv("SECRET_OTP_ADMIN")
secret_operator = os.getenv("SECRET_OTP_OPERATOR")
secret_user     = os.getenv("SECRET_OTP_USER")


totp_admin = pyotp.TOTP(secret_admin)
totp_operator = pyotp.TOTP(secret_operator)
totp_user = pyotp.TOTP(secret_user)

while 1:
    print(f"{time.strftime("%X")}\t{totp_admin.now()}\t{totp_operator.now()}\t{totp_user.now()}")
    time.sleep(10)
