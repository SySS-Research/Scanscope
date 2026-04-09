"""Clustering and projection parameter optimization using Bayesian optimization.

Optimizes HDBSCAN clustering parameters and projection parameters (UMAP or PCA).

This module requires the 'optimize' dependency group:
    uv sync --group optimize
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.manifold import trustworthiness

try:
    import optuna  # type: ignore[import-untyped]
    from optuna.trial import Trial  # type: ignore[import-untyped]
except ImportError as e:
    raise ImportError("Optuna is required for parameter optimization. Install it with: uv sync --group optimize") from e

from scanscope.data import DataResult, HDBSCANParams, UMAPParams, reduce, transform_data
from scanscope.parser import PortScan

log = logging.getLogger(__name__)


def fingerprint_clustering_quality(df: pd.DataFrame) -> float:
    """Measure how well fingerprints cluster in 2D space.

    Returns the ratio of within-fingerprint variance to between-fingerprint
    variance. Lower values indicate better clustering (tight groups, well separated).

    Args:
        df: DataFrame with columns 'x', 'y', and 'fingerprint'

    Returns:
        Float ratio (lower is better)
    """
    # Remove rows with no fingerprint (no open ports)
    df_with_fp = df[df["fingerprint"].notna()].copy()

    if len(df_with_fp) < 2:
        return float("inf")

    # Within-fingerprint variance (should be small)
    within_var_by_fp = df_with_fp.groupby("fingerprint")[["x", "y"]].var()
    within_var = float(np.mean(within_var_by_fp.to_numpy()))

    # Between-fingerprint separation (should be large)
    centroids = df_with_fp.groupby("fingerprint")[["x", "y"]].mean()
    if len(centroids) < 2:
        return float("inf")

    between_var = float(np.mean(centroids.to_numpy().var(axis=0)))

    if between_var == 0:
        return float("inf")

    return within_var / between_var


def trustworthiness_score(
    high_dim_data: pd.DataFrame, embedding: pd.DataFrame | np.ndarray, n_neighbors: int = 10
) -> float:
    """Measure how well local neighborhoods are preserved in the embedding.

    Uses sklearn's trustworthiness metric which checks if points that are close
    in the 2D embedding were also close in the high-dimensional space.

    Args:
        high_dim_data: Original high-dimensional data
        embedding: 2D embedding (DataFrame with 'x', 'y' or numpy array)
        n_neighbors: Number of neighbors to consider

    Returns:
        Score between 0 and 1 (higher is better, 1 is perfect)
    """
    if isinstance(embedding, pd.DataFrame):
        embedding_array = embedding[["x", "y"]].values
    else:
        embedding_array = embedding

    # Adjust n_neighbors if dataset is small
    actual_n_neighbors = min(n_neighbors, len(embedding_array) - 1)

    if actual_n_neighbors < 1:
        return 0.0

    return float(trustworthiness(high_dim_data, embedding_array, n_neighbors=actual_n_neighbors))


def combined_fitness(
    df: pd.DataFrame,
    high_dim_data: pd.DataFrame,
    alpha: float = 1.0,
    beta: float = 1.0,
    n_neighbors: int = 10,
) -> float:
    """Combined fitness function for UMAP parameter tuning.

    Combines trustworthiness (neighborhood preservation) with fingerprint
    clustering quality. Higher scores are better.

    Args:
        df: Result DataFrame with 'x', 'y', 'fingerprint' columns
        high_dim_data: Original high-dimensional sparse data
        alpha: Weight for trustworthiness component (default 1.0)
        beta: Weight for clustering quality component (default 1.0)
        n_neighbors: Number of neighbors for trustworthiness calculation

    Returns:
        Combined score (higher is better), 0.0 if computation fails
    """
    # Check for NaN values in embedding
    if df[["x", "y"]].isna().any(axis=None):  # type: ignore[call-overload]
        log.warning("NaN values detected in embedding, returning 0.0")
        return 0.0

    try:
        trust_score = trustworthiness_score(high_dim_data, df, n_neighbors)
        if np.isnan(trust_score):
            log.warning("Trustworthiness score is NaN, returning 0.0")
            return 0.0
    except Exception as e:
        log.warning(f"Trustworthiness calculation failed: {e}")
        return 0.0

    try:
        # Clustering quality returns lower=better, so we invert it
        cluster_quality = fingerprint_clustering_quality(df)
        cluster_score = 1.0 / (1.0 + cluster_quality) if cluster_quality != float("inf") else 0.0

        if np.isnan(cluster_score):
            log.warning("Cluster score is NaN, using only trustworthiness")
            cluster_score = 0.0
    except Exception as e:
        log.warning(f"Clustering quality calculation failed: {e}")
        cluster_score = 0.0

    final_score = alpha * trust_score + beta * cluster_score

    # Final safety check
    if np.isnan(final_score):
        log.warning("Final score is NaN, returning 0.0")
        return 0.0

    return final_score


def objective(
    trial: Trial,
    portscan: PortScan,
    fitness_alpha: float = 1.0,
    fitness_beta: float = 1.0,
    fitness_n_neighbors: int = 10,
    pre_deduplicate: bool = False,
    post_deduplicate: bool = False,
    remove_empty: bool = False,
    extended_search: bool = False,
    save_trial_plots: bool = False,
    trial_plots_dir: str | None = None,
    projection: str = "umap",
    cluster_on: str = "original",
) -> float:
    """Objective function for clustering and projection optimization.

    Args:
        trial: Optuna trial object
        portscan: PortScan data to optimize on
        fitness_alpha: Weight for trustworthiness in fitness function
        fitness_beta: Weight for clustering quality in fitness function
        fitness_n_neighbors: Number of neighbors for trustworthiness calculation
        pre_deduplicate: Whether to deduplicate before processing
        post_deduplicate: Whether to deduplicate after processing
        remove_empty: Whether to remove hosts with no open ports
        extended_search: Enable extended parameter search space
        save_trial_plots: Whether to save HTML bubble charts for each trial
        trial_plots_dir: Directory to save trial plots
        projection: Projection method ('pca' or 'umap')
        cluster_on: What to cluster on - 'original' (high-dim) or 'projection' (2D)

    Returns:
        Combined fitness score (higher is better)
    """
    # Set numpy seed for reproducibility
    np.random.seed(42)

    # Suggest projection hyperparameters (UMAP only, PCA has no tunable params)
    if projection.lower() == "pca":
        # PCA has no tunable parameters for our use case
        umap_params = UMAPParams()  # Unused but needed for interface
    else:  # UMAP
        n_neighbors = trial.suggest_int("n_neighbors", 2, 100 if extended_search else 50)
        min_dist = trial.suggest_float("min_dist", 0.0, 0.99 if extended_search else 0.5)
        umap_metric = trial.suggest_categorical("umap_metric", ["euclidean", "cosine", "hamming"])

        if extended_search:
            spread = trial.suggest_float("spread", 0.5, 3.0)
            negative_sample_rate = trial.suggest_int("negative_sample_rate", 1, 20)
        else:
            spread = 1.0
            negative_sample_rate = 5

        umap_params = UMAPParams(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric=umap_metric,
            spread=spread,
            negative_sample_rate=negative_sample_rate,
        )

    # Suggest HDBSCAN hyperparameters
    min_cluster_size = trial.suggest_int("min_cluster_size", 5, 100 if extended_search else 50)
    min_samples = trial.suggest_int("min_samples", 1, 20 if extended_search else 10)
    cluster_metric = trial.suggest_categorical("cluster_metric", ["hamming", "euclidean", "manhattan"])
    cluster_selection_epsilon = trial.suggest_float("cluster_selection_epsilon", 0.0, 1.0 if extended_search else 0.5)

    # Create HDBSCAN parameter object
    hdbscan_params = HDBSCANParams(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=cluster_metric,
        cluster_selection_epsilon=cluster_selection_epsilon,
    )

    # Run clustering + projection
    try:
        result = reduce(
            portscan,
            umap_params=umap_params,
            hdbscan_params=hdbscan_params,
            pre_deduplicate=pre_deduplicate,
            post_deduplicate=post_deduplicate,
            remove_empty=remove_empty,
            random_state=42,  # Fixed seed for reproducibility
            projection=projection,
            cluster_on=cluster_on,
        )
    except Exception as e:
        raise
        import traceback

        log.error(f"Hybrid reduction failed with params {trial.params}: {e}")
        log.debug(f"Full traceback:\n{traceback.format_exc()}")
        return 0.0

    # Calculate fitness
    # If post_deduplicate is used, high_dim_data must also be deduplicated to match result shape
    high_dim_data = transform_data(portscan.hosts, deduplicate=pre_deduplicate or post_deduplicate)[0]

    try:
        score = combined_fitness_hdbscan(
            df=result.dataframe,
            high_dim_data=high_dim_data,
            alpha=fitness_alpha,
            beta=fitness_beta,
            n_neighbors=fitness_n_neighbors,
        )
    except Exception as e:
        log.warning(f"Fitness calculation failed: {e}")
        return 0.0

    # Save trial visualization if requested
    if save_trial_plots and trial_plots_dir:
        try:
            import pathlib

            from bokeh.embed import file_html
            from bokeh.resources import CDN

            from scanscope.html import get_bokeh_plot

            plot_dir = pathlib.Path(trial_plots_dir)
            plot_dir.mkdir(parents=True, exist_ok=True)

            plot = get_bokeh_plot(result, title=f"Trial {trial.number} (score: {score:.4f})")
            output_path = plot_dir / f"trial_{trial.number:04d}.html"
            html = file_html(plot, CDN, f"Trial {trial.number}")
            output_path.write_text(html)

            log.info(f"Saved trial {trial.number} to {output_path}")
        except Exception as e:
            import traceback

            log.error(f"Failed to save trial plot for trial {trial.number}: {e}")
            log.debug(traceback.format_exc())

    return score


def optimize_parameters(
    portscan: PortScan,
    n_trials: int = 50,
    timeout: int | None = None,
    n_jobs: int = 1,
    study_name: str | None = None,
    storage: str | None = None,
    fitness_alpha: float = 1.0,
    fitness_beta: float = 1.0,
    fitness_n_neighbors: int = 10,
    pre_deduplicate: bool = False,
    post_deduplicate: bool = False,
    remove_empty: bool = False,
    extended_search: bool = False,
    show_progress_bar: bool = True,
    save_trial_plots: bool = False,
    trial_plots_dir: str | None = None,
    projection: str = "umap",
    cluster_on: str = "original",
) -> optuna.Study:
    """Optimize clustering and projection parameters using Bayesian optimization.

    Optimizes HDBSCAN clustering parameters and optionally UMAP projection parameters
    (PCA has no tunable parameters) to find the best combination for your port scan data.

    Args:
        portscan: PortScan data to optimize on
        n_trials: Number of optimization trials to run
        timeout: Maximum time in seconds (None for no limit)
        n_jobs: Number of parallel jobs (-1 for all cores)
        study_name: Name for the study (for resuming)
        storage: Database URL for persistence (e.g., 'sqlite:///optuna.db')
        fitness_alpha: Weight for trustworthiness in fitness function
        fitness_beta: Weight for clustering quality in fitness function
        fitness_n_neighbors: Number of neighbors for trustworthiness calculation
        pre_deduplicate: Whether to deduplicate before processing
        post_deduplicate: Whether to deduplicate after processing
        remove_empty: Whether to remove hosts with no open ports
        extended_search: Enable extended parameter space (wider ranges, more parameters)
        show_progress_bar: Whether to show progress bar
        save_trial_plots: Whether to save HTML bubble charts for each trial
        trial_plots_dir: Directory to save trial plots (e.g., 'trials/')
        projection: Projection method ('pca' or 'umap', default 'umap')
        cluster_on: What to cluster on - 'original' (high-dim) or 'projection' (2D)

    Returns:
        Completed Optuna study object

    Example:
        >>> study = optimize_parameters(portscan, n_trials=30, n_jobs=4)
        >>> print(f"Best params: {study.best_params}")
        >>> print(f"Best score: {study.best_value:.4f}")
        >>> # Extended search with more parameters
        >>> study = optimize_parameters(portscan, n_trials=100, extended_search=True)
    """
    # Create or load study with deterministic sampler
    sampler = optuna.samplers.TPESampler(seed=42)  # Fixed seed for reproducible parameter suggestions
    study = optuna.create_study(
        direction="maximize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        sampler=sampler,
    )

    cluster_mode = "on 2D projection" if cluster_on == "projection" else "on high-dim data"
    log.info(
        f"Starting HDBSCAN clustering "
        f"({cluster_mode}) + {projection.upper()} projection optimization with {n_trials} trials..."
    )

    # Run optimization
    study.optimize(
        lambda trial: objective(
            trial,
            portscan,
            fitness_alpha=fitness_alpha,
            fitness_beta=fitness_beta,
            fitness_n_neighbors=fitness_n_neighbors,
            pre_deduplicate=pre_deduplicate,
            post_deduplicate=post_deduplicate,
            remove_empty=remove_empty,
            extended_search=extended_search,
            save_trial_plots=save_trial_plots,
            trial_plots_dir=trial_plots_dir,
            projection=projection,
            cluster_on=cluster_on,
        ),
        n_trials=n_trials,
        timeout=timeout,
        n_jobs=n_jobs,
        show_progress_bar=show_progress_bar,
    )

    log.info(f"Optimization complete. Best score: {study.best_value:.4f}")
    log.info(f"Best parameters: {study.best_params}")

    return study


def print_study_results(study: optuna.Study) -> None:
    """Print formatted optimization results.

    Args:
        study: Completed Optuna study
    """
    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"\nBest score: {study.best_value:.4f}")
    print("\nBest parameters:")
    for param, value in study.best_params.items():
        print(f"  {param}: {value}")

    print(f"\nNumber of trials: {len(study.trials)}")
    print(f"Number of pruned trials: {len(study.get_trials(states=[optuna.trial.TrialState.PRUNED]))}")
    print(f"Number of complete trials: {len(study.get_trials(states=[optuna.trial.TrialState.COMPLETE]))}")

    # Top 5 trials
    print("\nTop 5 trials:")
    for i, trial in enumerate(study.best_trials[:5], 1):
        print(f"\n  {i}. Score: {trial.value:.4f}")
        print(f"     Params: {trial.params}")


def visualize_study(study: optuna.Study, output_dir: str = ".") -> None:
    """Generate and save optimization visualizations.

    Args:
        study: Completed Optuna study
        output_dir: Directory to save plots

    Note:
        Requires matplotlib and plotly for full visualization support.
    """
    try:
        from optuna.visualization import (  # type: ignore[import-untyped]
            plot_optimization_history,
            plot_parallel_coordinate,
            plot_param_importances,
            plot_slice,
        )
    except ImportError:
        log.warning("Optuna visualization requires plotly. Install with: pip install plotly")
        return

    import pathlib

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Optimization history
    fig = plot_optimization_history(study)
    fig.write_html(str(output_path / "optimization_history.html"))

    # Parameter importances
    try:
        fig = plot_param_importances(study)
        fig.write_html(str(output_path / "param_importances.html"))
    except Exception as e:
        log.warning(f"Could not generate parameter importance plot: {e}")

    # Parallel coordinate plot
    fig = plot_parallel_coordinate(study)
    fig.write_html(str(output_path / "parallel_coordinate.html"))

    # Slice plot
    fig = plot_slice(study)
    fig.write_html(str(output_path / "slice_plot.html"))

    log.info(f"Visualizations saved to {output_path}")


def run_with_best_params(study: optuna.Study, portscan: PortScan, **kwargs: Any) -> DataResult:
    """Run UMAP with the best parameters from optimization.

    Args:
        study: Completed Optuna study
        portscan: PortScan data
        **kwargs: Additional arguments to pass to reduce()

    Returns:
        DataResult with optimized parameters
    """
    best_params = study.best_params
    log.info(f"Running UMAP with best parameters: {best_params}")

    return reduce(portscan, **best_params, **kwargs)


def hdbscan_clustering_score(df: pd.DataFrame) -> float:
    """Score HDBSCAN clustering quality.

    Combines cluster separation with outlier ratio. Higher is better.

    Args:
        df: DataFrame with 'x', 'y', and 'cluster' columns

    Returns:
        Score between 0 and 1 (higher is better)
    """
    if "cluster" not in df.columns:
        return 0.0

    cluster_labels = df["cluster"].values
    n_clusters = len([c for c in np.unique(cluster_labels) if c != -1])  # type: ignore[arg-type]
    n_outliers = int(np.sum(cluster_labels == -1))  # type: ignore[arg-type]
    n_total = len(cluster_labels)

    if n_clusters == 0:
        return 0.0

    # Penalize excessive outliers (>30%) but allow some
    outlier_ratio = n_outliers / n_total
    outlier_penalty = 1.0 - min(outlier_ratio / 0.3, 1.0)

    # Reward having a reasonable number of clusters (not too few, not too many)
    # Optimal range: 5-50 clusters
    if n_clusters < 5:
        cluster_count_score = n_clusters / 5.0
    elif n_clusters <= 50:
        cluster_count_score = 1.0
    else:
        cluster_count_score = 50.0 / n_clusters

    # Measure cluster separation using silhouette-like metric
    try:
        from sklearn.metrics import silhouette_score

        # Only compute if we have multiple clusters and enough points
        if n_clusters > 1 and n_total - n_outliers >= n_clusters * 2:
            # Exclude outliers from silhouette calculation
            mask = cluster_labels != -1
            if int(np.sum(mask)) > n_clusters * 2:  # type: ignore[arg-type]
                separation_score = silhouette_score(df.loc[mask, ["x", "y"]].values, cluster_labels[mask])  # type: ignore[index]
                # Convert from [-1, 1] to [0, 1]
                separation_score = (separation_score + 1.0) / 2.0
            else:
                separation_score = 0.5
        else:
            separation_score = 0.5
    except Exception as e:
        log.warning(f"Silhouette score calculation failed: {e}")
        separation_score = 0.5

    # Combined score
    score = 0.4 * separation_score + 0.3 * outlier_penalty + 0.3 * cluster_count_score
    return float(score)


def combined_fitness_hdbscan(
    df: pd.DataFrame,
    high_dim_data: pd.DataFrame,
    alpha: float = 1.0,
    beta: float = 1.0,
    n_neighbors: int = 10,
) -> float:
    """Combined fitness function for HDBSCAN parameter tuning.

    Combines trustworthiness (neighborhood preservation) with clustering quality.
    Higher scores are better.

    Args:
        df: Result DataFrame with 'x', 'y', 'cluster' columns
        high_dim_data: Original high-dimensional sparse data
        alpha: Weight for trustworthiness component (default 1.0)
        beta: Weight for clustering quality component (default 1.0)
        n_neighbors: Number of neighbors for trustworthiness calculation

    Returns:
        Combined score (higher is better), 0.0 if computation fails
    """
    # Check for NaN values in embedding
    if df[["x", "y"]].isna().any(axis=None):  # type: ignore[call-overload]
        log.warning("NaN values detected in embedding, returning 0.0")
        return 0.0

    try:
        trust_score = trustworthiness_score(high_dim_data, df, n_neighbors)
        if np.isnan(trust_score):
            log.warning("Trustworthiness score is NaN, returning 0.0")
            return 0.0
    except Exception as e:
        log.warning(f"Trustworthiness calculation failed: {e}")
        return 0.0

    try:
        cluster_score = hdbscan_clustering_score(df)
        if np.isnan(cluster_score):
            log.warning("Cluster score is NaN, using only trustworthiness")
            cluster_score = 0.0
    except Exception as e:
        log.warning(f"Clustering score calculation failed: {e}")
        cluster_score = 0.0

    final_score = alpha * trust_score + beta * cluster_score

    # Final safety check
    if np.isnan(final_score):
        log.warning("Final score is NaN, returning 0.0")
        return 0.0

    return final_score
