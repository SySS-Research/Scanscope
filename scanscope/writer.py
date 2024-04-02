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
        write_png(fp, data)
    elif format == "svg":
        raise NotImplementedError("SVG not yet implemented")
    elif format == "html":
        from scanscope import html

        html.reduce_and_plot(data, outputfile)


def write_png(fp, data):
    raise NotImplementedError("PNG not yet implemented")
