// nmap top TCP/UDP ports:
// https://raw.githubusercontent.com/nmap/nmap/master/nmap-services
// cat nmap-services|sort -k3 -r |grep -vE '^#'|cut -f2  | grep tcp | head -n 24
// Decision: Replace 111/tcp with 88/tcp (=kerberos; important in windows networks)
document.scanscope = {};

document.scanscope.topTCPPorts = [
	80, 23, 443, 21, 22, 25, 3389, 110, 445, 139, 143, 53, 135, 3306, 8080, 1723,
	88, 995,
];

document.scanscope.topUDPPorts = [
	631, 161, 137, 123, 138, 1434, 445, 135, 67, 53, 139, 500,
];

/**
 * Calculate smart tooltip position that avoids going off-screen.
 * @param {number} mouseX - Mouse X position
 * @param {number} mouseY - Mouse Y position
 * @param {HTMLElement} tooltip - The tooltip element
 * @param {number} offset - Offset from cursor (default: 10px)
 * @returns {{left: string, top: string}} - CSS position values
 */
function calculateTooltipPosition(mouseX, mouseY, tooltip, offset = 10) {
	const padding = 5; // Extra padding from screen edge
	const cursorWidth = 10; // Approximate cursor width

	// Get tooltip dimensions
	const tooltipRect = tooltip.getBoundingClientRect();
	const tooltipWidth = tooltipRect.width || 200; // fallback if not rendered yet
	const tooltipHeight = tooltipRect.height || 100;

	// Get viewport dimensions
	const viewportWidth = window.innerWidth;
	const viewportHeight = window.innerHeight;

	// Calculate initial position (to the right and below cursor)
	let left = mouseX + cursorWidth + offset;
	let top = mouseY + offset;

	// Check if tooltip would go off right edge
	if (left + tooltipWidth + padding > viewportWidth) {
		// Flip to left side of cursor
		left = mouseX - tooltipWidth - offset;
	}

	// Check if tooltip would go off bottom edge
	if (top + tooltipHeight + padding > viewportHeight) {
		// Flip above cursor
		top = mouseY - tooltipHeight - offset;
	}

	// Ensure tooltip doesn't go off left edge (if flipped)
	if (left < padding) {
		left = padding;
	}

	// Ensure tooltip doesn't go off top edge (if flipped)
	if (top < padding) {
		top = padding;
	}

	return {
		left: `${left}px`,
		top: `${top}px`
	};
}

function portColors() {
	return [
		"success",
		"danger",
		"info",
		"light",
		"warning",
		"primary",
	];
}

function portFormatter(cell) {
	if (!cell) return "";

	const fragment = document.createElement("div");

	for (p of `${cell}`.split(",")) {
		const span = document.createElement("span");
		span.classList.add("scanscope-port");
		span.innerText = p;
		fragment.appendChild(span);
	}

	const result = fragment.outerHTML;

	return gridjs.html(result);
}

function addHosts(fragment, hosts) {
	let idx = 0;
	for (const [ip, hostname] of hosts) {
		const span = document.createElement("span");
		span.classList.add("scanscope-host-address");

		span.innerText = ip;

		if (hostname) span.title = hostname;

		const separator = document.createElement("span");
		separator.classList.add("scanscope-host-separator");
		separator.innerText = "·";

		if (idx >= 20 && hosts.length > 20) {
			span.style.display = "none";
			separator.style.display = "none";
		}

		fragment.appendChild(span);
		fragment.appendChild(document.createTextNode(" "));

		idx += 1;
	}

	if (idx >= 21 && hosts.length > 20) {
		const a = document.createElement("a");
		a.innerText = `Show all ${hosts.length} items`;
		a.classList.add("scanscope-expand-link");
		a.href = "#";
		fragment.appendChild(a);
		// We need to add event listener later when it has been inserted
	}
}

function hostGroupFormatter(cell) {
	if (!cell) return "";

	const fragment = document.createElement("div");

	fragment.classList.add("scanscope-host-list");

	const hosts = `${cell}`.split(",").map((pair) => pair.split(";"));
	const expand = addHosts(fragment, hosts);

	// Wrap in container div so querySelector works
	const par = document.createElement("div");
	par.appendChild(fragment);

	const result = par.outerHTML;

	return gridjs.html(result);
}

