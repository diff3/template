document.querySelectorAll("[data-lazy-table]").forEach((tableRoot) => {
    const search = tableRoot.querySelector("[data-lazy-search]");
    const factions = Array.from(tableRoot.querySelectorAll("[data-lazy-faction]"));
    const onlineOnly = tableRoot.querySelector("[data-lazy-online]");
    const count = tableRoot.querySelector("[data-lazy-count]");
    const rows = Array.from(tableRoot.querySelectorAll("tbody tr[data-search]"));

    if (!search || !count) {
        return;
    }

    function searchTokens(value) {
        return String(value || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
    }

    function filterRows() {
        const tokens = searchTokens(search.value);
        const selectedFaction = factions.find((item) => item.checked);
        const factionValue = selectedFaction ? selectedFaction.value : "";
        const onlineFilter = onlineOnly ? onlineOnly.checked : false;
        let visible = 0;

        for (const row of rows) {
            const haystack = String(row.dataset.search || "").toLowerCase();
            const textMatch = !tokens.length || tokens.every((token) => haystack.includes(token));
            const factionMatch = !factionValue || row.dataset.faction === factionValue;
            const onlineMatch = !onlineFilter || row.dataset.online === "1";
            const match = textMatch && factionMatch && onlineMatch;
            row.hidden = !match;
            if (match) {
                visible += 1;
            }
        }

        count.textContent = `${visible} shown / ${rows.length} total`;
    }

    search.addEventListener("input", filterRows);
    for (const faction of factions) {
        faction.addEventListener("change", filterRows);
    }
    if (onlineOnly) {
        onlineOnly.addEventListener("change", filterRows);
    }
});

document.querySelectorAll("tr[data-row-href]").forEach((row) => {
    row.addEventListener("click", (event) => {
        const interactive = event.target.closest("a, button, input, select, textarea, form");

        if (interactive) {
            return;
        }

        window.location.href = row.dataset.rowHref;
    });
});

function copyTextToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand("copy");
        return Promise.resolve();
    } catch (error) {
        return Promise.reject(error);
    } finally {
        document.body.removeChild(textarea);
    }
}

document.querySelectorAll("tr[data-copy-command]").forEach((row) => {
    row.addEventListener("click", (event) => {
        const interactive = event.target.closest("a, button, input, select, textarea, form");

        if (interactive) {
            return;
        }

        const command = row.dataset.copyCommand || "";
        const feedback = document.querySelector("[data-copy-feedback]");
        copyTextToClipboard(command).then(() => {
            row.classList.add("copied-row");
            if (feedback) {
                feedback.textContent = `Copied ${command}`;
            }
            window.setTimeout(() => row.classList.remove("copied-row"), 900);
        }).catch(() => {
            if (feedback) {
                feedback.textContent = `Copy failed: ${command}`;
            }
        });
    });
});
