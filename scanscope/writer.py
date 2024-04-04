import json
import sys

import numpy


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def write_output(data, outputfile, format="html"):
    if outputfile:
        fp = open(outputfile, "wb")
    else:
        fp = sys.stdout.buffer

    if format == "json":
        fp.write(data["dataframe"].to_json().encode())
    elif format == "png":
        raise NotImplementedError("PNG not yet implemented")
    elif format == "svg":
        raise NotImplementedError("SVG not yet implemented")
    elif format == "html":
        from scanscope import html, write_output

        plot = html.get_bokeh_plot(data, outputfile)
        write_output(data, plot, "", "/tmp/scanscope")