function expandHostGroup(evnt) {
	console.log(evnt);
	evnt.preventDefault();
	evnt.stopPropagation();
	const list = evnt.target.closest(".scanscope-host-list");
	for (el of list.querySelectorAll(
		".scanscope-host-address,.scanscope-host-separator",
	)) {
		el.style.display = "inline";
	}
	evnt.target.remove();
}

document.scanscope.columns = {
	services: [
		{
			label: "port_number",
			name: "Port",
			formatter: portFormatter,
		},
		{
			label: "hosts",
			name: "Hosts",
			formatter: hostGroupFormatter,
			order: "h.ip_address_int",
		},
	],
	hosts: [
		{
			label: "ip_address",
			name: "IP Address",
			order: "h.ip_address_int",
		},
		{
			label: "hostname",
			name: "Name",
		},
		{
			label: "ports",
			name: "Ports",
			formatter: portFormatter,
		},
		{
			label: "os",
			name: "OS",
		},
	],
};

function portStyles(topPorts, styles) {
	const result = {};

	styles.forEach((style, j) => {
		portColors().forEach((color, i) => {
			const item = {};
			item.color = color;
			item[style] = true;
			result[topPorts[portColors().length * j + i]] = item;
		});
	});

	return result;
}

function addPortHints(fragment) {
	const tcpStyles = portStyles(
		document.scanscope.topTCPPorts,
		[null, "dashed", "thick"],
	);
	const udpStyles = portStyles(
		document.scanscope.topUDPPorts,
		[null, "clipped"],
	);

	let doc = fragment;
	if (!doc) doc = document;

	const ports = doc.querySelectorAll("span.scanscope-port");
	let proto = null;
	let portMap = null;

	for (p of ports) {
		let text = p.innerText;

		if (text[0] === "-") {
			text = text.slice(1, text.length);
			portMap = portMapUDP;
			proto = "udp";
		} else {
			portMap = portMapTCP;
			proto = "tcp";
		}

		p.setAttribute("title", `${text}/${proto}: ${portMap[text]}`);
		p.classList.add("badge", "rounded-pill", "border", "border-secondary");

		if (proto === "udp") {
			p.classList.remove("border");
			p.classList.add("badge-secondary");
		}

		const tcpStyle = tcpStyles[text];
		const udpStyle = udpStyles[text];

		if (tcpStyle && proto === "tcp") {
			p.classList.remove("border-secondary");
			p.classList.add(`border-${tcpStyle.color}`);
			if (tcpStyle.dashed) {
				p.setAttribute("style", "border-style: dashed !important;");
			}
			if (tcpStyle.thick) {
				p.setAttribute("style", "border-width: 3px !important;");
			}
		} else if (udpStyle && proto === "udp") {
			p.classList.remove("badge-secondary");
			p.classList.add(`bg-${udpStyle.color}`);
			if (udpStyle.clipped) {
				p.setAttribute("style", "border-style: solid; !important;");
			}

			if (udpStyle.color === "light") {
				p.classList.add("text-dark");
			}
			if (udpStyle.color === "dark") {
				p.classList.add("text-white");
			}
		}
	}
}

function createPortSpan(p, template) {
	const port = template.content.cloneNode(true);
	const portSpan = port.querySelector("span.scanscope-port");
	portSpan.innerText = p;
	return portSpan;
}

/**
 * Convert category name to numeric value for visualization
 * @param {string} category - Category name
 * @returns {number} - Numeric category value
 */
function getCategoryNumber(category) {
	const categories = {
		'web': 0,
		'database': 1,
		'mail': 2,
		'remote_access': 3,
		'file_sharing': 4,
		'monitoring': 5,
		'empty': 6,
		'other': 7
	};
	return categories[category] || 7;
}

/**
 * Convert numeric category value to display name
 * @param {number} num - Numeric category value
 * @returns {string} - Category display name
 */
