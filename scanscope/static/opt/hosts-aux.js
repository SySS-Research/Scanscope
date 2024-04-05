async function main () {
    const hosts = await getHosts();

    const tableDiv = document.querySelector("#hosts-table");
    tableDiv.innerText = "";

    const table = document.createElement('table');

    const labels = {
        ip_address: "IP Address",
        port_numbers: "Ports",
        os: "OS",
        hostname: "Hostname",
    };

    var tr = document.createElement('tr');

    for (const [key, value] of Object.entries(labels)) {
        var th = document.createElement('th');
        var text = document.createTextNode(value);
        th.appendChild(text);
        tr.appendChild(th);
    };
    table.appendChild(tr);

    const templatePort = document.getElementById('template-port');

    hosts.values.forEach(row => {
        var tr = document.createElement('tr');

        for (const [key, value] of Object.entries(labels)) {
            var td = document.createElement('td');
            const val = row[hosts.columns.indexOf(key)];
            if (key == 'port_numbers') {
                val.split(',').forEach(p => {
                    const pSpan = templatePort.content.cloneNode(true);
                    pSpan.querySelector(".scanscope-port").innerText = p;
                    td.appendChild(pSpan);
                });
            } else {
                var text = document.createTextNode(row[hosts.columns.indexOf(key)]);
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
