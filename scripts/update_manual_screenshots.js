const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8011";
const outputDir = path.resolve(process.argv[3] || "截图与视频");
const edgePath = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

async function settle(page, selector) {
  await page.waitForSelector(selector, { state: "visible" });
  await page.waitForTimeout(700);
}

async function login(browser, username, viewport = { width: 1600, height: 1000 }) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.locator("#username").fill(username);
  await page.locator("#password").fill("123456");
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith("/login")),
    page.locator("#login-form button[type='submit']").click(),
  ]);
  return { context, page };
}

async function capture(page, filename, options = {}) {
  const extension = path.extname(filename).toLowerCase();
  const screenshotOptions = {
    path: path.join(outputDir, filename),
    fullPage: false,
    animations: "disabled",
    ...options,
  };
  if (extension === ".jpg" || extension === ".jpeg") {
    screenshotOptions.type = "jpeg";
    screenshotOptions.quality = 92;
  } else {
    screenshotOptions.type = "png";
  }
  await page.screenshot(screenshotOptions);
  console.log(`updated ${filename}`);
}

async function main() {
  const browser = await chromium.launch({ executablePath: edgePath, headless: true });
  try {
    const loginContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const loginPage = await loginContext.newPage();
    await loginPage.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
    await capture(loginPage, "01_登录页面.png");
    await loginContext.close();

    const student = await login(browser, "student001");
    await settle(student.page, "#student-feedback:not([hidden])");
    await capture(student.page, "02_学生学情反馈.jpg");

    await student.page.locator('[data-workspace-tab="alerts"]').click();
    await settle(student.page, "#student-alerts:not([hidden])");
    await student.page.evaluate(() => window.scrollTo(0, 0));
    await capture(student.page, "03_学生学情提醒.jpg");

    await student.page.locator('[data-workspace-tab="discussion"]').click();
    await settle(student.page, "#student-discussion:not([hidden])");
    await capture(student.page, "04_学生在线讨论.jpg");
    await student.context.close();

    const teacher = await login(browser, "teacher001");
    await settle(teacher.page, "#teacher-statistics:not([hidden])");
    await teacher.page.locator("#teacher-statistics").scrollIntoViewIfNeeded();
    await capture(teacher.page, "05_教师实时统计与图表.jpg");

    await teacher.page.locator('[data-workspace-tab="alerts"]').click();
    await settle(teacher.page, "#teacher-alerts:not([hidden])");
    await teacher.page.evaluate(() => window.scrollTo({ top: 0, behavior: "auto" }));
    const followUpButton = teacher.page.getByRole("button", { name: "查看并跟进" }).first();
    if (await followUpButton.count()) {
      await followUpButton.click();
      await settle(teacher.page, ".alert-drawer.open:not([hidden])");
    }
    await capture(teacher.page, "06_教师学情预警跟进.jpg");
    if (await teacher.page.locator(".alert-drawer.open").count()) {
      await teacher.page.locator("[data-alert-drawer-close]").click();
      await teacher.page.locator(".alert-drawer").waitFor({ state: "hidden" });
    }

    await teacher.page.locator('[data-workspace-tab="discussion"]').click();
    await settle(teacher.page, "#teacher-discussion:not([hidden])");
    await teacher.page.evaluate(() => window.scrollTo({ top: 0, behavior: "auto" }));
    await capture(teacher.page, "07_教师在线讨论.jpg");

    await teacher.page.goto(`${baseUrl}/teacher/history`, { waitUntil: "networkidle" });
    await settle(teacher.page, ".history-card");
    await capture(teacher.page, "08_历史学情查询.jpg");
    await teacher.context.close();

    const admin = await login(browser, "admin001", { width: 1920, height: 1080 });
    await admin.page.locator('[data-workspace-tab="users"]').click();
    await settle(admin.page, ".admin-user-table-wrap:not([hidden])");
    await capture(admin.page, "09_管理员用户管理.jpg");

    await admin.page.locator('[data-workspace-tab="settings"]').click();
    await settle(admin.page, ".settings-panel:not([hidden])");
    await capture(admin.page, "10_管理员统计周期.jpg");
    await admin.context.close();

    const mobile = await login(browser, "student001", { width: 390, height: 844 });
    await settle(mobile.page, "#student-feedback:not([hidden])");
    await capture(mobile.page, "11_学生移动端适配.jpg");
    await mobile.context.close();
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
