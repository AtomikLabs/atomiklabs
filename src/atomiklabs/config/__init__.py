from .settings import get_config

# Single exported instance - follows the singleton pattern
config = get_config()

__all__ = ["config"]