function getCategoryName(num) {
	const names = ['Web', 'Database', 'Mail', 'Remote Access', 'File Sharing', 'Monitoring', 'Empty', 'Other'];
	return names[num] || 'Other';
}

/**
 * Get color from data based on the specified color scheme
 * @param {Object} data - Data object containing color_* properties
 * @param {string} scheme - Color scheme name (category, cluster, port_count, fingerprint)
 * @returns {string} - Color value (hex or CSS color)
 */
function getColorByScheme(data, scheme) {
	const colorMap = {
		'category': data.color_category,
		'cluster': data.color_cluster,
		'port_count': data.color_port_count,
		'fingerprint': data.color_fingerprint
	};
	return colorMap[scheme] || data.color_category || '#999';
}

/**
 * Add a window resize handler that calls update function when chart is initialized
 * @param {Function} getChartRef - Function that returns the chart reference
 * @param {Function} updateFn - Function to call on resize
 * @returns {Function} - Event listener function (for potential cleanup)
 */
function addResizeHandler(getChartRef, updateFn) {
	const handler = () => {
		const chartRef = getChartRef();
		if (chartRef !== null && chartRef !== undefined) {
			updateFn();
		}
	};
	window.addEventListener('resize', handler);
	return handler;
}

/**
 * Display tooltip with popup content at smart position
 * @param {HTMLElement} tooltipElement - The tooltip DOM element
 * @param {DocumentFragment} popupContent - Content to display in tooltip
 * @param {number} pageX - Mouse X position
 * @param {number} pageY - Mouse Y position
 */
function showTooltipWithContent(tooltipElement, popupContent, pageX, pageY) {
	if (!popupContent) {
		return;
	}

	tooltipElement.innerHTML = '';
	tooltipElement.appendChild(popupContent);
	tooltipElement.style.display = 'block';

	const position = calculateTooltipPosition(pageX, pageY, tooltipElement);
	tooltipElement.style.left = position.left;
	tooltipElement.style.top = position.top;
}

/**
 * Update tooltip position (for mousemove events)
 * @param {HTMLElement} tooltipElement - The tooltip DOM element
 * @param {number} pageX - Mouse X position
 * @param {number} pageY - Mouse Y position
 */
function updateTooltipPosition(tooltipElement, pageX, pageY) {
	const position = calculateTooltipPosition(pageX, pageY, tooltipElement);
	tooltipElement.style.left = position.left;
	tooltipElement.style.top = position.top;
}

/**
 * Hide tooltip
 * @param {HTMLElement} tooltipElement - The tooltip DOM element
 */
function hideTooltip(tooltipElement) {
	tooltipElement.style.display = 'none';
}

/**
 * Create a map from fingerprints to values from data arrays
 * @param {Array<number>} indices - Array of data indices
 * @param {Object} data - Data object containing arrays
 * @param {string} fieldName - Name of the field to map (e.g., 'cluster', 'category')
 * @param {Function|null} customLogic - Optional custom logic for special cases (e.g., color_map handling)
 * @returns {Object} - Map from fingerprint to field value
 */
function createFingerprintMap(indices, data, fieldName, customLogic = null) {
	const resultMap = {};

	if (customLogic) {
		return customLogic(indices, data, resultMap);
	}

	if (data[fieldName]) {
		for (const i of indices) {
			resultMap[data.fingerprint[i]] = data[fieldName][i];
		}
	}

	return resultMap;
}

/**
 * Populate cluster and category metadata in a host element
 * @param {DocumentFragment|Element} hostElement - Element containing the popup structure
 * @param {number|undefined} cluster - Cluster ID (-1 for outliers, undefined/null if not available)
 * @param {string|undefined} category - Category name
 */
function populateHostMetadata(hostElement, cluster, category) {
	const clusterSpan = hostElement.querySelector(".popup-cluster");
	const categorySpan = hostElement.querySelector(".popup-category");
	const separatorSpan = hostElement.querySelector(".popup-separator");

	if (cluster !== undefined && cluster !== null) {
		clusterSpan.textContent = cluster === -1 ? "Outlier" : `Cluster ${cluster}`;
	}

	if (category) {
		categorySpan.textContent = category.charAt(0).toUpperCase() + category.slice(1);
	}

	if ((cluster !== undefined && cluster !== null) && category) {
		separatorSpan.textContent = " | ";
	}
}

