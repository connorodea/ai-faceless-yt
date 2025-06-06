import os
import logging
import yaml
from moviepy import (
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    AudioFileClip,
    CompositeAudioClip,
)
from elevenlabs import generate, save, set_api_key
from openai import OpenAI
from dotenv import load_dotenv
import requests
import tempfile
from tqdm import tqdm
import glob
import random
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
import math
import re
import time
# New integrations
try:
    import anthropic  # Anthropic Claude
except ImportError:
    anthropic = None
try:
    import deepgram  # Deepgram STT
except ImportError:
    deepgram = None
# For SRT/VTT subtitle writing
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
file_handler = logging.FileHandler("generation.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
logging.getLogger().addHandler(file_handler)

# Load API keys from .env
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if ELEVENLABS_API_KEY:
    set_api_key(ELEVENLABS_API_KEY)

DALLE_STYLES = ["vintage", "cinematic", "high quality", "grunge", "scratches", "moody lighting", "analog film"]

def validate_env():
    required_vars = ["OPENAI_API_KEY", "ELEVENLABS_API_KEY"]
    # Add new required vars as needed
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def validate_config(config):
    required = ["script", "output"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    # Validate provider selection
    valid_providers = {"openai", "anthropic"}
    if "script_provider" in config and config["script_provider"] not in valid_providers:
        raise ValueError(f"script_provider must be one of {valid_providers}")
    if "image_provider" in config and config["image_provider"] not in {"openai", "pexels"}:
        raise ValueError("image_provider must be 'openai' or 'pexels'")

# Helper: Generate voiceover from script
def generate_voiceover(script_text, voice="Rachel", output_path="voiceover.mp3"):
    validate_env()
    try:
        audio = generate(text=script_text, voice=voice)
        save(audio, output_path)

        # Load full audio and split by estimated sentence count
        full_audio = AudioSegment.from_file(output_path)
        sentence_count = max(1, len(re.split(r'[.!?]', script_text)))
        avg_duration = len(full_audio) / sentence_count
        durations = [avg_duration for _ in range(sentence_count)]
        return output_path, durations
    except Exception as e:
        logging.exception("Voiceover generation failed")
        raise

# Helper: Generate images using OpenAI DALL-E or Pexels

def generate_image_openai(prompt, output_path, style=None):
    """Generate image using OpenAI DALL-E."""
    if not OPENAI_API_KEY:
        raise ValueError("Set OPENAI_API_KEY in your .env file.")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        style = style or random.choice(DALLE_STYLES)
        enhanced_prompt = f"{prompt}, {style}"
        response = client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
        img_data = requests.get(image_url).content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            with open(tmpfile.name, 'wb') as handler:
                handler.write(img_data)
            return tmpfile.name
    except Exception as e:
        logging.exception("Image generation failed (OpenAI)")
        raise

def generate_image_pexels(prompt, output_path):
    """Generate/download image from Pexels API."""
    if not PEXELS_API_KEY:
        raise ValueError("Set PEXELS_API_KEY in your .env file.")
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": prompt, "per_page": 1}
        r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        if not data["photos"]:
            raise ValueError(f"No Pexels images found for prompt: {prompt}")
        img_url = data["photos"][0]["src"]["original"]
        img_data = requests.get(img_url).content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
            with open(tmpfile.name, 'wb') as handler:
                handler.write(img_data)
            return tmpfile.name
    except Exception as e:
        logging.exception("Image generation failed (Pexels)")
        raise

def generate_image(prompt, output_path, style=None, provider="openai"):
    """Dispatch image generation to OpenAI or Pexels based on provider."""
    if provider == "openai":
        return generate_image_openai(prompt, output_path, style=style)
    elif provider == "pexels":
        return generate_image_pexels(prompt, output_path)
    else:
        raise ValueError(f"Unknown image provider: {provider}")

# Helper: Download background music
def download_music(url, output_path):
    try:
        r = requests.get(url, stream=True)
        with open(output_path, 'wb') as f:
            for chunk in tqdm(r.iter_content(1024), desc="Downloading music"):
                f.write(chunk)
        return output_path
    except Exception as e:
        logging.exception("Music download failed")
        raise

# Helper: Apply Ken Burns effect (pan/zoom)
def ken_burns_effect(image_path, duration=5, zoom=1.1):
    clip = ImageClip(image_path).set_duration(duration)
    w, h = clip.size
    # Randomize start/end position for variety
    start_x = random.uniform(0, 0.1)
    start_y = random.uniform(0, 0.1)
    end_x = random.uniform(0.9, 1.0)
    end_y = random.uniform(0.9, 1.0)
    return (clip
        .resize(lambda t: 1 + (zoom-1)*t/duration)
        .set_position(lambda t: (
            int(start_x*w + (end_x-start_x)*w*t/duration),
            int(start_y*h + (end_y-start_y)*h*t/duration)))
        .crossfadein(0.5).crossfadeout(0.5))

# Helper: Overlay vintage/grunge effect
def apply_overlay(clip, overlay_folder=None, opacity=0.25):
    if not overlay_folder:
        return clip
    overlays = glob.glob(os.path.join(overlay_folder, '*.mp4')) + glob.glob(os.path.join(overlay_folder, '*.mov'))
    if not overlays:
        return clip
    overlay_path = random.choice(overlays)
    overlay_clip = (VideoFileClip(overlay_path)
                    .set_duration(clip.duration)
                    .resize(clip.size)
                    .set_opacity(opacity)
                    .set_position("center"))
    return CompositeVideoClip([clip, overlay_clip])

# Helper: Use stock footage if available
def get_scene_clip(image_path, stock_folder=None, duration=5, overlay_folder=None, overlay_opacity=0.25):
    # 50% chance to use stock footage if available
    use_stock = stock_folder and random.random() > 0.5
    if use_stock:
        stock_videos = glob.glob(os.path.join(stock_folder, '*.*'))
        if stock_videos:
            stock_path = random.choice(stock_videos)
            stock_clip = VideoFileClip(stock_path).subclip(0, duration).resize((1280, 720))
            return apply_overlay(stock_clip, overlay_folder, opacity=overlay_opacity)
    # Otherwise, use generated image with Ken Burns
    img_clip = ken_burns_effect(image_path, duration=duration)
    return apply_overlay(img_clip, overlay_folder, opacity=overlay_opacity)

# Improved scene splitting using paragraphs
def split_scenes(script):
    # Split by paragraph or long sentences
    paragraphs = re.split(r'\n\s*\n', script)
    scenes = [p.strip() for p in paragraphs if len(p.strip()) > 10]
    if not scenes:
        # fallback: split by sentences
        scenes = [s.strip() for s in re.split(r'[.!?]', script) if s.strip()]
    return scenes

# Script generation using OpenAI or Anthropic

def generate_script_openai(topic_or_prompt):
    """Generate or rewrite script using OpenAI GPT."""
    if not OPENAI_API_KEY:
        raise ValueError("Set OPENAI_API_KEY in your .env file.")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Write a YouTube video script."},
                      {"role": "user", "content": topic_or_prompt}],
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.exception("Script generation failed (OpenAI)")
        raise

def generate_script_anthropic(topic_or_prompt):
    """Generate or rewrite script using Anthropic Claude."""
    if not ANTHROPIC_API_KEY or anthropic is None:
        raise ValueError("Anthropic API or package not available.")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": topic_or_prompt}]
        )
        # Adjust as needed for Anthropic's API response structure
        return response.content[0].text
    except Exception as e:
        logging.exception("Script generation failed (Anthropic)")
        raise

