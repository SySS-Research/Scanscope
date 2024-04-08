import os
import math
from pathlib import Path
import shutil

import jinja2

from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.themes import built_in_themes
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


def write_output(data, plot, title, output_dir):
    from scanscope.parser import get_minimal_port_map

    context = get_minimal_port_map(data["portscan"])
    context.update(report=data["portscan"]["report"])

    os.makedirs(output_dir, exist_ok=True)
    write_html(plot, title, output_dir, context)
    write_sqlite(data, output_dir)


def get_bokeh_plot(data, circle_scale=7, title=None):
    df = data["dataframe"]
    color_field = "color_index"
    df["size"] = list(4 + math.sqrt(1 + x) * circle_scale for x in df["fp_count"])

    datasource = ColumnDataSource(df)
    color_mapping = CategoricalColorMapper(
        factors=["%02x" % x for x in range(256)], palette=palettes.Turbo256
    )

    plot_figure = figure(
        title=title,
        width=800,
        height=600,
        tools=("pan, wheel_zoom, reset, tap, box_select, lasso_select"),
        sizing_mode="stretch_width",
    )

    plot_figure.toolbar.active_scroll = plot_figure.select_one(WheelZoomTool)

    plot_figure.xaxis.major_label_text_font_size = "0pt"  # turn off x-axis tick labels
    plot_figure.yaxis.major_label_text_font_size = "0pt"  # turn off y-axis tick labels

    #  color_bar = ColorBar(color_mapper=color_mapping, ticker=LogTicker(),
    #                       label_standoff=12, border_line_color=None, location=(0, 0))
    #  plot_figure.add_layout(color_bar, 'right')

    hover = HoverTool(tooltips=None)
    callback_hover = CustomJS(
        args=dict(
            opts=dict(
                datasource=datasource, fp_map=data["fp_map"], color_map=color_mapping
            )
        ),
        code="hostGroupHover(opts, cb_data)",
    )
    hover.callback = callback_hover
    plot_figure.add_tools(hover)

    circle_args = dict(
        source=datasource,
        color=dict(field=color_field, transform=color_mapping),
        line_alpha=0.6,
        fill_alpha=0.4,
        size="size",
    )

    plot_figure.scatter("x", "y", **circle_args)

    callback_click = CustomJS(
        args=dict(
            opts=dict(
                datasource=datasource, fp_map=data["fp_map"], color_map=color_mapping
            )
        ),
        code="hostGroupClick(opts, cb_data)",
    )

    # set the callback to run when a selection geometry event occurs in the figure
    plot_figure.js_on_event("selectiongeometry", callback_click)

    return plot_figure


def _jinja2_filter_datetime(date, fmt=None):
    import datetime
    format = "%Y-%m-%d %H:%M:%S %Z"
    return datetime.datetime.fromtimestamp(date).strftime(format)


def write_html(plot, title, output_dir, context={}):
    js_files = []
    css_files = []
    loader = jinja2.ChoiceLoader(
        [
            jinja2.PackageLoader("scanscope", "templates"),
            jinja2.PackageLoader("bokeh.core", "_templates"),
        ]
    )
    scanscope_env = jinja2.Environment(loader=loader)
    scanscope_env.filters["strftime"] = _jinja2_filter_datetime

    # Copy and auto-include common files
    static_path = SCRIPT_PATH / "static" / "common"
    for file in os.listdir(static_path):
        src = static_path / file
        shutil.copyfile(src, Path(output_dir) / file)
        if file.endswith(".js"):
            js_files.append(file)
        if file.endswith(".css"):
            css_files.append(file)

    # Copy optional files only
    static_path = SCRIPT_PATH / "static" / "opt"
    for file in os.listdir(static_path):
        src = static_path / file
        shutil.copyfile(src, Path(output_dir) / file)

    # Render templates
    context = dict(
        css_files=css_files,
        js_files=js_files,
        theme="dark",
        sidebar=get_sidebar(),
        **context
    )

    for page in ["index.html", "hosts.html", "services.html", "info.html"]:
        template = scanscope_env.get_template(page)
        html = template.render(**context)
        open(Path(output_dir) / page, "w").write(html)

    # Bokeh template is treated differently
    html = file_html(
        #  column(stat_select, plot),
        plot,
        title=title,
        template=scanscope_env.get_template("bokeh.html"),
        template_variables=context,
        theme=built_in_themes["dark_minimal"] if context["theme"] == "dark" else None,
    )

    open(Path(output_dir) / "diagram.html", "w").write(html)


def write_sqlite(data, output_dir):
    import ipaddress
    from . import sql

    file_path = Path(output_dir) / "data.sqlite"
    conn = sql.create_connection(file_path)

    sql.create_table(conn)

    for ip_address, data_ in data["portscan"]["hosts"].items():
        host_data = (
            ip_address,
            int(ipaddress.ip_address(ip_address)),
            data_["fingerprint"],
            data_.get("hostname"),
            data_.get("os"),
        )
        host_id = sql.insert_host(conn, host_data)

        port_data = [(host_id, p, "") for p in data_["tcp_ports"]]
        port_data += [(host_id, -p, "") for p in data_["udp_ports"]]
        for port in port_data:
            sql.insert_port(conn, port)

    conn.commit()


def get_sidebar():
    result = [
        {"title": "Overview", "link": "index.html"},
        {"title": "Hosts", "link": "hosts.html"},
        {"title": "Services", "link": "services.html"},
        {"title": "Diagram", "link": "diagram.html"},
        {"title": "Info", "link": "info.html"},
    ]
    return result
