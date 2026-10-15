const courseForm = document.querySelector("#admin-course-form");
const classroomForm = document.querySelector("#admin-classroom-form");
const courseTeacherSelect = document.querySelector("#course-teacher");
const classroomCourseSelect = document.querySelector("#classroom-course");
const classroomStartTime = document.querySelector("#classroom-start-time");
const courseRows = document.querySelector("[data-course-rows]");
const classroomRows = document.querySelector("[data-classroom-rows]");
const courseTotal = document.querySelector("[data-course-total]");
const classroomTotal = document.querySelector("[data-classroom-total]");
const courseManagementMessage = document.querySelector(
    "[data-course-management-message]",
);

const CLASSROOM_STATUS_LABELS = {
    scheduled: "待开始",
    active: "进行中",
    finished: "已结束",
};

let courseManagementLoading = false;

function showCourseManagementMessage(message, isError = false) {
    courseManagementMessage.textContent = message;
    courseManagementMessage.classList.toggle("error", isError);
}

async function fetchCourseManagementJson(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: "same-origin",
    });
    if (response.status === 401) {
        window.location.href = "/login";
        return null;
    }

    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.detail || "操作失败");
    }
    return result;
}

function appendCourseTableCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    row.appendChild(cell);
    return cell;
}

function addCourseTableBadge(cell, label, ...classNames) {
    cell.textContent = "";
    const badge = document.createElement("span");
    badge.classList.add("table-badge", ...classNames);
    badge.textContent = label;
    cell.appendChild(badge);
}

function fillSelect(selectElement, items, placeholder, buildLabel) {
    const previousValue = selectElement.value;
    selectElement.replaceChildren();

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    selectElement.appendChild(placeholderOption);

    for (const item of items) {
        const option = document.createElement("option");
        option.value = String(item.id);
        option.textContent = buildLabel(item);
        selectElement.appendChild(option);
    }
    if (items.some((item) => String(item.id) === previousValue)) {
        selectElement.value = previousValue;
    }
    selectElement.disabled = items.length === 0;
}

function renderCourses(result) {
    courseRows.replaceChildren();
    courseTotal.textContent = String(result.total);

    fillSelect(
        courseTeacherSelect,
        result.teachers,
        result.teachers.length ? "请选择授课教师" : "请先添加并启用教师账号",
        (teacher) => `${teacher.name}（${teacher.username}）`,
    );

    const availableCourses = result.courses.filter(
        (course) => course.status === "active" && course.teacher_status === "active",
    );
    fillSelect(
        classroomCourseSelect,
        availableCourses,
        availableCourses.length ? "请选择课程" : "请先新增可用课程",
        (course) => `${course.name} · ${course.teacher_name}`,
    );

    for (const course of result.courses) {
        const row = document.createElement("tr");
        appendCourseTableCell(row, course.name);
        const teacherText = course.teacher_status === "active"
            ? course.teacher_name
            : `${course.teacher_name}（账号已停用）`;
        appendCourseTableCell(row, teacherText);
        appendCourseTableCell(row, course.description);
        appendCourseTableCell(row, `${course.session_count} 节`);
        appendCourseTableCell(row, `${course.active_session_count} 节`);

        const statusCell = appendCourseTableCell(
            row,
            course.status === "active" ? "启用" : "停用",
        );
        addCourseTableBadge(
            statusCell,
            course.status === "active" ? "启用" : "停用",
            "course-status",
            course.status,
        );
        courseRows.appendChild(row);
    }

    if (!result.courses.length) {
        const row = document.createElement("tr");
        const cell = appendCourseTableCell(row, "还没有课程，请使用上方表单新增。 ");
        cell.colSpan = 6;
        cell.className = "course-management-empty";
        courseRows.appendChild(row);
    }
}

