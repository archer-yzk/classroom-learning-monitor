/**
 * 系统时间统一约定：后端和 SQLite 保存无时区 UTC，前端按北京时间展示。
 * 后端历史接口仍接收 UTC，datetime-local 输入提交前需要反向转换。
 */
(function initializeClassInsightTime() {
    const DISPLAY_TIME_ZONE = "Asia/Shanghai";
    const EXPLICIT_TIME_ZONE_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i;

    function parseUtcDateTime(value) {
        if (!value) {
            return null;
        }

        let normalizedValue = String(value).trim().replace(" ", "T");
        if (!EXPLICIT_TIME_ZONE_PATTERN.test(normalizedValue)) {
            normalizedValue += "Z";
        }

        const parsedDate = new Date(normalizedValue);
        return Number.isNaN(parsedDate.getTime()) ? null : parsedDate;
    }

    function formatUtcDateTime(value, options = {}) {
        const parsedDate = parseUtcDateTime(value);
        if (!parsedDate) {
            return options.fallback || "—";
        }

        const formatter = new Intl.DateTimeFormat("zh-CN", {
            timeZone: DISPLAY_TIME_ZONE,
            hourCycle: "h23",
            ...(options.withYear === false ? {} : {year: "numeric"}),
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            ...(options.withSeconds === false ? {} : {second: "2-digit"}),
        });
        return formatter.format(parsedDate).replaceAll("/", "-");
    }

    function localInputToUtc(value) {
        if (!value) {
            return value;
        }

        const localDate = new Date(value);
        if (Number.isNaN(localDate.getTime())) {
            return value;
        }
        return localDate.toISOString().slice(0, 19);
    }

    window.ClassInsightTime = Object.freeze({
        displayTimeZone: DISPLAY_TIME_ZONE,
        formatUtcDateTime,
        localInputToUtc,
        parseUtcDateTime,
    });
})();
