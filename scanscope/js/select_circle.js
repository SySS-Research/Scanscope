const inds = cb_obj.indices;
const hostDetails = document.getElementById('hosts-details');
hostDetails.innerHTML = '';

const ToList = str => {
    const ul = document.createElement('ul');
    str.forEach(item => ul.innerHTML += `<li>${item}</li>`);
    return ul;
};

const sortIpList = ips => {
    // TODO consider IPv6
    return ips.sort((a,b) => {
        const num1 = Number(a.split(".").map((num) => (`000${num}`).slice(-3) ).join(""));
        const num2 = Number(b.split(".").map((num) => (`000${num}`).slice(-3) ).join(""));
        return num1-num2;
    });
}

datasource.selected.indices.forEach( i => {
    const container = document.createElement('div');
    const header = document.createElement('div');
    const hosts_node = document.createElement('div');
    const portconfig_node = document.createElement('div');
    const tcp_node = document.createElement('div');
    const udp_node = document.createElement('div');

    const hosts = sortIpList(fp_map.get(datasource.data.fingerprint[i]));
    const tcp_ports = datasource.data.tcp_ports[i];
    const udp_ports = datasource.data.udp_ports[i];

    const color_index = datasource.data.color_index[i];
    var color = color_map.palette[color_map.factors.indexOf(color_index)];
    if (!color) { color = 'gray' };
    header.setAttribute('style', 'height: 10px; opacity: 60%; background-color: ' + color);


    hosts_node.innerText = `${hosts.length} hosts`;
    hosts_node.appendChild(ToList(hosts));
    hosts_node.querySelector('ul').classList.add('collapsible-list');
    hosts_node.querySelector('ul').classList.add('collapsed');
    hosts_node.classList.add('portconfig-hosts');

    if (tcp_ports.length) {
        tcp_node.innerHTML = `<span class='list-title'>${tcp_ports.length} TCP ports</span>`;
        tcp_node.appendChild(ToList(tcp_ports));
    }
    if (udp_ports.length) {
        udp_node.innerHTML = `<span class='list-title'>${udp_ports.length} UDP ports</span>`;
        udp_node.appendChild(ToList(udp_ports));
    }
    if (!(tcp_ports.length+udp_ports.length)) {
        tcp_node.innerHTML = 'No open ports';
    }

    tcp_node.classList.add('portconfig-proto');
    udp_node.classList.add('portconfig-proto');

    portconfig_node.appendChild(tcp_node);
    portconfig_node.appendChild(udp_node);
    portconfig_node.classList.add('portconfig');

    container.appendChild(header);
    container.appendChild(portconfig_node);
    container.appendChild(hosts_node);
    container.classList.add('portconfig-container');

    hostDetails.appendChild(container);

});

function toggleCollapse(e) {
    const list = e.target.closest('ul');
    list.classList.toggle("collapsed");
    list.querySelector("a").textContent = list.classList.contains("collapsed") ? "Show more items" : "Show fewer items";
}

// Add "show more items" link
const lists = document.querySelectorAll(".collapsible-list");
lists.forEach(list => {
    const items = list.querySelectorAll("li");
    const moreItemsLink = document.createElement("li");
    moreItemsLink.className = "more-items";
    moreItemsLink.innerHTML = '<a href="#">Show more items</a>';
    moreItemsLink.addEventListener("click", toggleCollapse);
    if (list.children.length > 5) { list.prepend(moreItemsLink); }
});
