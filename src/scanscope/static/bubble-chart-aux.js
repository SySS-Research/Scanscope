let currentHoverIds = [];
let globalDatasource = null;
let originalDatasourceData = null;

function hoverIdsAreSame(indices) {
	const arr1 = indices;
	const arr2 = currentHoverIds;

	if (arr1.length !== arr2.length) {
		return false;
	}

	const arr2Copy = arr2.slice();
	for (let i = 0; i < arr1.length; i++) {
		const index = arr2Copy.indexOf(arr1[i]);
		if (index === -1) {
			return false;
		}
		arr2Copy.splice(index, 1);
	}

	return true;
}

async function createHostsPopup(fingerprints, colorMap, clusterMap, categoryMap) {
	const templateHost = document.getElementById("template-popup-host");
	const templatePort = document.getElementById("template-port");

	const hostGroups = await getHostGroupsByFingerprints(fingerprints);
	if (!hostGroups) {
		return;
	}

	const hostsFragments = hostGroups.values.map((h) => {
		const host = templateHost.content.cloneNode(true);
		host.querySelector(".group-size").textContent =
			h[hostGroups.columns.indexOf("ip_addresses")].split(",").length;
		const portNumbers = h[hostGroups.columns.indexOf("port_numbers")];
		ports = portNumbers ? portNumbers.split(",") : [];
		const portList = host.querySelector(".tcp-ports");
		for (p of ports) {
			if (p) {  // Skip empty strings
				portList.appendChild(createPortSpan(p, templatePort));
			}
		}

		const fingerprint = h[hostGroups.columns.indexOf("fingerprint")];
		const color = colorMap[fingerprint];
		host.querySelector("rect").setAttribute("fill", color);

		const cluster = clusterMap ? clusterMap[fingerprint] : undefined;
		const category = categoryMap ? categoryMap[fingerprint] : undefined;

		populateHostMetadata(host, cluster, category);

		return host;
	});

	const templatePopup = document.getElementById("template-popup");
	const popup = templatePopup.content.cloneNode(true);
	document.body.appendChild(popup);
	for (h of hostsFragments) {
		document.querySelector(".bokeh-popup").appendChild(h);
	}
	addPortHints();
}

function getColorMap(indices, data, color_map) {
	return createFingerprintMap(indices, data, 'color', (indices, data, colorMap) => {
		for (const i of indices) {
			if (data.color && data.color[i]) {
				colorMap[data.fingerprint[i]] = data.color[i];
			} else if (color_map) {
				const color_index = data.color_index[i];
				colorMap[data.fingerprint[i]] =
					color_map.palette[color_map.factors.indexOf(color_index)];
			}
		}
		return colorMap;
	});
}

function getClusterMap(indices, data) {
	return createFingerprintMap(indices, data, 'cluster');
}

function getCategoryMap(indices, data) {
	return createFingerprintMap(indices, data, 'category');
}

async function hostGroupHover(opts, cb_data) {
	// This is used as a callback from bokeh when the user hovers over a host group circle
	if (!globalDatasource) {
		globalDatasource = opts.datasource;
		initColorSchemeSelector();
		initHideEmptyHostsCheckbox();
	}
	const indices = cb_data.index.indices;

	if (indices.length === 0) {
		currentHoverIds = indices;
		for (el of document.querySelectorAll(".bokeh-popup")) {
			el.remove();
		}
		return;
	}

	if (!hoverIdsAreSame(indices)) {
		currentHoverIds = indices;
		for (el of document.querySelectorAll(".bokeh-popup")) {
			el.remove();
		}

		const fingerprints = indices.map(
			(i) => opts.datasource.data.fingerprint[i],
		);
		const colorMap = getColorMap(indices, opts.datasource.data, opts.color_map);
		const clusterMap = getClusterMap(indices, opts.datasource.data);
		const categoryMap = getCategoryMap(indices, opts.datasource.data);

		await createHostsPopup(fingerprints, colorMap, clusterMap, categoryMap);
	}

	const tooltipInstance = document.querySelector(".bokeh-popup");
	const bokehDiv = document.querySelector("#bokeh-div");
	if (!tooltipInstance || !bokehDiv) {
		return;
	}

	// Calculate mouse position relative to viewport
	const mouseX = bokehDiv.getBoundingClientRect().x + cb_data.geometry.sx;
	const mouseY = bokehDiv.getBoundingClientRect().y + cb_data.geometry.sy;

	// Use smart positioning to avoid going off-screen
	const position = calculateTooltipPosition(mouseX, mouseY, tooltipInstance);
	tooltipInstance.style.left = position.left;
	tooltipInstance.style.top = position.top;
}

