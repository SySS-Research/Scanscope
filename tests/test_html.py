import base64
import os
import pickle
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from scanscope.data import DataResult
from scanscope.parser import PortScan

SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def html_directory(request: pytest.FixtureRequest, reduced_portscan_data: DataResult) -> Generator[str, None, None]:
    from tempfile import TemporaryDirectory

    from scanscope.html import get_bokeh_plot, write_html

    with TemporaryDirectory(prefix="scanscope_pytest_") as tmpdir:
        bokeh_plot = get_bokeh_plot(reduced_portscan_data)
        context: dict[str, Any] = {
            "report": reduced_portscan_data.portscan.reports[0],
            "reports": reduced_portscan_data.portscan.reports,
            "title": "Test",
        }
        sqlite_db = b"\0" * 128
        write_html(bokeh_plot, tmpdir, context, sqlite_db=sqlite_db)

        yield tmpdir


def test_write_html(html_directory: str) -> None:
    files = os.listdir(html_directory)
    sqlite_db = b"\0" * 128

    for file in ["bubble-chart", "index", "hosts", "info", "licenses"]:
        assert f"{file}.html" in files
        html = open(Path(html_directory) / f"{file}.html").read()
        assert "bootstrap.bundle.min.js" in html
        assert "bootstrap.min.css" in html
        assert base64.b64encode(sqlite_db).decode() in html
        assert re.search(r'.*wasm_codearray = ".+".*', html)


def test_get_bokeh_html() -> None:
    import jinja2
    from bokeh.plotting import figure
    from bs4 import BeautifulSoup

    from scanscope.html import get_bokeh_html

    loader = jinja2.FileSystemLoader(SCRIPT_PATH / ".." / "src" / "scanscope" / "templates")
    scanscope_env = jinja2.Environment(loader=loader)

    plot = figure()
    context: dict[str, Any] = {"title": "Title"}

    html = get_bokeh_html(scanscope_env, plot, ["bubble-chart-aux.js"], [], context)

    BeautifulSoup(html, "lxml")

    assert '<div id="hosts-details">' in html
    assert '<div id="bokeh-div">' in html
    assert "bubble-chart-aux.js" in html
    assert 'id="sidebar"' in html
    assert "@@@BOKEH_DIV@@@" not in html
    assert "data-root-id" in html


def test_interactive_html_output(reduced_portscan_data: DataResult) -> None:
    # Only generate output for interactive testing
    from scanscope.html import get_bokeh_plot, write_output

    os.environ["SCANSCOPE_DEBUG"] = "true"

    tmpdir = SCRIPT_PATH / "_output" / "default"
    bokeh_plot = get_bokeh_plot(reduced_portscan_data)
    write_output(reduced_portscan_data, bokeh_plot, "TestTitle", str(tmpdir))


@pytest.fixture(scope="session")
def portscan_data(request: pytest.FixtureRequest) -> PortScan:
    data = request.config.cache.get("portscan_data", None)

    if data is None:
        from scanscope.parser import read_input

        data_result = read_input((str(SCRIPT_PATH / "data" / "server-range.xml"),))

        data = pickle.dumps(data_result).decode("cp437")
        request.config.cache.set("portscan_data", data)

    data_result = pickle.loads(data.encode("cp437"))
    return data_result


@pytest.fixture(scope="session")
def reduced_portscan_data(request: pytest.FixtureRequest, portscan_data: PortScan) -> DataResult:
    from io import StringIO

    import pandas

    from scanscope.data import DataResult

    data = request.config.cache.get("reduced_portscan_data", None)

    # DataFrames can't be pickled, NmapReport can't be JSON serialized ...

    if data is None:
        from scanscope.data import reduce

        data_result = reduce(
            portscan_data,
            post_deduplicate=True,
            pre_deduplicate=False,
        )

        data = {
            "dataframe": data_result.dataframe.to_json(),
            "portscan": pickle.dumps(data_result.portscan).decode("cp437"),
            "fp_map": data_result.fp_map,
        }
        request.config.cache.set("reduced_portscan_data", data)

    result = DataResult(
        portscan=pickle.loads(data["portscan"].encode("cp437")),
        dataframe=pandas.read_json(StringIO(data["dataframe"])),
        fp_map=data["fp_map"],
    )
    return result