async function createHostsPopupForFingerprint(fingerprint, color, cluster, category) {
	const templateHost = document.getElementById("template-popup-host");
	const templatePort = document.getElementById("template-port");

	if (!templateHost || !templatePort) {
		console.error("Popup templates not found");
		return null;
	}

	const hostGroups = await getHostGroupsByFingerprints([fingerprint]);
	if (!hostGroups || !hostGroups.values || hostGroups.values.length === 0) {
		return null;
	}

	const h = hostGroups.values[0];
	const host = templateHost.content.cloneNode(true);
	host.querySelector(".group-size").textContent =
		h[hostGroups.columns.indexOf("ip_addresses")].split(",").length;
	ports = h[hostGroups.columns.indexOf("port_numbers")].split(",");
	const portList = host.querySelector(".tcp-ports");
	for (p of ports) {
		portList.appendChild(createPortSpan(p, templatePort));
	}

	host.querySelector("rect").setAttribute("fill", color);

	populateHostMetadata(host, cluster, category);

	const fragment = document.createDocumentFragment();
	fragment.appendChild(host);

	addPortHints(fragment);

	return fragment;
}

function addContextMenus(fragment) {
	let doc = fragment;
	if (!doc) doc = document;

	const hostlists = doc.querySelectorAll(".scanscope-host-list");

	const templateMenu = document.querySelector(
		"#template-hosts-list-context-menu",
	);

	for (h of hostlists) {
		const menu = templateMenu.content.cloneNode(true);
		menu
			.querySelector("a.copy-line")
			.addEventListener("click", (e) => copyHosts(e, "\n"));
		menu
			.querySelector("a.copy-space")
			.addEventListener("click", (e) => copyHosts(e, " "));
		menu
			.querySelector("a.copy-comma")
			.addEventListener("click", (e) => copyHosts(e, ","));
		h.appendChild(menu);
	}

	for (el of doc.querySelectorAll(".scanscope-expand-link")) {
		el.addEventListener("click", expandHostGroup);
	}
}

function showPopup(evnt, text) {
	const popup = document.createElement("div");
	popup.innerText = text;
	popup.style.position = "absolute";
	popup.style.backgroundColor = "#333";
	popup.style.color = "#fff";
	popup.style.padding = "5px 10px";
	popup.style.borderRadius = "5px";
	popup.style.fontSize = "12px";
	popup.style.zIndex = "1000";
	popup.style.opacity = "0";
	popup.style.transition = "opacity 0.3s ease";

	// Position the popup near the link
	const rect = evnt.target.getBoundingClientRect();
	popup.style.left = `${rect.right + window.scrollX}px`;
	popup.style.top = `${rect.top + window.scrollY - 5}px`;

	// Add the popup to the body
	document.body.appendChild(popup);

	// Make the popup visible
	setTimeout(() => {
		popup.style.opacity = "1";
	}, 0);

	// Remove the popup after 2 seconds
	setTimeout(() => {
		popup.style.opacity = "0";
		setTimeout(() => {
			popup.remove();
		}, 300); // Wait for the transition to complete before removing the element
	}, 2000);
}

async function copyHosts(evnt, separator) {
	evnt.preventDefault();
	evnt.stopPropagation();

	const list = evnt.target.closest(".scanscope-host-list");
	const result = [];

	for (a of list.querySelectorAll(".scanscope-host-address")) {
		result.push(a.innerText);
	}

	const text = result.join(separator);

	try {
		await navigator.clipboard.writeText(text);
		showPopup(evnt, "Copied!");
	} catch (e) {
		console.error(e);
	}
}

