import logging
import hashlib
import sys

from libnmap.parser import NmapParser, NmapParserException

log = logging.getLogger(__name__)


def fingerprint(array):
    """Create a fingerprint of a port configuration"""
    h = hashlib.new("sha256")
    h.update(str(array).encode())
    return h.hexdigest()


def read_nmap_file(filename):
    nm = NmapParser.parse_fromfile(filename)
    hosts = {}

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

        hosts[host.address] = host_info

    nm.filename = filename
    results = dict(
        hosts=hosts,
        report=nm,
    )

    return results


def read_input(input_files):
    """Take a list of input files and return a list of hosts"""
    result = {
        "hosts": {},
        "reports": [],
    }

    log.info("Reading input files...")

    for f in input_files:
        try:
            nmap_info = read_nmap_file(f)
        except NmapParserException:
            log.error(f"Not a valid XML file: {f}")
            continue
        except FileNotFoundError:
            log.error(f"File not found: {f}")
            continue
        result["hosts"].update(nmap_info["hosts"])
        nmap_info["report"].total_open_ports = sum(
            len(h.services) for h in nmap_info["report"].hosts
        )
        result["reports"].append(nmap_info["report"])

    if not result["hosts"]:
        log.info("No hosts found")
        sys.exit(0)

    return result


def get_minimal_port_map(portscan):
    from scanscope.portmap import port_map_tcp, port_map_udp

    tcp_ports = set()
    for k in portscan["hosts"].values():
        tcp_ports.update(k["tcp_ports"])

    udp_ports = set()
    for k in portscan["hosts"].values():
        udp_ports.update(k["udp_ports"])

    tcp = {k: v for k, v in port_map_tcp.items() if int(k) in tcp_ports}
    udp = {k: v for k, v in port_map_udp.items() if int(k) in udp_ports}

    return dict(port_map_tcp=tcp, port_map_udp=udp)
