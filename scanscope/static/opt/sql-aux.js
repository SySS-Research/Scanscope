const scanscope = {};

async function initDb() {
    if (scanscope.db) { return scanscope.db }
    const initSqlJs = window.initSqlJs;
    const sqlPromise = initSqlJs({
        locateFile: file => `${file}`
    });
    const dataPromise = fetch("data.sqlite").then(res => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise])
    const db = new SQL.Database(new Uint8Array(buf));
    scanscope.db = db;
    return db;
}

async function getHosts() {
    const db = await initDb();
    const result = db.exec("SELECT * FROM hosts");
    return result[0];
}
