import collections
import logging

import umap.umap_ as umap
import pandas as pd

log = logging.getLogger(__name__)


def transform_data(data, deduplicate=True):
    """Create a sparse DataFrame given the portscan data

    indices 0:2**16-1 are for tcp ports
    indices 2**16:2**32-1 are for udp ports

    0 means closed
    1 means open

    Return: the dataframe, a count of port configuration fingerprints, and a
    dict mapping fingerprints to hosts
    """

    # Create list of dicts that can be converted to a sparse DataFrame
    data_ = []
    fp_count = collections.defaultdict(lambda: 0)
    fp_map = collections.defaultdict(lambda: [])

    for i, (host, props) in enumerate(data.items()):
        row = {}
        for p in props["tcp_ports"]:
            row[p] = 1
        for p in props["udp_ports"]:
            row[2**16 + p] = 1

        fp = props["fingerprint"]
        fp_map[fp].append(host)
        if fp_count[fp] == 0 or not deduplicate:
            data_.append(row)
        fp_count[fp] += 1

    df = pd.DataFrame(data_, index=range(len(data_)), dtype="Sparse")
    df = df.fillna(0)

    return df, fp_count, fp_map


def reduce(
    portscan,
    pre_deduplicate=False,
    post_deduplicate=False,
    remove_empty=False,
    **kwargs,
):
    # Extract kwargs that don't get passed to UMAP()
    if pre_deduplicate and post_deduplicate:
        raise ValueError(
            "'pre_deduplicate' and 'post_deduplicate' must not both be true"
        )
    for k in ["pre_deduplicate", "post_deduplicate"]:
        kwargs.pop(k, None)

    # Perform dimensionality reduction
    reducer = umap.UMAP(**kwargs)

    log.info("Transforming data...")
    data, fp_count, fp_map = transform_data(portscan["hosts"], deduplicate=pre_deduplicate)

    log.info("Reduce...")
    embedding = reducer.fit_transform(data)
    df = pd.DataFrame(embedding, columns=("x", "y"))

    # Add supplemental data to the dataframe
    if pre_deduplicate:
        df["fingerprint"] = list(fp_map.keys())
        df["fp_count"] = list(fp_count.values())
        df["tcp_ports"] = [portscan["hosts"][x[0]]["tcp_ports"] for x in fp_map.values()]
        df["udp_ports"] = [portscan["hosts"][x[0]]["udp_ports"] for x in fp_map.values()]
    else:
        df["fingerprint"] = list(x["fingerprint"] for x in portscan["hosts"].values())
        df["fp_count"] = list(fp_count[x["fingerprint"]] for x in portscan["hosts"].values())
        df["tcp_ports"] = [x["tcp_ports"] for x in portscan["hosts"].values()]
        df["udp_ports"] = [x["udp_ports"] for x in portscan["hosts"].values()]

    if post_deduplicate:
        x = df.groupby(["fingerprint"], dropna=False, sort=False)["x"]
        x = x.mean().reset_index()["x"]

        y = df.groupby(["fingerprint"], dropna=False, sort=False)["y"]
        y = y.mean().reset_index()["y"]

        df.drop_duplicates(subset="fingerprint", inplace=True)
        df["x"] = x.values
        df["y"] = y.values
        # TODO add IPs

    df["color_index"] = list(
        x[:2] if x is not None else "xx" for x in df["fingerprint"]
    )
    if remove_empty:
        df = df[df.fingerprint.notnull()]

    result = {
        "dataframe": df,
        "portscan": portscan,
        "fp_map": fp_map,
    }

    return result


# TODO: find fitness function
