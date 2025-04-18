# AI Faceless YouTube Channel MVP

This is a Python command-line tool that automates the creation of faceless YouTube videos with AI-generated voiceover, images, Ken Burns effects, transitions, and background music.

## Features
- Input a text script
- Generate AI voiceover
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
voice: Rachel
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

## Example Output

![Example Output Screenshot](assets/example_output.png)

## Troubleshooting
- Ensure all API keys are set in `.env` (see below).
- If you see `Cannot declare ... twice` in `pyproject.toml`, remove duplicate sections as shown above.
- For missing dependencies, run `pip install -r requirements.txt`.
- For video/audio errors, check your ffmpeg installation (`brew install ffmpeg` on Mac).
- For config errors, see the example in `README.md` and `examples/demo_config.yaml`.

## API Key Setup
- Copy `.env.example` to `.env` and fill in your API keys:
  - `ELEVENLABS_API_KEY` (voiceover)
  - `OPENAI_API_KEY` (images, script)
  - `PEXELS_API_KEY` (stock footage, optional)
  - `ANTHROPIC_API_KEY` (optional, for LLMs)

## Roadmap
- Add overlays (vintage/grunge)
- Support for stock footage
- Advanced transitions
- Web UI (future)
