import logging
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

from scanscope.__init__ import __version__

if TYPE_CHECKING:
    from scanscope.data import DataResult

log = logging.getLogger(__name__)


def umap_option(*args, **kwargs):
    """Conditional decorator that only adds option if UMAP is available."""
    from scanscope.utils import is_umap_available

    if is_umap_available():
        return click.option(*args, **kwargs)
    else:
        # Return identity decorator if UMAP not available
        return lambda f: f


@dataclass
class Config:
    """Configuration for scanscope run."""

    log_level: str
    output_format: str
    output_path: str | None
    use_cdn: bool
    skip_post_deduplicate: bool
    pre_deduplicate: bool
    remove_empty_host_group: bool
    # UMAP parameters
    n_neighbors: int
    min_dist: float
    umap_metric: str
    spread: float
    negative_sample_rate: int
    # HDBSCAN parameters
    min_cluster_size: int
    min_samples: int | None
    cluster_metric: str
    cluster_selection_epsilon: float
    # General
    projection: str
    cluster_on: str
    random_state: int
    input_files: tuple[str, ...]
    command_line: str


def disable_warnings() -> None:
    """Disable numba deprecation warnings."""
    from numba.core.errors import (
        NumbaDeprecationWarning,
        NumbaPendingDeprecationWarning,
    )

    warnings.simplefilter("ignore", category=NumbaDeprecationWarning)
    warnings.simplefilter("ignore", category=NumbaPendingDeprecationWarning)


def run(config: Config) -> None:
    """Main execution function."""
    log.info("Starting up...")

    from scanscope.writer import write_output_html, write_output_json

    data = process(config)
    if config.output_format == "json":
        write_output_json(data, config.output_path)
    elif config.output_format in ["html", "html-directory"]:
        write_output_html(
            data,
            config.output_path,
            zundler=(config.output_format == "html"),
            use_cdn=config.use_cdn,
            command_line=config.command_line,
        )


def process(config: Config) -> "DataResult":
    """Process input files and perform dimensionality reduction."""
    from scanscope.data import HDBSCANParams, UMAPParams, reduce
    from scanscope.parser import read_input

    portscan = read_input(config.input_files)
    if not portscan:
        log.error("No ports found")
        exit(1)

    cluster_mode = "on 2D projection" if config.cluster_on == "projection" else "on high-dim data"
    log.info(f"Using HDBSCAN clustering ({cluster_mode}) + {config.projection.upper()} visualization")

    # Create parameter objects
    umap_params = UMAPParams(
        n_neighbors=config.n_neighbors,
        min_dist=config.min_dist,
        metric=config.umap_metric,
        spread=config.spread,
        negative_sample_rate=config.negative_sample_rate,
    )

    hdbscan_params = HDBSCANParams(
        min_cluster_size=config.min_cluster_size,
        min_samples=config.min_samples,
        metric=config.cluster_metric,
        cluster_selection_epsilon=config.cluster_selection_epsilon,
    )

    data = reduce(
        portscan,
        umap_params=umap_params,
        hdbscan_params=hdbscan_params,
        post_deduplicate=not config.skip_post_deduplicate,
        pre_deduplicate=config.pre_deduplicate,
        remove_empty=config.remove_empty_host_group,
        random_state=config.random_state,
        projection=config.projection,
        cluster_on=config.cluster_on,
    )
    return data


