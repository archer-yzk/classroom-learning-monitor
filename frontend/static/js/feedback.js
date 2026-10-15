let currentSessionId = null;
let latestScore = null;

const feedbackPanel = document.querySelector("[data-feedback-panel]");
const feedbackOptionsElement = document.querySelector("[data-feedback-options]");
const feedbackMessageElement = document.querySelector("[data-feedback-message]");
const feedbackForm = document.querySelector("#feedback-form");

function showFeedbackMessage(message, isError = false) {
    feedbackMessageElement.textContent = message;
    feedbackMessageElement.classList.toggle("error", isError);
}

function selectLatestScore() {
    feedbackOptionsElement.querySelectorAll(".feedback-option.saved").forEach(
        (option) => option.classList.remove("saved"),
    );
    if (latestScore === null) {
        return;
    }

    const selectedInput = feedbackOptionsElement.querySelector(
        `input[value="${latestScore}"]`
    );
    if (selectedInput) {
        selectedInput.checked = true;
        selectedInput.closest(".feedback-option").classList.add("saved");
    }
}

async function loadFeedbackOptions() {
    try {
        const {data: options} = await window.ClassInsightApi.requestJson(
            "/api/feedbacks/options",
            {},
            {fallbackMessage: "表情选项读取失败"},
        );
        feedbackOptionsElement.replaceChildren();

        options.forEach((option) => {
            const labelElement = document.createElement("label");
            labelElement.className = "feedback-option";

            const inputElement = document.createElement("input");
            inputElement.type = "radio";
            inputElement.name = "score";
            inputElement.value = option.score;
            inputElement.required = true;

            const emojiElement = document.createElement("span");
            emojiElement.className = "feedback-emoji";
            emojiElement.textContent = option.emoji;

            const textElement = document.createElement("span");
            textElement.className = "feedback-label";
            textElement.textContent = `${option.score} 分 · ${option.label}`;

            labelElement.append(inputElement, emojiElement, textElement);
            feedbackOptionsElement.append(labelElement);
        });

        selectLatestScore();
    } catch (error) {
        if (!error.isUnauthorized) {
            showFeedbackMessage(error.message, true);
        }
    }
}

async function loadLatestFeedback() {
    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            `/api/feedbacks/current/${currentSessionId}`,
            {},
            {fallbackMessage: "最近反馈读取失败"},
        );

        if (result.feedback) {
            latestScore = result.feedback.score;
            selectLatestScore();
            showFeedbackMessage(
                `最近提交：${result.feedback.emoji} ${result.feedback.label}（${result.feedback.score} 分）`
            );
        } else {
            showFeedbackMessage("本次课堂尚未提交反馈");
        }
    } catch (error) {
        if (!error.isUnauthorized) {
            showFeedbackMessage(error.message, true);
        }
    }
}

async function submitFeedback(event) {
    event.preventDefault();
    const selectedInput = feedbackForm.querySelector("input[name='score']:checked");
    if (!selectedInput || currentSessionId === null) {
        showFeedbackMessage("请先选择一个表情", true);
        return;
    }

    const submitButton = feedbackForm.querySelector("button[type='submit']");
    window.ClassInsightApi.setButtonBusy(submitButton, true, "正在提交……");
    showFeedbackMessage("正在提交……");

    try {
        const {data: result} = await window.ClassInsightApi.requestJson("/api/feedbacks", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                session_id: currentSessionId,
                score: Number(selectedInput.value),
            }),
        }, {
            fallbackMessage: "反馈提交失败",
        });

        latestScore = result.score;
        selectLatestScore();
        showFeedbackMessage(
            `提交成功：${result.emoji} ${result.label}（${result.score} 分）`
        );
        window.ClassInsightApi.showToast("学情反馈已提交");
        document.dispatchEvent(
            new CustomEvent("feedback:submitted", {detail: result})
        );
    } catch (error) {
        if (!error.isUnauthorized) {
            showFeedbackMessage(error.message, true);
        }
    } finally {
        window.ClassInsightApi.setButtonBusy(submitButton, false);
    }
}

document.addEventListener("classroom:loaded", async (event) => {
    currentSessionId = event.detail.session_id;
    feedbackPanel.hidden = false;
    await loadFeedbackOptions();
    await loadLatestFeedback();
});

feedbackForm.addEventListener("submit", submitFeedback);
