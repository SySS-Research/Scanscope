import json
import sys
from typing import Any

import numpy

from scanscope.data import DataResult


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, numpy.ndarray):
            return o.tolist()
        return json.JSONEncoder.default(self, o)


def write_output_json(data: DataResult, output_path: str | None) -> None:
    if output_path:
        fp = open(output_path, "wb")
    else:
        fp = sys.stdout.buffer
    fp.write((data.dataframe.to_json() or "").encode())


def write_output_html(
    data: DataResult, output_path: str | None, zundler: bool = False, use_cdn: bool = False, command_line: str = ""
) -> None:
    from scanscope import html
    from scanscope.html import write_output

    plot = html.get_bokeh_plot(data)

    if zundler:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from zundler.embed import embed_assets

        with TemporaryDirectory() as tmpdirname:
            write_output(data, plot, "", tmpdirname, use_cdn=use_cdn, command_line=command_line)
            embed_assets(
                Path(tmpdirname) / "index.html",
                output_path=output_path,
            )
    else:
        if output_path is None:
            raise ValueError("output_path cannot be None when zundler=False")
        write_output(data, plot, "", output_path, use_cdn=use_cdn, embed_sqlite=True, command_line=command_line)
