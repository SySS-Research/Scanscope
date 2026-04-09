"""Color assignment functions for different visualization schemes."""

import colorsys
import logging

import pandas as pd

from scanscope.port_categories import categorize_host, get_category_color

log = logging.getLogger(__name__)


def assign_colors_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Assign colors based on port category (web, database, etc.).

    Args:
        df: DataFrame with tcp_ports and udp_ports columns

    Returns:
        DataFrame with added 'category' and 'color' columns
    """
    df = df.copy()

    categories = []
    colors = []

    for _, row in df.iterrows():
        tcp_ports = row["tcp_ports"] if isinstance(row["tcp_ports"], list) else []
        udp_ports = row["udp_ports"] if isinstance(row["udp_ports"], list) else []

        # Ensure lists contain integers
        tcp_ports = list(tcp_ports) if isinstance(tcp_ports, list) else []
        udp_ports = list(udp_ports) if isinstance(udp_ports, list) else []

        category = categorize_host(tcp_ports, udp_ports)
        categories.append(category)
        colors.append(get_category_color(category))

    df["category"] = categories
    df["color"] = colors

    log.info(f"Assigned colors by category: {df['category'].value_counts().to_dict()}")

    return df


def assign_colors_by_cluster(df: pd.DataFrame) -> pd.DataFrame:
    """Assign colors based on cluster ID using perceptually uniform palette.

    Args:
        df: DataFrame with 'cluster' column (from HDBSCAN)

    Returns:
        DataFrame with added 'color' column
    """
    df = df.copy()

    if "cluster" not in df.columns:
        log.warning("No 'cluster' column found, falling back to fingerprint-based coloring")
        return assign_colors_by_fingerprint(df)

    unique_clusters = sorted(df["cluster"].unique())
    n_clusters = len([c for c in unique_clusters if c != -1])

    log.info(f"Assigning colors for {n_clusters} clusters")

    cluster_colors = {}
    cluster_colors[-1] = "#95a5a6"

    non_noise_clusters = [c for c in unique_clusters if c != -1]

    for i, cluster_id in enumerate(non_noise_clusters):
        hue = i / max(n_clusters, 1)
        saturation = 0.7
        value = 0.8

        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        cluster_colors[cluster_id] = color

    df["color"] = df["cluster"].map(cluster_colors)  # type: ignore[arg-type]

    return df


def assign_colors_by_port_count(df: pd.DataFrame) -> pd.DataFrame:
    """Assign colors based on number of open ports (blue=low, red=high).

    Args:
        df: DataFrame with tcp_ports and udp_ports columns

    Returns:
        DataFrame with added 'port_count' and 'color' columns
    """
    df = df.copy()

    port_counts = []
    for _, row in df.iterrows():
        tcp_count = len(row["tcp_ports"]) if isinstance(row["tcp_ports"], list) else 0
        udp_count = len(row["udp_ports"]) if isinstance(row["udp_ports"], list) else 0
        port_counts.append(tcp_count + udp_count)

    df["port_count"] = port_counts

    min_count = min(port_counts) if port_counts else 0
    max_count = max(port_counts) if port_counts else 1
    count_range = max_count - min_count if max_count > min_count else 1

    colors = []

    for count in port_counts:
        normalized = (count - min_count) / count_range

        blue = (52, 152, 219)
        red = (231, 76, 60)

        r = int(blue[0] + (red[0] - blue[0]) * normalized)
        g = int(blue[1] + (red[1] - blue[1]) * normalized)
        b = int(blue[2] + (red[2] - blue[2]) * normalized)

        colors.append(f"#{r:02x}{g:02x}{b:02x}")

    df["color"] = colors

    log.info(f"Port count range: {min_count}-{max_count}, assigned blue-red gradient")

    return df


def assign_colors_by_fingerprint(df: pd.DataFrame) -> pd.DataFrame:
    """Assign colors based on fingerprint hash (current behavior).

    This maintains backwards compatibility with the original color assignment.

    Args:
        df: DataFrame with 'color_index' column

    Returns:
        DataFrame with added 'color' column
    """
    from bokeh import palettes

    df = df.copy()

    color_palette = palettes.Turbo256

    colors = []
    for color_index in df["color_index"]:
        try:
            idx = int(color_index, 16)
        except (ValueError, TypeError):
            idx = 0
        colors.append(color_palette[idx])

    df["color"] = colors

    return df


def assign_all_color_schemes(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Compute all color schemes and store them as separate columns.

    This allows interactive switching in the HTML interface.

    Args:
        df: Input DataFrame
        method: Reduction method ('umap', 'hdbscan', or 'hybrid')

    Returns:
        DataFrame with color columns: color_category, color_cluster, color_port_count, color_fingerprint
    """
    df = df.copy()

    log.info("Computing all color schemes for interactive switching...")

    df_category = assign_colors_by_category(df)
    df["color_category"] = df_category["color"]

    df_cluster = assign_colors_by_cluster(df)
    df["color_cluster"] = df_cluster["color"]

    df_port_count = assign_colors_by_port_count(df)
    df["color_port_count"] = df_port_count["color"]

    df_fingerprint = assign_colors_by_fingerprint(df)
    df["color_fingerprint"] = df_fingerprint["color"]

    if "category" in df_category.columns:
        df["category"] = df_category["category"]
    if "port_count" in df_port_count.columns:
        df["port_count"] = df_port_count["port_count"]

    return df


def assign_colors(df: pd.DataFrame, method: str, scheme: str) -> pd.DataFrame:
    """Assign colors to dataframe based on selected scheme.

    Args:
        df: Input DataFrame
        method: Reduction method ('umap', 'hdbscan', or 'hybrid')
        scheme: Color scheme to use ('auto', 'category', 'cluster', 'port_count', 'fingerprint')

    Returns:
        DataFrame with added color-related columns
    """
    df = assign_all_color_schemes(df, method)

    if scheme == "auto":
        if method.lower() in ("hdbscan", "hybrid") and "cluster" in df.columns:
            log.info("Auto mode: using cluster-based coloring")
            df["color"] = df["color_cluster"]
        else:
            log.info("Auto mode: using category-based coloring")
            df["color"] = df["color_category"]
    elif scheme == "category":
        df["color"] = df["color_category"]
    elif scheme == "cluster":
        df["color"] = df["color_cluster"]
    elif scheme == "port_count":
        df["color"] = df["color_port_count"]
    elif scheme == "fingerprint":
        df["color"] = df["color_fingerprint"]
    else:
        log.warning(f"Unknown color scheme '{scheme}', falling back to 'auto'")
        return assign_colors(df, method, "auto")

    return df
