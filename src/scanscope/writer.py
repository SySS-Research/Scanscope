import json
import sys

import numpy


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def write_output_json(data, output_path):
    if output_path:
        fp = open(output_path, "wb")
    else:
        fp = sys.stdout.buffer
    fp.write(data["dataframe"].to_json().encode())


def write_output_html(data, output_path, zundler=False, use_cdn=False):
    from scanscope import html
    from scanscope.html import write_output

    plot = html.get_bokeh_plot(data)

    if zundler:
        from tempfile import TemporaryDirectory
        from zundler.embed import embed_assets
        from pathlib import Path

        with TemporaryDirectory() as tmpdirname:
            write_output(data, plot, "", tmpdirname, use_cdn=use_cdn)
            embed_assets(
                Path(tmpdirname) / "index.html",
                output_path=output_path,
            )
    else:
        write_output(data, plot, "", output_path, use_cdn=use_cdn, embed_sqlite=True)