def generate_script(topic_or_prompt, provider="openai"):
    if provider == "openai":
        return generate_script_openai(topic_or_prompt)
    elif provider == "anthropic":
        return generate_script_anthropic(topic_or_prompt)
    else:
        raise ValueError(f"Unknown script provider: {provider}")

# Deepgram integration for subtitles

def transcribe_audio_deepgram(audio_path):
    """
    Transcribe audio using Deepgram API, return transcript and SRT with accurate timing.
    """
    if not DEEPGRAM_API_KEY:
        raise ValueError("Set DEEPGRAM_API_KEY in your .env file.")
    try:
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/mp3"
        }
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers=headers,
            data=audio_data,
            params={"punctuate": True, "diarize": False, "utterances": True, "paragraphs": True, "smart_format": True, "timestamps": True}
        )
        response.raise_for_status()
        result = response.json()
        transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        words = result["results"]["channels"][0]["alternatives"][0].get("words", [])
        srt = words_to_srt(words)
        return transcript, srt
    except Exception as e:
        logging.exception("Deepgram transcription failed")
        raise

def words_to_srt(words):
    """
    Convert Deepgram words list to SRT format with accurate timings.
    """
    if not words:
        return ""
    srt = ""
    idx = 1
    chunk = []
    chunk_start = None
    chunk_end = None
    max_words = 10  # Subtitle length per line
    for w in words:
        if not chunk:
            chunk_start = w["start"]
        chunk_end = w["end"]
        chunk.append(w["word"])
        if len(chunk) >= max_words or w["punctuated_word"].endswith(('.', '?', '!')):
            start = seconds_to_srt_time(chunk_start)
            end = seconds_to_srt_time(chunk_end)
            srt += f"{idx}\n{start} --> {end}\n{' '.join(chunk)}\n\n"
            idx += 1
            chunk = []
    if chunk:
        start = seconds_to_srt_time(chunk_start)
        end = seconds_to_srt_time(chunk_end)
        srt += f"{idx}\n{start} --> {end}\n{' '.join(chunk)}\n\n"
    return srt

