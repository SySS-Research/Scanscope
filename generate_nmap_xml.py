#!/usr/bin/env python3
"""
Generate a realistic synthetic nmap XML report simulating a corporate network scan.

Produces large host groups with identical base port configurations (simulating
e.g. 200 identical Windows workstations), with per-host jitter that randomly
opens or closes individual ports.

Usage: python3 generate_nmap_xml.py [--hosts N] [--subnet 10.10.0] [--output report.xml]
"""

import argparse
import datetime
import logging
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from xml.dom import minidom

log = logging.getLogger(__name__)

# -- Port definition type alias ------------------------------------------------

PortEntry = tuple[int, str, str, str, str]  # (port, proto, state, service, product)

# -- Data pools ----------------------------------------------------------------

WINDOWS_WORKSTATION = {
    "os": ("Windows 10 Pro", "Windows 10 Enterprise", "Windows 11 Pro"),
    "hostname_prefix": ("DESKTOP-", "WS-", "PC-", "LAPTOP-"),
    "ports": [
        (135, "tcp", "open", "msrpc", "Microsoft Windows RPC"),
        (139, "tcp", "open", "netbios-ssn", "Microsoft Windows netbios-ssn"),
        (445, "tcp", "open", "microsoft-ds", "Windows 10 microsoft-ds"),
        (3389, "tcp", "open", "ms-wbt-server", "Microsoft Terminal Services"),
        (5985, "tcp", "open", "http", "Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)"),
    ],
    "optional_ports": [
        (80, "tcp", "open", "http", "Microsoft IIS httpd 10.0"),
        (8080, "tcp", "open", "http", "Apache httpd 2.4.54"),
        (49152, "tcp", "open", "msrpc", "Microsoft Windows RPC"),
        (49153, "tcp", "open", "msrpc", "Microsoft Windows RPC"),
    ],
}

WINDOWS_SERVER = {
    "os": ("Windows Server 2016", "Windows Server 2019", "Windows Server 2022"),
    "hostname_prefix": ("SRV-", "SERVER-", "WIN-"),
    "ports": [
        (53, "tcp", "open", "domain", "Simple DNS Plus"),
        (80, "tcp", "open", "http", "Microsoft IIS httpd 10.0"),
        (135, "tcp", "open", "msrpc", "Microsoft Windows RPC"),
        (139, "tcp", "open", "netbios-ssn", "Microsoft Windows netbios-ssn"),
        (443, "tcp", "open", "ssl/http", "Microsoft IIS httpd 10.0"),
        (445, "tcp", "open", "microsoft-ds", "Windows Server microsoft-ds"),
        (3389, "tcp", "open", "ms-wbt-server", "Microsoft Terminal Services"),
    ],
    "optional_ports": [
        (88, "tcp", "open", "kerberos-sec", "Microsoft Windows Kerberos"),
        (389, "tcp", "open", "ldap", "Microsoft Windows Active Directory LDAP"),
        (636, "tcp", "open", "ssl/ldap", "Microsoft Windows Active Directory LDAP"),
        (3268, "tcp", "open", "ldap", "Microsoft Windows Active Directory LDAP"),
        (5985, "tcp", "open", "http", "Microsoft HTTPAPI httpd 2.0"),
        (8443, "tcp", "open", "ssl/http", "Microsoft IIS httpd 10.0"),
        (1433, "tcp", "open", "ms-sql-s", "Microsoft SQL Server 2019"),
        (5432, "tcp", "open", "postgresql", "PostgreSQL DB 13.4"),
    ],
}

LINUX_SERVER = {
    "os": ("Linux 4.15", "Linux 5.4", "Linux 5.15"),
    "hostname_prefix": ("lnx-", "app-", "web-", "db-", "svc-"),
    "ports": [
        (22, "tcp", "open", "ssh", "OpenSSH 8.2p1 Ubuntu 4ubuntu0.5"),
        (80, "tcp", "open", "http", "nginx 1.18.0"),
        (443, "tcp", "open", "https", "nginx 1.18.0"),
    ],
    "optional_ports": [
        (21, "tcp", "open", "ftp", "vsftpd 3.0.3"),
        (25, "tcp", "open", "smtp", "Postfix smtpd"),
        (3306, "tcp", "open", "mysql", "MySQL 8.0.29"),
        (5432, "tcp", "open", "postgresql", "PostgreSQL DB 14.2"),
        (6379, "tcp", "open", "redis", "Redis key-value store 7.0.0"),
        (8080, "tcp", "open", "http", "Apache Tomcat 9.0.65"),
        (8443, "tcp", "open", "ssl/http", "Apache Tomcat 9.0.65"),
        (9200, "tcp", "open", "http", "Elasticsearch REST API 8.2.0"),
        (27017, "tcp", "open", "mongodb", "MongoDB 5.0.9"),
    ],
}

