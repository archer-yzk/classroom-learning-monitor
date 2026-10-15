let statisticsSessionId = null;
let statisticsTimer = null;
let scoreBarChart = null;
let scoreTrendChart = null;
let statisticsRequestInFlight = false;

const SCORE_COLORS = {
    6: "#079455",
    5: "#47cd89",
    4: "#2e90fa",
    3: "#fdb022",
    2: "#f79009",
    1: "#d92d20",
};

const statisticsPanel = document.querySelector("[data-statistics-panel]");
const statisticsMessage = document.querySelector("[data-statistics-message]");
const distributionElement = document.querySelector("[data-score-distribution]");

function initializeCharts() {
    if (typeof echarts === "undefined") {
        statisticsMessage.textContent = "ECharts 图表库加载失败";
        statisticsMessage.classList.add("error");
        return false;
    }

    if (scoreBarChart === null) {
        scoreBarChart = echarts.init(document.querySelector("#score-bar-chart"));
    }
    if (scoreTrendChart === null) {
        scoreTrendChart = echarts.init(document.querySelector("#score-trend-chart"));
    }
    return true;
}

function updateCharts(statistics) {
    if (!initializeCharts()) {
        return;
    }

    const labels = statistics.score_counts.map(
        (item) => `${item.emoji} ${item.score}分`
    );
    const barData = statistics.score_counts.map((item) => ({
        value: item.count,
        itemStyle: {color: SCORE_COLORS[item.score]},
    }));
    const trendLabels = statistics.recent_periods.map((item) =>
        window.ClassInsightTime.formatUtcDateTime(item.period_end).slice(5)
    );
    const trendData = statistics.recent_periods.map((item) => item.average_score);

    scoreBarChart.setOption({
        animationDuration: 400,
        aria: {enabled: true},
        tooltip: {trigger: "axis", axisPointer: {type: "shadow"}},
        grid: {left: 48, right: 20, top: 28, bottom: 48},
        xAxis: {
            type: "category",
            data: labels,
            axisLabel: {interval: 0},
        },
        yAxis: {
            type: "value",
            minInterval: 1,
            name: "人数",
        },
        series: [
            {
                name: "学生人数",
                type: "bar",
                data: barData,
                barMaxWidth: 46,
                label: {show: true, position: "top"},
            },
        ],
    });

    scoreTrendChart.setOption({
        animationDuration: 400,
        aria: {enabled: true},
        title: {
            text: trendData.length === 0 ? "完整周期结束后显示趋势" : "",
            left: "center",
            top: "middle",
            textStyle: {color: "#98a2b3", fontSize: 15},
        },
        tooltip: {trigger: "axis"},
        grid: {left: 48, right: 24, top: 34, bottom: 48},
        xAxis: {
            type: "category",
            boundaryGap: false,
            data: trendLabels,
            axisLabel: {color: "#667085"},
        },
        yAxis: {
            type: "value",
            min: 0,
            max: 6,
            interval: 1,
            name: "平均分",
        },
        series: [
            {
                name: "平均理解度",
                type: "line",
                smooth: true,
                symbolSize: 8,
                data: trendData,
                lineStyle: {width: 3, color: "#0f8f83"},
                itemStyle: {color: "#0f8f83"},
                areaStyle: {color: "rgba(20, 184, 166, 0.12)"},
            },
        ],
    });
}

function describeVariance(value, totalStudents) {
    if (!totalStudents) return "暂无数据";
    if (value < 0.8) return "较低，理解状态较集中";
    if (value < 2) return "适中，存在一定差异";
    return "较高，建议关注两端学生";
}

function renderScoreDistribution(scoreCounts) {
    distributionElement.replaceChildren();
    const total = scoreCounts.reduce((sum, item) => sum + item.count, 0);

    scoreCounts.forEach((item) => {
        const rowElement = document.createElement("div");
        rowElement.className = "score-row";
        rowElement.dataset.score = String(item.score);

        const emojiElement = document.createElement("span");
        emojiElement.className = "score-emoji";
        emojiElement.textContent = item.emoji;

        const labelElement = document.createElement("span");
        labelElement.className = "score-label";
        labelElement.textContent = `${item.score} 分 · ${item.label}`;

        const countElement = document.createElement("strong");
        countElement.textContent = `${item.count} 人`;

        const shareElement = document.createElement("small");
        const share = total ? Math.round((item.count / total) * 100) : 0;
        shareElement.textContent = `${share}%`;

        const meterElement = document.createElement("span");
        meterElement.className = "score-meter";
        const meterFill = document.createElement("i");
        meterFill.style.width = `${share}%`;
        meterElement.appendChild(meterFill);

        const valueElement = document.createElement("span");
        valueElement.className = "score-value";
        valueElement.append(countElement, shareElement);

        rowElement.append(emojiElement, labelElement, valueElement, meterElement);
        distributionElement.append(rowElement);
    });
}

