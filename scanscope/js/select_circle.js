const inds = cb_obj.indices;
const hostDetails = document.getElementById('hosts-details');
hostDetails.innerHTML = '';

const ToList = str => {
    const ul = document.createElement('ul');
    str.forEach(item => ul.innerHTML += `<li>${item}</li>`);
    return ul;
};

datasource.selected.indices.forEach( i => {
    const container = document.createElement('div');
    const header = document.createElement('div');
    const badges = document.createElement('div');
    const hosts_node = document.createElement('div');
    const portconfig_node = document.createElement('div');
    const tcp_node = document.createElement('div');
    const udp_node = document.createElement('div');

    const hosts = fp_map.get(datasource.data.fingerprint[i]);

    const color_index = datasource.data.color_index[i];
    var color = color_map.palette[color_map.factors.indexOf(color_index)];
    if (!color) { color = 'gray' };
    header.setAttribute('style', 'height: 10px; opacity: 60%; background-color: ' + color);


    badges.classList.add('badges');
    badges.innerHTML = '<div title="Hosts">' + hosts.length + '</div><div title="TCP-Ports">' + datasource.data.tcp_ports[i].length + '</div><div title="UDP-Ports">' + datasource.data.udp_ports[i].length + '</div>';

    hosts_node.innerText = "Hosts: ";
    hosts_node.appendChild(ToList(hosts));
    hosts_node.classList.add('portconfig-hosts');

    if (datasource.data.tcp_ports[i].length) {
        tcp_node.innerHTML = "TCP-Ports: ";
        tcp_node.appendChild(ToList(datasource.data.tcp_ports[i]));
    }
    if (datasource.data.udp_ports[i].length) {
        udp_node.innerHTML = "UDP-Ports: ";
        udp_node.appendChild(ToList(datasource.data.udp_ports[i]));
    }
    if (!(datasource.data.tcp_ports[i].length+datasource.data.udp_ports[i].length)) {
        tcp_node.innerHTML = 'No open ports';
    }

    tcp_node.classList.add('portconfig-proto');
    udp_node.classList.add('portconfig-proto');

    portconfig_node.appendChild(tcp_node);
    portconfig_node.appendChild(udp_node);
    portconfig_node.classList.add('portconfig');

    container.appendChild(header);
    container.appendChild(badges);
    container.appendChild(portconfig_node);
    container.appendChild(hosts_node);
    container.classList.add('portconfig-container');

    hostDetails.appendChild(container);
});
