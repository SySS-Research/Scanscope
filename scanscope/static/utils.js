// nmap top 14:
// 21-23,25,53,80,110,135,139,143,443,445,3306,3389
//
const portStylesTCP = {
    "21": { "color": "success", },
    "22": { "color": "danger", },
    "23": { "color": "info", },
    "25": { "color": "dark", },
    "53": { "color": "success", "dashed": true},
    "80": { "color": "primary", },
    "110": { "color": "info", "dashed": true},
    "135": { "color": "primary", "dashed": true},
    "139": { "color": "dark", "dashed": true},
    "143": { "color": "danger", "dashed": true},
    "443": { "color": "warning", },
    "445": { "color": "warning", "dashed": true},
    "3306": { "color": "light", "dashed": true},
    "3398": { "color": "light", },
};
// nmap top 7/udp:
// 123,137-138,161,445,631,1434
const portStylesUDP = {
    "123": "success",
    "137": "danger",
    "138": "info",
    "161": "dark",
    "445": "warning",
    "631": "light",
    "1434": "primary",
}

async function addPortHints() {
    const ports = document.querySelectorAll("span.scanscope-port");
    let proto = null;
    let portMap = null;

    ports.forEach(p => {
        var text = p.innerText;

        if (text[0] == '-') {
            text = text.slice(1, text.length-1);
            portMap = portMapUDP;
            proto = "udp";
        } else {
            portMap = portMapTCP;
            proto = "tcp";
        }

        p.setAttribute("title", `${text}/${proto}: ${portMap[text]}`);

        if (proto === "udp") {
            p.classList.remove("border");
            p.classList.add("badge-secondary");
        }

        if (portStylesTCP[text] && proto === "tcp") {
            p.classList.remove("border-secondary");
            p.classList.add("border-" + portStylesTCP[text].color);
            if (portStylesTCP[text].dashed) {
                p.setAttribute("style", "border-style: dashed !important;");
            }
            if (portStylesTCP[text].thick) {
                p.setAttribute("style", "border-width: 3px !important;");
            }
        } else if (portStylesUDP[text] && proto === "udp") {
            p.classList.remove("badge-secondary");
            p.classList.add("badge-" + portStylesUDP[text]);
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
