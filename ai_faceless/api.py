import asyncio
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import yaml

from . import run_pipeline

load_dotenv()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

class GenerateRequest(BaseModel):
    script: str


def _verify_api_key(request: Request) -> None:
    """Ensure X-API-Key header matches API_KEY if set."""
    api_key = os.getenv("API_KEY")
    if api_key and request.headers.get("x-api-key") != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

@app.post("/generate")
async def generate(req: GenerateRequest, request: Request):
    _verify_api_key(request)
    """Run the video generation pipeline with a provided script."""
    # Load base config
    cfg_path = os.getenv("CONFIG_PATH", "config.yaml")
    with open(cfg_path, "r") as f:
        config = yaml.safe_load(f)
    config["script"] = req.script
    # unique output per request
    output_file = f"output_{uuid.uuid4().hex}.mp4"
    config["output"] = output_file
    tmp_cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
    with open(tmp_cfg, "w") as f:
        yaml.safe_dump(config, f)
    await asyncio.to_thread(run_pipeline, config_path=tmp_cfg)
    os.remove(tmp_cfg)
    return {"output": output_file}


@app.post("/generate-form", response_class=HTMLResponse)
async def generate_form(request: Request, script: str = Form(...)):
    _verify_api_key(request)
    cfg_path = os.getenv("CONFIG_PATH", "config.yaml")
    with open(cfg_path, "r") as f:
        config = yaml.safe_load(f)
    config["script"] = script
    output_file = f"output_{uuid.uuid4().hex}.mp4"
    config["output"] = output_file
    tmp_cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
    with open(tmp_cfg, "w") as f:
        yaml.safe_dump(config, f)
    await asyncio.to_thread(run_pipeline, config_path=tmp_cfg)
    os.remove(tmp_cfg)
    return templates.TemplateResponse(
        "index.html", {"request": request, "output": output_file}
    )

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
