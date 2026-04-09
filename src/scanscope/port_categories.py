"""Port categorization for semantic coloring of hosts."""

from dataclasses import dataclass


@dataclass
class PortCategory:
    name: str
    ports: list[int]
    color: str
    priority: int


PORT_CATEGORIES = {
    "domain_controller": PortCategory(
        name="domain_controller",
        ports=[53, 88, 389, 445, 636, 3268, 3269],  # DNS, Kerberos, LDAP, SMB
        color="#8e44ad",
        priority=1,
    ),
    "printer": PortCategory(
        name="printer",
        ports=[515, 631, 9100],  # LPD, IPP, RAW printing
        color="#16a085",
        priority=2,
    ),
    "database": PortCategory(
        name="database",
        ports=[
            1433,
            1434,
            3306,
            5432,
            5984,
            6379,
            9042,
            9200,
            27017,
            28015,
        ],  # MSSQL, MySQL, PostgreSQL, CouchDB, Redis, Cassandra, Elasticsearch, MongoDB, RethinkDB
        color="#e74c3c",
        priority=3,
    ),
    "web": PortCategory(
        name="web",
        ports=[80, 443, 8000, 8008, 8080, 8443, 8888, 9000],
        color="#3498db",
        priority=4,
    ),
    "mail": PortCategory(
        name="mail",
        ports=[25, 110, 143, 465, 587, 993, 995, 2525],
        color="#9b59b6",
        priority=5,
    ),
    "remote_access": PortCategory(
        name="remote_access",
        ports=[22, 23, 3389, 5900, 5901, 5902],
        color="#e67e22",
        priority=6,
    ),
    "file_sharing": PortCategory(
        name="file_sharing",
        ports=[21, 20, 2049],  # FTP, NFS (removed 139, 445 as they're too common on Windows)
        color="#1abc9c",
        priority=7,
    ),
    "monitoring": PortCategory(
        name="monitoring",
        ports=[161, 162, 514, 9090, 9093, 9100, 3000, 4000],
        color="#f39c12",
        priority=8,
    ),
    "dns": PortCategory(
        name="dns",
        ports=[53],
        color="#27ae60",
        priority=9,
    ),
    "vpn": PortCategory(
        name="vpn",
        ports=[500, 1194, 1723, 4500],
        color="#2980b9",
        priority=10,
    ),
    "ldap": PortCategory(
        name="ldap",
        ports=[389, 636, 3268, 3269],
        color="#c0392b",
        priority=11,
    ),
    "messaging": PortCategory(
        name="messaging",
        ports=[5222, 5269, 6667, 6697, 8883, 1883],
        color="#2c3e50",
        priority=12,
    ),
    "empty": PortCategory(
        name="empty",
        ports=[],
        color="#95a5a6",
        priority=999,
    ),
    "other": PortCategory(
        name="other",
        ports=[],
        color="#34495e",
        priority=998,
    ),
}


def categorize_host(tcp_ports: list[int], udp_ports: list[int]) -> str:
    """Determine primary category based on open ports.

    Returns category name based on highest-priority match.
    If multiple categories match, return the one with highest priority (lowest number).
    If no open ports, return 'empty'.
    If ports don't match any category, return 'other'.

    Special rules:
    - Domain Controller: Must have SMB (445) AND (LDAP (389/636) OR LDAP GC (3268/3269))
      AND Kerberos (88) AND DNS (53)
    - Printer: Strong indicator if typical printer ports are present
    - Database: Strong indicator if typical database ports are present

    Args:
        tcp_ports: List of open TCP ports
        udp_ports: List of open UDP ports

    Returns:
        Category name (e.g., 'web', 'database', 'domain_controller', 'empty')
    """
    all_ports = set(tcp_ports + udp_ports)

    if not all_ports:
        return "empty"

    # Special rule: Domain Controller requires specific combination of ports
    dc_required_ports = {445, 88, 53}  # SMB, Kerberos, DNS
    dc_ldap_ports = {389, 636, 3268, 3269}  # At least one LDAP port
    if dc_required_ports.issubset(all_ports) and any(p in all_ports for p in dc_ldap_ports):
        return "domain_controller"

    scores: dict[str, tuple[float, int]] = {}

    for category_name, category in PORT_CATEGORIES.items():
        if category_name in ["empty", "other", "domain_controller"]:
            continue

        matching_ports = all_ports.intersection(set(category.ports))
        if matching_ports:
            # Give extra weight to printer and database categories
            weight = 1.5 if category_name in ["printer", "database"] else 1.0
            scores[category_name] = (len(matching_ports) * weight, category.priority)

    if not scores:
        return "other"

    best_category = max(scores.items(), key=lambda x: (x[1][0], -x[1][1]))[0]
    return best_category


def get_category_color(category: str) -> str:
    """Get color for a given category.

    Args:
        category: Category name

    Returns:
        Hex color string (e.g., '#3498db')
    """
    return PORT_CATEGORIES.get(category, PORT_CATEGORIES["other"]).color
