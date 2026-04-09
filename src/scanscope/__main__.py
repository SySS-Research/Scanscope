import warnings

# Suppress known warnings
warnings.filterwarnings(
    "ignore", message=".*force_all_finite.*was renamed to.*ensure_all_finite.*", category=FutureWarning
)
warnings.filterwarnings(
    "ignore", message=".*gradient function is not yet implemented for hamming distance.*", category=UserWarning
)
# From hdbscan/robust_single_linkage_.py:154:
warnings.filterwarnings("ignore", message="invalid escape sequence '\\{'", category=SyntaxWarning)


def main(argv: list[str] | None = None) -> None:
    """Entry point for scanscope CLI."""
    from scanscope.args import cli

    cli(argv)  # type: ignore[call-arg]  # Click decorates this function


if __name__ == "__main__":
    main()
