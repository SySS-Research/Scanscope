import collections
import logging
from dataclasses import dataclass

import pandas as pd

from scanscope.parser import HostInfo, PortScan
from scanscope.utils import is_umap_available

log = logging.getLogger(__name__)


@dataclass
class DataResult:
    dataframe: pd.DataFrame
    portscan: PortScan
    fp_map: dict[str | None, list[str]]


@dataclass
class UMAPParams:
    """Parameters for UMAP dimensionality reduction."""

    n_neighbors: int = 15
    min_dist: float = 0.1
    metric: str = "euclidean"
    spread: float = 1.0
    negative_sample_rate: int = 5


@dataclass
class HDBSCANParams:
    """Parameters for HDBSCAN clustering."""

    min_cluster_size: int = 5
    min_samples: int | None = None
    metric: str = "hamming"
    cluster_selection_epsilon: float = 0.0


def transform_data(
    hosts: dict[str, HostInfo], deduplicate: bool = True
) -> tuple[pd.DataFrame, dict[str | None, int], dict[str | None, list[str]]]:
    """Create a sparse DataFrame given the portscan data

    indices 0:2**16-1 are for tcp ports
    indices 2**16:2**32-1 are for udp ports

    0 means closed
    1 means open

    Return: the dataframe, a count of port configuration fingerprints, and a
    dict mapping fingerprints to hosts
    """

    # Create list of dicts that can be converted to a sparse DataFrame
    data_: list[dict[int, int]] = []
    index_: list[str] = []  # Track IP addresses for each row
    fp_count: dict[str | None, int] = collections.defaultdict(lambda: 0)
    fp_map: dict[str | None, list[str]] = collections.defaultdict(lambda: [])

    for _, (host, props) in enumerate(hosts.items()):
        row: dict[int, int] = {}
        for p in props.tcp_ports:
            row[p] = 1
        for p in props.udp_ports:
            row[2**16 + p] = 1

        fp = props.fingerprint
        fp_map[fp].append(host)
        if fp_count[fp] == 0 or not deduplicate:
            data_.append(row)
            index_.append(host)  # Store the IP address for this row
        fp_count[fp] += 1

    df = pd.DataFrame(data_, index=index_, dtype="Sparse")  # type: ignore[call-overload]
    df = df.fillna(0)

    return df, fp_count, fp_map


def _run_pca_projection(data_dense, random_state: int | None):
    """Run PCA projection to 2D."""
    import numpy as np
    from sklearn.decomposition import PCA

    log.info("Running PCA for 2D projection...")
    n_components = min(2, data_dense.shape[0], data_dense.shape[1])
    pca = PCA(n_components=n_components, random_state=random_state)
    pca_coords = pca.fit_transform(data_dense)
    log.info("Explained variance (2 components): %.1f%%", 100 * pca.explained_variance_ratio_.sum())

    # If we only got 1 component, pad with zeros
    if pca_coords.shape[1] == 1:
        return np.hstack([pca_coords, np.zeros((pca_coords.shape[0], 1))])
    return pca_coords


def _run_umap_projection(data_dense, umap_params: UMAPParams, random_state: int | None):
    """Run UMAP projection to 2D."""
    import umap.umap_ as umap  # type: ignore[import-untyped]

    log.info("Running UMAP for 2D projection...")
    reducer = umap.UMAP(
        n_neighbors=umap_params.n_neighbors,
        min_dist=umap_params.min_dist,
        metric=umap_params.metric,
        spread=umap_params.spread,
        negative_sample_rate=umap_params.negative_sample_rate,
        random_state=random_state,
        n_components=2,
        n_jobs=1,  # Force single-threaded for reproducibility
        transform_seed=random_state if random_state is not None else 42,
        init="random",  # Use random init instead of spectral (more stable and deterministic)
    )
    return reducer.fit_transform(data_dense)


def _run_projection(data_dense, projection: str, umap_params: UMAPParams, random_state: int | None):
    """Run 2D projection using either PCA or UMAP."""
    if projection.lower() == "pca":
        return _run_pca_projection(data_dense, random_state)
    else:  # UMAP
        return _run_umap_projection(data_dense, umap_params, random_state)


def _run_clustering(data_dense, hdbscan_params: HDBSCANParams, on_projection: bool = False):
    """Run HDBSCAN clustering."""
    import hdbscan
    import numpy as np

    data_type = "2D projection" if on_projection else "high-dimensional data"
    log.info(f"Clustering with HDBSCAN on {data_type}...")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=hdbscan_params.min_cluster_size,
        min_samples=hdbscan_params.min_samples,
        metric=hdbscan_params.metric,
        cluster_selection_epsilon=hdbscan_params.cluster_selection_epsilon,
    )
    cluster_labels = clusterer.fit_predict(data_dense)

    n_clusters = len([label for label in np.unique(cluster_labels) if label != -1])
    n_outliers = int(np.sum(cluster_labels == -1))
    log.info(f"Found {n_clusters} clusters and {n_outliers} outliers")

    return cluster_labels


