#!/usr/bin/env python3
"""Example script for optimizing clustering and projection parameters.

This script demonstrates how to use the optimization module to find
the best combination of HDBSCAN clustering and projection (PCA or UMAP)
parameters for your port scan data.

Installation:
    uv sync --group optimize

Usage:
    uv run examples/optimize_umap.py nmap_output.xml --trials 50

For parallel execution:
    uv run examples/optimize_umap.py nmap_output.xml --trials 50 --jobs 4

With PCA projection (faster, no extra parameters to tune):
    uv run examples/optimize_umap.py nmap_output.xml --trials 50 --projection pca

With clustering on 2D projection (may find more generalizable parameters):
    uv run examples/optimize_umap.py nmap_output.xml --trials 50 --cluster-on projection
"""

import argparse
import sys
import warnings
from pathlib import Path

from scanscope.optimize import optimize_parameters, print_study_results, visualize_study
from scanscope.parser import read_input

# Suppress known warnings
warnings.filterwarnings(
    "ignore", message=".*force_all_finite.*was renamed to.*ensure_all_finite.*", category=FutureWarning
)
warnings.filterwarnings(
    "ignore", message=".*gradient function is not yet implemented for hamming distance.*", category=UserWarning
)

warnings.filterwarnings("ignore", message=".*Use no seed for parallelism.*", category=UserWarning)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize HDBSCAN clustering and projection parameters for port scan visualization",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Nmap XML output file")
    parser.add_argument("--trials", type=int, default=50, help="Number of optimization trials")
    parser.add_argument("--timeout", type=int, help="Timeout in seconds (optional)")
    parser.add_argument("--jobs", type=int, default=1, help="Number of parallel jobs (-1 for all cores)")
    parser.add_argument("--study-name", type=str, help="Study name for resuming optimization")
    parser.add_argument("--storage", type=str, help="Database URL (e.g., sqlite:///optuna.db)")
    parser.add_argument("--alpha", type=float, default=1.0, help="Weight for trustworthiness score")
    parser.add_argument("--beta", type=float, default=1.0, help="Weight for clustering quality score")
    parser.add_argument("--visualize", action="store_true", help="Generate visualization plots")
    parser.add_argument("--output-dir", type=Path, default=".", help="Directory for visualizations")
    parser.add_argument("--save-trials", action="store_true", help="Save bubble chart HTML for each trial")
    parser.add_argument("--skip-post-deduplicate", action="store_true", help="Skip deduplication after clustering")
    parser.add_argument("--pre-deduplicate", action="store_true", help="Deduplicate before UMAP")
    parser.add_argument("--remove-empty", action="store_true", help="Remove hosts with no open ports")
    parser.add_argument(
        "--extended-search",
        action="store_true",
        help="Enable extended parameter search (spread, negative_sample_rate, wider ranges)",
    )
    parser.add_argument(
        "--projection",
        type=str,
        default="umap",
        choices=["pca", "umap"],
        help="Projection method: 'pca' (fast, no extra parameters) or 'umap' (more parameters to optimize)",
    )
    parser.add_argument(
        "--cluster-on",
        type=str,
        default="original",
        choices=["original", "projection"],
        help="What to cluster on: 'original' (high-dim data, more accurate) "
        "or 'projection' (2D, may generalize better)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.input.exists():
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)

    # Check if UMAP is available when needed
    if args.projection == "umap":
        from scanscope.data import is_umap_available

        if not is_umap_available():
            print(
                "Error: UMAP projection requires the 'umap-learn' package, which is not installed.",
                file=sys.stderr,
            )
            print("Install it with: pip install umap-learn", file=sys.stderr)
            print("Or use PCA projection instead: --projection pca", file=sys.stderr)
            sys.exit(1)

    # Parse nmap data
    print(f"Parsing {args.input}...")
    portscan = read_input((str(args.input),))
    print(f"Loaded {len(portscan.hosts)} hosts")

    # Run optimization
    if args.save_trials:
        trial_plots_dir = args.output_dir / "trials"
        print(f"Saving trial visualizations to {trial_plots_dir}/")
    else:
        trial_plots_dir = None

    study = optimize_parameters(
        portscan=portscan,
        n_trials=args.trials,
        timeout=args.timeout,
        n_jobs=args.jobs,
        study_name=args.study_name,
        storage=args.storage,
        fitness_alpha=args.alpha,
        fitness_beta=args.beta,
        pre_deduplicate=args.pre_deduplicate,
        post_deduplicate=not args.skip_post_deduplicate,
        remove_empty=args.remove_empty,
        extended_search=args.extended_search,
        save_trial_plots=args.save_trials,
        trial_plots_dir=str(trial_plots_dir) if trial_plots_dir else None,
        projection=args.projection,
        cluster_on=args.cluster_on,
    )

    # Print results
    print_study_results(study)

    # Generate visualizations
    if args.visualize:
        print(f"\nGenerating visualizations in {args.output_dir}...")
        visualize_study(study, output_dir=str(args.output_dir))

    # Demonstrate using best parameters
    print("\nTo use these parameters with scanscope:")
    params = " ".join(f"--{k.replace('_', '-')} {v}" for k, v in study.best_params.items())
    print(
        f"  scanscope {args.input} -o output.html --projection {args.projection} "
        f"--cluster-on {args.cluster_on} {params}"
    )


if __name__ == "__main__":
    main()
