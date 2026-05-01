import os
from dotenv import load_dotenv


load_dotenv()

SECRET_OTP_ADMIN = os.getenv('SECRET_OTP_ADMIN')
SECRET_OTP_OPERATOR = os.getenv('SECRET_OTP_OPERATOR')
SECRET_OTP_USER = os.getenv('SECRET_OTP_USER')
SECRET_KEY = 'dev'
DB_FILENAME = os.getenv('DB_FILENAME')
