import asyncio
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import yaml

from . import run_pipeline

load_dotenv()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Simple in-memory job store
jobs = {}

class GenerateRequest(BaseModel):
    script: str


def _verify_api_key(request: Request) -> None:
    """Ensure X-API-Key header matches API_KEY if set."""
    api_key = os.getenv("API_KEY")
    if api_key and request.headers.get("x-api-key") != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _run_job(job_id: str, cfg: str) -> None:
    """Run pipeline and update job status."""
    try:
        run_pipeline(config_path=cfg)
        jobs[job_id]["status"] = "completed"
    except Exception:
        jobs[job_id]["status"] = "failed"
    finally:
        if os.path.exists(cfg):
            os.remove(cfg)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/job/{job_id}")
def job_status(job_id: str) -> JSONResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)

@app.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    _verify_api_key(request)
    """Schedule video generation and return a job ID."""
    cfg_path = os.getenv("CONFIG_PATH", "config.yaml")
    with open(cfg_path, "r") as f:
        config = yaml.safe_load(f)
    config["script"] = req.script
    job_id = uuid.uuid4().hex
    output_file = f"output_{job_id}.mp4"
    config["output"] = output_file
    tmp_cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
    with open(tmp_cfg, "w") as f:
        yaml.safe_dump(config, f)
    jobs[job_id] = {"status": "running", "output": output_file}
    background_tasks.add_task(_run_job, job_id, tmp_cfg)
    return {"job_id": job_id}


@app.post("/generate-form", response_class=HTMLResponse)
async def generate_form(
    request: Request,
    background_tasks: BackgroundTasks,
    script: str = Form(...),
):
    _verify_api_key(request)
    cfg_path = os.getenv("CONFIG_PATH", "config.yaml")
    with open(cfg_path, "r") as f:
        config = yaml.safe_load(f)
    config["script"] = script
    job_id = uuid.uuid4().hex
    output_file = f"output_{job_id}.mp4"
    config["output"] = output_file
    tmp_cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
    with open(tmp_cfg, "w") as f:
        yaml.safe_dump(config, f)
    jobs[job_id] = {"status": "running", "output": output_file}
    background_tasks.add_task(_run_job, job_id, tmp_cfg)
    return templates.TemplateResponse(
        "index.html", {"request": request, "job_id": job_id}
    )

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
