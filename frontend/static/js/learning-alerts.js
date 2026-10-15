const learningAlertStatus = document.querySelector("[data-learning-alert-status]");
const learningAlertRows = document.querySelector("[data-learning-alert-rows]");
const learningAlertTableWrap = document.querySelector("[data-learning-alert-table-wrap]");
const learningAlertEmpty = document.querySelector("[data-learning-alert-empty]");
const learningAlertMessage = document.querySelector("[data-learning-alert-message]");
const pendingAlertCount = document.querySelector("[data-pending-alert-count]");
const alertDrawer = document.querySelector("[data-alert-drawer]");
const alertDrawerBackdrop = document.querySelector("[data-alert-drawer-backdrop]");
const alertDrawerTitle = document.querySelector("[data-alert-drawer-title]");
const alertDrawerDetails = document.querySelector("[data-alert-drawer-details]");
const alertDrawerNote = document.querySelector("[data-alert-drawer-note]");
const alertDrawerForm = document.querySelector("[data-alert-drawer-form]");
const alertDrawerTextarea = alertDrawerForm.querySelector("textarea");
const alertDrawerValidation = document.querySelector("[data-alert-drawer-validation]");
let selectedLearningAlert = null;
let drawerReturnFocus = null;

function formatLearningAlertTime(value, options = {}) {
    return window.ClassInsightTime.formatUtcDateTime(value, options);
}

function appendLearningAlertCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    row.appendChild(cell);
    return cell;
}

function closeLearningAlertDrawer() {
    alertDrawer.classList.remove("open");
    alertDrawerBackdrop.classList.remove("open");
    window.setTimeout(() => {
        alertDrawer.hidden = true;
        alertDrawerBackdrop.hidden = true;
    }, 180);
    document.body.classList.remove("drawer-open");
    alertDrawerValidation.textContent = "";
    drawerReturnFocus?.focus();
}

function getDrawerFocusableElements() {
    return Array.from(
        alertDrawer.querySelectorAll(
            "button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), a[href]",
        ),
    ).filter((element) => element.offsetParent !== null);
}

function trapDrawerFocus(event) {
    if (event.key !== "Tab" || alertDrawer.hidden) return;
    const focusableElements = getDrawerFocusableElements();
    if (!focusableElements.length) return;
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
    }
}

function appendDrawerDetail(label, value) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value ?? "—";
    item.append(term, detail);
    alertDrawerDetails.appendChild(item);
}

function openLearningAlertDrawer(alert, trigger) {
    selectedLearningAlert = alert;
    drawerReturnFocus = trigger;
    alertDrawerTitle.textContent = `${alert.student_name} · 学情预警`;
    alertDrawerDetails.replaceChildren();
    appendDrawerDetail("学号", alert.student_no);
    appendDrawerDetail("班级", alert.class_name);
    appendDrawerDetail("课程与课堂", `${alert.course_name} · ${alert.topic}`);
    appendDrawerDetail("最新反馈", `${alert.latest_score} 分`);
    appendDrawerDetail("更新时间", formatLearningAlertTime(alert.updated_at));
    appendDrawerDetail("处理状态", alert.status === "pending" ? "待处理" : "已处理");

    alertDrawerNote.replaceChildren();
    alertDrawerForm.hidden = alert.status === "resolved";
    if (alert.status === "resolved") {
        const label = document.createElement("strong");
        const content = document.createElement("p");
        label.textContent = `教师意见${alert.handler_name ? ` · ${alert.handler_name}` : ""}`;
        content.textContent = alert.teacher_note || "—";
        alertDrawerNote.append(label, content);
    } else {
        alertDrawerTextarea.value = "";
    }
    alertDrawerValidation.textContent = "";

    alertDrawer.hidden = false;
    alertDrawerBackdrop.hidden = false;
    document.body.classList.add("drawer-open");
    window.requestAnimationFrame(() => {
        alertDrawer.classList.add("open");
        alertDrawerBackdrop.classList.add("open");
        document.querySelector("[data-alert-drawer-close]").focus();
    });
}

