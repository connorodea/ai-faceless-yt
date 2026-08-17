import pytest
import yaml
from pathlib import Path


@pytest.fixture
def config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def test_required_keys_present(config):
    required = ["script", "output", "voice", "transition", "overlay", "background_music", "stock_footage"]
    for key in required:
        assert key in config, f"Missing required config key: {key}"


def test_script_not_empty(config):
    assert isinstance(config.get("script"), str)
    assert config["script"].strip() != "", "Script must not be empty"


def test_output_path_valid(config):
    output = config.get("output")
    assert isinstance(output, str)
    assert output.endswith(".mp4"), "Output must be an .mp4 file"


def test_transition_structure(config):
    t = config.get("transition", {})
    assert "duration" in t
    assert isinstance(t["duration"], (int, float))


def test_overlay_structure(config):
    o = config.get("overlay", {})
    assert "folder" in o and "opacity" in o
    assert Path(o["folder"]).exists()
    assert 0.0 <= o["opacity"] <= 1.0


def test_music_tracks_valid(config):
    tracks = config.get("background_music", {}).get("tracks", [])
    assert isinstance(tracks, list)
    for track in tracks:
        assert "url" in track and "volume" in track
        assert track["url"].startswith("http")
        assert 0.0 <= track["volume"] <= 1.0