function createClassroomAction(classroom) {
    const cell = document.createElement("td");
    if (classroom.status === "finished") {
        cell.textContent = "—";
        return cell;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = classroom.status === "active"
        ? "table-action-button danger-button"
        : "table-action-button";
    button.textContent = classroom.status === "active" ? "结束课堂" : "开始上课";
    button.addEventListener("click", async () => {
        const nextStatus = classroom.status === "active" ? "finished" : "active";
        if (
            nextStatus === "finished"
            && !window.confirm(`确定结束“${classroom.course_name} · ${classroom.topic}”吗？`)
        ) {
            return;
        }

        window.ClassInsightApi.setButtonBusy(
            button,
            true,
            nextStatus === "active" ? "正在开始……" : "正在结束……",
        );
        showCourseManagementMessage(
            nextStatus === "active" ? "正在开始课堂……" : "正在结束课堂……",
        );
        try {
            const updated = await fetchCourseManagementJson(
                `/api/admin/classrooms/${classroom.id}/status`,
                {
                    method: "PATCH",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({status: nextStatus}),
                },
            );
            if (!updated) {
                return;
            }
            await loadCourseManagement();
            showCourseManagementMessage(
                nextStatus === "active"
                    ? `课堂已开始：${updated.course_name} · ${updated.class_name}`
                    : `课堂已结束：${updated.course_name} · ${updated.class_name}`,
            );
            window.ClassInsightApi.showToast(
                nextStatus === "active" ? "课堂已开始" : "课堂已结束",
            );
        } catch (error) {
            showCourseManagementMessage(error.message, true);
        } finally {
            window.ClassInsightApi.setButtonBusy(button, false);
        }
    });
    cell.appendChild(button);
    return cell;
}

function renderClassrooms(result) {
    classroomRows.replaceChildren();
    classroomTotal.textContent = String(result.total);

    for (const classroom of result.sessions) {
        const row = document.createElement("tr");
        appendCourseTableCell(row, classroom.course_name);
        appendCourseTableCell(row, classroom.teacher_name);
        appendCourseTableCell(row, classroom.class_name);
        appendCourseTableCell(row, classroom.topic);
        appendCourseTableCell(
            row,
            window.ClassInsightTime.formatUtcDateTime(classroom.start_time, {
                withSeconds: false,
            }),
        );
        const statusCell = appendCourseTableCell(
            row,
            CLASSROOM_STATUS_LABELS[classroom.status],
        );
        addCourseTableBadge(
            statusCell,
            CLASSROOM_STATUS_LABELS[classroom.status],
            "classroom-status",
            classroom.status,
        );
        row.appendChild(createClassroomAction(classroom));
        classroomRows.appendChild(row);
    }

    if (!result.sessions.length) {
        const row = document.createElement("tr");
        const cell = appendCourseTableCell(row, "还没有课堂场次。 ");
        cell.colSpan = 7;
        cell.className = "course-management-empty";
        classroomRows.appendChild(row);
    }
}

async function loadCourseManagement() {
    if (courseManagementLoading) {
        return;
    }
    courseManagementLoading = true;
    showCourseManagementMessage("正在读取课程与课堂……");
    try {
        const [courseResult, classroomResult] = await Promise.all([
            fetchCourseManagementJson("/api/admin/courses"),
            fetchCourseManagementJson("/api/admin/classrooms"),
        ]);
        if (!courseResult || !classroomResult) {
            return;
        }
        renderCourses(courseResult);
        renderClassrooms(classroomResult);
        showCourseManagementMessage(
            `已读取 ${courseResult.total} 门课程、${classroomResult.total} 节课堂。`,
        );
    } catch (error) {
        showCourseManagementMessage(error.message || "课程与课堂读取失败", true);
    } finally {
        courseManagementLoading = false;
    }
}

async function submitCourse(event) {
    event.preventDefault();
    const submitButton = courseForm.querySelector("button[type='submit']");
    const formData = new FormData(courseForm);
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在保存……");
    showCourseManagementMessage("正在保存课程……");
    try {
        const course = await fetchCourseManagementJson("/api/admin/courses", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                teacher_id: Number(formData.get("teacher_id")),
                name: formData.get("name"),
                description: formData.get("description") || null,
            }),
        });
        if (!course) {
            return;
        }
        courseForm.reset();
        await loadCourseManagement();
        classroomCourseSelect.value = String(course.id);
        showCourseManagementMessage(`课程已新增：${course.name}`);
        window.ClassInsightApi.showToast(`课程 ${course.name} 已创建`);
    } catch (error) {
        showCourseManagementMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

function setDefaultClassroomStartTime() {
    const currentTime = new Date();
    currentTime.setMinutes(currentTime.getMinutes() - currentTime.getTimezoneOffset());
    classroomStartTime.value = currentTime.toISOString().slice(0, 16);
}

async function submitClassroom(event) {
    event.preventDefault();
    const submitButton = classroomForm.querySelector("button[type='submit']");
    const formData = new FormData(classroomForm);
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在创建……");
    showCourseManagementMessage("正在创建课堂……");
    try {
        const classroom = await fetchCourseManagementJson("/api/admin/classrooms", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                course_id: Number(formData.get("course_id")),
                class_name: formData.get("class_name"),
                topic: formData.get("topic"),
                start_time: window.ClassInsightTime.localInputToUtc(
                    formData.get("start_time"),
                ),
                status: formData.get("status"),
            }),
        });
        if (!classroom) {
            return;
        }
        classroomForm.reset();
        setDefaultClassroomStartTime();
        await loadCourseManagement();
        showCourseManagementMessage(
            classroom.status === "active"
                ? `课堂已创建并开始：${classroom.course_name} · ${classroom.class_name}`
                : `课堂已创建，等待开始：${classroom.course_name} · ${classroom.class_name}`,
        );
        window.ClassInsightApi.showToast(
            classroom.status === "active" ? "课堂已创建并开始" : "课堂已创建",
        );
    } catch (error) {
        showCourseManagementMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

courseForm.addEventListener("submit", submitCourse);
classroomForm.addEventListener("submit", submitClassroom);
document.querySelector("[data-refresh-courses]").addEventListener(
    "click",
    loadCourseManagement,
);
document.addEventListener("admin-users:changed", loadCourseManagement);

setDefaultClassroomStartTime();
loadCourseManagement();
