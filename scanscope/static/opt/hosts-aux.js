async function main () {
    const hosts = await getHosts();
    console.log(hosts);

    const tableDiv = document.querySelector("#hosts-table");
    tableDiv.innerText = "";

    const table = document.createElement('table');

    const labels = {
        ip_address: "IP Address",
        tcp_ports: "TCP Ports",
        udp_ports: "UDP Ports",
        fingerprint: "Fingerprint",
    };

    var tr = document.createElement('tr');

    for (const [key, value] of Object.entries(labels)) {
        var th = document.createElement('th');
        var text = document.createTextNode(value);
        th.appendChild(text);
        tr.appendChild(th);
    };
    table.appendChild(tr);

    hosts.values.forEach(row => {
        var tr = document.createElement('tr');

        for (const [key, value] of Object.entries(labels)) {
            var td = document.createElement('td');
            var text = document.createTextNode(row[hosts.columns.findIndex(x => x==key)]);
            td.appendChild(text);
            tr.appendChild(td);
        }

        table.appendChild(tr);
    })

    tableDiv.appendChild(table);
}

window.addEventListener("load", main);