function portUnion(hostGroups) {
	// Return union of all port number lists
	if (!hostGroups) {
		return [];
	}
	const arrays = hostGroups.values.map((g) => {
		const portNumbers = g[hostGroups.columns.indexOf("port_numbers")];
		return portNumbers ? portNumbers.split(",") : [];
	});
	return [...new Set(arrays.flat())].filter(p => p);  // Filter out empty strings
}

function portIntersection(hostGroups) {
	// Return intersection of all port number lists
	if (!hostGroups) {
		return [];
	}
	const arrays = hostGroups.values.map((g) => {
		const portNumbers = g[hostGroups.columns.indexOf("port_numbers")];
		return portNumbers ? portNumbers.split(",").filter(p => p) : [];
	});
	// If any host group has no ports, intersection is empty
	if (arrays.some(arr => arr.length === 0)) {
		return [];
	}
	return arrays.reduce((acc, array) =>
		acc.filter((value) => array.includes(value)),
	);
}

async function createHostsGroupList(fingerprints, colorMap) {
	// Create the DOM elements after the user clicked on host group circle
	const hostGroups = await getHostGroupsByFingerprints(fingerprints);
	if (!hostGroups) {
		return;
	}

	const templateHostGroupList = document.getElementById(
		"template-host-group-list",
	);
	const templateHostGroup = document.getElementById("template-host-group");
	const templateHostAddress = document.getElementById("template-host-address");
	const templatePort = document.getElementById("template-port");

	const hostGroupList = templateHostGroupList.content.cloneNode(true);
	for (p of portIntersection(hostGroups)) {
		const port = templatePort.content.cloneNode(true);
		port.querySelector("span.scanscope-port").innerText = p;
		hostGroupList.querySelector("span.ports-intersection").appendChild(port);
	}
	for (p of portUnion(hostGroups)) {
		const port = templatePort.content.cloneNode(true);
		port.querySelector("span.scanscope-port").innerText = p;
		hostGroupList.querySelector("span.ports-union").appendChild(port);
	}

	for (h of hostGroups.values) {
		const hostGroup = templateHostGroup.content.cloneNode(true);

		const hostnames = h[hostGroups.columns.indexOf("hostnames")].split(",");
		const addresses = h[hostGroups.columns.indexOf("ip_addresses")].split(",");
		const hosts = addresses.map((e, i) => [e, hostnames[i]]);
		addHosts(hostGroup.querySelector(".host-group-addresses"), hosts);

		const portNumbers = h[hostGroups.columns.indexOf("port_numbers")];
		const ports = portNumbers ? portNumbers.split(",") : [];
		ports.map((p) => {
			if (p) {  // Skip empty strings
				port = createPortSpan(p, templatePort);
				hostGroup.querySelector(".host-group-ports").appendChild(port);
			}
		});

		const color = colorMap[h[hostGroups.columns.indexOf("fingerprint")]];
		hostGroup.querySelector("div.bokeh-host-group").style =
			`border-left-color: ${color}`;
		hostGroupList
			.querySelector("div.bokeh-host-group-list-body")
			.appendChild(hostGroup);
	}

	const hostsDetails = document.querySelector("#hosts-details");
	hostsDetails.innerText = "";
	hostsDetails.append(hostGroupList);
}

