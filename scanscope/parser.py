import logging
import hashlib
from libnmap.parser import NmapParser

log = logging.getLogger(__name__)


def fingerprint(array):
    """Create a fingerprint of a port configuration"""
    h = hashlib.new("sha256")
    h.update(str(array).encode())
    return h.hexdigest()


def get_host_info(filename):
    nm = NmapParser.parse_fromfile(filename)
    results = {}

    # Check number of scanned ports and emit warning if < 100

    for host in nm.hosts:
        host_info = {"tcp_ports": [], "udp_ports": []}

        host_info["tcp_ports"] = [
            p for p, proto in host.get_open_ports() if proto == "tcp"
        ]

        host_info["udp_ports"] = [
            p for p, proto in host.get_open_ports() if proto == "udp"
        ]

        if host_info["tcp_ports"] or host_info["udp_ports"]:
            host_info["fingerprint"] = fingerprint(
                host_info["tcp_ports"] + ["X"] + host_info["udp_ports"]
            )
        else:
            # This will cause hosts with NO open ports to be gray
            host_info["fingerprint"] = None

        if host.hostnames:
            host_info["hostname"] = host.hostnames[0]
        if host.os_match_probabilities():
            host_info["os"] = host.os_match_probabilities()[0]

        results[host.address] = host_info

    return results


def read_input(input_files):
    """Take a list of input files and return a list of hosts"""
    result = {}

    log.info("Reading input files...")

    for f in input_files:
        result.update(get_host_info(f))

    return result
