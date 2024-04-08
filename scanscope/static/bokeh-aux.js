let currentHoverIds = [];

function hoverIdsAreSame(indices) {
    let arr1 = indices;
    let arr2 = currentHoverIds;

    if (arr1.length !== arr2.length) {
        return false;
    }

    let arr2Copy = arr2.slice();
    for (let i = 0; i < arr1.length; i++) {
        let index = arr2Copy.indexOf(arr1[i]);
        if (index === -1) {
            return false;
        }
        arr2Copy.splice(index, 1);
    }

    return true;
}

async function createHostsPopup(fingerprints, colorMap) {
    const templateHost = document.getElementById('template-popup-host');
    const templatePort = document.getElementById('template-port');

    const hostGroups = await getHostGroupsByFingerprints(fingerprints);
    if (!hostGroups) { return };

    const hostsFragments = hostGroups.values.map(h => {
        const host = templateHost.content.cloneNode(true);
        host.querySelector('.group-size').textContent = h[hostGroups.columns.indexOf("ip_addresses")].split(',').length;
        ports = h[hostGroups.columns.indexOf("port_numbers")].split(',');
        const portList = host.querySelector('.tcp-ports');
        ports.forEach(p => portList.appendChild(createPortSpan(p, templatePort)));

        const color = colorMap[h[hostGroups.columns.indexOf("fingerprint")]];
        host.querySelector('rect').setAttribute("fill", color);
        return host;
    });

    const templatePopup = document.getElementById('template-popup');
    const popup = templatePopup.content.cloneNode(true);
    document.body.appendChild(popup);
    hostsFragments.forEach(h => document.querySelector('.bokeh-popup').appendChild(h));
    addPortHints();
}

function getColorMap(indices, data, color_map){
    const colorMap = {};
    indices.forEach(i => {
        const color_index = data.color_index[i];
        colorMap[data.fingerprint[i]] = color_map.palette[color_map.factors.indexOf(color_index)];
    });
    return colorMap;
}

async function hostGroupHover(opts, cb_data) {
    // This is used as a callback from bokeh when the user hovers over a host group circle
    const indices = cb_data.index.indices;

    if (indices.length == 0) {
        currentHoverIds = indices;
        document.querySelectorAll(".bokeh-popup").forEach(el => el.remove());
        return;
    };

    if (!hoverIdsAreSame(indices)) {
        currentHoverIds = indices;
        document.querySelectorAll(".bokeh-popup").forEach(el => el.remove());

        const fingerprints = indices.map(i => opts.datasource.data.fingerprint[i]);
        const colorMap = getColorMap(indices, opts.datasource.data, opts.color_map);

        await createHostsPopup(fingerprints, colorMap);
    }

    let tooltipInstance = document.querySelector(".bokeh-popup");
    let bokehDiv = document.querySelector("#bokeh-div");
    if (!tooltipInstance || !bokehDiv) {return};
    const padding = 5; // Space between the tooltip and the cursor
    const cursorWidth = 10; // Approximate width of the cursor
    const x = bokehDiv.getBoundingClientRect().x + cb_data.geometry.sx + cursorWidth + padding;
    const y = bokehDiv.getBoundingClientRect().y + cb_data.geometry.sy + padding;

    tooltipInstance.style.left = `${x}px`;
    tooltipInstance.style.top = `${y}px`;
}

function portUnion(hostGroups) {
    // Return union of all port number lists
    if (!hostGroups) {return []}
    const arrays = hostGroups.values.map(g => g[hostGroups.columns.indexOf("port_numbers")].split(','));
    return [...new Set(arrays.flat())];
}

function portIntersection(hostGroups) {
    // Return intersection of all port number lists
    if (!hostGroups) {return []}
    const arrays = hostGroups.values.map(g => g[hostGroups.columns.indexOf("port_numbers")].split(','));
    return arrays.reduce((acc, array) => acc.filter(value => array.includes(value)));
}

async function createHostsGroupList(fingerprints, colorMap) {
    // Create the DOM elements after the user clicked on host group circle
    const hostGroups = await getHostGroupsByFingerprints(fingerprints);
    if (!hostGroups) {return};

    const templateHostGroupList = document.getElementById('template-host-group-list');
    const templateHostGroup = document.getElementById('template-host-group');
    const templateHostAddress = document.getElementById('template-host-address');
    const templatePort = document.getElementById('template-port');

    const hostGroupList = templateHostGroupList.content.cloneNode(true);
    portIntersection(hostGroups).forEach(p => {
        const port = templatePort.content.cloneNode(true);
        port.querySelector("span.scanscope-port").innerText = p;
        hostGroupList.querySelector("span.ports-intersection").appendChild(port);
    });
    portUnion(hostGroups).forEach(p => {
        const port = templatePort.content.cloneNode(true);
        port.querySelector("span.scanscope-port").innerText = p;
        hostGroupList.querySelector("span.ports-union").appendChild(port);
    });

    hostGroups.values.forEach(h => {
        const hostGroup = templateHostGroup.content.cloneNode(true);

        const hostnames = h[hostGroups.columns.indexOf("hostnames")].split(",");
        const addresses = h[hostGroups.columns.indexOf("ip_addresses")].split(',');
        addresses.forEach((a, i, row) => {
            const address = templateHostAddress.content.cloneNode(true);
            address.querySelector("span.scanscope-host-address").innerText = a;
            if (hostnames[i]) {
                address.querySelector("span.scanscope-host-address").title = hostnames[i];
            }
            hostGroup.querySelector('.host-group-addresses').appendChild(address);
            // if (i + 1 != row.length) {
            //     // Only if this is not the last item: insert a middot
            //     hostGroup.querySelector('.host-group-addresses').appendChild(document.createTextNode(' \u00b7 '));
            // }
        });

        const ports = h[hostGroups.columns.indexOf("port_numbers")].split(',');
        ports.map(p => {
            port = createPortSpan(p, templatePort);
            hostGroup.querySelector('.host-group-ports').appendChild(port);
        });

        const color = colorMap[h[hostGroups.columns.indexOf("fingerprint")]];
        hostGroup.querySelector('div.bokeh-host-group').style = "border-left-color: " + color;
        hostGroupList.querySelector("div.bokeh-host-group-list-body").appendChild(hostGroup);
    });

    let hostsDetails = document.querySelector("#hosts-details");
    hostsDetails.innerText = "";
    hostsDetails.append(hostGroupList);
}

function createPortSpan(p, template) {
    const port = template.content.cloneNode(true);
    const portSpan = port.querySelector("span.scanscope-port");
    portSpan.innerText = p;
    if (p<0) {
        portSpan.classList.add("bg-light");
        portSpan.classList.remove("bg-secondary");
    }
    return portSpan;
}

async function hostGroupClick(opts, cb_data) {
    // This is used as a callback from bokeh when the user clicks on a host group circle
    const indices = opts.datasource.selected.indices;
    const fingerprints = indices.map(i => opts.datasource.data.fingerprint[i]);
    const colorMap = getColorMap(indices, opts.datasource.data, opts.color_map);
    await createHostsGroupList(fingerprints, colorMap);
    addPortHints();
    addContextMenus();
}
