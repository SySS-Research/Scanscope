// Treemap visualization using D3.js

let treemapChart = null;
let currentGroupBy = 'category';
let currentColorScheme = 'category';

function initTreemap() {
    if (typeof treemapData === 'undefined') {
        console.error('treemapData not defined');
        return;
    }

    // Initialize event listeners
    document.getElementById('treemap-group-select').addEventListener('change', function(e) {
        currentGroupBy = e.target.value;
        updateTreemap();
    });

    document.getElementById('treemap-color-select').addEventListener('change', function(e) {
        currentColorScheme = e.target.value;
        updateTreemap();
    });

    // Initial render
    updateTreemap();
}

function prepareTreemapHierarchy(data, groupBy) {
    // Group hosts by the selected criterion
    const groups = {};

    data.forEach(host => {
        let groupKey;
        let groupName;

        if (groupBy === 'category') {
            groupKey = host.category || 'other';
            groupName = groupKey.charAt(0).toUpperCase() + groupKey.slice(1);
        } else if (groupBy === 'cluster') {
            groupKey = host.cluster !== undefined ? `cluster_${host.cluster}` : 'cluster_-1';
            groupName = host.cluster === -1 ? 'Outliers' : `Cluster ${host.cluster}`;
        } else if (groupBy === 'port_count_range') {
            const portCount = host.port_count || 0;
            if (portCount === 0) {
                groupKey = 'range_0';
                groupName = '0 ports';
            } else if (portCount <= 5) {
                groupKey = 'range_1_5';
                groupName = '1-5 ports';
            } else if (portCount <= 10) {
                groupKey = 'range_6_10';
                groupName = '6-10 ports';
            } else if (portCount <= 20) {
                groupKey = 'range_11_20';
                groupName = '11-20 ports';
            } else if (portCount <= 50) {
                groupKey = 'range_21_50';
                groupName = '21-50 ports';
            } else {
                groupKey = 'range_51_plus';
                groupName = '51+ ports';
            }
        }

        if (!groups[groupKey]) {
            groups[groupKey] = {
                name: groupName,
                children: [],
                key: groupKey
            };
        }

        groups[groupKey].children.push(host);
    });

    // Convert to hierarchy format
    const children = Object.values(groups).map(group => ({
        name: group.name,
        key: group.key,
        value: group.children.reduce((sum, h) => sum + (h.fp_count || 1), 0),
        hostCount: group.children.length,
        children: group.children
    }));

    return {
        name: 'All Hosts',
        children: children
    };
}

function updateTreemap() {
    const container = document.getElementById('treemap-container');
    const svg = d3.select('#treemap-svg');
    svg.selectAll('*').remove();

    const width = container.clientWidth;
    const height = container.clientHeight;

    const hierarchyData = prepareTreemapHierarchy(treemapData, currentGroupBy);

    const root = d3.hierarchy(hierarchyData)
        .sum(d => d.fp_count || 0)
        .sort((a, b) => b.value - a.value);

    d3.treemap()
        .size([width, height])
        .padding(2)
        .round(true)
        (root);

    const tooltip = d3.select('#treemap-tooltip');

    // Create groups
    const cell = svg.selectAll('g')
        .data(root.leaves())
        .join('g')
        .attr('transform', d => `translate(${d.x0},${d.y0})`);

    // Add rectangles
    cell.append('rect')
        .attr('width', d => d.x1 - d.x0)
        .attr('height', d => d.y1 - d.y0)
        .attr('fill', d => getColorByScheme(d.data, currentColorScheme))
        .attr('stroke', '#333')
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')
        .on('mouseover', async function(event, d) {
            d3.select(this)
                .attr('stroke', '#fff')
                .attr('stroke-width', 2);

            const color = getColorByScheme(d.data, currentColorScheme);
            const cluster = d.data.cluster;
            const category = d.data.category;
            const popupContent = await createHostsPopupForFingerprint(d.data.fingerprint, color, cluster, category);

            showTooltipWithContent(tooltip.node(), popupContent, event.pageX, event.pageY);
        })
        .on('mousemove', function(event) {
            updateTooltipPosition(tooltip.node(), event.pageX, event.pageY);
        })
        .on('mouseout', function() {
            d3.select(this)
                .attr('stroke', '#333')
                .attr('stroke-width', 1);
            hideTooltip(tooltip.node());
        })
        .on('click', function(event, d) {
            showTreemapDetails(d);
        });

    // Add text labels for larger cells
    cell.append('text')
        .attr('x', 4)
        .attr('y', 16)
        .text(d => {
            const width = d.x1 - d.x0;
            const height = d.y1 - d.y0;
            // Only show text if cell is large enough
            if (width > 60 && height > 30) {
                const count = d.data.fp_count || 1;
                return count > 1 ? count : '';
            }
            return '';
        })
        .attr('font-size', '12px')
        .attr('fill', '#fff')
        .attr('font-weight', 'bold')
        .style('pointer-events', 'none');
}