function getOrderClause(table, opts) {
	const column = document.scanscope.columns[table];
	let order = `${column[0].order || column[0].label} ASC`;

	if (opts.url.order) {
		order = opts.url.order
			.map((o) => {
				let result = null;
				for (c of column) {
					if (c.label === o.order) {
						result = `${c.order || o.order} ${o.direction || "ASC"}`;
						break;
					}
				}
				if (!result) result = `${o.order} ${o.direction || "ASC"}`;
				return result;
			})
			.join(", ");
	}

	return order;
}

function getWhereClause(table, opts) {
	let where = "TRUE";
	if (opts.url.keyword) {
		opts.url.keyword = opts.url.keyword.replaceAll("'", "''");
		where = document.scanscope.columns[table]
			.map((c) => `${c.label} LIKE '%${opts.url.keyword}%'`)
			.join(" OR ");
	}
	return where;
}

function buildQuery(table, opts) {
	let query;
	const order = getOrderClause(table, opts);
	const where = getWhereClause(table, opts);

	if (table === "services") {
		query = `
            SELECT
                p.port_number AS port_number,
                GROUP_CONCAT(CONCAT(h.ip_address, ";", h.hostname) ORDER BY h.ip_address_int) AS hosts
            FROM
                ports p
            JOIN
                hosts h ON p.host_id = h.id
            GROUP BY port_number
            HAVING ${where}
            ORDER BY ${order}
            LIMIT ${opts.url.limit}
            OFFSET ${opts.url.page * opts.url.limit};`;
	} else {
		query = `
            SELECT
                h.ip_address AS ip_address,
                h.hostname AS hostname,
                GROUP_CONCAT(p.port_number ORDER BY p.port_number ASC) AS ports,
                h.os AS os
            FROM
                hosts h
            LEFT JOIN
                ports p ON h.id = p.host_id
            GROUP BY h.id
            HAVING ${where}
            ORDER BY ${order}
            LIMIT ${opts.url.limit}
            OFFSET ${opts.url.page * opts.url.limit};
        `;
	}
	return query;
}

function getTotalRows(table, opts) {
	let query;
	if (table === "services") {
		query = "SELECT COUNT(DISTINCT port_number) AS row_count FROM ports";
	} else {
		query = "SELECT COUNT(*) AS row_count FROM hosts";
	}
	const result = document.scanscope.db.exec(query)[0].values[0][0];
	return result;
}

function queryDb(table, opts) {
	// This function acts as the custom HTTP client for Grid.js
	return new Promise((resolve, reject) => {
		const query = buildQuery(table, opts);
		const total = getTotalRows(table, opts);
		const rows = document.scanscope.db.exec(query)[0];
		//  console.log(query, total, rows);

		if (!rows) {
			reject("Query returned no results");
		}

		resolve({
			data: rows.values,
			total: total,
		});
	});
}

function makeGrid(table) {
	const grid = new gridjs.Grid({
		columns: document.scanscope.columns[table],
		server: {
			data: (opts) => queryDb(table, opts),
		},
		pagination: {
			limit: 50,
			server: {
				data: (opts) => queryDb(table, opts),
				url: (prev, page, limit) => {
					const result = prev || {};
					result.page = page;
					result.limit = limit;
					return result;
				},
			},
		},
		search: {
			server: {
				url: (prev, keyword) => {
					const result = prev || {};
					result.keyword = keyword;
					return result;
				},
			},
		},
		sort: {
			multiColumn: true,
			server: {
				url: (prev, columns) => {
					if (!columns.length) return prev;

					const result = prev || {};

					const order = columns.map((c) => {
						return {
							order: document.scanscope.columns[table][c.index].label,
							direction: c.direction === 1 ? "ASC" : "DESC",
						};
					});

					result.order = order;

					return result;
				},
			},
		},
		style: {
			td: { "font-family": "monospace", "word-break": "break-all" },
			style: {
				container: {
					width: "90%",
					height: "90%",
				},
			},
		},
	});
	return grid;
}

function mutationCallback(mutationList, observer) {
	for (const mutation of mutationList) {
		if (mutation.type === "childList") {
			addPortHints(mutation.target);
			addContextMenus(mutation.target);
		}
	}
}
