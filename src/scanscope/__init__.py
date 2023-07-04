import importlib.metadata

_name = __package__ or __name__
try:
    __version__ = importlib.metadata.version(_name)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0.not-a-package"

