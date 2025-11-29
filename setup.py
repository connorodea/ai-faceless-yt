from setuptools import setup, find_packages

setup(
    name="ai-faceless-yt",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "moviepy",
        "pydub",
        "python-dotenv",
        "openai",
        "elevenlabs",
        "requests",
        "tqdm",
        "pyyaml",
        "fastapi",
        "uvicorn",
        "Jinja2",
    ],
    entry_points={
        "console_scripts": [
            "generate-video=ai_faceless.generator:run_pipeline",
            "ai-faceless-api=ai_faceless.api:main",
        ]
    },
)