def reduce(
    portscan: PortScan,
    umap_params: UMAPParams | None = None,
    hdbscan_params: HDBSCANParams | None = None,
    pre_deduplicate: bool = False,
    post_deduplicate: bool = False,
    remove_empty: bool = False,
    random_state: int | None = 42,
    color_scheme: str = "auto",
    projection: str = "umap",
    cluster_on: str = "original",
) -> DataResult:
    """HDBSCAN clustering + PCA/UMAP visualization.

    Supports two modes:
    - cluster_on="original": Cluster on high-dimensional data, then project to 2D (more accurate)
    - cluster_on="projection": Project to 2D first, then cluster on 2D coordinates (WYSIWYG, may generalize better)

    Args:
        portscan: PortScan data to process
        umap_params: UMAP parameters (uses defaults if None, ignored if projection="pca")
        hdbscan_params: HDBSCAN parameters (uses defaults if None)
        pre_deduplicate: Deduplicate hosts before processing
        post_deduplicate: Deduplicate hosts after processing
        remove_empty: Remove hosts with no open ports
        random_state: Random seed for reproducibility
        color_scheme: Color scheme ('auto', 'category', 'cluster', 'port_count', 'fingerprint')
        projection: Projection method ('pca' or 'umap')
        cluster_on: What to cluster on - 'original' (high-dim data) or 'projection' (2D coordinates)

    Returns:
        DataResult with 2D coordinates and HDBSCAN cluster labels
    """

    if pre_deduplicate and post_deduplicate:
        raise ValueError("'pre_deduplicate' and 'post_deduplicate' must not both be true")

    # Check if UMAP is needed and available
    if projection.lower() == "umap" and not is_umap_available():
        raise ImportError(
            "UMAP is required for UMAP projection but is not installed. Install it with: pip install umap-learn"
        )

    # Use default params if not provided
    if umap_params is None:
        umap_params = UMAPParams()
    if hdbscan_params is None:
        hdbscan_params = HDBSCANParams()

    # Transform data
    log.info("Transforming data...")
    data, fp_count, fp_map = transform_data(portscan.hosts, deduplicate=pre_deduplicate)

    # Store IP addresses before converting to dense array
    ip_addresses = list(data.index)
    data_dense = data.to_numpy()

    # Perform clustering and projection based on mode
    if cluster_on.lower() == "projection":
        # Project to 2D first, then cluster on 2D coordinates
        embedding = _run_projection(data_dense, projection, umap_params, random_state)
        cluster_labels = _run_clustering(embedding, hdbscan_params, on_projection=True)
    else:  # cluster_on == "original"
        # Cluster on high-dimensional data first, then project for visualization
        cluster_labels = _run_clustering(data_dense, hdbscan_params, on_projection=False)
        embedding = _run_projection(data_dense, projection, umap_params, random_state)

    # Create DataFrame with results
    df = pd.DataFrame(
        {
            "ip": ip_addresses,
            "fingerprint": [portscan.hosts[ip].fingerprint for ip in ip_addresses],
            "fp_count": [fp_count[portscan.hosts[ip].fingerprint] for ip in ip_addresses],
            "tcp_ports": [portscan.hosts[ip].tcp_ports for ip in ip_addresses],
            "udp_ports": [portscan.hosts[ip].udp_ports for ip in ip_addresses],
            "x": embedding[:, 0].tolist(),  # type: ignore[index]
            "y": embedding[:, 1].tolist(),  # type: ignore[index]
            "cluster": cluster_labels.tolist(),
        }
    )

    # Post-deduplicate if requested
    if post_deduplicate:
        log.info("Post-deduplicating...")
        grouped = df.groupby("fingerprint", dropna=False)

        # Build deduplicated data
        deduplicated_data = []
        for fingerprint, group in grouped:
            deduplicated_data.append(
                {
                    "ip": ", ".join(str(ip) for ip in group.ip.values),
                    "fingerprint": fingerprint,
                    "fp_count": fp_count.get(fingerprint, len(group)),  # type: ignore[arg-type]  # Default to group size if not found
                    "tcp_ports": group["tcp_ports"].iloc[0],  # Use first host's ports as representative
                    "udp_ports": group["udp_ports"].iloc[0],
                    "x": group["x"].mean(),
                    "y": group["y"].mean(),
                    "cluster": group["cluster"].iloc[0],
                }
            )

        df = pd.DataFrame(deduplicated_data)

    df["color_index"] = [str(x)[:2] if pd.notna(x) and x is not None else "xx" for x in df["fingerprint"]]
    if remove_empty:
        mask = df.fingerprint.notnull()
        df = df.loc[mask].copy()

    from scanscope.colors import assign_colors

    df = assign_colors(df, method="hybrid", scheme=color_scheme)

    result = DataResult(
        dataframe=df,
        portscan=portscan,
        fp_map=fp_map,
    )

    return result
