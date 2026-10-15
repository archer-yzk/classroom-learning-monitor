const adminUserFilterForm = document.querySelector("#admin-user-filter-form");
const adminUserRows = document.querySelector("[data-admin-user-rows]");
const adminUserTotal = document.querySelector("[data-admin-user-total]");
const adminUserTableWrap = document.querySelector("[data-admin-user-table-wrap]");
const adminUsersEmpty = document.querySelector("[data-admin-users-empty]");
const adminUsersMessage = document.querySelector("[data-admin-users-message]");
const resetAdminUserFilter = document.querySelector("[data-reset-admin-user-filter]");
const adminUserCreatePanel = document.querySelector("[data-admin-user-create-panel]");
const adminUserCreateForm = document.querySelector("#admin-user-create-form");
const adminUserCreateMessage = document.querySelector("[data-admin-user-create-message]");
const newUserRole = document.querySelector("#new-user-role");
const studentFields = document.querySelector("[data-student-fields]");
const userFormTitle = document.querySelector("[data-user-form-title]");
const userPasswordLabel = document.querySelector("[data-user-password-label]");
const userFormSubmit = document.querySelector("[data-user-form-submit]");
const newUserPassword = document.querySelector("#new-user-password");

let editingAdminUserId = null;

const ADMIN_ROLE_LABELS = {
    student: "学生",
    teacher: "教师",
    admin: "管理员",
};

function appendAdminUserCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    row.appendChild(cell);
    return cell;
}

function addCellBadge(cell, label, ...classNames) {
    cell.textContent = "";
    const badge = document.createElement("span");
    badge.classList.add("table-badge", ...classNames);
    badge.textContent = label;
    cell.appendChild(badge);
}

function renderAdminUsers(users) {
    adminUserRows.replaceChildren();
    adminUserTotal.textContent = String(users.length);
    adminUserTableWrap.hidden = users.length === 0;
    adminUsersEmpty.hidden = users.length !== 0;

    for (const user of users) {
        const row = document.createElement("tr");
        appendAdminUserCell(row, user.id);
        appendAdminUserCell(row, user.username);

        const roleCell = appendAdminUserCell(row, ADMIN_ROLE_LABELS[user.role]);
        addCellBadge(
            roleCell,
            ADMIN_ROLE_LABELS[user.role],
            "admin-user-role",
            user.role,
        );

        appendAdminUserCell(row, user.student_no);
        appendAdminUserCell(row, user.name);
        appendAdminUserCell(row, user.age);
        appendAdminUserCell(row, user.gender);
        appendAdminUserCell(row, user.grade);
        appendAdminUserCell(row, user.class_name);
        appendAdminUserCell(row, user.major);
        appendAdminUserCell(row, user.phone);

        const statusCell = appendAdminUserCell(
            row,
            user.status === "active" ? "启用" : "停用",
        );
        addCellBadge(
            statusCell,
            user.status === "active" ? "启用" : "停用",
            "admin-user-status",
            user.status,
        );

        const actionCell = document.createElement("td");
        actionCell.className = "admin-user-actions";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "table-action-button";
        editButton.textContent = "修改";
        editButton.addEventListener("click", () => showEditUserPanel(user));
        actionCell.appendChild(editButton);

        const moreMenu = document.createElement("details");
        moreMenu.className = "table-more-menu";
        const moreSummary = document.createElement("summary");
        moreSummary.className = "table-more-summary";
        moreSummary.textContent = "更多";
        moreSummary.setAttribute("aria-label", `更多操作：${user.name}`);
        const moreActions = document.createElement("div");
        moreActions.className = "table-more-actions";

        moreMenu.addEventListener("toggle", () => {
            if (!moreMenu.open) return;
            document.querySelectorAll(".table-more-menu[open]").forEach((menu) => {
                if (menu !== moreMenu) menu.open = false;
            });
            requestAnimationFrame(() => {
                const triggerRect = moreSummary.getBoundingClientRect();
                const menuWidth = moreActions.offsetWidth;
                const menuHeight = moreActions.offsetHeight;
                const left = Math.min(
                    window.innerWidth - menuWidth - 12,
                    Math.max(12, triggerRect.right - menuWidth),
                );
                const top = triggerRect.top > menuHeight + 18
                    ? triggerRect.top - menuHeight - 7
                    : triggerRect.bottom + 7;
                moreActions.style.left = `${left}px`;
                moreActions.style.top = `${top}px`;
            });
        });

        const statusButton = document.createElement("button");
        statusButton.type = "button";
        statusButton.className = "table-action-button secondary-button";
        statusButton.textContent = user.status === "active" ? "停用" : "启用";
        statusButton.setAttribute(
            "aria-label",
            `${statusButton.textContent}用户：${user.name}`,
        );
        statusButton.addEventListener("click", () => {
            moreMenu.open = false;
            changeAdminUserStatus(user);
        });
        moreActions.appendChild(statusButton);

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "table-action-button danger-button";
        deleteButton.textContent = "删除";
        deleteButton.setAttribute("aria-label", `删除用户：${user.name}`);
        deleteButton.addEventListener("click", () => {
            moreMenu.open = false;
            deleteAdminUser(user);
        });
        moreActions.appendChild(deleteButton);
        moreMenu.append(moreSummary, moreActions);
        actionCell.appendChild(moreMenu);

        row.appendChild(actionCell);
        adminUserRows.appendChild(row);
    }
}

