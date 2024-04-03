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

function createHostsPopup(indices) {
    const templateHost = document.getElementById('template-popup-host');

    var hosts = indices.map(i => {
        const host = templateHost.content.cloneNode(true);
        //TODO: these are example values. Get this from the DB.
        host.querySelector('.group-size').textContent = i;
        host.querySelector('.tcp-ports').textContent = '80,443';
        host.querySelector('.udp-ports').textContent = '53';
        return host;
    });

    const templatePopup = document.getElementById('template-popup');
    const popup = templatePopup.content.cloneNode(true);
    document.body.appendChild(popup);
    hosts.forEach(h => document.querySelector('.bokeh-popup').appendChild(h));
}

function hostGroupHover(cb_data) {
    // console.log('hostGroupHover', cb_data);
    const indices = cb_data.index.indices;

    if (indices.length == 0) {
        currentHoverIds = indices;
        document.querySelectorAll(".bokeh-popup").forEach(el => el.remove());
        return;
    };

    if (!hoverIdsAreSame(indices)) {
        currentHoverIds = indices;
        document.querySelectorAll(".bokeh-popup").forEach(el => el.remove());
        createHostsPopup(indices);
    }

    let tooltipInstance = document.querySelector(".bokeh-popup");
    let bokehDiv = document.querySelector("#bokeh-div");
    const padding = 5; // Space between the tooltip and the cursor
    const cursorWidth = 10; // Approximate width of the cursor
    const x = bokehDiv.getBoundingClientRect().x + cb_data.geometry.sx + cursorWidth + padding;
    const y = bokehDiv.getBoundingClientRect().y + cb_data.geometry.sy + padding;

    tooltipInstance.style.left = `${x}px`;
    tooltipInstance.style.top = `${y}px`;
}

function hostGroupClick(opts) {
    const indices = opts.datasource.selected.indices;
    console.log('hostGroupClick', indices);
    let hostsDetails = document.querySelector("#hosts-details");
    hostsDetails.innerText = indices;
}
