# AI Faceless YouTube Channel MVP

This is a Python command-line tool that automates the creation of faceless YouTube videos with AI-generated voiceover, images, Ken Burns effects, transitions, and background music.

## Features
- Input a text script
- Generate AI voiceover with Deepgram TTS
- Create/gather images for scenes
- Assemble video with Ken Burns effects and transitions
- Add background music

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional) Set up API keys for image generation or TTS in a `.env` file.

## Usage
Create a `config.yaml` file to define your video parameters, then run:

```bash
python main.py
```

## Configuration Example

```yaml
script: |
  The future of AI is evolving rapidly...

output: output.mp4
voice: aura-asteria-en
style: cinematic

transition:
  duration: 1.0

overlay:
  folder: overlays/
  opacity: 0.25

background_music:
  tracks:
    - url: https://example.com/track1.mp3
      volume: 0.2

stock_footage:
  folder: stock/
  use_probability: 0.5

resolution:
  width: 1280
  height: 720

fps: 24
```

See `config.yaml` for customizable options such as voice, overlays, music, transitions, and more.

The `voice` field should match a Deepgram Aura model (for example `aura-asteria-en`,
`aura-lyra-en`, etc.). The pipeline sends the script text to Deepgram Text-to-Speech
and stores the returned MP3 before composing the video.

## Example Output

![Example Output Screenshot](assets/example_output.png)

## Web API

You can run the pipeline via a small FastAPI server:

```bash
ai-faceless-api
```

Send a POST request to `/generate` with a JSON body containing a `script` field.
The endpoint returns a `job_id` immediately. Poll `/job/{job_id}` to retrieve the
output path once processing finishes.

The API reads environment variables from a `.env` file. You can override the
configuration path with `CONFIG_PATH` and change the listening port via `PORT`.
Set `API_KEY` to require authentication; clients must send the key in an
`X-API-Key` header.

### Docker

You can also run the API server in a container:

```bash
docker build -t ai-faceless .
docker run -p 8000:8000 ai-faceless
```

## Web UI

The FastAPI server also ships with a small Bootstrap-based interface at
`http://localhost:8000/`. Paste your script into the form and click
**Generate Video**. The page will display a job link where you can monitor
progress and download the video once ready.

## Troubleshooting
- Ensure all API keys are set in `.env` (see below).
- If you see `Cannot declare ... twice` in `pyproject.toml`, remove duplicate sections as shown above.
- For missing dependencies, run `pip install -r requirements.txt`.
- For video/audio errors, check your ffmpeg installation (`brew install ffmpeg` on Mac).
- For config errors, see the example in `README.md` and `examples/demo_config.yaml`.

## API Key Setup
- Copy `.env.example` to `.env` and fill in your API keys:
- `OPENAI_API_KEY` (images, script)
- `DEEPGRAM_API_KEY` (voiceover + subtitles)
- `PEXELS_API_KEY` (stock footage, optional)
- `ANTHROPIC_API_KEY` (optional, for LLMs)

## Roadmap
- Add overlays (vintage/grunge)
- Support for stock footage
- Advanced transitions
