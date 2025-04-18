#!/bin/bash

echo "🔧 Creating project scaffolding..."

# Required folders (skip if exists)
mkdir -p \
  assets/overlays \
  assets/stock \
  assets/sfx \
  output \
  temp \
  logs \
  examples \
  tests \
  ai_faceless

# .env template
if [ ! -f .env.example ]; then
  cat <<EOF > .env.example
# Example environment file
ELEVENLABS_API_KEY=your-elevenlabs-api-key
OPENAI_API_KEY=your-openai-api-key
EOF
  echo "✅ Created .env.example"
fi

# Python module scaffold
touch ai_faceless/__init__.py

# Add example config if missing
if [ ! -f examples/demo_config.yaml ]; then
  cat <<EOF > examples/demo_config.yaml
script: |
  The future of AI is being written by those who automate.

output: output/demo_video.mp4
voice: Rachel
style: cinematic

transition:
  duration: 1.0

overlay:
  folder: assets/overlays/
  opacity: 0.25

background_music:
  tracks:
    - url: https://example.com/music.mp3
      volume: 0.2

stock_footage:
  folder: assets/stock/
  use_probability: 0.5

resolution:
  width: 1280
  height: 720

fps: 24
EOF
  echo "✅ Created examples/demo_config.yaml"
fi

# Minimal test scaffold
if [ ! -f tests/test_config.py ]; then
  cat <<EOF > tests/test_config.py
def test_config_load():
    assert True  # TODO: Implement actual tests
EOF
  echo "✅ Created tests/test_config.py"
fi

echo "✅ Project structure is ready."