def seconds_to_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def save_srt(srt, output_path):
    with open(output_path, 'w') as f:
        f.write(srt)

def run_pipeline(config_path: str = "config.yaml"):
    """
    Main pipeline entrypoint. Supports configurable providers for script and image generation, subtitle generation, and all API integrations.
    """
    start_time = time.time()
    validate_env()
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    validate_config(config)

    # Provider selection
    script_provider = config.get("script_provider", "openai")
    image_provider = config.get("image_provider", "openai")

    # Script generation (if script is a topic or prompt)
    script = config["script"]
    if config.get("generate_script", False):
        logging.info(f"Generating script using {script_provider}...")
        script = generate_script(script, provider=script_provider)
        logging.info("Script generated.")

    output = config["output"]
    music_tracks = config.get("background_music", {}).get("tracks", [])
    overlay_folder = config.get("overlay", {}).get("folder")
    stock_folder = config.get("stock_footage", {}).get("folder")
    duration = config.get("duration", 5)
    voice = config.get("voice", "Rachel")
    style = config.get("style")
    transition_duration = config.get("transition", {}).get("duration", 1.0)
    overlay_opacity = config.get("overlay", {}).get("opacity", 0.25)
    music_volume = sum(track.get("volume", 0.2) for track in music_tracks)

    try:
        logging.info("Generating voiceover...")
        voiceover_path, durations = generate_voiceover(script, voice=voice)
        logging.info(f"Voiceover saved to {voiceover_path}")
    except Exception as e:
        logging.exception("Voiceover generation failed")
        return

    try:
        logging.info("Splitting script into scenes...")
        scenes = split_scenes(script)
        logging.info(f"{len(scenes)} scenes detected.")
    except Exception as e:
        logging.exception("Scene splitting failed")
        return

    try:
        logging.info("Generating images for scenes...")
        def generate_image_for_scene(idx, scene):
            logging.info(f"Generating image for scene {idx+1}...")
            img_path = f"scene_{idx+1}.png"
            generate_image(scene, img_path, style=style, provider=image_provider)
            return img_path

        with ThreadPoolExecutor() as executor:
            image_paths = list(tqdm(executor.map(lambda i_s: generate_image_for_scene(*i_s), enumerate(scenes)), total=len(scenes), desc="Generating images"))
    except Exception as e:
        logging.exception("Image generation failed")
        return

    try:
        logging.info("Creating video clips with Ken Burns/stock footage and overlays...")
        # --- Custom Video Transitions ---
        transitions_config = config.get("transitions", {})
        transitions_enabled = transitions_config.get("enabled", False)
        transitions_folder = transitions_config.get("folder", "transitions/")
        transitions_mode = transitions_config.get("mode", "insert")  # 'insert' or 'overlay'
        scene_transitions = transitions_config.get("scene_transitions", [])

        clips = []
        import glob
        transition_files = glob.glob(os.path.join(transitions_folder, '*.mp4')) + glob.glob(os.path.join(transitions_folder, '*.mov'))

        transition_duration = transitions_config.get("duration", 1.0)  # seconds, default 1.0
        transition_duck_db = transitions_config.get("duck_db", -8)  # dB to lower audio during transition
        transition_sfx_combo = transitions_config.get("sfx_combo", True)
        sfx_config = config.get("sound_effects", {})
        sfx_types = sfx_config.get("types", {}) if sfx_config.get("enabled", False) else {}
        sfx_files = []
        if sfx_config.get("enabled", False):
            import glob
            sfx_folder = sfx_config.get("folder", "sfx/")
            sfx_files = glob.glob(os.path.join(sfx_folder, "*.mp3")) + glob.glob(os.path.join(sfx_folder, "*.wav"))

        for idx, img_path in enumerate(image_paths):
            clip = get_scene_clip(img_path, stock_folder=stock_folder, duration=math.ceil(durations[idx] / 1000), overlay_folder=overlay_folder, overlay_opacity=overlay_opacity)
            clips.append(clip)
            # Insert transition after every scene except last
            if transitions_enabled and idx < len(image_paths) - 1 and transition_files:
                # Pick transition file based on scene_transitions or random
                t_file = None
                t_type = None
                if scene_transitions and idx < len(scene_transitions):
                    t_type = scene_transitions[idx]
                    candidates = [f for f in transition_files if t_type in os.path.basename(f).lower()]
                    if candidates:
                        t_file = random.choice(candidates)
                if not t_file:
                    t_file = random.choice(transition_files)
                t_clip = VideoFileClip(t_file).resize((1280, 720))
                # Trim or extend transition to specified duration
                if t_clip.duration > transition_duration:
                    t_clip = t_clip.subclip(0, transition_duration)
                elif t_clip.duration < transition_duration:
                    t_clip = t_clip.loop(duration=transition_duration)
                # Duck audio during transition (applies to insert mode)
                if transitions_mode == "insert":
                    # Pair SFX with transition if combo enabled and sfx_types available
                    if transition_sfx_combo and t_type and sfx_types:
                        candidates = []
                        for k, v in sfx_types.items():
                            if t_type == k or t_type in v:
                                # Find sfx files that match type keyword
                                candidates += [f for f in sfx_files if any(word in os.path.basename(f).lower() for word in v+[k])]
                        if candidates:
                            sfx_path = random.choice(candidates)
                            # Overlay SFX onto transition video audio
                            from pydub import AudioSegment
                            t_audio = AudioSegment.silent(duration=int(transition_duration*1000))
                            sfx = AudioSegment.from_file(sfx_path)
                            sfx = sfx.fade_in(100).fade_out(100)
                            t_audio = t_audio.overlay(sfx, position=0)
                            temp_t_audio = f"_temp_transition_audio_{idx}.wav"
                            t_audio.export(temp_t_audio, format="wav")
                            t_clip = t_clip.set_audio(AudioFileClip(temp_t_audio).set_duration(t_clip.duration))
                    # Duck previous clip's audio at the end and next at start
                    if len(clips) > 1:
                        prev_clip = clips[-2]
                        prev_clip = prev_clip.audio_fadeout(transition_duration/2).volumex(10**(transition_duck_db/20))
                        clips[-2] = prev_clip
                    next_clip = clip.audio_fadein(transition_duration/2).volumex(10**(transition_duck_db/20))
                    clips[-1] = next_clip
                    clips.append(t_clip)
                    logging.info(f"Inserted transition {os.path.basename(t_file)} after scene {idx} with ducking and combo SFX")
                else:
                    # Overlay transition on top of end of previous and start of next
                    overlay_dur = min(transition_duration, t_clip.duration, clip.duration/2)
                    prev_clip = clips[-2] if len(clips) > 1 else None
                    if prev_clip:
                        prev_clip = prev_clip.set_end(prev_clip.end - overlay_dur)
                        clips[-2] = CompositeVideoClip([prev_clip, t_clip.set_start(prev_clip.end)])
                    next_clip = CompositeVideoClip([clip.set_start(0), t_clip.set_start(0)])
                    clips[-1] = next_clip
                    logging.info(f"Overlayed transition {os.path.basename(t_file)} at scene {idx}")
        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(AudioFileClip(voiceover_path).set_duration(video.duration))
    except Exception as e:
        logging.exception("Video creation failed")
        return

    try:
        logging.info("Adding voiceover audio...")
        audio = AudioFileClip(voiceover_path).set_duration(video.duration)
        video = video.set_audio(audio)
    except Exception as e:
        logging.exception("Audio sync failed")
        return

    # Optional: Add background music with fade in/out
    composite_audio = None
    if music_tracks:
        try:
            logging.info("Downloading background music...")
            music_clips = []
            for track in music_tracks:
                path = download_music(track["url"], f"music_{os.path.basename(track['url'])}")
                music = (AudioFileClip(path)
                         .volumex(track.get("volume", 0.2))
                         .set_duration(video.duration)
                         .audio_fadein(2)
                         .audio_fadeout(2))
                music_clips.append(music)
            composite_audio = CompositeAudioClip([audio] + music_clips)
        except Exception as e:
            logging.exception("Background music sync failed")
            return
    else:
        composite_audio = audio

    # --- Sound Effects (SFX) at scene transitions ---
    sfx_config = config.get("sound_effects", {})
    if sfx_config.get("enabled", False):
        try:
            import glob
            sfx_folder = sfx_config.get("folder", "sfx/")
            sfx_timing = sfx_config.get("timing", "between")
            sfx_volume = sfx_config.get("volume", 0.7)
            sfx_types = sfx_config.get("types", {})  # e.g. {"slide": ["slide", "whoosh"], "pop": ["pop"]}
            sfx_fade_ms = sfx_config.get("fade_ms", 200)  # fade-in/out in ms
            sfx_files = glob.glob(os.path.join(sfx_folder, "*.mp3")) + glob.glob(os.path.join(sfx_folder, "*.wav"))
            if not sfx_files:
                logging.warning(f"No SFX files found in {sfx_folder}")
            else:
                from pydub import AudioSegment
                temp_audio_path = "_temp_final_audio.wav"
                composite_audio.write_audiofile(temp_audio_path)
                final_audio = AudioSegment.from_file(temp_audio_path)
                os.remove(temp_audio_path)

                # Scene transition times (in ms)
                transition_times = []
                scene_durations = [math.ceil(d/1000) for d in durations]
                t = 0
                for dur in scene_durations[:-1]:
                    t += dur * 1000
                    transition_times.append(t)
                # SFX insertion logic
                sfx_insert_times = []
                if sfx_timing == "between":
                    sfx_insert_times = transition_times
                elif sfx_timing == "random":
                    sfx_insert_times = random.sample(transition_times, k=min(len(transition_times), len(sfx_files)))
                elif sfx_timing == "start":
                    sfx_insert_times = [0]
                elif sfx_timing == "end":
                    sfx_insert_times = [len(final_audio) - 1000]
                # Per-scene SFX type matching
                scene_types = []
                if "scene_types" in config:
                    scene_types = config["scene_types"]  # e.g. ["slide", "pop", ...] per scene
                # Overlay SFX
                for i, insert_time in enumerate(sfx_insert_times):
                    sfx_path = None
                    if scene_types and i < len(scene_types) and sfx_types:
                        # Try to match SFX type for this scene transition
                        s_type = scene_types[i]
                        candidates = []
                        for k, v in sfx_types.items():
                            if s_type == k or s_type in v:
                                # Find sfx files that match type keyword
                                candidates += [f for f in sfx_files if any(word in os.path.basename(f).lower() for word in v+[k])]
                        if candidates:
                            sfx_path = random.choice(candidates)
                    if not sfx_path:
                        sfx_path = random.choice(sfx_files)
                    sfx = AudioSegment.from_file(sfx_path).apply_gain(20 * (sfx_volume - 1))
                    # Add fade in/out
                    if sfx_fade_ms > 0:
                        sfx = sfx.fade_in(sfx_fade_ms).fade_out(sfx_fade_ms)
                    final_audio = final_audio.overlay(sfx, position=insert_time)
                    logging.info(f"Inserted SFX {os.path.basename(sfx_path)} at {insert_time/1000:.2f}s (type: {scene_types[i] if scene_types and i < len(scene_types) else 'any'})")
                final_audio.export("_temp_final_audio_sfx.wav", format="wav")
                composite_audio = AudioFileClip("_temp_final_audio_sfx.wav").set_duration(video.duration)
        except Exception as e:
            logging.exception("Sound effects insertion failed")

    video = video.set_audio(composite_audio)

    # Subtitles: Deepgram transcription
    try:
        logging.info("Transcribing audio for subtitles (Deepgram)...")
        transcript, srt = transcribe_audio_deepgram(voiceover_path)
        srt_path = output.replace(".mp4", ".srt")
        save_srt(srt, srt_path)
        logging.info(f"Subtitles saved to {srt_path}")

        # Optionally burn subtitles into video
        if config.get("burn_subtitles", False):
            try:
                import ffmpeg
                logging.info("Burning subtitles into video using ffmpeg-python...")
                temp_burned = output.replace(".mp4", "_subtitled.mp4")
                (
                    ffmpeg
                    .input(output)
                    .output(temp_burned, vf=f"subtitles={srt_path}", c="copy")
                    .overwrite_output()
                    .run()
                )
                os.replace(temp_burned, output)
                logging.info("Subtitles burned into video.")
            except ImportError:
                logging.warning("ffmpeg-python not installed, cannot burn subtitles. Run: pip install ffmpeg-python")
            except Exception as e:
                logging.exception("Failed to burn subtitles into video.")
    except Exception as e:
        logging.exception("Subtitle generation failed")
        # Not fatal, continue

    logging.info(f"Rendering final video to {output}...")
    video.write_videofile(output, fps=24, codec='libx264', audio_codec='aac')
    logging.info("Done!")

    duration = video.duration
    elapsed = time.time() - start_time
    logging.info(f"Generated {len(scenes)} scenes")
    logging.info(f"Final video duration: {duration:.2f} seconds")
    logging.info(f"Pipeline completed in {elapsed:.2f} seconds")

    # Clean up temp images
    for img in image_paths:
        if os.path.exists(img):
            os.remove(img)
    if music_tracks:
        for track in music_tracks:
            path = f"music_{os.path.basename(track['url'])}"
            if os.path.exists(path):
                os.remove(path)