async function loadCurrentStatistics() {
    if (
        statisticsSessionId === null
        || document.hidden
        || statisticsPanel.classList.contains("workspace-panel-inactive")
        || statisticsRequestInFlight
    ) {
        return;
    }

    statisticsRequestInFlight = true;
    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            `/api/statistics/current/${statisticsSessionId}`,
            {},
            {fallbackMessage: "统计数据读取失败"},
        );

        document.querySelector("[data-total-students]").textContent =
            result.total_students;
        document.querySelector("[data-eligible-students]").textContent =
            ` / ${result.eligible_students} 人`;
        const submissionRate = result.eligible_students
            ? Math.round((result.total_students / result.eligible_students) * 100)
            : 0;
        document.querySelector("[data-submission-meta]").textContent =
            `提交率 ${submissionRate}%`;
        const currentAverage = Number(result.average_score);
        document.querySelector("[data-average-score]").textContent =
            currentAverage.toFixed(2);
        const latestPeriod = result.recent_periods.at(-1);
        const previousAverage = latestPeriod ? Number(latestPeriod.average_score) : null;
        const averageDelta = previousAverage === null ? null : currentAverage - previousAverage;
        document.querySelector("[data-average-meta]").textContent = averageDelta === null
            ? "完整周期后生成趋势"
            : Math.abs(averageDelta) < 0.005
                ? "与上一周期持平"
                : `较上一周期 ${averageDelta > 0 ? "+" : ""}${averageDelta.toFixed(2)}`;
        document.querySelector("[data-pending-kpi]").textContent =
            result.pending_alerts;
        document.querySelector("[data-variance]").textContent =
            Number(result.variance).toFixed(2);
        document.querySelector("[data-variance-insight]").firstChild.textContent =
            `班级分歧程度：${describeVariance(Number(result.variance), result.total_students)}（方差 `;
        const refreshTime = new Date().toLocaleTimeString("zh-CN", {hour12: false});
        document.querySelector("[data-refresh-time]").textContent = refreshTime;
        document.querySelector("[data-topbar-refresh]").textContent = `最近更新 ${refreshTime}`;

        renderScoreDistribution(result.score_counts);
        updateCharts(result);
        const accessibleSummary = result.score_counts
            .map((item) => `${item.score} 分 ${item.count} 人`)
            .join("，");
        document.querySelector("#score-bar-chart").setAttribute(
            "aria-label",
            `六级理解程度人数柱状图：${accessibleSummary}`,
        );
        const trendSummary = result.recent_periods.length
            ? result.recent_periods.map((item) =>
                `${window.ClassInsightTime.formatUtcDateTime(item.period_end)} 平均 ${Number(item.average_score).toFixed(2)} 分`
            ).join("，")
            : "暂无已完成统计周期";
        document.querySelector("#score-trend-chart").setAttribute(
            "aria-label",
            `最近五个统计周期平均理解度趋势图：${trendSummary}`,
        );
        statisticsMessage.textContent = "统计数据已更新";
        statisticsMessage.classList.remove("error");
    } catch (error) {
        if (!error.isUnauthorized) {
            statisticsMessage.textContent = error.message;
            statisticsMessage.classList.add("error");
        }
    } finally {
        statisticsRequestInFlight = false;
    }
}

document.addEventListener("classroom:loaded", async (event) => {
    statisticsSessionId = event.detail.session_id;
    statisticsPanel.hidden = false;
    await loadCurrentStatistics();

    if (statisticsTimer !== null) {
        window.clearInterval(statisticsTimer);
    }
    statisticsTimer = window.setInterval(loadCurrentStatistics, 5000);
});

window.addEventListener("resize", () => {
    scoreBarChart?.resize();
    scoreTrendChart?.resize();
});

document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
        loadCurrentStatistics();
    }
});

document.addEventListener("workspace:changed", (event) => {
    if (event.detail.tab === "overview") {
        scoreBarChart?.resize();
        scoreTrendChart?.resize();
        loadCurrentStatistics();
    }
});

window.addEventListener("beforeunload", () => {
    if (statisticsTimer !== null) {
        window.clearInterval(statisticsTimer);
    }
    scoreBarChart?.dispose();
    scoreTrendChart?.dispose();
});