NETWORK_DEVICE = {
    "os": ("Cisco IOS 15.6", "Cisco IOS-XE 16.12", "Juniper Junos 20.2R1"),
    "hostname_prefix": ("sw-", "rt-", "fw-", "core-"),
    "ports": [
        (22, "tcp", "open", "ssh", "Cisco SSH 2.0"),
        (23, "tcp", "open", "telnet", "Cisco router telnetd"),
        (80, "tcp", "open", "http", "Cisco IOS http config"),
        (443, "tcp", "open", "https", "Cisco IOS https config"),
        (161, "udp", "open", "snmp", "SNMPv2c or later"),
    ],
    "optional_ports": [
        (179, "tcp", "open", "bgp", "Quagga bgpd 1.2.4"),
        (514, "udp", "open", "syslog", ""),
    ],
}

PRINTER = {
    "os": ("HP JetDirect", "Ricoh embedded", "Xerox embedded"),
    "hostname_prefix": ("PRN-", "PRINTER-", "HP-"),
    "ports": [
        (80, "tcp", "open", "http", "HP HTTP Server; HP LaserJet"),
        (443, "tcp", "open", "ssl/http", "HP HTTP Server"),
        (515, "tcp", "open", "printer", "lpd"),
        (631, "tcp", "open", "ipp", "CUPS 2.3"),
        (9100, "tcp", "open", "jetdirect", ""),
    ],
    "optional_ports": [
        (161, "udp", "open", "snmp", "SNMPv1 server"),
        (21, "tcp", "open", "ftp", "HP LaserJet FTP"),
    ],
}

DEVICE_TYPES = [
    (WINDOWS_WORKSTATION, 0.40),
    (WINDOWS_SERVER, 0.20),
    (LINUX_SERVER, 0.20),
    (NETWORK_DEVICE, 0.10),
    (PRINTER, 0.10),
]

OS_CPE = {
    "Windows 10 Pro": "cpe:/o:microsoft:windows_10",
    "Windows 10 Enterprise": "cpe:/o:microsoft:windows_10",
    "Windows 11 Pro": "cpe:/o:microsoft:windows_11",
    "Windows Server 2016": "cpe:/o:microsoft:windows_server_2016",
    "Windows Server 2019": "cpe:/o:microsoft:windows_server_2019",
    "Windows Server 2022": "cpe:/o:microsoft:windows_server_2022",
    "Linux 4.15": "cpe:/o:linux:linux_kernel:4.15",
    "Linux 5.4": "cpe:/o:linux:linux_kernel:5.4",
    "Linux 5.15": "cpe:/o:linux:linux_kernel:5.15",
    "Cisco IOS 15.6": "cpe:/o:cisco:ios:15.6",
    "Cisco IOS-XE 16.12": "cpe:/o:cisco:ios_xe:16.12",
    "Juniper Junos 20.2R1": "cpe:/o:juniper:junos:20.2r1",
    "HP JetDirect": "cpe:/h:hp:jetdirect",
    "Ricoh embedded": "cpe:/h:ricoh:printer",
    "Xerox embedded": "cpe:/h:xerox:printer",
}

# Extra noise ports that can appear via jitter
NOISE_PORTS: list[PortEntry] = [
    (8080, "tcp", "open", "http", "Apache httpd 2.4"),
    (8443, "tcp", "open", "ssl/http", "nginx 1.18.0"),
    (2222, "tcp", "open", "ssh", "OpenSSH 7.9"),
    (4848, "tcp", "open", "http", "GlassFish Server Open Source"),
    (7070, "tcp", "open", "http", ""),
    (9090, "tcp", "open", "http", "Prometheus"),
    (8161, "tcp", "open", "http", "Apache ActiveMQ"),
    (61616, "tcp", "open", "amqp", "Apache ActiveMQ"),
]

