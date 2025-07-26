from fastapi import FastAPI, Depends, HTTPException, status, Response, Cookie, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime
import os
import shutil

import models
import schemas
from database import engine, SessionLocal

# Создаём таблицы
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
UPLOAD_AVATAR_DIR = "static/avatars"
os.makedirs(UPLOAD_AVATAR_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ----- Регистрация -----
@app.post("/auth/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем или email уже существует")

    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Вы успешно зарегистрированы"}

# ----- Вход -----
@app.post("/auth/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    response = JSONResponse(content={"redirect_url": "/auth/welcome"})
    response.set_cookie(
        key="username",
        value=db_user.username,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response

# ----- Приветствие -----
@app.get("/auth/welcome", response_class=HTMLResponse)
def welcome(request: Request, db: Session = Depends(get_db), username: str | None = Cookie(default=None)):
    if not username:
        raise HTTPException(status_code=401, detail="Не авторизован")
    users = db.query(models.User).order_by(models.User.amount.desc()).all()
    current_user = db.query(models.User).filter(models.User.username == username).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "top_users": users,
        "current_user": current_user
    })

# ----- Донат -----
class DonateRequest(BaseModel):
    amount: int

@app.post("/auth/donate")
def donate(data: DonateRequest, username: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not username:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if data.amount < 1:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")

    user.amount += data.amount
    user.last_donation_time = datetime.utcnow()
    db.commit()

    return {"message": "Спасибо за донат!"}

# ----- Профиль -----
@app.get("/auth/profile", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db), username: str | None = Cookie(default=None)):
    if not username:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    avatar_url = f"/static/avatars/{user.avatar}" if user.avatar else None

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": user,
        "avatar_url": avatar_url
    })

@app.post("/auth/profile")
async def update_profile(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    avatar: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_username: str | None = Cookie(default=None)
):
    if not current_username:
        raise HTTPException(status_code=401, detail="Не авторизован")

    user = db.query(models.User).filter(models.User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if username != current_username:
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(status_code=400, detail="Имя пользователя уже занято")

    if email != user.email:
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email уже занят")

    user.username = username
    user.email = email

    if password:
        user.hashed_password = get_password_hash(password)

    if avatar:
        if avatar.content_type not in ["image/png", "image/jpeg", "image/svg+xml"]:
            raise HTTPException(status_code=400, detail="Тип аватара не поддерживается")

        ext = os.path.splitext(avatar.filename)[1]
        avatar_filename = f"{username}{ext}"
        avatar_path = os.path.join(UPLOAD_AVATAR_DIR, avatar_filename)

        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        user.avatar = avatar_filename

    db.commit()

    response = JSONResponse(content={"message": "Профиль успешно обновлен"})

    if username != current_username:
        response.set_cookie(
            key="username",
            value=username,
            path="/",
            httponly=True,
            samesite="lax",
            secure=False
        )

    return response
