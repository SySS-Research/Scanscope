import json
import sys

import numpy


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def write_output(data, output_path, format="html"):
    if format == "json":
        if output_path:
            fp = open(output_path, "wb")
        else:
            fp = sys.stdout.buffer
        fp.write(data["dataframe"].to_json().encode())
    else:
        from scanscope import html
        plot = html.get_bokeh_plot(data)

        if format == "png":
            raise NotImplementedError("PNG not yet implemented")
        elif format == "svg":
            raise NotImplementedError("SVG not yet implemented")
        elif format == "html-directory":
            from scanscope.html import write_output
            write_output(data, plot, "", output_path)
        elif format == "html":
            from scanscope.html import write_output
            from tempfile import TemporaryDirectory
            from zundler.embed import embed_assets
            from pathlib import Path

            with TemporaryDirectory() as tmpdirname:
                write_output(data, plot, "", tmpdirname)
                embed_assets(
                    Path(tmpdirname) / "index.html",
                    output_path=output_path,
                )
