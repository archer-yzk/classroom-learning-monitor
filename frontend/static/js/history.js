const historyForm = document.querySelector("#history-filter-form");
const historyMessage = document.querySelector("[data-history-message]");
const historyTotal = document.querySelector("[data-history-total]");
const historyRows = document.querySelector("[data-history-rows]");
const historyTableWrap = document.querySelector("[data-history-table-wrap]");
const historyEmpty = document.querySelector("[data-history-empty]");
const resetFilterButton = document.querySelector("[data-reset-filter]");
const exportHistoryButton = document.querySelector("[data-export-history]");

let lastSuccessfulQueryString = "";
let currentResultCount = 0;

function formatDateTime(value) {
    return window.ClassInsightTime.formatUtcDateTime(value);
}

function appendTextCell(row, text) {
    const cell = document.createElement("td");
    cell.textContent = text;
    row.appendChild(cell);
}

function appendDistributionCell(row, scoreCounts) {
    const cell = document.createElement("td");
    const distribution = document.createElement("div");
    distribution.className = "history-distribution";
    distribution.setAttribute(
        "aria-label",
        scoreCounts.map((item) => `${item.score} 分 ${item.count} 人`).join("，"),
    );
    for (const item of scoreCounts) {
        const chip = document.createElement("span");
        chip.dataset.score = String(item.score);
        chip.title = `${item.score} 分 · ${item.label}：${item.count} 人`;
        chip.innerHTML = `<i aria-hidden="true"></i><strong>${item.score}</strong><small>${item.count}</small>`;
        distribution.appendChild(chip);
    }
    cell.appendChild(distribution);
    row.appendChild(cell);
}

function renderHistory(records) {
    historyRows.replaceChildren();
    historyTotal.textContent = String(records.length);
    historyTableWrap.hidden = records.length === 0;
    historyEmpty.hidden = records.length !== 0;
    currentResultCount = records.length;
    exportHistoryButton.disabled = records.length === 0;

    for (const record of records) {
        const row = document.createElement("tr");
        appendTextCell(
            row,
            `${record.course_name} / ${record.class_name}\n${record.topic}`,
        );
        appendTextCell(row, formatDateTime(record.class_start_time));
        appendTextCell(
            row,
            `${formatDateTime(record.period_start)}\n至 ${formatDateTime(record.period_end)}`,
        );
        appendTextCell(row, `${record.total_students} 人`);
        appendTextCell(row, Number(record.average_score).toFixed(2));
        appendTextCell(row, Number(record.variance).toFixed(2));

        appendDistributionCell(row, record.score_counts);
        historyRows.appendChild(row);
    }
}

function buildQueryString() {
    const formData = new FormData(historyForm);
    const query = new URLSearchParams();

    for (const [name, value] of formData.entries()) {
        let cleanedValue = value.trim();
        if (name === "start_time" || name === "end_time") {
            cleanedValue = window.ClassInsightTime.localInputToUtc(cleanedValue);
        }
        if (cleanedValue) {
            query.set(name, cleanedValue);
        }
    }

    return query.toString();
}

async function loadHistory() {
    historyMessage.textContent = "正在查询……";
    historyMessage.classList.remove("error");

    try {
        const queryString = buildQueryString();
        const url = queryString
            ? `/api/statistics/history?${queryString}`
            : "/api/statistics/history";
        const response = await fetch(url, {credentials: "same-origin"});

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        const result = await response.json();
        if (!response.ok) {
            historyMessage.textContent = result.detail || "查询失败，请稍后重试";
            historyMessage.classList.add("error");
            return;
        }

        renderHistory(result.records);
        lastSuccessfulQueryString = queryString;
        historyMessage.textContent = result.total
            ? `查询完成，共找到 ${result.total} 条记录。`
            : "查询完成，没有符合条件的记录。";
    } catch (_error) {
        historyMessage.textContent = "无法连接服务器，请确认项目已经启动";
        historyMessage.classList.add("error");
    }
}

function getDownloadFilename(contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) {
        return decodeURIComponent(utf8Match[1]);
    }
    return "学情历史.xlsx";
}

async function exportHistory() {
    if (currentResultCount === 0) {
        return;
    }

    exportHistoryButton.disabled = true;
    historyMessage.textContent = "正在生成 Excel 文件……";
    historyMessage.classList.remove("error");

    try {
        const url = lastSuccessfulQueryString
            ? `/api/statistics/history/export?${lastSuccessfulQueryString}`
            : "/api/statistics/history/export";
        const response = await fetch(url, {credentials: "same-origin"});

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (!response.ok) {
            const result = await response.json();
            historyMessage.textContent = result.detail || "导出失败，请稍后重试";
            historyMessage.classList.add("error");
            return;
        }

        const fileBlob = await response.blob();
        const downloadUrl = URL.createObjectURL(fileBlob);
        const downloadLink = document.createElement("a");
        downloadLink.href = downloadUrl;
        downloadLink.download = getDownloadFilename(
            response.headers.get("Content-Disposition") || "",
        );
        document.body.appendChild(downloadLink);
        downloadLink.click();
        downloadLink.remove();
        URL.revokeObjectURL(downloadUrl);
        historyMessage.textContent = `已导出当前 ${currentResultCount} 条查询结果。`;
    } catch (_error) {
        historyMessage.textContent = "无法连接服务器，请确认项目已经启动";
        historyMessage.classList.add("error");
    } finally {
        exportHistoryButton.disabled = currentResultCount === 0;
    }
}

historyForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadHistory();
});

resetFilterButton.addEventListener("click", () => {
    historyForm.reset();
    loadHistory();
});

exportHistoryButton.addEventListener("click", exportHistory);

loadHistory();
