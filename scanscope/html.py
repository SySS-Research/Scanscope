import os
import math
from pathlib import Path
import shutil

import jinja2

from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.models import (
    HoverTool,
    ColumnDataSource,
    CategoricalColorMapper,
    WheelZoomTool,
    CustomJS,
    #  Select,
)
from bokeh import palettes
#  from bokeh.layouts import column
#  from bokeh.models import ColorBar, LogTicker

SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


def tooltip():
    result = """
    <div>
        <p>
            <span style='font-size: 18px'>Hosts:</span>
            <span style='font-size: 18px'>@fp_count (0x@color_index)</span>
        </p>
        <p>
            <span style='font-size: 18px'>TCP: @tcp_ports</span>
        </p>
        <p>
            <span style='font-size: 18px'>UDP: @udp_ports</span>
        </p>
        <hr/>
    </div>
    """
    return result


def plot(data, filename, circle_scale=1, title=None, **kwargs):
    df = data["dataframe"]
    color_field = "color_index"
    df["size"] = list(4 + math.sqrt(1 + x) * circle_scale for x in df["fp_count"])

    datasource = ColumnDataSource(df)
    color_mapping = CategoricalColorMapper(
        factors=["%02x" % x for x in range(256)], palette=palettes.Turbo256
    )

    if title:
        title = "Portscan - %s" % title
    else:
        title = "Portscan"

    plot_figure = figure(
        title=title,
        width=800,
        height=600,
        tools=("pan, wheel_zoom, reset, tap, box_select, lasso_select"),
    )

    plot_figure.toolbar.active_scroll = plot_figure.select_one(WheelZoomTool)

    plot_figure.xaxis.major_label_text_font_size = "0pt"  # turn off x-axis tick labels
    plot_figure.yaxis.major_label_text_font_size = "0pt"  # turn off y-axis tick labels

    #  color_bar = ColorBar(color_mapper=color_mapping, ticker=LogTicker(),
    #                       label_standoff=12, border_line_color=None, location=(0, 0))
    #  plot_figure.add_layout(color_bar, 'right')

    plot_figure.add_tools(HoverTool(tooltips=tooltip()))

    #  tooltips = [tooltip()]

    #  callback_hover = CustomJS(
    #      args=dict(tt=plot_figure.hover, opts=tooltips), code="""
    #      if (cb_obj.value=='Stat Set 1') {
    #          tt[0].tooltips=opts[0]
    #      } else {
    #          tt[0].tooltips=opts[1]
    #      }
    #  """)

    circle_args = dict(
        source=datasource,
        color=dict(field=color_field, transform=color_mapping),
        line_alpha=0.6,
        fill_alpha=0.4,
    )

    circle_args["size"] = "size"

    plot_figure.scatter(
        "x",
        "y",
        **circle_args,
    )

    # make a custom javascript callback that exports the indices of the
    # selected points to the Jupyter notebook

    select_circle_js = SCRIPT_PATH / "js" / "select_circle.js"
    select_circle_js = open(select_circle_js, "r").read()
    callback_click = CustomJS(
        args=dict(
            datasource=datasource, fp_map=data["fp_map"], color_map=color_mapping
        ),
        code=select_circle_js,
    )

    # set the callback to run when a selection geometry event occurs in the figure
    plot_figure.js_on_event("selectiongeometry", callback_click)

    #  stat_select = Select(
    #      options=["Stat Set 1", "Stat Set 2"],
    #      value="Stat Set 1",
    #      title="Show port numbers",
    #      #  callback=callback_hover,
    #  )

    write_html(plot_figure, title, data)


def write_html(plot_figure, title, data, output_dir="."):
    os.makedirs(output_dir, exist_ok=True)
    js_files = []
    css_files = []
    loader = jinja2.FileSystemLoader(SCRIPT_PATH / "assets" / "templates")
    scanscope_env = jinja2.Environment(loader=loader)

    static_path = SCRIPT_PATH / "assets" / "static"

    for file in os.listdir(static_path):
        src = static_path / file
        shutil.copyfile(src, Path(output_dir) / file)
        if file.endswith('.js'):
            js_files.append(file)
        if file.endswith('.css'):
            css_files.append(file)

    for page in ["index.html", "info.html"]:
        template = scanscope_env.get_template(page)
        html = template.render(css_files=css_files, js_files=js_files)
        open(Path(output_dir) / page, "w").write(html)

    template = get_bokeh_template(scanscope_env, css_files, js_files)
    html = file_html(
        #  column(stat_select, plot_figure),
        plot_figure,
        title=title,
        template=template,
    )

    open(Path(output_dir) / "diagram.html", "w").write(html)

    write_sqlite(data, output_dir)

    # TODO bundle and write to 'filename'


def get_bokeh_template(scanscope_env, css_files, js_files):
    from bokeh.core.templates import get_env, JS_RESOURCES, CSS_RESOURCES
    from bs4 import BeautifulSoup

    bokeh_env = get_env()
    css_resources = CSS_RESOURCES.render(
        css_files=css_files,
    )
    js_resources = JS_RESOURCES.render(
        js_files=js_files,
    )

    bokeh_code = scanscope_env.get_template("bokeh.html").render()
    bokeh_soup = BeautifulSoup(bokeh_code, "lxml")
    bokeh_body = bokeh_soup.body.decode_contents()
    pre_bokeh_div, post_bokeh_div = str(bokeh_body).split("@@@BOKEH_DIV@@@")

    template = bokeh_env.from_string(
        """
    {% extends "file.html" %}
    {% block css_resources %}
        """
        + css_resources
        + """
    {% endblock %}
    {% block js_resources %}
        """
        + js_resources
        + """
    {% endblock %}
    {% block inner_body scoped %}
        """
        + pre_bokeh_div
        + """ {{ super() }} """
        + post_bokeh_div
        + """
    {% endblock %}
    """
    )

    return template


def write_sqlite(data, output_dir):
    from . import sql
    file_path = Path(output_dir) / "data.sqlite"
    con = sql.create_connection(file_path)

    sql.create_table(con)

    for host in data["hosts"]:
        host_data = ('192.168.1.1', 'example_host')
        host_id = sql.insert_host(con, host_data)

        port_data = [
            (host_id, 80, 'http'),
            (host_id, 443, 'https'),
            (host_id, -53, 'dns')
        ]
        for port in port_data:
            sql.insert_port(con, port)


def reduce_and_plot(
    data, filename, circle_scale=1, title="", post_deduplicate=True, **kwargs
):
    if not post_deduplicate:
        circle_scale /= 10
    plot(data, filename, circle_scale=7 * circle_scale, title=title, **kwargs)