async function sendAdminUserAction(url, options, waitingMessage) {
    adminUsersMessage.textContent = waitingMessage;
    adminUsersMessage.classList.remove("error");

    try {
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
            adminUsersMessage.textContent = result.detail || "操作失败";
            adminUsersMessage.classList.add("error");
            return null;
        }
        return result;
    } catch (_error) {
        adminUsersMessage.textContent = "无法连接服务器，请确认项目已经启动";
        adminUsersMessage.classList.add("error");
        return null;
    }
}

async function changeAdminUserStatus(user) {
    const nextStatus = user.status === "active" ? "disabled" : "active";
    const actionLabel = nextStatus === "disabled" ? "停用" : "启用";
    if (!window.confirm(`确定要${actionLabel}用户“${user.name}”吗？`)) {
        return;
    }

    const result = await sendAdminUserAction(
        `/api/admin/users/${user.id}/status`,
        {
            method: "PATCH",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({status: nextStatus}),
        },
        `正在${actionLabel}账号……`,
    );
    if (!result) {
        return;
    }

    await loadAdminUsers();
    document.dispatchEvent(new CustomEvent("admin-users:changed"));
    adminUsersMessage.textContent = `已${actionLabel}用户：${result.name}（${result.username}）`;
    window.ClassInsightApi.showToast(`已${actionLabel}用户：${result.name}`);
}

async function deleteAdminUser(user) {
    const confirmed = window.confirm(
        `确定永久删除用户“${user.name}（${user.username}）”吗？\n` +
        "删除后不能恢复；已有课堂或系统记录的用户会受到保护。",
    );
    if (!confirmed) {
        return;
    }

    const result = await sendAdminUserAction(
        `/api/admin/users/${user.id}`,
        {method: "DELETE"},
        "正在删除账号……",
    );
    if (!result) {
        return;
    }

    if (editingAdminUserId === user.id) {
        hideCreateUserPanel();
    }
    await loadAdminUsers();
    document.dispatchEvent(new CustomEvent("admin-users:changed"));
    adminUsersMessage.textContent = result.message;
    window.ClassInsightApi.showToast(result.message);
}

function buildAdminUserQuery() {
    const formData = new FormData(adminUserFilterForm);
    const query = new URLSearchParams();
    for (const [name, value] of formData.entries()) {
        const cleanedValue = value.trim();
        if (cleanedValue) {
            query.set(name, cleanedValue);
        }
    }
    return query.toString();
}

async function loadAdminUsers() {
    adminUsersMessage.textContent = "正在查询用户……";
    adminUsersMessage.classList.remove("error");

    try {
        const query = buildAdminUserQuery();
        const url = query ? `/api/admin/users?${query}` : "/api/admin/users";
        const response = await fetch(url, {credentials: "same-origin"});
        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        const result = await response.json();
        if (!response.ok) {
            adminUsersMessage.textContent = result.detail || "用户列表读取失败";
            adminUsersMessage.classList.add("error");
            return;
        }

        renderAdminUsers(result.users);
        adminUsersMessage.textContent = result.total
            ? `查询完成，共找到 ${result.total} 名用户。`
            : "查询完成，没有符合条件的用户。";
    } catch (_error) {
        adminUsersMessage.textContent = "无法连接服务器，请确认项目已经启动";
        adminUsersMessage.classList.add("error");
    }
}

function updateStudentFields() {
    const isStudent = newUserRole.value === "student";
    studentFields.hidden = !isStudent;
    for (const input of studentFields.querySelectorAll("input")) {
        input.required = isStudent;
        if (!isStudent) {
            input.value = "";
        }
    }
}

function showCreateUserPanel() {
    editingAdminUserId = null;
    adminUserCreateForm.reset();
    newUserRole.disabled = false;
    newUserPassword.required = true;
    userFormTitle.textContent = "添加用户账号";
    userPasswordLabel.textContent = "初始密码";
    userFormSubmit.textContent = "保存新用户";
    updateStudentFields();
    adminUserCreatePanel.hidden = false;
    document.querySelector("#new-user-username").focus();
}

