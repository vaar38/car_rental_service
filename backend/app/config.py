import os

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/car_rental")

# Ключ для подписи токенов. На сервере обязательно задать свой в .env
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 7
