import os
from pathlib import Path

import pytest


SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


def test_write_html(bokeh_plot):
    from scanscope.html import write_html
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="scanscope_pytest_") as tmpdir:
        write_html(bokeh_plot, "TestTitle", [], tmpdir)

        files = os.listdir(tmpdir)

        for file in ["diagram", "index", "hosts", "info"]:
            assert f"{file}.html" in files
            html = open(Path(tmpdir) / f"{file}.html", "r").read()
            assert "bootstrap.bundle.min.js" in html
            assert "bootstrap.min.css" in html


def test_get_bokeh_template():
    from bs4 import BeautifulSoup
    from bokeh.embed import file_html
    from bokeh.plotting import figure
    import jinja2
    from scanscope.html import get_bokeh_template

    loader = jinja2.FileSystemLoader(
        SCRIPT_PATH / ".." / "scanscope" / "assets" / "templates"
    )
    scanscope_env = jinja2.Environment(loader=loader)

    template = get_bokeh_template(scanscope_env, ["foobar.css"], ["foobar.js"])

    plot_figure = figure()

    html = file_html(
        plot_figure,
        template=template,
    )

    BeautifulSoup(html, "lxml")

    assert '<div id="hosts-details">' in html
    assert '<div id="bokeh-div">' in html
    assert "foobar.js" in html
    assert "foobar.css" in html
    assert 'id="sidebar"' in html
    assert "@@@BOKEH_DIV@@@" not in html
    assert "data-root-id" in html


def test_html_output(reduced_portscan_data):
    from scanscope.html import write_output
    from scanscope.html import get_bokeh_plot

    tmpdir = SCRIPT_PATH / "_output" / "default"
    bokeh_plot = get_bokeh_plot(reduced_portscan_data)
    write_output(reduced_portscan_data, bokeh_plot, "TestTitle", tmpdir)


@pytest.fixture(scope="session")
def portscan_data(request):
    data = request.config.cache.get("portscan_data", None)

    if data is None:
        from scanscope.parser import read_input

        data = read_input([SCRIPT_PATH / "data" / "server-range.xml"])
        request.config.cache.set("portscan_data", data)

    return data


@pytest.fixture(scope="session")
def reduced_portscan_data(request, portscan_data):
    import pandas
    from io import StringIO

    data = request.config.cache.get("reduced_portscan_data", None)

    if data is None:
        from scanscope.data import reduce

        data = reduce(
            portscan_data,
            post_deduplicate=True,
            pre_deduplicate=False,
        )
        data["dataframe"] = data["dataframe"].to_json()
        request.config.cache.set("reduced_portscan_data", data)

    data["dataframe"] = pandas.read_json(StringIO(data["dataframe"]))
    return data