function showEditUserPanel(user) {
    editingAdminUserId = user.id;
    adminUserCreateForm.reset();
    newUserRole.value = user.role;
    newUserRole.disabled = true;
    newUserPassword.required = false;
    userFormTitle.textContent = `修改用户：${user.name}`;
    userPasswordLabel.textContent = "新密码（留空表示不修改）";
    userFormSubmit.textContent = "保存修改";
    updateStudentFields();

    const values = {
        username: user.username,
        name: user.name,
        age: user.age,
        gender: user.gender,
        phone: user.phone,
        student_no: user.student_no,
        grade: user.grade,
        class_name: user.class_name,
        major: user.major,
    };
    for (const [name, value] of Object.entries(values)) {
        const field = adminUserCreateForm.elements.namedItem(name);
        if (field) {
            field.value = value ?? "";
        }
    }

    adminUserCreateMessage.textContent = "角色不能直接修改；新密码留空则保持原密码。";
    adminUserCreateMessage.classList.remove("error");
    adminUserCreatePanel.hidden = false;
    adminUserCreatePanel.scrollIntoView({behavior: "smooth", block: "start"});
}

function hideCreateUserPanel() {
    adminUserCreatePanel.hidden = true;
    editingAdminUserId = null;
    newUserRole.disabled = false;
    adminUserCreateMessage.textContent = "";
}

function buildCreateUserData() {
    const formData = new FormData(adminUserCreateForm);
    const data = {
        // 修改状态下角色下拉框被禁用，因此直接读取它的当前值。
        role: newUserRole.value,
        username: formData.get("username"),
        password: formData.get("password"),
        name: formData.get("name"),
        age: Number(formData.get("age")),
        gender: formData.get("gender"),
        phone: formData.get("phone"),
    };

    if (data.role === "student") {
        data.student_no = formData.get("student_no");
        data.grade = formData.get("grade");
        data.class_name = formData.get("class_name");
        data.major = formData.get("major");
    }
    return data;
}

function buildUpdateUserData() {
    const data = buildCreateUserData();
    delete data.role;
    if (!data.password) {
        delete data.password;
    }
    return data;
}

async function submitAdminUser(event) {
    event.preventDefault();
    const submitButton = adminUserCreateForm.querySelector("button[type='submit']");
    submitButton.disabled = true;
    adminUserCreateMessage.textContent = editingAdminUserId === null
        ? "正在创建账号……"
        : "正在保存修改……";
    adminUserCreateMessage.classList.remove("error");

    try {
        const isEditing = editingAdminUserId !== null;
        const url = isEditing
            ? `/api/admin/users/${editingAdminUserId}`
            : "/api/admin/users";
        const response = await fetch(url, {
            method: isEditing ? "PUT" : "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify(
                isEditing ? buildUpdateUserData() : buildCreateUserData(),
            ),
        });
        const result = await response.json();
        if (!response.ok) {
            adminUserCreateMessage.textContent = result.detail || "用户创建失败";
            adminUserCreateMessage.classList.add("error");
            return;
        }

        adminUserCreateMessage.textContent = isEditing
            ? `修改成功：${result.name}（${result.username}）`
            : `创建成功：${result.name}（${result.username}）`;
        adminUserCreateForm.reset();
        editingAdminUserId = null;
        newUserRole.disabled = false;
        newUserPassword.required = true;
        userFormTitle.textContent = "添加用户账号";
        userPasswordLabel.textContent = "初始密码";
        userFormSubmit.textContent = "保存新用户";
        updateStudentFields();
        adminUserFilterForm.reset();
        await loadAdminUsers();
        document.dispatchEvent(new CustomEvent("admin-users:changed"));
        window.ClassInsightApi.showToast(
            isEditing ? `用户 ${result.name} 已更新` : `用户 ${result.name} 已创建`,
        );
    } catch (_error) {
        adminUserCreateMessage.textContent = "无法连接服务器，请确认项目已经启动";
        adminUserCreateMessage.classList.add("error");
    } finally {
        submitButton.disabled = false;
    }
}

adminUserFilterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadAdminUsers();
});

resetAdminUserFilter.addEventListener("click", () => {
    adminUserFilterForm.reset();
    loadAdminUsers();
});

document.querySelector("[data-show-create-user]").addEventListener("click", showCreateUserPanel);
document.querySelector("[data-hide-create-user]").addEventListener("click", hideCreateUserPanel);
newUserRole.addEventListener("change", updateStudentFields);
adminUserCreateForm.addEventListener("submit", submitAdminUser);
document.addEventListener("click", (event) => {
    for (const menu of document.querySelectorAll(".table-more-menu[open]")) {
        if (!menu.contains(event.target)) menu.open = false;
    }
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        document.querySelectorAll(".table-more-menu[open]").forEach(
            (menu) => { menu.open = false; },
        );
    }
});
window.addEventListener("scroll", () => {
    document.querySelectorAll(".table-more-menu[open]").forEach(
        (menu) => { menu.open = false; },
    );
}, true);

updateStudentFields();
loadAdminUsers();
