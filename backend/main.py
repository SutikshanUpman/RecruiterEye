from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

"""
app = FastAPI() creates your application, the front door.
@app.get("/health") means: when someone visits /health, run the function below.
The returned dictionary is sent back as JSON.
"""