async function hostGroupClick(opts, cb_data) {
	// This is used as a callback from bokeh when the user clicks on a host group circle
	if (!globalDatasource) {
		globalDatasource = opts.datasource;
		initColorSchemeSelector();
		initHideEmptyHostsCheckbox();
	}
	const indices = opts.datasource.selected.indices;
	const fingerprints = indices.map((i) => opts.datasource.data.fingerprint[i]);
	const colorMap = getColorMap(indices, opts.datasource.data, opts.color_map);
	await createHostsGroupList(fingerprints, colorMap);
	addPortHints();
	addContextMenus();
}

function initColorSchemeSelector() {
	const selector = document.getElementById("color-scheme-select");
	if (!selector || selector.dataset.initialized) {
		return;
	}

	// Detect which color schemes are available
	const data = globalDatasource.data;
	const availableSchemes = [];
	if (data.color_category) availableSchemes.push("category");
	if (data.color_cluster) availableSchemes.push("cluster");
	if (data.color_port_count) availableSchemes.push("port_count");
	if (data.color_fingerprint) availableSchemes.push("fingerprint");

	// Disable options that aren't available
	for (const option of selector.options) {
		if (!availableSchemes.includes(option.value)) {
			option.disabled = true;
		}
	}

	// Detect current color scheme by comparing with color_* columns
	let currentScheme = "category";
	for (const scheme of availableSchemes) {
		const colorColumn = `color_${scheme}`;
		if (data[colorColumn] && data.color && data[colorColumn][0] === data.color[0]) {
			currentScheme = scheme;
			break;
		}
	}
	selector.value = currentScheme;

	// Add event listener
	selector.addEventListener("change", (e) => {
		switchColorScheme(e.target.value);
	});

	// Mark as initialized and enable
	selector.dataset.initialized = "true";
	selector.disabled = false;
	selector.title = "";
}

function switchColorScheme(scheme) {
	if (!globalDatasource) {
		return;
	}

	const data = globalDatasource.data;
	const sourceColumn = `color_${scheme}`;

	if (!data[sourceColumn]) {
		console.error(`Color scheme '${scheme}' not available in datasource`);
		return;
	}

	// Update the color column
	data.color = [...data[sourceColumn]];

	// Trigger Bokeh to redraw
	globalDatasource.change.emit();

	console.log(`Switched to color scheme: ${scheme}`);
}

function toggleEmptyHosts(hideEmpty) {
	if (!globalDatasource) {
		return;
	}

	// Store original data on first call
	if (!originalDatasourceData) {
		originalDatasourceData = {};
		for (const key in globalDatasource.data) {
			originalDatasourceData[key] = [...globalDatasource.data[key]];
		}
	}

	const data = globalDatasource.data;

	if (hideEmpty) {
		// Filter out rows where fingerprint is null/NaN/undefined
		const indices = [];
		for (let i = 0; i < originalDatasourceData.fingerprint.length; i++) {
			const fp = originalDatasourceData.fingerprint[i];
			// Keep if fingerprint is not null, undefined, or NaN
			if (fp !== null && fp !== undefined && !(typeof fp === 'number' && isNaN(fp))) {
				indices.push(i);
			}
		}

		// Update all data columns with filtered values
		for (const key in data) {
			data[key] = indices.map(i => originalDatasourceData[key][i]);
		}
	} else {
		// Restore original data
		for (const key in data) {
			data[key] = [...originalDatasourceData[key]];
		}
	}

	// Trigger Bokeh to redraw
	globalDatasource.change.emit();
}

function initHideEmptyHostsCheckbox() {
	const checkbox = document.getElementById("hide-empty-hosts");
	if (!checkbox) {
		return;
	}

	checkbox.addEventListener("change", (e) => {
		toggleEmptyHosts(e.target.checked);
	});
}
