from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import yaml
import uuid
import os
from . import run_pipeline

app = FastAPI()

class GenerateRequest(BaseModel):
    script: str

@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

@app.post("/generate")
def generate(req: GenerateRequest):
    """Run the video generation pipeline with a provided script."""
    # Load base config
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    config["script"] = req.script
    # unique output per request
    output_file = f"output_{uuid.uuid4().hex}.mp4"
    config["output"] = output_file
    tmp_cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
    with open(tmp_cfg, "w") as f:
        yaml.safe_dump(config, f)
    run_pipeline(config_path=tmp_cfg)
    os.remove(tmp_cfg)
    return {"output": output_file}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
