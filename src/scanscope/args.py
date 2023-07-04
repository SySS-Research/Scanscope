import argparse
import logging

from scanscope.__init__ import __version__

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Visualize portscan results")

parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=__version__,
)

parser.add_argument(
    "-c",
    "--config",
    type=str,
    help="path to config file; if empty we will try ./scanscope.conf"
    " and ${XDG_CONFIG_HOME:-$HOME/.config}/scanscope/scanscope.conf"
    " in that order",
)

parser.add_argument(
    "-l",
    "--log-level",
    choices=["INFO", "WARNING", "ERROR", "DEBUG"],
    default="INFO",
    help="log level (default: %(default)s)",
)

parser.add_argument(
    "-f",
    "--format",
    choices=["html-directory", "html", "json"],  # "png", "svg"
    default="html",
    help="Output format (default: %(default)s)",
)

parser.add_argument(
    "-E",
    "--remove-empty-host-group",
    default=False,
    action="store_true",
    help="Remove the group of hosts without open ports",
)

parser.add_argument(
    "-o",
    "--output-path",
    default=None,
    help="Path to the output file/directory (default: stdout)",
)

parser.add_argument(
    "input",
    nargs="+",
    help="Input files",
)

params = parser.add_argument_group(
    title="Data parameters", description="These arguments influence the data processing"
)


params.add_argument(
    "-C",
    "--use-cdn",
    default=False,
    action="store_true",
    help="Use a CDN instead of embedding dependencies to reduce the file size",
)


params.add_argument(
    "--skip-post-deduplicate",
    default=False,
    action="store_true",
    help="DO NOT deduplicate hosts after data reduction",
)


params.add_argument(
    "--pre-deduplicate",
    default=False,
    action="store_true",
    help="Deduplicate hosts before data reduction",
)


def parse_args(argv=None):
    args = parser.parse_args(argv)
    return args


def parse_config(path):
    import configparser
    import collections
    import os

    import xdg.BaseDirectory

    config_parser = configparser.ConfigParser()
    if not path:
        path = "./scanscope.conf"
        if not os.path.exists(path):
            path = os.path.join(
                xdg.BaseDirectory.xdg_config_home,
                "scanscope",
                "scanscope.conf",
            )
    config_parser.read(path)
    attrs = "rule wordlist hashcat_bin hash_speed db_uri hibp_db".split()
    for a in attrs:
        if a not in config_parser["DEFAULT"]:
            log.error("Attribute undefined: " + a)
    Config = collections.namedtuple("Config", attrs)
    config = Config(*[config_parser["DEFAULT"].get(a) for a in attrs])

    return config
