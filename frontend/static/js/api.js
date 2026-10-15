(function initializeClassInsightApi() {
    class ApiError extends Error {
        constructor(message, status = 0, payload = null) {
            super(message);
            this.name = "ApiError";
            this.status = status;
            this.payload = payload;
        }

        get isUnauthorized() {
            return this.status === 401;
        }
    }

    function describeValidationIssue(issue) {
        if (!issue || typeof issue !== "object") {
            return String(issue || "");
        }

        const fieldPath = Array.isArray(issue.loc)
            ? issue.loc.filter((item) => item !== "body").join(".")
            : "";
        const message = issue.msg || "输入内容不符合要求";
        return fieldPath ? `${fieldPath}：${message}` : message;
    }

    function getErrorMessage(payload, fallback = "操作失败，请稍后重试") {
        if (typeof payload === "string" && payload.trim()) {
            return payload.trim();
        }
        if (!payload || typeof payload !== "object") {
            return fallback;
        }
        if (typeof payload.detail === "string" && payload.detail.trim()) {
            return payload.detail.trim();
        }
        if (Array.isArray(payload.detail) && payload.detail.length) {
            return payload.detail.map(describeValidationIssue).filter(Boolean).join("；") || fallback;
        }
        if (typeof payload.message === "string" && payload.message.trim()) {
            return payload.message.trim();
        }
        return fallback;
    }

    async function readPayload(response) {
        const responseText = await response.text();
        if (!responseText) {
            return null;
        }

        try {
            return JSON.parse(responseText);
        } catch (_error) {
            return responseText;
        }
    }

    async function requestJson(url, fetchOptions = {}, requestOptions = {}) {
        const {
            fallbackMessage = "操作失败，请稍后重试",
            redirectOnUnauthorized = true,
        } = requestOptions;

        let response;
        try {
            response = await fetch(url, {
                credentials: "same-origin",
                ...fetchOptions,
            });
        } catch (_error) {
            throw new ApiError("无法连接服务器，请确认项目已经启动");
        }

        const payload = await readPayload(response);
        if (response.status === 401 && redirectOnUnauthorized) {
            window.location.assign("/login");
            throw new ApiError("登录状态已失效，正在返回登录页", 401, payload);
        }
        if (!response.ok) {
            throw new ApiError(
                getErrorMessage(payload, fallbackMessage),
                response.status,
                payload,
            );
        }
        return {data: payload, response};
    }

    function setButtonBusy(button, isBusy, busyText = "处理中……") {
        if (!button) {
            return;
        }

        if (isBusy) {
            if (!button.dataset.idleText) {
                button.dataset.idleText = button.textContent;
            }
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
            if (busyText) {
                button.textContent = busyText;
            }
            return;
        }

        button.disabled = false;
        button.removeAttribute("aria-busy");
        if (button.dataset.idleText) {
            button.textContent = button.dataset.idleText;
            delete button.dataset.idleText;
        }
    }

    function showToast(message, options = {}) {
        if (!message) {
            return;
        }
        const {
            type = "success",
            duration = 3200,
        } = options;
        let container = document.querySelector("[data-toast-container]");
        if (!container) {
            container = document.createElement("div");
            container.className = "toast-container";
            container.dataset.toastContainer = "";
            container.setAttribute("aria-live", "polite");
            container.setAttribute("aria-atomic", "false");
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `app-toast ${type}`;
        toast.setAttribute("role", type === "error" ? "alert" : "status");

        const icon = document.createElement("span");
        icon.className = "app-toast-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = type === "error" ? "!" : "✓";

        const text = document.createElement("span");
        text.textContent = message;

        const closeButton = document.createElement("button");
        closeButton.type = "button";
        closeButton.className = "app-toast-close";
        closeButton.setAttribute("aria-label", "关闭通知");
        closeButton.textContent = "×";

        const removeToast = () => {
            toast.classList.add("leaving");
            window.setTimeout(() => toast.remove(), 180);
        };
        closeButton.addEventListener("click", removeToast);
        toast.append(icon, text, closeButton);
        container.appendChild(toast);
        window.setTimeout(removeToast, duration);
    }

    window.ClassInsightApi = Object.freeze({
        ApiError,
        getErrorMessage,
        readPayload,
        requestJson,
        setButtonBusy,
        showToast,
    });
})();
