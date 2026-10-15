const discussionPanel = document.querySelector("[data-discussion-panel]");
const discussionList = document.querySelector("[data-discussion-list]");
const discussionEmpty = document.querySelector("[data-discussion-empty]");
const discussionForm = document.querySelector("#discussion-form");
const discussionContent = document.querySelector("#discussion-content");
const discussionCharacterCount = document.querySelector("[data-discussion-count]");
const discussionStatus = document.querySelector("[data-discussion-status]");
const discussionImage = document.querySelector("#discussion-image");
const discussionFileName = document.querySelector("[data-discussion-file-name]");
const discussionFileRemove = document.querySelector("[data-discussion-file-remove]");

const MAX_DISCUSSION_IMAGE_SIZE = 5 * 1024 * 1024;
const DEFAULT_IMAGE_NAME = "未选择图片";

let discussionSessionId = null;
let lastDiscussionMessageId = 0;
let discussionPollingTimer = null;
let discussionRequestInFlight = false;

function showDiscussionStatus(message, isError = false) {
    discussionStatus.textContent = message;
    discussionStatus.classList.toggle("error", isError);
}

function formatDiscussionTime(value) {
    return window.ClassInsightTime.formatUtcDateTime(value);
}

function syncDiscussionEmptyState() {
    const hasMessages = discussionList.querySelector("[data-message-id]") !== null;
    discussionEmpty.hidden = hasMessages;
    discussionEmpty.setAttribute("aria-hidden", String(hasMessages));
}

function appendDiscussionMessage(message) {
    if (discussionList.querySelector(`[data-message-id="${message.id}"]`)) {
        return;
    }

    const messageElement = document.createElement("article");
    messageElement.className = "discussion-message";
    messageElement.classList.toggle("mine", message.is_mine);
    messageElement.classList.add(`from-${message.sender_role}`);
    messageElement.dataset.messageId = String(message.id);
    messageElement.dataset.senderRole = message.sender_role;
    messageElement.setAttribute(
        "aria-label",
        `${message.is_mine ? "我" : message.sender_name}发送的${message.sender_role === "teacher" ? "教师" : "学生"}消息`,
    );

    const messageHeader = document.createElement("header");
    const senderElement = document.createElement("strong");
    const roleElement = document.createElement("span");
    const timeElement = document.createElement("time");

    senderElement.textContent = message.sender_name;
    roleElement.className = `discussion-role ${message.sender_role}`;
    roleElement.textContent = message.sender_role === "teacher" ? "教师" : "学生";
    timeElement.dateTime = message.created_at;
    timeElement.textContent = formatDiscussionTime(message.created_at);
    messageHeader.append(senderElement, roleElement, timeElement);

    messageElement.append(messageHeader);

    if (message.content) {
        const contentElement = document.createElement("p");
        contentElement.textContent = message.content;
        messageElement.append(contentElement);
    }

    if (message.image_url) {
        const imageLink = document.createElement("a");
        const imageElement = document.createElement("img");
        imageLink.className = "discussion-image-link";
        imageLink.href = message.image_url;
        imageLink.target = "_blank";
        imageLink.rel = "noopener";
        imageElement.src = message.image_url;
        imageElement.alt = `${message.sender_name}发送的讨论图片`;
        imageElement.loading = "lazy";
        imageLink.appendChild(imageElement);
        messageElement.appendChild(imageLink);
    }

    discussionList.appendChild(messageElement);
    syncDiscussionEmptyState();
    lastDiscussionMessageId = Math.max(lastDiscussionMessageId, message.id);
}

