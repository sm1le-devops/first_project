from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import ping

app = FastAPI()

# Подключаем маршруты
app.include_router(ping.router)

# Статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Главная страница
@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")

