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

SCRIPT_PATH = Path(os.path.abspath(os.path.dirname(__file__)))

CDN = {
    "bootstrap.bundle.min.js": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/js/bootstrap.bundle.min.js",
    "bootstrap.min.css": "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/css/bootstrap.min.css",
    "sql-wasm.min.js": "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.min.js",
    "sql-wasm.wasm": "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2",
    # only the base where the script sql-wasm.min.js looks
}


def write_output(data, plot, title, output_dir, use_cdn=False, embed_sqlite=False):
    from scanscope.parser import get_minimal_port_map

    context = get_minimal_port_map(data["portscan"])
    context.update(
        reports=data["portscan"]["reports"],
        title=", ".join(r.filename for r in data["portscan"]["reports"]),
    )

    os.makedirs(output_dir, exist_ok=True)
    if embed_sqlite:
        sqlite_db = get_sqlite(data)
        write_html(plot, output_dir, context, use_cdn=use_cdn, sqlite_db=sqlite_db)
    else:
        sqlite_db = get_sqlite(data)
        file_path = Path(output_dir) / "data.sqlite"
        open(file_path, "wb").write(sqlite_db)
        write_html(plot, output_dir, context, use_cdn=use_cdn)


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
        tools=("pan, wheel_zoom, reset, tap, box_select, lasso_select"),
        sizing_mode="stretch_both",
    )

    plot_figure.toolbar.active_scroll = plot_figure.select_one(WheelZoomTool)

    plot_figure.xaxis.major_label_text_font_size = "0pt"  # turn off x-axis tick labels
    plot_figure.yaxis.major_label_text_font_size = "0pt"  # turn off y-axis tick labels

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


def write_html(plot, output_dir, context={}, use_cdn=False, sqlite_db=None):
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

    if sqlite_db:
        import base64

        sqlite_db = base64.b64encode(sqlite_db).decode()
        if use_cdn:
            sql_wasm = ""
        else:
            filename = SCRIPT_PATH / "static" / "sql-wasm.wasm"
            sql_wasm = open(filename, "rb").read()
            sql_wasm = base64.b64encode(sql_wasm).decode()
    else:
        sql_wasm = ""
        sqlite_db = ""

    context = dict(
        theme="dark",
        sidebar=get_sidebar(),
        wasm_base="",
        wasm_codearray=sql_wasm,
        sqlite_db=sqlite_db,
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
        "info.html",
        "licenses.html",
    ] + (["_test.html"] if os.environ.get("SCANSCOPE_DEBUG") else []):
        template = scanscope_env.get_template(page)
        _js_files, _css_files = get_resources(js_files, css_files, page)
        html = template.render(css_files=_css_files, js_files=_js_files, **context)
        open(Path(output_dir) / page, "w").write(html)

    # Bokeh template is treated differently
    diagram_html = get_bokeh_html(scanscope_env, plot, js_files, css_files, context)
    open(Path(output_dir) / "diagram.html", "w").write(diagram_html)


def get_bokeh_html(env, plot, js_files, css_files, context):
    _js_files, _css_files = get_resources(js_files, css_files, "diagram.html")
    html = file_html(
        #  column(stat_select, plot),
        plot,
        title=context["title"],
        template=env.get_template("diagram.html"),
        template_variables=dict(js_files=_js_files, css_files=_css_files, **context),
        theme=built_in_themes["dark_minimal"] if context["theme"] == "dark" else None,
    )
    return html


def get_sqlite(data):
    import ipaddress
    from . import sql

    conn = sql.create_connection(":memory:")

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

    return conn.serialize()


def get_sidebar():
    result = [
        {"title": "Overview", "link": "index.html"},
        {"title": "Hosts", "link": "hosts.html"},
        {"title": "Services", "link": "services.html"},
        {"title": "Diagram", "link": "diagram.html"},
        {"title": "Info", "link": "info.html"},
    ]
    if os.environ.get("SCANSCOPE_DEBUG"):
        result.append({"title": "Test", "link": "_test.html"})
    return result


def get_resources(js_files, css_files, page):
    common = [
        "bootstrap.bundle.min.js",
        "bootstrap.min.css",
        "utils.js",
        "scanscope.css",
    ]
    resource_map = {
        "index.html": [],
        "info.html": [],
        "licenses.html": [],
        "diagram.html": [
            "diagram-aux.js",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
        "services.html": [
            "gridjs.production.min.js",
            "mermaid.min.css",
            "mermaid.dark.css",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
        "hosts.html": [
            "hosts-aux.js",
            "gridjs.production.min.js",
            "mermaid.min.css",
            "mermaid.dark.css",
            "sql-aux.js",
            "sql-wasm.min.js",
        ],
    }
    _js_files = [
        file
        for file in js_files
        if Path(file).name in resource_map.get(page, []) + common
    ]
    _css_files = [
        file
        for file in css_files
        if Path(file).name in resource_map.get(page, []) + common
    ]

    return _js_files, _css_files
