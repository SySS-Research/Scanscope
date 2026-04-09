import hashlib
import logging
import sys
from dataclasses import dataclass, field

from libnmap.objects import NmapReport
from libnmap.parser import NmapParser, NmapParserException

log = logging.getLogger(__name__)


@dataclass
class HostInfo:
    tcp_ports: list[int]
    udp_ports: list[int]
    fingerprint: str | None
    hostname: str | None = None
    os: str | None = None


@dataclass
class NmapResult:
    hosts: dict[str, HostInfo]
    report: NmapReport


@dataclass
class PortScan:
    hosts: dict[str, HostInfo]
    reports: list[NmapReport] = field(default_factory=list)


@dataclass
class PortMap:
    port_map_tcp: dict[str, str]
    port_map_udp: dict[str, str]


def fingerprint(array: list[int | str]) -> str:
    """Create a fingerprint of a port configuration"""
    h = hashlib.new("sha256")
    h.update(str(array).encode())
    return h.hexdigest()


def read_nmap_file(filename: str) -> NmapResult:
    nm = NmapParser.parse_fromfile(filename)
    hosts: dict[str, HostInfo] = {}

    # Check number of scanned ports and emit warning if < 100

    for host in nm.hosts:  # type: ignore[attr-defined]
        tcp_ports = [p for p, proto in host.get_open_ports() if proto == "tcp"]

        udp_ports = [p for p, proto in host.get_open_ports() if proto == "udp"]

        if tcp_ports or udp_ports:
            fp = fingerprint(tcp_ports + ["X"] + udp_ports)
        else:
            # This will cause hosts with NO open ports to be gray
            fp = None

        host_info = HostInfo(
            tcp_ports=tcp_ports,
            udp_ports=udp_ports,
            fingerprint=fp,
        )

        if host.hostnames:
            host_info.hostname = host.hostnames[0]
        if host.os_match_probabilities():
            host_info.os = host.os_match_probabilities()[0].name

        hosts[host.address] = host_info

    nm.filename = filename  # type: ignore[attr-defined]
    results = NmapResult(
        hosts=hosts,
        report=nm,  # type: ignore[arg-type]
    )

    return results


def read_input(input_files: tuple[str, ...]) -> PortScan:
    """Take a list of input files and return a list of hosts"""
    result = PortScan(hosts={}, reports=[])

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
        result.hosts.update(nmap_info.hosts)
        nmap_info.report.total_open_ports = sum(len(h.services) for h in nmap_info.report.hosts)  # type: ignore[attr-defined]
        result.reports.append(nmap_info.report)

    if not result.hosts:
        log.info("No hosts found")
        sys.exit(0)

    return result


def get_minimal_port_map(portscan: PortScan) -> PortMap:
    from scanscope.portmap import port_map_tcp, port_map_udp

    tcp_ports: set[int] = set()
    for host_info in portscan.hosts.values():
        tcp_ports.update(host_info.tcp_ports)

    udp_ports: set[int] = set()
    for host_info in portscan.hosts.values():
        udp_ports.update(host_info.udp_ports)

    tcp = {k: v for k, v in port_map_tcp.items() if int(k) in tcp_ports}
    udp = {k: v for k, v in port_map_udp.items() if int(k) in udp_ports}

    return PortMap(port_map_tcp=tcp, port_map_udp=udp)