async function resolveLearningAlert(alertId, teacherNote, submitButton) {
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在保存……");
    learningAlertMessage.textContent = "正在保存教师处理意见……";
    learningAlertMessage.classList.remove("error");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            `/api/teacher/learning-alerts/${alertId}`,
            {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({teacher_note: teacherNote}),
            },
            {fallbackMessage: "预警处理失败"},
        );
        closeLearningAlertDrawer();
        await loadTeacherLearningAlerts();
        learningAlertMessage.textContent = `${result.message}，处理人：${result.handler_name}`;
        window.ClassInsightApi.showToast("学情预警已完成跟进");
    } catch (error) {
        if (!error.isUnauthorized) {
            learningAlertMessage.textContent = error.message;
            learningAlertMessage.classList.add("error");
        }
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

function renderLearningAlerts(alerts) {
    learningAlertRows.replaceChildren();
    learningAlertTableWrap.hidden = alerts.length === 0;
    learningAlertEmpty.hidden = alerts.length !== 0;
    for (const alert of alerts) {
        const row = document.createElement("tr");
        const studentCell = appendLearningAlertCell(row, "");
        const studentName = document.createElement("strong");
        const studentNo = document.createElement("small");
        studentName.textContent = alert.student_name;
        studentNo.textContent = alert.student_no;
        studentCell.className = "alert-student-cell";
        studentCell.append(studentName, studentNo);
        appendLearningAlertCell(row, alert.class_name);
        appendLearningAlertCell(row, alert.course_name);

        const scoreCell = appendLearningAlertCell(row, `${alert.latest_score} 分`);
        scoreCell.classList.add("learning-alert-score", `score-${alert.latest_score}`);
        const statusCell = appendLearningAlertCell(row, "");
        const statusBadge = document.createElement("span");
        statusBadge.classList.add("table-badge", "learning-alert-status", alert.status);
        statusBadge.textContent = alert.status === "pending" ? "待处理" : "已处理";
        statusCell.appendChild(statusBadge);
        appendLearningAlertCell(
            row,
            formatLearningAlertTime(alert.updated_at, {withYear: false, withSeconds: false}),
        );

        const actionCell = document.createElement("td");
        const detailButton = document.createElement("button");
        detailButton.type = "button";
        detailButton.className = "table-detail-button";
        detailButton.textContent = alert.status === "pending" ? "查看并跟进" : "查看详情";
        detailButton.addEventListener("click", () => openLearningAlertDrawer(alert, detailButton));
        actionCell.appendChild(detailButton);
        row.appendChild(actionCell);
        learningAlertRows.appendChild(row);
    }
}

async function loadTeacherLearningAlerts() {
    learningAlertMessage.textContent = "正在读取学情预警……";
    learningAlertMessage.classList.remove("error");
    try {
        const query = learningAlertStatus.value
            ? `?status=${encodeURIComponent(learningAlertStatus.value)}`
            : "";
        const {data: result} = await window.ClassInsightApi.requestJson(
            `/api/teacher/learning-alerts${query}`,
            {},
            {fallbackMessage: "预警读取失败"},
        );
        pendingAlertCount.textContent = String(result.pending_count);
        document.querySelector("[data-pending-kpi]").textContent = String(result.pending_count);
        renderLearningAlerts(result.alerts);
        learningAlertMessage.textContent = result.total
            ? `查询完成，共显示 ${result.total} 条预警。`
            : "查询完成，当前没有符合条件的预警。";
    } catch (error) {
        if (!error.isUnauthorized) {
            learningAlertMessage.textContent = error.message;
            learningAlertMessage.classList.add("error");
        }
    }
}

alertDrawerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const teacherNote = alertDrawerTextarea.value.trim();
    if (!selectedLearningAlert || !teacherNote) {
        alertDrawerValidation.textContent = "请填写教师跟进意见后再提交。";
        alertDrawerTextarea.focus();
        return;
    }
    await resolveLearningAlert(
        selectedLearningAlert.id,
        teacherNote,
        alertDrawerForm.querySelector("button[type='submit']"),
    );
});
alertDrawerTextarea.addEventListener("invalid", (event) => {
    event.preventDefault();
    alertDrawerValidation.textContent = "请填写教师跟进意见后再提交。";
    alertDrawerTextarea.focus();
});
alertDrawerTextarea.addEventListener("input", () => {
    if (alertDrawerTextarea.value.trim()) alertDrawerValidation.textContent = "";
});
document.querySelector("[data-alert-drawer-close]").addEventListener("click", closeLearningAlertDrawer);
alertDrawerBackdrop.addEventListener("click", closeLearningAlertDrawer);
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !alertDrawer.hidden) {
        closeLearningAlertDrawer();
        return;
    }
    trapDrawerFocus(event);
});
learningAlertStatus.addEventListener("change", loadTeacherLearningAlerts);
document.querySelector("[data-refresh-learning-alerts]").addEventListener("click", loadTeacherLearningAlerts);
loadTeacherLearningAlerts();
