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

Start-Process PowerShell -Verb RunAs -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath, "-InstallPath",$InstallPath) -ErrorAction Stop


Get-Item $scriptPath | Remove-Item
