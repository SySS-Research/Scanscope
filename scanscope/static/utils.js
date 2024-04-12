// nmap top TCP/UDP ports:
// https://raw.githubusercontent.com/nmap/nmap/master/nmap-services
// cat nmap-services|sort -k3 -r |grep -vE '^#'|cut -f2  | grep tcp | head -n 24
// Decision: Replace 111/tcp with 88/tcp (=kerberos; important in windows networks)

const topTCPPorts = [80, 23, 443, 21, 22, 25, 3389, 110, 445, 139, 143, 53, 135, 3306, 8080, 1723, 88, 995];
const topUDPPorts = [631, 161, 137, 123, 138, 1434, 445, 135, 67, 53, 139, 500];
const portColors = theme => ["success", "danger", "info", theme == "dark" ? "light" : "dark", "warning", "primary"];

function portStyles(theme, topPorts, styles) {
    const result = {};

    styles.forEach((style, j) => {
        portColors(theme).forEach((color, i) => {
            var item = {}
            item.color = color;
            item[style] = true;
            result[topPorts[portColors(theme).length*j + i]] = item;
        });
    });

    return result;
}

async function addPortHints() {
    const bootstrap_theme = document.getElementsByTagName('html')[0].dataset.bsTheme;
    const tcpStyles = portStyles(bootstrap_theme, topTCPPorts, [null, "dashed", "thick"]);
    const udpStyles = portStyles(bootstrap_theme, topUDPPorts, [null, "clipped"]);

    const ports = document.querySelectorAll("span.scanscope-port");
    let proto = null;
    let portMap = null;

    ports.forEach(p => {
        var text = p.innerText;

        if (text[0] == '-') {
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
            p.classList.add("border-" + tcpStyle.color);
            if (tcpStyle.dashed) {
                p.setAttribute("style", "border-style: dashed !important;");
            }
            if (tcpStyle.thick) {
                p.setAttribute("style", "border-width: 3px !important;");
            }
        } else if (udpStyle && proto === "udp") {
            p.classList.remove("badge-secondary");
            p.classList.add("bg-" + udpStyle.color);
            if (udpStyle.clipped) {
                p.setAttribute("style", "border-style: solid; !important;");
            }

            if (udpStyle.color == "light") {
                p.classList.add("text-dark");
            }
            if (udpStyle.color == "dark") {
                p.classList.add("text-white");
            }
        }
    });
}

async function addContextMenus() {
    const hostlists = document.querySelectorAll(".scanscope-host-list");
    const templateMenu = document.querySelector("#template-hosts-list-context-menu")
    hostlists.forEach(h => {
        const menu = templateMenu.content.cloneNode(true);
        menu.querySelector("a.copy-line").addEventListener("click", e => copyHosts(e, "\n"));
        menu.querySelector("a.copy-space").addEventListener("click", e => copyHosts(e, " "));
        menu.querySelector("a.copy-comma").addEventListener("click", e => copyHosts(e, ","));
        h.appendChild(menu);
    });
}

async function copyHosts(evnt, separator) {
    const list = evnt.target.closest(".scanscope-host-list");
    var result = []
    list.querySelectorAll(".scanscope-host-address").forEach(a => {
        result.push(a.innerText);
    });
    var text = result.join(separator);
    try {
        await navigator.clipboard.writeText(text);
        // TODO show indicator that text has been copied
    } catch (e) {
    }
}