@click.command(
    help="Visualize portscan results",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__)
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(["INFO", "WARNING", "ERROR", "DEBUG"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="log level",
)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["html-directory", "html", "json"], case_sensitive=False),
    default="html",
    show_default=True,
    help="Output format",
)
@click.option(
    "-E",
    "--remove-empty-host-group",
    is_flag=True,
    help="Remove the group of hosts without open ports",
)
@click.option(
    "-o",
    "--output-path",
    type=str,
    default=None,
    help="Path to the output file/directory (default: stdout)",
)
@click.option(
    "-C",
    "--use-cdn",
    is_flag=True,
    help="Use a CDN instead of embedding dependencies to reduce the file size",
)
@click.option(
    "--skip-post-deduplicate",
    is_flag=True,
    help="DO NOT deduplicate hosts after data reduction",
)
@click.option(
    "--pre-deduplicate",
    is_flag=True,
    help="Deduplicate hosts before data reduction",
)
@click.option(
    "--random-state",
    type=int,
    default=42,
    show_default=True,
    help="Random seed for reproducibility (use different values for varied layouts)",
)
@click.option(
    "--projection",
    type=click.Choice(["pca", "umap"], case_sensitive=False),
    default="pca",
    show_default=True,
    help=(
        "2D projection method: 'pca' (fast, deterministic) or 'umap' "
        "(better visualization, slower, requires umap-learn)"
    ),
)
@click.option(
    "--cluster-on",
    type=click.Choice(["original", "projection"], case_sensitive=False),
    default="projection",
    show_default=True,
    help="What to cluster on: 'original' (high-dim data, more accurate) or 'projection' (2D coordinates, WYSIWYG)",
)
@umap_option(
    "--n-neighbors",
    type=int,
    default=15,
    show_default=True,
    help="[UMAP] n_neighbors parameter: controls local vs global structure (5-50)",
)
@umap_option(
    "--min-dist",
    type=float,
    default=0.8,
    show_default=True,
    help="[UMAP] min_dist parameter: minimum distance between points (0.0-0.99)",
)
@umap_option(
    "--umap-metric",
    type=click.Choice(["euclidean", "cosine", "hamming"], case_sensitive=False),
    default="euclidean",
    show_default=True,
    help="[UMAP] Distance metric for UMAP visualization",
)
@click.option(
    "--cluster-metric",
    type=click.Choice(["hamming", "euclidean", "manhattan"], case_sensitive=False),
    default="euclidean",
    show_default=True,
    help="[HDBSCAN] Distance metric for clustering (hamming recommended for port data)",
)
@umap_option(
    "--spread",
    type=float,
    default=1.0,
    show_default=True,
    help="[UMAP] Spread parameter: scale of embedded space (0.5-3.0)",
)
@umap_option(
    "--negative-sample-rate",
    type=int,
    default=5,
    show_default=True,
    help="[UMAP] Negative sample rate: non-neighbor samples per point (1-20)",
)
@click.option(
    "--min-cluster-size",
    type=int,
    default=5,
    show_default=True,
    help="[HDBSCAN] Minimum cluster size (5-100)",
)
@click.option(
    "--min-samples",
    type=int,
    default=None,
    help="[HDBSCAN] Number of samples for core points (defaults to min_cluster_size)",
)
@click.option(
    "--cluster-selection-epsilon",
    type=float,
    default=0.0,
    show_default=True,
    help="[HDBSCAN] Distance threshold for merging clusters (0.0-1.0)",
)
@click.argument("input_files", nargs=-1, required=True, metavar="INPUT")
def cli(
    log_level: str,
    output_format: str,
    remove_empty_host_group: bool,
    output_path: str | None,
    use_cdn: bool,
    skip_post_deduplicate: bool,
    pre_deduplicate: bool,
    projection: str,
    cluster_on: str,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    umap_metric: str = "euclidean",
    cluster_metric: str = "hamming",
    spread: float = 1.0,
    negative_sample_rate: int = 5,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    cluster_selection_epsilon: float = 0.0,
    random_state: int = 42,
    input_files: tuple[str, ...] = (),
) -> None:
    """CLI entry point."""
    import sys

    from scanscope.data import is_umap_available
    from scanscope.log import init_logging

    init_logging(loglevel=log_level)
    disable_warnings()

    # Check if UMAP is available when needed
    if projection.lower() == "umap" and not is_umap_available():
        click.echo(
            "Error: UMAP projection requires the 'umap-learn' package, which is not installed.\n"
            "Install it with: pip install umap-learn\n"
            "Or use PCA projection instead: --projection pca",
            err=True,
        )
        sys.exit(1)

    # Capture the command line
    command_line = " ".join(sys.argv)

    config = Config(
        log_level=log_level,
        output_format=output_format,
        output_path=output_path,
        use_cdn=use_cdn,
        skip_post_deduplicate=skip_post_deduplicate,
        pre_deduplicate=pre_deduplicate,
        remove_empty_host_group=remove_empty_host_group,
        projection=projection,
        cluster_on=cluster_on,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        umap_metric=umap_metric,
        spread=spread,
        negative_sample_rate=negative_sample_rate,
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_metric=cluster_metric,
        cluster_selection_epsilon=cluster_selection_epsilon,
        random_state=random_state,
        input_files=input_files,
        command_line=command_line,
    )

    run(config)
