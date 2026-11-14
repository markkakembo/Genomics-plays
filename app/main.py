import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .pipeline import run_pipeline

app = FastAPI(title="Da Vinci's Poet: ResearchOrchestra", version="0.1.0")

class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    limit: int = Field(default=8, ge=1, le=15)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")

@app.post("/api/research")
async def research(request: ResearchRequest, x_api_key: str | None = Header(default=None)):
    configured = os.getenv("APP_API_KEY")
    if configured and x_api_key != configured:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        return await run_pipeline(request.question, request.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Research provider failed. Check server logs.") from exc