FILTERED_CANDIDATES: list[PortEntry] = [
    (8888, "tcp", "filtered", "unknown", ""),
    (4444, "tcp", "filtered", "unknown", ""),
    (1080, "tcp", "filtered", "unknown", ""),
    (2222, "tcp", "filtered", "unknown", ""),
    (9090, "tcp", "filtered", "unknown", ""),
    (3128, "tcp", "filtered", "unknown", ""),
    (6000, "tcp", "filtered", "unknown", ""),
]


# -- Host group ----------------------------------------------------------------


@dataclass
class HostGroup:
    """A group of hosts sharing the same base port configuration."""

    device: dict
    base_ports: list[PortEntry]
    os_name: str
    count: int = 0
    jitter_close_prob: float = 0.03
    jitter_open_prob: float = 0.02


def generate_groups(num_hosts: int, num_groups: int) -> list[HostGroup]:
    """Pre-generate host groups with fixed base port profiles.

    Each group picks a device type and a deterministic subset of optional ports.
    Hosts within a group share the same base config; per-host jitter is applied
    later when building the XML.
    """
    groups: list[HostGroup] = []

    for _ in range(num_groups):
        device = _pick_device_type()
        base_ports = list(device["ports"])

        # Each group gets a deterministic selection of optional ports
        for op in device.get("optional_ports", []):
            if random.random() < 0.4:
                base_ports.append(op)

        os_name = random.choice(device["os"])
        groups.append(HostGroup(device=device, base_ports=base_ports, os_name=os_name))

    # Distribute hosts across groups using a Dirichlet-like draw so some groups
    # are much larger than others (realistic: 200 identical workstations vs
    # 5 DB servers).
    weights = [random.paretovariate(1.0) for _ in groups]
    total_weight = sum(weights)
    for i, g in enumerate(groups):
        g.count = max(1, round(num_hosts * weights[i] / total_weight))

    # Adjust to hit exact host count
    diff = num_hosts - sum(g.count for g in groups)
    while diff != 0:
        g = random.choice(groups)
        if diff > 0:
            g.count += 1
            diff -= 1
        elif g.count > 1:
            g.count -= 1
            diff += 1

    log.info(
        "Generated %d groups: %s",
        len(groups),
        ", ".join(f"{g.count}x" for g in groups),
    )

    return groups


def apply_jitter(group: HostGroup) -> list[PortEntry]:
    """Return a per-host port list by applying jitter to the group's base ports.

    Jitter can:
    - Close (drop) individual base ports with small probability
    - Open extra noise/filtered ports with small probability
    """
    # ~95% of hosts in a group are identical; ~5% get jitter
    if random.random() > 0.05:
        return list(group.base_ports)

    # Apply jitter: drop some ports, add some noise
    ports = [p for p in group.base_ports if random.random() > group.jitter_close_prob]

    for np in NOISE_PORTS:
        if random.random() < group.jitter_open_prob:
            ports.append(np)

    if random.random() < 0.3:
        ports.append(random.choice(FILTERED_CANDIDATES))

    return ports


# -- Helpers -------------------------------------------------------------------


def _pick_device_type() -> dict:
    r = random.random()
    cumulative = 0.0
    for dtype, weight in DEVICE_TYPES:
        cumulative += weight
        if r < cumulative:
            return dtype
    return DEVICE_TYPES[0][0]


def _random_hostname(prefix_list: tuple[str, ...]) -> str:
    prefix = random.choice(prefix_list)
    suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
    return f"{prefix}{suffix}"


def _random_mac() -> str:
    ouis = [
        "00:50:56",
        "00:0C:29",
        "08:00:27",
        "52:54:00",
        "00:1A:2B",
        "3C:52:82",
        "D4:BE:D9",
        "00:90:27",
    ]
    oui = random.choice(ouis)
    rest = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))
    return f"{oui}:{rest}"


def _timestamp_str(dt: datetime.datetime) -> str:
    return str(int(dt.timestamp()))


