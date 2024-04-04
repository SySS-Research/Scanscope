const scanscope_cache = {};

async function initDb() {
    if (scanscope_cache.db) { return scanscope_cache.db }
    const initSqlJs = window.initSqlJs;
    const sqlPromise = initSqlJs({
        locateFile: file => `${file}`
    });
    const dataPromise = fetch("data.sqlite").then(res => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise])
    const db = new SQL.Database(new Uint8Array(buf));
    scanscope_cache.db = db;
    return db;
}

async function getHosts() {
    const db = await initDb();
    const result = db.exec("SELECT * FROM hosts");
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
    GROUP_CONCAT(DISTINCT h.ip_address) AS ip_addresses,
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
