import sys
from pathlib import Path
from dotenv import load_dotenv


# Read .env from root directory and populate os.environ
load_dotenv()

# Ensures the project root is ALWAYS in Python's search path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Standard absolute imports using 'src.'
from src.api.routes import router as api_router

app = FastAPI(title="SRE Log Triage Engine", version="1.0.0")

# 1. Register API routes from routes.py
app.include_router(api_router)

# 2. Path to the web frontend directory
WEB_DIR = Path(__file__).parent / "web"

# 3. Mount static files directory if there are local CSS/JSS assets
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# 4. Serve index.html at the root URL
@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    return FileResponse(WEB_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main.app", host="127.0.0.1", port=8000, reload=True)