def _generate_ips(subnet_base: str, count: int) -> list[str]:
    """Generate unique IPs across as many /24 subnets as needed.

    subnet_base is the first two octets, e.g. "10.10".  Subnets are
    10.10.0.0/24, 10.10.1.0/24, etc.  Each subnet yields up to 253 usable
    host addresses (.1-.254).
    """
    ips: list[str] = []
    subnet_idx = 0
    remaining = count

    while remaining > 0:
        third = subnet_idx
        if third > 255:
            log.warning("Ran out of /24 subnets in %s.x.0/24, wrapping", subnet_base)
            break

        batch = min(remaining, 253)
        octets = list(range(1, 255))
        random.shuffle(octets)
        for last in sorted(octets[:batch]):
            ips.append(f"{subnet_base}.{third}.{last}")

        remaining -= batch
        subnet_idx += 1

    return ips


# -- XML builders --------------------------------------------------------------


def build_host_element(
    ip: str,
    group: HostGroup,
    ports: list[PortEntry],
    scan_time: datetime.datetime,
) -> ET.Element:
    """Build a single <host> XML element."""
    host_el = ET.Element("host")
    host_el.set("starttime", _timestamp_str(scan_time))
    host_el.set(
        "endtime",
        _timestamp_str(scan_time + datetime.timedelta(seconds=random.randint(1, 30))),
    )

    # status
    status = ET.SubElement(host_el, "status")
    status.set("state", "up")
    status.set("reason", random.choice(["echo-reply", "syn-ack", "arp-response"]))
    status.set("reason_ttl", str(random.randint(60, 128)))

    # address (IPv4)
    addr = ET.SubElement(host_el, "address")
    addr.set("addr", ip)
    addr.set("addrtype", "ipv4")

    # MAC (70% chance)
    if random.random() < 0.7:
        mac_el = ET.SubElement(host_el, "address")
        mac_el.set("addr", _random_mac())
        mac_el.set("addrtype", "mac")

    # hostnames
    hostnames_el = ET.SubElement(host_el, "hostnames")
    hn = ET.SubElement(hostnames_el, "hostname")
    hn.set("name", _random_hostname(group.device["hostname_prefix"]).lower())
    hn.set("type", "PTR")

    # ports -- deduplicate by (portnum, proto)
    ports_el = ET.SubElement(host_el, "ports")
    seen: set[tuple[int, str]] = set()
    for portnum, proto, state, service, product in ports:
        if (portnum, proto) in seen:
            continue
        seen.add((portnum, proto))

        port_el = ET.SubElement(ports_el, "port")
        port_el.set("protocol", proto)
        port_el.set("portid", str(portnum))

        state_el = ET.SubElement(port_el, "state")
        state_el.set("state", state)
        state_el.set("reason", "syn-ack" if state == "open" else "no-response")
        state_el.set("reason_ttl", str(random.randint(60, 128)))

        svc_el = ET.SubElement(port_el, "service")
        svc_el.set("name", service)
        if product:
            svc_el.set("product", product)
        svc_el.set("method", "probed")
        svc_el.set("conf", str(random.randint(7, 10)))

    # OS detection
    os_el = ET.SubElement(host_el, "os")
    osmatch = ET.SubElement(os_el, "osmatch")
    osmatch.set("name", group.os_name)
    osmatch.set("accuracy", str(random.randint(85, 100)))
    osmatch.set("line", str(random.randint(1000, 99999)))
    osclass = ET.SubElement(osmatch, "osclass")
    vendor = (
        "Microsoft"
        if "Windows" in group.os_name
        else "Linux"
        if "Linux" in group.os_name
        else "Cisco"
        if "Cisco" in group.os_name
        else "Juniper"
        if "Juniper" in group.os_name
        else "HP"
    )
    osclass.set("type", "general purpose")
    osclass.set("vendor", vendor)
    osfamily = (
        "Windows"
        if "Windows" in group.os_name
        else "Linux"
        if "Linux" in group.os_name
        else "IOS"
        if "IOS" in group.os_name
        else "embedded"
    )
    osclass.set("osfamily", osfamily)
    osclass.set("accuracy", osmatch.get("accuracy", "90"))
    cpe = ET.SubElement(osclass, "cpe")
    cpe.text = OS_CPE.get(group.os_name, "cpe:/o:unknown:unknown")

    # uptime (80% chance)
    if random.random() < 0.8:
        uptime = ET.SubElement(host_el, "uptime")
        uptime.set("seconds", str(random.randint(3600, 7776000)))
        uptime.set(
            "lastboot",
            (scan_time - datetime.timedelta(seconds=random.randint(3600, 7776000))).strftime("%a %b %d %H:%M:%S %Y"),
        )

    # times
    times_el = ET.SubElement(host_el, "times")
    times_el.set("srtt", str(random.randint(500, 50000)))
    times_el.set("rttvar", str(random.randint(100, 5000)))
    times_el.set("to", str(random.randint(100000, 1000000)))

    return host_el


