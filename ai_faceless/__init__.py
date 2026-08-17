__version__ = "0.1.0"

def run_pipeline(*args, **kwargs):
    """Lazy-load the heavy generator module when needed."""
    from .generator import run_pipeline as _run
    return _run(*args, **kwargs)
