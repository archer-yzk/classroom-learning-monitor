const statisticsSettingForm = document.querySelector("#statistics-setting-form");
const intervalSelect = document.querySelector("#interval-minutes");
const settingsMessage = document.querySelector("[data-settings-message]");

function formatDatabaseTime(value) {
    return window.ClassInsightTime.formatUtcDateTime(value, {
        fallback: "尚未生成",
    });
}

function renderStatisticsSetting(setting) {
    intervalSelect.value = String(setting.interval_minutes);
    document.querySelector("[data-snapshot-count]").textContent =
        setting.snapshot_count;
    document.querySelector("[data-latest-snapshot]").textContent =
        formatDatabaseTime(setting.latest_snapshot_at);
    document.querySelector("[data-active-session-count]").textContent =
        setting.active_session_count;
    document.querySelector("[data-current-interval]").textContent =
        setting.interval_minutes;
    document.querySelector("[data-setting-updated-at]").textContent =
        formatDatabaseTime(setting.updated_at);
    document.querySelector("[data-setting-updated-by]").textContent =
        setting.updated_by_name || "系统初始化";

    const trend = setting.recent_daily_snapshots;
    const chart = document.querySelector("[data-snapshot-mini-chart]");
    const maximum = Math.max(1, ...trend.map((item) => item.count));
    chart.replaceChildren();
    chart.setAttribute(
        "aria-label",
        trend.map((item) => `${item.day}：${item.count} 个`).join("，"),
    );
    for (const item of trend) {
        const column = document.createElement("div");
        const value = document.createElement("strong");
        const bar = document.createElement("i");
        const label = document.createElement("small");
        value.textContent = String(item.count);
        bar.style.height = `${Math.max(5, Math.round((item.count / maximum) * 72))}px`;
        label.textContent = item.day.slice(5).replace("-", "/");
        column.append(value, bar, label);
        chart.appendChild(column);
    }
    document.querySelector("[data-recent-snapshot-total]").textContent =
        `${trend.reduce((sum, item) => sum + item.count, 0)} 个`;
}

async function loadStatisticsSetting() {
    const response = await fetch("/api/admin/statistics-settings", {
        credentials: "same-origin",
    });
    const result = await response.json();

    if (response.status === 401) {
        window.location.href = "/login";
        return;
    }
    if (!response.ok) {
        settingsMessage.textContent = result.detail || "统计配置读取失败";
        settingsMessage.classList.add("error");
        return;
    }

    renderStatisticsSetting(result);
    settingsMessage.textContent = "统计配置读取成功";
    settingsMessage.classList.remove("error");
}

async function saveStatisticsSetting(event) {
    event.preventDefault();
    const submitButton = statisticsSettingForm.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在保存……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            "/api/admin/statistics-settings",
            {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    interval_minutes: Number(intervalSelect.value),
                }),
            },
            {fallbackMessage: "统计周期保存失败"},
        );

        renderStatisticsSetting(result);
        settingsMessage.textContent = `保存成功，当前周期为 ${result.interval_minutes} 分钟`;
        settingsMessage.classList.remove("error");
        window.ClassInsightApi.showToast(`统计周期已设为 ${result.interval_minutes} 分钟`);
    } catch (error) {
        if (!error.isUnauthorized) {
            settingsMessage.textContent = error.message;
            settingsMessage.classList.add("error");
        }
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

statisticsSettingForm.addEventListener("submit", saveStatisticsSetting);
loadStatisticsSetting();
