def get_minimal_port_map(portscan):
    from scanscope.portmap import port_map_tcp, port_map_udp

    tcp_ports = set()
    for k in portscan.values():
        tcp_ports.update(k["tcp_ports"])

    udp_ports = set()
    for k in portscan.values():
        udp_ports.update(k["udp_ports"])

    tcp = {
        k: v for k, v in port_map_tcp.items() if int(k) in tcp_ports
    }
    udp = {
        k: v for k, v in port_map_udp.items() if int(k) in udp_ports
    }

    return dict(port_map_tcp=tcp, port_map_udp=udp)