async function loadDiscussionMessages(onlyNew = false) {
    if (discussionSessionId === null) {
        return;
    }
    // 后台标签页无需持续轮询；同时防止慢请求尚未完成时发出重叠请求。
    if (
        (onlyNew && document.hidden)
        || discussionPanel.classList.contains("workspace-panel-inactive")
        || discussionRequestInFlight
    ) {
        return;
    }

    const afterId = onlyNew ? lastDiscussionMessageId : 0;
    discussionRequestInFlight = true;
    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            `/api/discussions/${discussionSessionId}/messages?after_id=${afterId}`,
            {},
            {fallbackMessage: "讨论消息读取失败"},
        );

        for (const message of result.messages) {
            appendDiscussionMessage(message);
        }
        if (!onlyNew) {
            syncDiscussionEmptyState();
            discussionList.scrollTop = discussionList.scrollHeight;
        }
    } catch (error) {
        if (!error.isUnauthorized) {
            showDiscussionStatus(error.message, true);
        }
    } finally {
        discussionRequestInFlight = false;
    }
}

async function submitDiscussionMessage(event) {
    event.preventDefault();
    const content = discussionContent.value.trim();
    const imageFile = discussionImage.files[0];
    if ((!content && !imageFile) || discussionSessionId === null) {
        showDiscussionStatus("请输入讨论内容或选择一张图片", true);
        return;
    }
    if (imageFile && imageFile.size > MAX_DISCUSSION_IMAGE_SIZE) {
        showDiscussionStatus("图片不能超过 5 MB", true);
        return;
    }

    const submitButton = discussionForm.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在发送……");
    showDiscussionStatus("正在发送……");

    try {
        let result;
        if (imageFile) {
            const formData = new FormData();
            formData.append("image", imageFile);
            if (content) {
                formData.append("content", content);
            }
            ({data: result} = await window.ClassInsightApi.requestJson(
                `/api/discussions/${discussionSessionId}/images`,
                {
                    method: "POST",
                    body: formData,
                },
                {fallbackMessage: "图片消息发送失败"},
            ));
        } else {
            ({data: result} = await window.ClassInsightApi.requestJson(
                `/api/discussions/${discussionSessionId}/messages`,
                {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({content}),
                },
                {fallbackMessage: "消息发送失败"},
            ));
        }

        appendDiscussionMessage(result);
        discussionContent.value = "";
        discussionImage.value = "";
        discussionFileName.textContent = DEFAULT_IMAGE_NAME;
        discussionFileRemove.hidden = true;
        discussionCharacterCount.textContent = "0 / 500";
        discussionList.scrollTop = discussionList.scrollHeight;
        showDiscussionStatus("发送成功");
        window.ClassInsightApi.showToast("讨论消息已发送");
    } catch (error) {
        if (!error.isUnauthorized) {
            showDiscussionStatus(error.message, true);
        }
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

discussionContent.addEventListener("input", () => {
    discussionCharacterCount.textContent = `${discussionContent.value.length} / 500`;
});

discussionImage.addEventListener("change", () => {
    const selectedFile = discussionImage.files[0];
    discussionFileName.textContent = selectedFile
        ? selectedFile.name
        : DEFAULT_IMAGE_NAME;
    discussionFileRemove.hidden = !selectedFile;
});

discussionFileRemove.addEventListener("click", () => {
    discussionImage.value = "";
    discussionFileName.textContent = DEFAULT_IMAGE_NAME;
    discussionFileRemove.hidden = true;
    discussionImage.focus();
});

discussionForm.addEventListener("submit", submitDiscussionMessage);

document.addEventListener("classroom:loaded", async (event) => {
    discussionSessionId = event.detail.session_id;
    discussionList.querySelectorAll("[data-message-id]").forEach((message) => message.remove());
    lastDiscussionMessageId = 0;
    syncDiscussionEmptyState();
    discussionPanel.hidden = false;
    await loadDiscussionMessages();

    if (discussionPollingTimer !== null) {
        window.clearInterval(discussionPollingTimer);
    }
    discussionPollingTimer = window.setInterval(
        () => loadDiscussionMessages(true),
        3000,
    );
});

window.addEventListener("beforeunload", () => {
    if (discussionPollingTimer !== null) {
        window.clearInterval(discussionPollingTimer);
    }
});

document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
        loadDiscussionMessages(true);
    }
});

document.addEventListener("workspace:changed", (event) => {
    if (event.detail.tab === "discussion") {
        loadDiscussionMessages(lastDiscussionMessageId > 0);
    }
});
