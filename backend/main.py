from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.routers.review import router as review_router

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI()
app.include_router(review_router)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False)
def home():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

"""
app = FastAPI() creates your application, the front door.
@app.get("/health") means: when someone visits /health, run the function below.
The returned dictionary is sent back as JSON.
"""
