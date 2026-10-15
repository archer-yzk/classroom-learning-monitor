const studentAlertList = document.querySelector("[data-student-alert-list]");
const studentAlertEmpty = document.querySelector("[data-student-alert-empty]");
const studentAlertMessage = document.querySelector("[data-student-alert-message]");
const studentPendingAlertCount = document.querySelector(
    "[data-student-pending-alert-count]",
);

function formatStudentAlertTime(value) {
    return window.ClassInsightTime.formatUtcDateTime(value, {
        withYear: false,
        withSeconds: false,
    });
}

function appendAlertDetail(list, label, value) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value ?? "—";
    row.append(term, description);
    list.appendChild(row);
}

function renderStudentAlerts(alerts) {
    studentAlertList.replaceChildren();
    studentAlertEmpty.hidden = alerts.length !== 0;

    for (const alert of alerts) {
        const card = document.createElement("article");
        card.className = `student-alert-card ${alert.status}`;

        const header = document.createElement("header");
        const title = document.createElement("strong");
        const statusBadge = document.createElement("span");
        title.textContent = `${alert.course_name} · ${alert.topic}`;
        statusBadge.className = `student-alert-status ${alert.status}`;
        statusBadge.textContent = alert.status === "pending" ? "待教师跟进" : "已处理";
        header.append(title, statusBadge);

        const details = document.createElement("dl");
        appendAlertDetail(details, "最新低分", `${alert.latest_score} 分`);
        appendAlertDetail(details, "预警时间", formatStudentAlertTime(alert.created_at));
        appendAlertDetail(
            details,
            "处理时间",
            formatStudentAlertTime(alert.resolved_at),
        );

        const note = document.createElement("div");
        note.className = "student-alert-note";
        const noteTitle = document.createElement("strong");
        const noteText = document.createElement("p");
        noteTitle.textContent = alert.handler_name
            ? `${alert.handler_name}的跟进意见`
            : "教师跟进意见";
        noteText.textContent = alert.teacher_note || "教师尚未填写处理意见，请耐心等待。";
        note.append(noteTitle, noteText);

        card.append(header, details, note);
        studentAlertList.appendChild(card);
    }
}

async function loadStudentLearningAlerts() {
    studentAlertMessage.textContent = "正在读取我的学情提醒……";
    studentAlertMessage.classList.remove("error");

    try {
        const response = await fetch("/api/student/learning-alerts", {
            credentials: "same-origin",
        });
        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        const result = await response.json();
        if (!response.ok) {
            studentAlertMessage.textContent = result.detail || "学情提醒读取失败";
            studentAlertMessage.classList.add("error");
            return;
        }

        studentPendingAlertCount.textContent = String(result.pending_count);
        renderStudentAlerts(result.alerts);
        studentAlertMessage.textContent = result.total
            ? `共找到 ${result.total} 条学情提醒。`
            : "当前没有学情提醒。";
    } catch (_error) {
        studentAlertMessage.textContent = "无法连接服务器，请确认项目已经启动";
        studentAlertMessage.classList.add("error");
    }
}

document.querySelector("[data-refresh-student-alerts]").addEventListener(
    "click",
    loadStudentLearningAlerts,
);
document.addEventListener("feedback:submitted", loadStudentLearningAlerts);

loadStudentLearningAlerts();
