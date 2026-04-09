import math
import os
import shutil
from pathlib import Path
from typing import Any

import jinja2
from bokeh.embed import file_html
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    #  Select,
    HoverTool,
    WheelZoomTool,
)
from bokeh.plotting import figure
from bokeh.themes import built_in_themes
from jinja2 import Environment

from scanscope.data import DataResult

SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))

CDN = {
    "bootstrap.bundle.min.js": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/js/bootstrap.bundle.min.js",
    "bootstrap.min.css": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/css/bootstrap.min.css",
    "sql-wasm.min.js": "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.min.js",
    "sql-wasm.wasm": "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2",
    "d3.min.js": "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js",
    # only the base where the script sql-wasm.min.js looks
}


def write_output(
    data: DataResult,
    plot: figure,
    title: str,
    output_dir: str,
    use_cdn: bool = False,
    embed_sqlite: bool = False,
    command_line: str = "",
) -> None:
    from scanscope import __version__
    from scanscope.parser import get_minimal_port_map

    port_map = get_minimal_port_map(data.portscan)
    context: dict[str, Any] = {
        "port_map_tcp": port_map.port_map_tcp,
        "port_map_udp": port_map.port_map_udp,
    }
    context.update(
        {
            "reports": data.portscan.reports,
            "title": ", ".join(r.filename for r in data.portscan.reports),  # type: ignore[attr-defined]
            "scanscope_command": command_line,
            "scanscope_version": __version__,
        }
    )

    os.makedirs(output_dir, exist_ok=True)
    if embed_sqlite:
        sqlite_db = get_sqlite(data)
        write_html(plot, output_dir, context, use_cdn=use_cdn, sqlite_db=sqlite_db, data=data)
    else:
        sqlite_db = get_sqlite(data)
        file_path = Path(output_dir) / "data.sqlite"
        open(file_path, "wb").write(sqlite_db)
        write_html(plot, output_dir, context, use_cdn=use_cdn, data=data)


def get_bokeh_plot(data: DataResult, circle_scale: int = 7, title: str | None = None) -> figure:
    df = data.dataframe
    df["size"] = list(4 + math.sqrt(1 + x) * circle_scale for x in df["fp_count"])

    datasource = ColumnDataSource(df)

    plot_figure = figure(
        title=title,
        tools=("pan, wheel_zoom, reset, tap, box_select, lasso_select"),
        sizing_mode="stretch_both",
    )

    plot_figure.toolbar.active_scroll = plot_figure.select_one(WheelZoomTool)  # type: ignore[assignment, arg-type]

    plot_figure.xaxis.major_label_text_font_size = "0pt"  # turn off x-axis tick labels
    plot_figure.yaxis.major_label_text_font_size = "0pt"  # turn off y-axis tick labels

    hover = HoverTool(tooltips=None)
    callback_hover = CustomJS(
        args=dict(opts=dict(datasource=datasource, fp_map=data.fp_map)),
        code="hostGroupHover(opts, cb_data)",
    )
    hover.callback = callback_hover
    plot_figure.add_tools(hover)

    circle_args = dict(
        source=datasource,
        color="color",
        line_alpha=0.6,
        fill_alpha=0.4,
        size="size",
    )

    plot_figure.scatter("x", "y", **circle_args)  # type: ignore[arg-type]

    callback_click = CustomJS(
        args=dict(opts=dict(datasource=datasource, fp_map=data.fp_map)),
        code="hostGroupClick(opts, cb_data)",
    )

    # set the callback to run when a selection geometry event occurs in the figure
    plot_figure.js_on_event("selectiongeometry", callback_click)

    return plot_figure


def _jinja2_filter_datetime(date: float, fmt: str | None = None) -> str:
    import datetime

    format = "%Y-%m-%d %H:%M:%S %Z"
    return datetime.datetime.fromtimestamp(date).strftime(format)


def get_treemap_data(data: DataResult) -> str:
    """Prepare data for treemap visualization.

    Returns:
        JSON string with treemap data
    """
    import json

    df = data.dataframe

    treemap_data = []
    for _, row in df.iterrows():
        fp_count_val = row.get("fp_count", 1)
        port_count_val = row.get("port_count", 0)
        item = {
            "fingerprint": row.get("fingerprint"),
            "fp_count": int(fp_count_val) if fp_count_val is not None else 1,
            "tcp_ports": row.get("tcp_ports", []),
            "udp_ports": row.get("udp_ports", []),
            "category": row.get("category"),
            "port_count": int(port_count_val) if port_count_val is not None else 0,
            "color_category": row.get("color_category"),
            "color_cluster": row.get("color_cluster"),
            "color_port_count": row.get("color_port_count"),
            "color_fingerprint": row.get("color_fingerprint"),
        }

        if "cluster" in row:
            item["cluster"] = int(row["cluster"])

        treemap_data.append(item)

    return json.dumps(treemap_data)


