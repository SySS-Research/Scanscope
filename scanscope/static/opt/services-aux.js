async function main () {
    const services = await getServices();
    console.log(services);

    const tableDiv = document.querySelector("#services-table");
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

    services.values.forEach(row => {
        var tr = document.createElement('tr');

        for (const [key, value] of Object.entries(labels)) {
            var td = document.createElement('td');
            const val = row[services.columns.indexOf(key)];
            if (key == 'ip_addresses') {
                val.split(',').forEach(ip => {
                    const ipSpan = templateHostAddress.content.cloneNode(true);
                    ipSpan.querySelector(".scanscope-host-address").innerText = ip;
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
}

window.addEventListener("load", main);
