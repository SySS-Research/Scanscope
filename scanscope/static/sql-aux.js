const scanscope_cache = {};

async function initDb() {
    if (scanscope_cache.db) { return scanscope_cache.db }
    const initSqlJs = window.initSqlJs;
    const sqlPromise = initSqlJs({
        locateFile: file => (wasm_base + "/" + file)
    });
    console.log("initDb", wasm_base);

    const dataPromise = fetch("data.sqlite").then(res => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise])
    const db = new SQL.Database(new Uint8Array(buf));
    scanscope_cache.db = db;
    return db;
}

async function getHosts() {
    const db = await initDb();
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
    const result = db.exec(sql);
    return result[0];
}

async function getServices() {
    const db = await initDb();
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
    const result = db.exec(sql);
    return result[0];
}

async function getHostsByIndices(indices) {
    const db = await initDb();
    const result = db.exec("SELECT * FROM hosts WHERE id IN (" + indices.join() + ")");
    return result[0];
}

async function getHostGroupsByFingerprints(fingerprints) {
    const db = await initDb();
    const sql = `
SELECT
    h.fingerprint,
    GROUP_CONCAT(DISTINCT h.ip_address ORDER BY h.ip_address_int) AS ip_addresses,
    COALESCE(GROUP_CONCAT(h.hostname ORDER BY h.ip_address_int), '') AS hostnames,
    (
        SELECT GROUP_CONCAT(p.port_number)
        FROM ports p
        WHERE p.host_id IN (
            SELECT h2.id
            FROM hosts h2
            WHERE h2.fingerprint = h.fingerprint
        )
        GROUP BY p.host_id
        ORDER BY p.port_number ASC
    ) AS port_numbers
FROM
    hosts h
INNER JOIN
    ports p ON h.id = p.host_id
GROUP BY
    h.fingerprint
HAVING
    COUNT(DISTINCT p.port_number) = (
        SELECT COUNT(*)
        FROM ports p2
        WHERE p2.host_id = h.id
    )
AND h.fingerprint IN ("${fingerprints.join('","')}")
    `;
    const result = db.exec(sql);
    return result[0];
}
