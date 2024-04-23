async function main () {
    const services = await getServices();

    const tableDiv = document.querySelector("#services-table");
    if (!tableDiv) {return;}
    tableDiv.innerText = "";

    const table = document.createElement('table');

    const labels = {
        port_number: "Port",
        ip_addresses: "IP Addresses",
    };

    var tr = document.createElement('tr');

    for (const [key, value] of Object.entries(labels)) {
        var th = document.createElement('th');
        var text = document.createTextNode(value);
        th.appendChild(text);
        tr.appendChild(th);
    };
    table.appendChild(tr);

    const templateHostAddress = document.getElementById('template-host-address');
    const templatePort = document.getElementById('template-port');

    services.values.forEach((row, rowIndex) => {
        var tr = document.createElement('tr');
        const hostnames = row[services.columns.indexOf("hostnames")].split(",");

        for (const [key, value] of Object.entries(labels)) {
            var td = document.createElement('td');
            const val = row[services.columns.indexOf(key)];
            if (key == 'ip_addresses') {
                td.classList.add("scanscope-host-list");
                val.split(',').forEach((ip, ipIndex) => {
                    const ipSpan = templateHostAddress.content.cloneNode(true);
                    let addressElement = ipSpan.querySelector(".scanscope-host-address");
                    addressElement.innerText = ip;
                    if (hostnames[ipIndex]) {
                        addressElement.title = hostnames[ipIndex];
                    }
                    td.appendChild(ipSpan);
                });
            } else if (key == 'port_number') {
                const pSpan = templatePort.content.cloneNode(true);
                pSpan.querySelector(".scanscope-port").innerText = val;
                td.appendChild(pSpan);
            } else {
                var text = document.createTextNode(row[services.columns.indexOf(key)]);
                if (val) { td.appendChild(text); }
            }
            tr.appendChild(td);
        }

        table.appendChild(tr);
    })

    tableDiv.appendChild(table);
    addPortHints();
    addContextMenus();
}

window.addEventListener("load", main);
