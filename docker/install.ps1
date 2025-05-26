param (
    [string]$InstallPath
)

if ([string]::IsNullOrWhiteSpace($InstallPath)) {
    $InstallPath = Join-Path $env:LOCALAPPDATA "NekroAgent"
}

$scriptUrl = "https://raw.githubusercontent.com/KroMiose/nekro-agent/refs/heads/main/docker/wslinstall.ps1"
$scriptPath = Join-Path $env:TEMP "NA_wslinstall.ps1"

try {
    $response = Invoke-WebRequest -Uri $scriptUrl -OutFile $scriptPath
} catch {
    Write-Host "安装脚本获取失败"
    Read-Host "按 Enter 键退出..."
    Exit 1
}

try {
    Write-Host "正在尝试以管理员权限启动脚本..."
    Start-Process PowerShell -Verb RunAs -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-InstallPath", $InstallPath
    ) -ErrorAction Stop -Wait
} catch {
    Write-Host "获取管理员权限失败，取消..."
}

Get-Item $scriptPath | Remove-Item
