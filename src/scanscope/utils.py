def is_umap_available() -> bool:
    """Check if UMAP is available without importing it (avoids heavy import)."""
    import importlib.util

    return importlib.util.find_spec("umap") is not None