def write_html(
    plot: figure,
    output_dir: str,
    context: dict[str, Any] | None = None,
    use_cdn: bool = False,
    sqlite_db: bytes | None = None,
    data: DataResult | None = None,
) -> None:
    if context is None:
        context = {}
    js_files: list[str] = []
    css_files: list[str] = []
    loader = jinja2.ChoiceLoader(
        [
            jinja2.PackageLoader("scanscope", "templates"),
            jinja2.PackageLoader("bokeh.core", "_templates"),
        ]
    )
    scanscope_env = jinja2.Environment(
        loader=loader,
        autoescape=False,  # noqa
    )
    scanscope_env.filters["strftime"] = _jinja2_filter_datetime

    sqlite_db_encoded: str
    sql_wasm: str
    if sqlite_db:
        import base64

        sqlite_db_encoded = base64.b64encode(sqlite_db).decode()
        if use_cdn:
            sql_wasm = ""
        else:
            filename = SCRIPT_PATH / "static" / "sql-wasm.wasm"
            sql_wasm_bytes = open(filename, "rb").read()
            sql_wasm = base64.b64encode(sql_wasm_bytes).decode()
    else:
        sql_wasm = ""
        sqlite_db_encoded = ""

    # Prepare data for new views
    treemap_data_json = ""
    if data is not None:
        treemap_data_json = get_treemap_data(data)

    context = dict(
        sidebar=get_sidebar(),
        wasm_base="",
        wasm_codearray=sql_wasm,
        sqlite_db=sqlite_db_encoded,
        treemap_data=treemap_data_json,
        **context,
    )

    # Copy and auto-include static files
    static_path = SCRIPT_PATH / "static"
    for file in os.listdir(static_path):
        if use_cdn and file in CDN:
            if file == "sql-wasm.wasm":
                context["wasm_base"] = CDN[file]
            file = CDN[file]
        else:
            src = static_path / file
            shutil.copyfile(src, Path(output_dir) / file)

        if file.endswith(".js"):
            js_files.append(file)
        if file.endswith(".css"):
            css_files.append(file)

    # Render templates
    for page in [
        "index.html",
        "hosts.html",
        "services.html",
        "treemap.html",
        "info.html",
        "licenses.html",
    ] + (["_test.html"] if os.environ.get("SCANSCOPE_DEBUG") else []):
        template = scanscope_env.get_template(page)
        _js_files, _css_files = get_resources(js_files, css_files, page)
        html = template.render(css_files=_css_files, js_files=_js_files, **context)
        open(Path(output_dir) / page, "w").write(html)

    # Bokeh template is treated differently
    bubble_chart_html = get_bokeh_html(scanscope_env, plot, js_files, css_files, context)
    open(Path(output_dir) / "bubble-chart.html", "w").write(bubble_chart_html)


def get_bokeh_html(
    env: Environment, plot: figure, js_files: list[str], css_files: list[str], context: dict[str, Any]
) -> str:
    _js_files, _css_files = get_resources(js_files, css_files, "bubble-chart.html")
    html = file_html(
        #  column(stat_select, plot),
        plot,
        title=context["title"],
        template=env.get_template("bubble-chart.html"),
        template_variables=dict(js_files=_js_files, css_files=_css_files, **context),
        theme=built_in_themes["dark_minimal"],
    )
    return html


def get_sqlite(data: DataResult) -> bytes:
    import ipaddress

    from . import sql

    conn = sql.create_connection(":memory:")

    sql.create_table(conn)

    for ip_address, host_info in data.portscan.hosts.items():
        host_data = (
            ip_address,
            int(ipaddress.ip_address(ip_address)),
            host_info.fingerprint,
            host_info.hostname,
            host_info.os,
        )
        host_id = sql.insert_host(conn, host_data)

        port_data = [(host_id, p, "") for p in host_info.tcp_ports]
        port_data += [(host_id, -p, "") for p in host_info.udp_ports]
        for port in port_data:
            sql.insert_port(conn, port)

    conn.commit()

    return conn.serialize()


def get_sidebar() -> list[dict[str, str]]:
    result = [
        {"title": "Overview", "link": "index.html"},
        {"title": "Hosts", "link": "hosts.html"},
        {"title": "Services", "link": "services.html"},
        {"title": "Bubble Chart", "link": "bubble-chart.html"},
        {"title": "Treemap", "link": "treemap.html"},
        {"title": "Info", "link": "info.html"},
    ]
    if os.environ.get("SCANSCOPE_DEBUG"):
        result.append({"title": "Test", "link": "_test.html"})
    return result


def get_resources(js_files: list[str], css_files: list[str], page: str) -> tuple[list[str], list[str]]:
    common = [
        "bootstrap.bundle.min.js",
        "bootstrap.min.css",
        "utils.js",
        "scanscope.css",
    ]
    resource_map: dict[str, list[str]] = {
        "index.html": [],
        "info.html": [],
        "licenses.html": [],
        "bubble-chart.html": [
            "bubble-chart-aux.js",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
        "services.html": [
            "gridjs.production.min.js",
            "mermaid.dark.css",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
        "hosts.html": [
            "hosts-aux.js",
            "gridjs.production.min.js",
            "mermaid.dark.css",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
        "treemap.html": [
            "d3.min.js",
            "sql-aux.js",
            "sql-wasm.min.js",
            "treemap-aux.js",
        ],
    }
    _js_files = [file for file in js_files if Path(file).name in resource_map.get(page, []) + common]
    _css_files = [file for file in css_files if Path(file).name in resource_map.get(page, []) + common]

    return _js_files, _css_files
