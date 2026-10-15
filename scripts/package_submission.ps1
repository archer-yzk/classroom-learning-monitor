[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$StudentNo,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Name
)

$ErrorActionPreference = "Stop"

$StudentNo = $StudentNo.Trim()
$Name = $Name.Trim()
$invalidNamePattern = '[\\/:*?"<>|]'
if ($StudentNo -match $invalidNamePattern -or $Name -match $invalidNamePattern) {
    throw "学号或姓名包含 Windows 文件名不允许的字符。"
}
if ($StudentNo -match '^\[.*\]$' -or $Name -match '^\[.*\]$') {
    throw "请传入真实学号和姓名，不能使用占位符。"
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "未找到 .venv\Scripts\python.exe，请先按安装手册创建虚拟环境。"
}

Write-Host "正在执行最终提交严格检查..." -ForegroundColor Cyan
& $pythonPath -m scripts.validate_submission --strict
if ($LASTEXITCODE -ne 0) {
    throw "最终提交严格检查未通过，请先修正上方问题。"
}

$distRoot = Join-Path $projectRoot "dist"
$packageName = "${StudentNo}_${Name}_课堂学情监控系统"
$stageRoot = Join-Path $distRoot $packageName
$zipPath = Join-Path $distRoot "${packageName}.zip"

New-Item -ItemType Directory -Path $distRoot -Force | Out-Null

# 删除旧打包目录前验证绝对路径，确保目标严格位于本项目 dist 内。
$distFullPath = [System.IO.Path]::GetFullPath($distRoot).TrimEnd('\') + '\'
$stageFullPath = [System.IO.Path]::GetFullPath($stageRoot)
$zipFullPath = [System.IO.Path]::GetFullPath($zipPath)
if (-not $stageFullPath.StartsWith($distFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "打包临时目录越出项目 dist，已停止。"
}
if (-not $zipFullPath.StartsWith($distFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "压缩包路径越出项目 dist，已停止。"
}

if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$sourceRoot = Join-Path $stageRoot "源代码"
$documentRoot = Join-Path $stageRoot "文档"
$screenshotRoot = Join-Path $stageRoot "截图与视频"
New-Item -ItemType Directory -Path $sourceRoot, $documentRoot, $screenshotRoot -Force | Out-Null

$sourceDirectories = @("backend", "frontend", "database", "scripts", "tests")
foreach ($directoryName in $sourceDirectories) {
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot $directoryName) `
        -Destination (Join-Path $sourceRoot $directoryName) `
        -Recurse `
        -Force
}

$sourceFiles = @("requirements.txt", "run.bat", "README.md")
foreach ($fileName in $sourceFiles) {
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot $fileName) `
        -Destination (Join-Path $sourceRoot $fileName) `
        -Force
}

Copy-Item -Path (Join-Path $projectRoot "docs\*") -Destination $documentRoot -Recurse -Force
$screenshotFiles = @(
    "01_登录页面.png",
    "02_学生学情反馈.jpg",
    "03_学生学情提醒.jpg",
    "04_学生在线讨论.jpg",
    "05_教师实时统计与图表.jpg",
    "06_教师学情预警跟进.jpg",
    "07_教师在线讨论.jpg",
    "08_历史学情查询.jpg",
    "09_管理员用户管理.jpg",
    "10_管理员统计周期.jpg",
    "11_学生移动端适配.jpg"
)
foreach ($fileName in $screenshotFiles) {
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot "截图与视频\$fileName") `
        -Destination (Join-Path $screenshotRoot $fileName) `
        -Force
}

$requirementRoot = Join-Path $documentRoot "需求依据"
New-Item -ItemType Directory -Path $requirementRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "产品要求文档.pdf") -Destination $requirementRoot -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "课堂学情监控管理系统大作业清单.pdf") -Destination $requirementRoot -Force

# 只清理已经验证位于 dist 下的打包副本，不触碰开发目录原文件。
Get-ChildItem -LiteralPath $stageRoot -Directory -Filter "__pycache__" -Recurse |
    Sort-Object FullName -Descending |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $stageRoot -File -Recurse |
    Where-Object {
        $_.Extension -eq ".pyc" -or
        $_.Name -like "temp_*" -or
        $_.Name -like "*.db-wal" -or
        $_.Name -like "*.db-shm"
    } |
    Remove-Item -Force

Compress-Archive -LiteralPath $stageRoot -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "打包完成：" -ForegroundColor Green
Write-Host $zipPath
Write-Host "请务必解压一次，核对源代码、文档、截图与视频三个目录。"
