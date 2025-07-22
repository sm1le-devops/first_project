from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import ping

app = FastAPI()


app.include_router(ping.router)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")




