const workspaceDashboard = document.querySelector(".dashboard-card");
const workspaceTabButtons = Array.from(
    document.querySelectorAll("[data-workspace-tab]"),
);
const workspacePanels = Array.from(
    document.querySelectorAll("[data-workspace-panel]"),
);

function activateWorkspaceTab(tabName, options = {}) {
    if (!workspaceTabButtons.some((button) => button.dataset.workspaceTab === tabName)) {
        return;
    }

    for (const button of workspaceTabButtons) {
        const isActive = button.dataset.workspaceTab === tabName;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
    }
    for (const panel of workspacePanels) {
        panel.classList.toggle(
            "workspace-panel-inactive",
            panel.dataset.workspacePanel !== tabName,
        );
    }

    workspaceDashboard?.classList.add("workspace-ready");
    if (workspaceDashboard) {
        workspaceDashboard.dataset.activeWorkspace = tabName;
    }
    if (options.updateUrl) {
        window.history.replaceState(null, "", `#workspace-${tabName}`);
    }

    document.dispatchEvent(
        new CustomEvent("workspace:changed", {detail: {tab: tabName}}),
    );

    if (options.scroll) {
        const firstPanel = workspacePanels.find(
            (panel) => panel.dataset.workspacePanel === tabName,
        );
        window.requestAnimationFrame(() => {
            if (!firstPanel) {
                return;
            }
            const teacherBusinessPage = document.body.dataset.role === "teacher"
                && tabName !== "overview";
            const topbarHeight = document.querySelector(".app-topbar")?.offsetHeight ?? 0;
            const targetTop = teacherBusinessPage
                ? 0
                : firstPanel.getBoundingClientRect().top
                    + window.scrollY
                    - topbarHeight
                    - 16;
            const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            window.scrollTo({
                top: Math.max(0, targetTop),
                behavior: reduceMotion ? "auto" : "smooth",
            });
        });
    }
}

if (workspaceTabButtons.length && workspacePanels.length) {
    const hashTab = window.location.hash.startsWith("#workspace-")
        ? window.location.hash.slice("#workspace-".length)
        : "";
    const defaultTab = workspaceTabButtons.find((button) => button.classList.contains("active"))
        ?.dataset.workspaceTab;
    const initialTab = workspaceTabButtons.some(
        (button) => button.dataset.workspaceTab === hashTab,
    )
        ? hashTab
        : defaultTab || workspaceTabButtons[0].dataset.workspaceTab;
    activateWorkspaceTab(initialTab);

    workspaceTabButtons.forEach((button, index) => {
        button.addEventListener("click", () => {
            activateWorkspaceTab(button.dataset.workspaceTab, {
                updateUrl: true,
                scroll: true,
            });
        });
        button.addEventListener("keydown", (event) => {
            if (!["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(event.key)) {
                return;
            }
            event.preventDefault();
            const moveForward = event.key === "ArrowDown" || event.key === "ArrowRight";
            const nextIndex = (
                index + (moveForward ? 1 : -1) + workspaceTabButtons.length
            ) % workspaceTabButtons.length;
            workspaceTabButtons[nextIndex].focus();
            workspaceTabButtons[nextIndex].click();
        });
    });
}