function showTreemapDetails(d) {
    const detailsContent = document.getElementById('treemap-details-content');
    const tcpPorts = d.data.tcp_ports || [];
    const udpPorts = d.data.udp_ports || [];

    // Create container
    const container = document.createElement('div');

    // Add title
    const title = document.createElement('h6');
    title.textContent = d.parent.data.name;
    container.appendChild(title);

    // Add host count
    const hostCount = document.createElement('p');
    hostCount.innerHTML = `<strong>Host Count:</strong> ${d.data.fp_count || 1}`;
    container.appendChild(hostCount);

    // Add TCP ports with pills
    const tcpContainer = document.createElement('p');
    const tcpLabel = document.createElement('strong');
    tcpLabel.textContent = `TCP Ports (${tcpPorts.length}): `;
    tcpContainer.appendChild(tcpLabel);

    if (tcpPorts.length > 0) {
        const tcpPortsSpan = document.createElement('span');
        tcpPorts.forEach(port => {
            const portSpan = document.createElement('span');
            portSpan.className = 'scanscope-port';
            portSpan.textContent = port;
            tcpPortsSpan.appendChild(portSpan);
            tcpPortsSpan.appendChild(document.createTextNode(' '));
        });
        tcpContainer.appendChild(tcpPortsSpan);
    } else {
        tcpContainer.appendChild(document.createTextNode('None'));
    }
    container.appendChild(tcpContainer);

    // Add UDP ports with pills
    const udpContainer = document.createElement('p');
    const udpLabel = document.createElement('strong');
    udpLabel.textContent = `UDP Ports (${udpPorts.length}): `;
    udpContainer.appendChild(udpLabel);

    if (udpPorts.length > 0) {
        const udpPortsSpan = document.createElement('span');
        udpPorts.forEach(port => {
            const portSpan = document.createElement('span');
            portSpan.className = 'scanscope-port';
            portSpan.textContent = `-${port}`;
            udpPortsSpan.appendChild(portSpan);
            udpPortsSpan.appendChild(document.createTextNode(' '));
        });
        udpContainer.appendChild(udpPortsSpan);
    } else {
        udpContainer.appendChild(document.createTextNode('None'));
    }
    container.appendChild(udpContainer);

    // Add category if present
    if (d.data.category) {
        const categoryP = document.createElement('p');
        categoryP.innerHTML = `<strong>Category:</strong> ${d.data.category}`;
        container.appendChild(categoryP);
    }

    // Add cluster if present
    if (d.data.cluster !== undefined) {
        const clusterP = document.createElement('p');
        clusterP.innerHTML = `<strong>Cluster:</strong> ${d.data.cluster === -1 ? 'Outlier' : d.data.cluster}`;
        container.appendChild(clusterP);
    }

    // Add fingerprint if present
    if (d.data.fingerprint) {
        const fingerprintP = document.createElement('p');
        fingerprintP.innerHTML = `<strong>Fingerprint:</strong> ${d.data.fingerprint}`;
        container.appendChild(fingerprintP);
    }

    // Clear and add new content
    detailsContent.innerHTML = '';
    detailsContent.appendChild(container);

    // Apply port styling
    addPortHints(detailsContent);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initTreemap);

// Re-render on window resize
addResizeHandler(() => treemapChart, updateTreemap);
