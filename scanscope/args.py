import argparse
import logging

from scanscope._meta import __version__, __doc__

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description=__doc__,
)

parser.add_argument(
    '-v', '--version', action='version',
    version='scanscope %s' % __version__,
)

parser.add_argument(
    '-c', '--config',
    type=str,
    help="path to config file; if empty we will try ./scanscope.conf"
    " and ${XDG_CONFIG_HOME:-$HOME/.config}/scanscope/scanscope.conf"
    " in that order",
)

parser.add_argument(
    '-l', '--log-level',
    choices=['INFO', 'WARNING', 'ERROR', 'DEBUG'],
    default='INFO',
    help="log level (default: %(default)s)",
)

parser.add_argument(
    '-o', '--outputfile',
    default=None,
    help="Path to the output file (default: stdout)",
)

parser.add_argument(
    'input',
    nargs='+',
    help="Input files",
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
        path = './scanscope.conf'
        if not os.path.exists(path):
            path = os.path.join(
                xdg.BaseDirectory.xdg_config_home,
                'scanscope',
                'scanscope.conf',
            )
    config_parser.read(path)
    attrs = 'rule wordlist hashcat_bin hash_speed db_uri hibp_db'.split()
    for a in attrs:
        if a not in config_parser['DEFAULT']:
            log.error('Attribute undefined: ' + a)
    Config = collections.namedtuple('Config', attrs)
    config = Config(
        *[config_parser['DEFAULT'].get(a) for a in attrs]
    )

    return config