def build_scan(subnet_base: str, num_hosts: int, num_groups: int) -> ET.Element:
    """Build the complete <nmaprun> XML tree."""
    scan_start = datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 48))
    scan_end = scan_start + datetime.timedelta(seconds=random.randint(300, 7200))
    scan_duration = int((scan_end - scan_start).total_seconds())

    nmaprun = ET.Element("nmaprun")
    nmaprun.set("scanner", "nmap")
    nmaprun.set("args", f"nmap -sV -sC -O -T4 -p- --open {subnet_base}.0.0/16")
    nmaprun.set("start", _timestamp_str(scan_start))
    nmaprun.set("startstr", scan_start.strftime("%a %b %d %H:%M:%S %Y"))
    nmaprun.set("version", "7.94")
    nmaprun.set("xmloutputversion", "1.05")

    # scaninfo
    si = ET.SubElement(nmaprun, "scaninfo")
    si.set("type", "syn")
    si.set("protocol", "tcp")
    si.set("numservices", "65535")
    si.set("services", "1-65535")

    # verbose / debugging
    verbose = ET.SubElement(nmaprun, "verbose")
    verbose.set("level", "0")
    debug = ET.SubElement(nmaprun, "debugging")
    debug.set("level", "0")

    # Generate groups and IPs
    groups = generate_groups(num_hosts, num_groups)
    ips = _generate_ips(subnet_base, num_hosts)

    # Assign IPs to groups, build hosts
    ip_idx = 0
    hosts_up = 0
    for group in groups:
        for _ in range(group.count):
            if ip_idx >= len(ips):
                break
            ip = ips[ip_idx]
            ip_idx += 1

            ports = apply_jitter(group)
            host_el = build_host_element(
                ip,
                group,
                ports,
                scan_start + datetime.timedelta(seconds=random.randint(0, scan_duration)),
            )
            nmaprun.append(host_el)
            hosts_up += 1

    # runstats
    runstats = ET.SubElement(nmaprun, "runstats")
    finished = ET.SubElement(runstats, "finished")
    finished.set("time", _timestamp_str(scan_end))
    finished.set("timestr", scan_end.strftime("%a %b %d %H:%M:%S %Y"))
    finished.set("elapsed", str(scan_duration))
    finished.set(
        "summary",
        f"Nmap done at {scan_end.strftime('%a %b %d %H:%M:%S %Y')}; "
        f"{hosts_up} IP addresses ({hosts_up} hosts up) scanned",
    )
    finished.set("exit", "success")

    hosts_el = ET.SubElement(runstats, "hosts")
    hosts_el.set("up", str(hosts_up))
    hosts_el.set("down", "0")
    hosts_el.set("total", str(hosts_up))

    return nmaprun


def pretty_print(element: ET.Element) -> str:
    raw = ET.tostring(element, encoding="unicode")
    reparsed = minidom.parseString(raw)
    return reparsed.toprettyxml(indent="  ", encoding=None)


# -- Main ----------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Generate synthetic nmap XML report with large host groups")
    parser.add_argument("--hosts", type=int, default=3000, help="Number of hosts (default: 3000)")
    parser.add_argument(
        "--groups",
        type=int,
        default=15,
        help="Number of distinct host groups/profiles (default: 15)",
    )
    parser.add_argument(
        "--subnet",
        type=str,
        default="10.10",
        help="First 2 octets for IP generation, e.g. 10.10 (default: 10.10)",
    )
    parser.add_argument("--output", type=str, default="report.xml", help="Output file path")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    log.info(
        "Generating %d hosts in %d groups on %s.x.0/24 ...",
        args.hosts,
        args.groups,
        args.subnet,
    )

    tree = build_scan(args.subnet, args.hosts, args.groups)
    xml_str = pretty_print(tree)

    # minidom adds an xml declaration -- ensure it matches nmap's expected header
    lines = xml_str.splitlines()
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    # insert nmap DOCTYPE
    lines.insert(1, "<!DOCTYPE nmaprun>")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info("Written %d hosts to %s", args.hosts, args.output)


if __name__ == "__main__":
    main()
