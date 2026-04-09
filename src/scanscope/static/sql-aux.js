function base64ToArrayBuffer(base64) {
	if (!base64) {
		return [];
	}
	const binary_string = window.atob(base64);
	const len = binary_string.length;
	const bytes = new Uint8Array(len);
	for (let i = 0; i < len; i++) {
		bytes[i] = binary_string.charCodeAt(i);
	}
	return bytes.buffer;
}

async function initDb() {
	const initSqlJs = window.initSqlJs;
	let sqlite_db_url = "";

	function _wasm_url(file) {
		let wasm_url = "";
		if (wasm_codearray) {
			wasm_url = URL.createObjectURL(
				new Blob([base64ToArrayBuffer(wasm_codearray)], {
					type: "application/wasm",
				}),
			);
		} else {
			wasm_url = `${wasm_base}/${file}`;
		}
		return wasm_url;
	}

	const sqlPromise = initSqlJs({
		locateFile: _wasm_url,
	});

	if (sqlite_db) {
		sqlite_db_url = URL.createObjectURL(
			new Blob([base64ToArrayBuffer(sqlite_db)], {
				type: "application/x-sqlite3",
			}),
		);
	} else {
		sqlite_db_url = "data.sqlite";
	}

	const dataPromise = fetch(sqlite_db_url).then((res) => res.arrayBuffer());

	const [SQL, buf] = await Promise.all([sqlPromise, dataPromise]);
	const db = new SQL.Database(new Uint8Array(buf));

	if (!document.scanscope) document.scanscope = {};
	document.scanscope.db = db;
}

async function getHosts() {
	const sql = `
SELECT
    h.ip_address,
    h.hostname,
    h.os,
    GROUP_CONCAT(p.port_number ORDER BY p.port_number ASC) AS port_numbers
FROM
    hosts h
LEFT JOIN
    ports p ON h.id = p.host_id
GROUP BY
    h.id
ORDER BY
    h.ip_address_int
;
    `;
	const result = document.scanscope.db.exec(sql);
	return result[0];
}

async function getServices() {
	const sql = `
SELECT
    p.port_number,
    COALESCE(GROUP_CONCAT(h.hostname ORDER BY h.ip_address_int), '') AS hostnames,
    GROUP_CONCAT(h.ip_address ORDER BY h.ip_address_int) AS ip_addresses
FROM
    ports p
JOIN
    hosts h ON p.host_id = h.id
GROUP BY
    p.port_number
ORDER BY
    p.port_number;
    `;
	const result = document.scanscope.db.exec(sql);
	return result[0];
}

async function getHostsByIndices(indices) {
	const result = document.scanscope.db.exec(
		`SELECT * FROM hosts WHERE id IN (${indices.join()})`,
	);
	return result[0];
}

async function getHostGroupsByFingerprints(fingerprints) {
	// Separate null/NaN and non-null fingerprints
	// NaN, null, and undefined all represent hosts with no fingerprint
	const hasNull = fingerprints.some(fp => fp === null || fp === undefined || (typeof fp === 'number' && isNaN(fp)));
	const nonNullFingerprints = fingerprints.filter(fp => fp !== null && fp !== undefined && !(typeof fp === 'number' && isNaN(fp)));

	// Build WHERE clause to handle both null and non-null fingerprints
	let whereClause = '';
	if (hasNull && nonNullFingerprints.length > 0) {
		whereClause = `(main_hosts.fingerprint IS NULL OR main_hosts.fingerprint IN ("${nonNullFingerprints.join('","')}"))`;
	} else if (hasNull) {
		whereClause = 'main_hosts.fingerprint IS NULL';
	} else {
		whereClause = `main_hosts.fingerprint IN ("${nonNullFingerprints.join('","')}")`;
	}

	const sql = `
SELECT
    main_hosts.fingerprint,
    GROUP_CONCAT(DISTINCT main_hosts.ip_address ORDER BY main_hosts.ip_address_int) AS ip_addresses,
    COALESCE(GROUP_CONCAT(DISTINCT main_hosts.hostname ORDER BY main_hosts.ip_address_int), '') AS hostnames,
    COALESCE((
        SELECT GROUP_CONCAT(DISTINCT p.port_number ORDER BY p.port_number ASC)
        FROM hosts h2
        LEFT JOIN ports p ON h2.id = p.host_id
        WHERE (main_hosts.fingerprint IS NOT NULL AND h2.fingerprint = main_hosts.fingerprint)
           OR (main_hosts.fingerprint IS NULL AND h2.fingerprint IS NULL)
    ), '') AS port_numbers
FROM
    hosts main_hosts
WHERE ${whereClause}
GROUP BY
    main_hosts.fingerprint
    `;
	const result = document.scanscope.db.exec(sql);
	return result[0];
}
