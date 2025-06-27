__all__ = ['profile', 'cli']
__version__ = '0.0.0'

def profile(path: str) -> None:
    from .tracer import profile_script
    profile_script(path)
