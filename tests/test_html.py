import os
import pickle
from pathlib import Path
import base64
import re

import pytest


SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def html_directory(request, reduced_portscan_data):
    from scanscope.html import write_html
    from scanscope.html import get_bokeh_plot
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="scanscope_pytest_") as tmpdir:
        bokeh_plot = get_bokeh_plot(reduced_portscan_data)
        context = {}
        context.update(report=reduced_portscan_data["portscan"]["report"])
        sqlite_db = b"\0"*128
        write_html(bokeh_plot, "TestTitle", tmpdir, context, sqlite_db=sqlite_db)

        yield tmpdir


def test_write_html(html_directory):
    files = os.listdir(html_directory)
    sqlite_db = b"\0"*128

    for file in ["diagram", "index", "hosts", "info", "licenses"]:
        assert f"{file}.html" in files
        html = open(Path(html_directory) / f"{file}.html", "r").read()
        assert "bootstrap.bundle.min.js" in html
        assert "bootstrap.min.css" in html
        assert base64.b64encode(sqlite_db).decode() in html
        assert re.search(r'.*wasm_codearray = ".+".*', html)


def test_get_bokeh_html():
    from bs4 import BeautifulSoup
    from bokeh.plotting import figure
    import jinja2

    from scanscope.html import get_bokeh_html

    loader = jinja2.FileSystemLoader(
        SCRIPT_PATH / ".." / "src" / "scanscope" / "templates"
    )
    scanscope_env = jinja2.Environment(loader=loader)

    plot = figure()
    context = {"theme": "dark", "report": {}}

    html = get_bokeh_html(scanscope_env, plot, "Title", ["diagram-aux.js"], [], context)

    BeautifulSoup(html, "lxml")

    assert '<div id="hosts-details">' in html
    assert '<div id="bokeh-div">' in html
    assert "diagram-aux.js" in html
    assert 'id="sidebar"' in html
    assert "@@@BOKEH_DIV@@@" not in html
    assert "data-root-id" in html


def test_interactive_html_output(reduced_portscan_data):
    # Only generate output for interactive testing
    from scanscope.html import write_output
    from scanscope.html import get_bokeh_plot

    os.environ["SCANSCOPE_DEBUG"] = "true"

    tmpdir = SCRIPT_PATH / "_output" / "default"
    bokeh_plot = get_bokeh_plot(reduced_portscan_data)
    write_output(reduced_portscan_data, bokeh_plot, "TestTitle", tmpdir)


@pytest.fixture(scope="session")
def portscan_data(request):
    data = request.config.cache.get("portscan_data", None)

    if data is None:
        from scanscope.parser import read_input

        data = read_input([SCRIPT_PATH / "data" / "server-range.xml"])

        data = pickle.dumps(data).decode('cp437')
        request.config.cache.set("portscan_data", data)

    data = pickle.loads(data.encode('cp437'))
    return data


@pytest.fixture(scope="session")
def reduced_portscan_data(request, portscan_data):
    import pandas
    from io import StringIO

    data = request.config.cache.get("reduced_portscan_data", None)

    # DataFrames can't be pickled, NmapReport can't be JSON serialized ...

    if data is None:
        from scanscope.data import reduce

        data = reduce(
            portscan_data,
            post_deduplicate=True,
            pre_deduplicate=False,
        )

        data["dataframe"] = data["dataframe"].to_json()
        data["portscan"] = pickle.dumps(data["portscan"]).decode('cp437')
        request.config.cache.set("reduced_portscan_data", data)

    data["portscan"] = pickle.loads(data["portscan"].encode('cp437'))
    data["dataframe"] = pandas.read_json(StringIO(data["dataframe"]))
    return data
