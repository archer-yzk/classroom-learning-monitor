const ROLE_PAGES = {
    student: "/student",
    teacher: "/teacher",
    admin: "/admin",
};

// 本地课程演示用授权码；真实项目中应由微信授权页面临时返回。
const WECHAT_DEMO_AUTHORIZATION_CODE = "wechat_demo_authorized";
const QQ_DEMO_AUTHORIZATION_CODE = "qq_demo_authorized";

function showFormMessage(message, isError = false) {
    const messageElement = document.querySelector("#form-message");
    if (!messageElement) {
        return;
    }

    messageElement.textContent = message;
    messageElement.classList.toggle("error", isError);
}

async function handleLogin(event) {
    event.preventDefault();
    showFormMessage("正在登录……");

    const form = event.currentTarget;
    const submitButton = form.querySelector("button[type='submit']");
    const loginData = {
        username: form.username.value.trim(),
        password: form.password.value,
    };

    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在登录……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/auth/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(loginData),
        }, {
            fallbackMessage: "登录失败，请检查账号和密码",
            redirectOnUnauthorized: false,
        });

        window.location.href = ROLE_PAGES[result.user.role] || "/login";
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

function switchLoginMethod(method) {
    for (const tab of document.querySelectorAll("[data-login-method]")) {
        const isActive = tab.dataset.loginMethod === method;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
    }
    for (const panel of document.querySelectorAll("[data-login-panel]")) {
        panel.hidden = panel.dataset.loginPanel !== method;
    }
    showFormMessage("");
}

async function sendSmsCode() {
    const smsForm = document.querySelector("#sms-login-form");
    const sendButton = document.querySelector("[data-send-sms-code]");
    const phone = smsForm.phone.value.trim();
    if (!phone) {
        showFormMessage("请先输入手机号", true);
        smsForm.phone.focus();
        return;
    }

    window.ClassInsightApi.setButtonBusy(sendButton, true, "正在获取……");
    showFormMessage("正在生成模拟短信验证码……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/auth/sms/send", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({phone}),
        }, {
            fallbackMessage: "验证码获取失败",
            redirectOnUnauthorized: false,
        });

        showFormMessage(`${result.message}，测试验证码：${result.debug_code}`);
        smsForm.code.focus();
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(sendButton, false);
    }
}

async function handleSmsLogin(event) {
    event.preventDefault();
    showFormMessage("正在校验验证码……");

    const form = event.currentTarget;
    const submitButton = form.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在登录……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/auth/sms/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                phone: form.phone.value.trim(),
                code: form.code.value.trim(),
            }),
        }, {
            fallbackMessage: "短信验证码登录失败",
            redirectOnUnauthorized: false,
        });

        window.location.href = ROLE_PAGES[result.user.role] || "/login";
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

async function handleWechatLogin(event) {
    event.preventDefault();
    showFormMessage("正在模拟微信授权……");

    const submitButton = event.currentTarget.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在授权……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/auth/wechat/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({code: WECHAT_DEMO_AUTHORIZATION_CODE}),
        }, {
            fallbackMessage: "微信登录失败",
            redirectOnUnauthorized: false,
        });

        window.location.href = ROLE_PAGES[result.user.role] || "/login";
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

async function handleQqLogin(event) {
    event.preventDefault();
    showFormMessage("正在模拟 QQ 授权……");

    const submitButton = event.currentTarget.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在授权……");
    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/auth/qq/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({code: QQ_DEMO_AUTHORIZATION_CODE}),
        }, {
            fallbackMessage: "QQ 登录失败",
            redirectOnUnauthorized: false,
        });

        window.location.href = ROLE_PAGES[result.user.role] || "/login";
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

async function loadCurrentUser() {
    const requiredRole = document.body.dataset.role;
    if (!requiredRole) {
        return;
    }

    try {
        const {data: user} = await window.ClassInsightApi.requestJson("/api/auth/me");
        if (user.role !== requiredRole) {
            window.location.href = ROLE_PAGES[user.role] || "/login";
            return;
        }

        document.querySelector("[data-user-name]").textContent = user.name;
        document.querySelector("[data-username]").textContent = user.username;
        const currentDate = document.querySelector("[data-current-date]");
        if (currentDate) {
            currentDate.textContent = new Intl.DateTimeFormat("zh-CN", {
                year: "numeric",
                month: "long",
                day: "numeric",
            }).format(new Date());
        }
    } catch (error) {
        if (!error.isUnauthorized) {
            window.location.href = "/login";
        }
    }
}

async function handleLogout() {
    const logoutButton = document.querySelector("[data-logout]");
    window.ClassInsightApi.setButtonBusy(logoutButton, true, "正在退出……");
    try {
        await window.ClassInsightApi.requestJson(
            "/api/auth/logout",
            {method: "POST"},
            {redirectOnUnauthorized: false},
        );
    } finally {
        window.location.href = "/login";
    }
}

const loginForm = document.querySelector("#login-form");
if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
}

const smsLoginForm = document.querySelector("#sms-login-form");
if (smsLoginForm) {
    smsLoginForm.addEventListener("submit", handleSmsLogin);
    document.querySelector("[data-send-sms-code]").addEventListener(
        "click",
        sendSmsCode,
    );
    for (const tab of document.querySelectorAll("[data-login-method]")) {
        tab.addEventListener("click", () => switchLoginMethod(tab.dataset.loginMethod));
    }
}

const wechatLoginForm = document.querySelector("#wechat-login-form");
if (wechatLoginForm) {
    wechatLoginForm.addEventListener("submit", handleWechatLogin);
}

const qqLoginForm = document.querySelector("#qq-login-form");
if (qqLoginForm) {
    qqLoginForm.addEventListener("submit", handleQqLogin);
}

const logoutButton = document.querySelector("[data-logout]");
if (logoutButton) {
    logoutButton.addEventListener("click", handleLogout);
}

loadCurrentUser();
