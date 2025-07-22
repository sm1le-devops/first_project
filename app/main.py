from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.routes import ping, auth

app = FastAPI()


app.include_router(ping.router)
app.include_router(auth.router)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")

@app.get("/login")
async def login_page():
    return FileResponse(os.path.join("app/static", "login.html"))
