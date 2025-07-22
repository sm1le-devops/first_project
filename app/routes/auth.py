from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

# Пароли
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подгружаем секрет (не нужен прямо сейчас, но на будущее)
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")

# Имитация базы данных
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123")
    }
}

# Pydantic модель
class UserData(BaseModel):
    username: str
    password: str

# Проверка пароля
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str):
    return pwd_context.hash(password)

def get_user(username: str):
    return fake_users_db.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

# Роут логина
@router.post("/login")
def login(data: UserData):
    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"message": "Успешно"}

# Роут регистрации
@router.post("/register")
def register(data: UserData):
    if get_user(data.username):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    hashed = hash_password(data.password)
    fake_users_db[data.username] = {
        "username": data.username,
        "hashed_password": hashed
    }
    return {"message": "Регистрация прошла успешно"}
