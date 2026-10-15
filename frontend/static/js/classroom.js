async function loadCurrentClassroom() {
    const classroomElement = document.querySelector("[data-classroom]");
    if (!classroomElement) {
        return;
    }

    const messageElement = document.querySelector("[data-classroom-message]");

    try {
        const {data: result} = await window.ClassInsightApi.requestJson(
            "/api/classrooms/current",
            {},
            {fallbackMessage: "当前课堂读取失败"},
        );

        document.querySelector("[data-course-name]").textContent = result.course_name;
        document.querySelector("[data-class-name]").textContent = result.class_name;
        document.querySelector("[data-topic]").textContent = result.topic;
        document.querySelector("[data-teacher-name]").textContent = result.teacher_name;
        document.querySelector("[data-start-time]").textContent =
            window.ClassInsightTime.formatUtcDateTime(result.start_time, {
                withSeconds: false,
            });
        messageElement.textContent = "课堂数据读取成功";
        document.dispatchEvent(
            new CustomEvent("classroom:loaded", {detail: result})
        );
    } catch (error) {
        classroomElement.hidden = true;
        if (!error.isUnauthorized) {
            messageElement.textContent = error.message;
        }
    }
}

loadCurrentClassroom();
