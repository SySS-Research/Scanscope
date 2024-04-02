import os

import math
from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.models import (
    HoverTool,
    ColumnDataSource,
    CategoricalColorMapper,
    WheelZoomTool,
    CustomJS,
    Select,
)
from bokeh import palettes
from bokeh.layouts import column
from bokeh.models import ColorBar, LogTicker

SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))


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

    plot_figure.circle(
        "x",
        "y",
        **circle_args,
    )

    # make a custom javascript callback that exports the indices of the
    # selected points to the Jupyter notebook

    select_circle_js = os.path.join(SCRIPT_PATH, "js", "select_circle.js")
    select_circle_js = open(select_circle_js, "r").read()
    callback_click = CustomJS(
        args=dict(
            datasource=datasource, fp_map=data["fp_map"], color_map=color_mapping
        ),
        code=select_circle_js,
    )

    # set the callback to run when a selection geometry event occurs in the figure
    plot_figure.js_on_event("selectiongeometry", callback_click)

    stat_select = Select(
        options=["Stat Set 1", "Stat Set 2"],
        value="Stat Set 1",
        title="Show port numbers",
        #  callback=callback_hover,
    )

    css = open(os.path.join(SCRIPT_PATH, "css", "style.css"), "r").read()
    template = get_template(css)
    html = file_html(
        #  column(stat_select, plot_figure),
        plot_figure,
        title=title,
        template=template,
    )
    open(filename, "w").write(html)


def get_template(css):
    from bokeh.core.templates import get_env

    env = get_env()

    template = env.from_string(
        """
    {% extends "file.html" %}
    {% block inner_head scoped %}
    {{super()}}<style>"""
        + css
        + """</style>
    {% endblock %}
    {% block inner_body scoped %}
    <div id='bokeh-plot'>{{ super() }}</div><div id='hosts-details'></div>
    {% endblock %}
    """
    )

    return template


def reduce_and_plot(
    data, filename, circle_scale=1, title="", post_deduplicate=True, **kwargs
):
    if not post_deduplicate:
        circle_scale /= 10
    plot(data, filename, circle_scale=7 * circle_scale, title=title, **kwargs)
