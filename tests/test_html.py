import os
from pathlib import Path


SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


def test_write_html():
    from scanscope.html import write_html
    from bokeh.plotting import figure
    from tempfile import TemporaryDirectory

    plot_figure = figure()

    with TemporaryDirectory(prefix="scanscope_pytest_") as tmpdir:
        write_html(plot_figure, "TestTitle", [], tmpdir)

        files = os.listdir(tmpdir)

        for file in ["diagram", "index", "hosts", "info"]:
            assert f"{file}.html" in files
            html = open(Path(tmpdir) / f"{file}.html", "r").read()
            assert 'bootstrap.bundle.min.js' in html
            assert 'bootstrap.min.css' in html


def test_get_bokeh_template():
    from bs4 import BeautifulSoup
    from bokeh.embed import file_html
    from bokeh.plotting import figure
    import jinja2
    from scanscope.html import get_bokeh_template

    loader = jinja2.FileSystemLoader(SCRIPT_PATH / ".." / "scanscope" / "assets" / "templates")
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
    assert 'foobar.js' in html
    assert 'foobar.css' in html
    assert 'id="sidebar"' in html
    assert '@@@BOKEH_DIV@@@' not in html
    assert 'data-root-id' in html
