﻿[CmdletBinding()]
param (
    [string]$InstallPath
)

if ([string]::IsNullOrWhiteSpace($InstallPath)) {
    $InstallPath = Join-Path $env:LOCALAPPDATA "NekroAgent"
}

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "此脚本需要管理员权限。"
    Write-Host "正在尝试以管理员身份重新运行..."
    try {
        $scriptPath = $MyInvocation.PSCommandPath
        if ([string]::IsNullOrEmpty($scriptPath)) {
            $scriptPath = $MyInvocation.MyCommand.Definition
        }

        if ([string]::IsNullOrEmpty($scriptPath)) {
            Write-Host "无法确定脚本路径以进行提权。请以管理员身份手动运行此脚本。"
            Read-Host "按 Enter 键退出..."
            Exit 1
        }
        Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" `"$InstallPath`"" -ErrorAction Stop
        Exit
    } catch {
        Write-Error "提权失败: $($_.Exception.Message)"
        Write-Error "请右键单击此脚本文件，选择“以管理员身份运行”。"
        Read-Host "按 Enter 键退出..."
        Exit 1
    }
}

Write-Host "脚本以管理员权限运行"

$Global:RebootNeeded = $false
$Global:FeatureState = 0
$Global:Arch = $null
$Global:ArchString = $null

$DebianLink = "https://aka.ms/wsl-debian-gnulinux"

$DistroName = "nekro-agent"
$WorkDir = (Join-Path $env:TEMP ("NekroAgent_" + (Get-Date -Format "yyyyMMddHH") + (Get-Random)))
$DistroFilePath = Join-Path $WorkDir "distro.zip"
$AppxFilePath = Join-Path $WorkDir "appx.zip"
$TarballFilePath = Join-Path $WorkDir "install.tar.gz"

$DistroInstallLocation = Join-Path $env:LOCALAPPDATA "NekroAgent"

$WSLStatus = [PSCustomObject]@{
    Enabled = $true
    Version = $null
    DistroInstalled = $false
}

# 注册脚本退出清理操作
$action = {
    if (Test-Path -Path $WorkDir -PathType Container) {
        Write-Host "正在清理临时目录..."
        Remove-Item $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $action -SupportEvent

# 确认退出
function Confirm-ExitWithEnter {
    param (
        [Parameter()]
        [int]$ExitCode = 0
    )

    Write-Host ""
    Write-Host "按 Enter 键退出脚本..." -NoNewline -ForegroundColor Cyan
    Read-Host
    Exit $ExitCode
}

# 下载 Distro 文件
function Download-WslDistroZip {
    [CmdletBinding(SupportsShouldProcess=$true)]
    param (
        [Parameter(Mandatory=$true, Position=0)]
        [string]$AkaMsLink,
        [Parameter(Mandatory=$true, Position=1)]
        [string]$OutputFilePath
    )

    try {
        if ($PSCmdlet.ShouldProcess($AkaMsLink, "下载文件到 '$OutputFilePath'")) {
            Write-Host "开始下载文件..."
            Invoke-WebRequest -Uri $AkaMsLink -OutFile $OutputFilePath -ErrorAction Stop
        } else {
            Write-Warning "下载操作已被用户通过 ShouldProcess 中止。"
            return $false
        }
    }
    catch {
        Write-Error "下载过程中发生错误: $($_.Exception.Message)"
        if ($_.Exception.StackTrace) {
            Write-Verbose "堆栈跟踪: $($_.Exception.StackTrace)"
        }
        return $null
    }
    return $true
}

# 从存档提取文件
function Extract-FileFromArchive {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true, Position=0)]
        [string]$ArchivePath,
        [Parameter(Mandatory=$true, Position=1)]
        [string]$EntryPathRegexPattern,
        [Parameter(Mandatory=$true, Position=2)]
        [string]$DestinationFilePath
    )

    if (-not (Test-Path -Path $ArchivePath -PathType Leaf)) {
        Write-Host "'$ArchivePath' 未找到或不是一个文件。"
        return $false
    }

    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
    } catch {}


    $archive = $null
    $fileExtracted = $false
    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
        $matchingEntries = $archive.Entries | Where-Object { $_.FullName -match $EntryPathRegexPattern }

        if ($matchingEntries.Count -eq 1) {
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($matchingEntries[0], $DestinationFilePath, $true)
            Write-Host "文件 '$($matchingEntries.FullName)' 已成功提取"
            $fileExtracted = $true
        } else {
            Write-Error "在文件 '$ArchivePath' 中未找到或找到多个匹配文件。"
        }
    }
    catch {
        Write-Error "$($_.Exception.Message)"
    }
    finally {
        if ($null -ne $archive) {
            $archive.Dispose()
        }
    }
    return $fileExtracted
}

# 启用 Windows 功能并检查是否需要重启
function Ensure-WindowsFeatureEnabled {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FeatureName,
        [Parameter(Mandatory=$true)]
        [string]$FeatureDisplayName
    )

    Write-Host "正在启用 '$FeatureDisplayName' 功能..."
    try {
        $result = Enable-WindowsOptionalFeature -Online -FeatureName $FeatureName -NoRestart -ErrorAction Stop -WarningAction SilentlyContinue
        $info = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName -ErrorAction Stop
        if (($info.State -ne "Enabled") -and ($info.State -ne "EnablePending")) {
            Write-Warning "启用失败：'$FeatureDisplayName'"
            return
        }
        $Global:FeatureState += 1

        if ($result.RestartNeeded) {
            Write-Warning "启用 '$FeatureDisplayName' 后需要重启计算机。"
            $Global:RebootNeeded = $Global:RebootNeeded -or $result.RestartNeeded
        }
    } catch {
        Write-Error "启用 '$FeatureDisplayName' 功能失败: $($_.Exception.Message)"
        Confirm-ExitWithEnter 1
    }
}

# 在 WSL 执行代码
function Invoke-WslCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistributionName,
        [Parameter(Mandatory=$true)]
        [string]$Command,
        [Parameter()]
        [string]$Username = "root"
    )
    Write-Verbose "在发行版 '$DistributionName' 中以用户 '$Username' 执行命令: $Command"
    $execResult = wsl.exe -d $DistributionName -u $Username -e bash -c "$Command"
    if (-not [string]::IsNullOrWhiteSpace($execResult)) {
        Write-Host "命令输出:"
        $execResult | ForEach-Object { Write-Verbose "  $_" }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "命令执行失败：" -ForegroundColor RED
        $Command | ForEach-Object { Write-Host "  $_"  -ForegroundColor RED }
    }
}

# 安装 WSL2
function Install-Wsl {
    try {
        Write-Host "正在尝试使用 'wsl.exe' 安装 WSL 功能..."
        $null = wsl.exe --install --no-distribution
        if ($LASTEXITCODE -ne 0) { Throw }
        $Global:RebootNeeded = $true
    } catch {
        Write-Warning "尝试使用 `wsl.exe` 安装失败，尝试手动启用组件..."
        Ensure-WindowsFeatureEnabled -FeatureName "Microsoft-Windows-Subsystem-Linux" -FeatureDisplayName "适用于 Linux 的 Windows 子系统"
        Ensure-WindowsFeatureEnabled -FeatureName "VirtualMachinePlatform" -FeatureDisplayName "虚拟机平台"
        if ($Global:FeatureState -lt 2) {
            Write-Warning "功能启用失败或部分失败，请尝试重新运行"
            Confirm-ExitWithEnter 1
        }
    }
}

# 检测 WSL2 可用性
function Test-WslAvailability {
    param(
        [string]$DistroName
    )

    $installedDistributions = wsl.exe --list --quiet --all
    if ($LASTEXITCODE -ne 0) { $WSLStatus.Enabled = $false }
    if ($installedDistributions -contains $DistroName) {
        $WSLStatus.DistroInstalled = $true
    }
}


# 检测环境可用性
Test-WslAvailability $DistroName
if ($WSLStatus.DistroInstalled) {
    Write-Host "'$DistroName' 已安装，退出..."
    Confirm-ExitWithEnter
}

try {
    $processorInfo = Get-CimInstance -Class Win32_Processor -ErrorAction Stop | Select-Object -First 1
    $processorArchitectureId = $processorInfo.Architecture
    $Global:Arch = $processorArchitectureId

    switch ($processorArchitectureId) {
        0 { $Global:ArchString = "x86" }
        5 { $Global:ArchString = "ARM" }
        6 { $Global:ArchString = "ia64" }
        9 { $Global:ArchString = "x64" }
        12 { $Global:ArchString = "ARM64" }
        default {}
    }
} catch {
    Write-Warning "无法获取架构信息: $($_.Exception.Message)"
}

Write-Host "处理器架构: $Global:ArchString"
if (($Global:Arch -ne 9) -and ($Global:Arch -ne 12)) {
    Write-Warning "设备架构可能不支持，ID：$Global:Arch"
}
if ($null -eq $Global:ArchString) {
    Write-Error "未知架构，暂不支持..."
    Confirm-ExitWithEnter 1
}

$Global:HypervisorPresent = Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -ExpandProperty HypervisorPresent
$Global:VirtualizationFirmwareEnabled = Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty VirtualizationFirmwareEnabled
if ($Global:HypervisorPresent -or $Global:VirtualizationFirmwareEnabled) {
    Write-Host "虚拟化状态：已启用"
} else {
    Write-Host "虚拟化状态：未启用或不支持"
    Write-Warning "可能会导致后续步骤失败（未验证）"
}


Write-Warning "NekroAgent 将安装在 '$InstallPath'"
$userConfirmation = Read-Host -Prompt "是否继续安装？ (y/N)"
if ($userConfirmation.ToLower() -ne 'y') {
    Exit
}

# 确保功能启用
if (-not $WSLStatus.Enabled) {
    Install-Wsl
    if ($Global:RebootNeeded) {
        Write-Host "--------------------------------------------------------------------"
        Write-Host "WSL 安装成功"
        Write-Host "Windows 功能更改需要重启计算机才能生效。"
        Write-Host "请保存所有工作并重启您的计算机。" -ForegroundColor RED
        Write-Host "重启后，请再次以管理员身份运行此脚本以完成 WSL2 的配置。"
        Write-Host "--------------------------------------------------------------------"
        Confirm-ExitWithEnter
    }
} else {
    Write-Host "WSL 已安装"
}

# 更新 WSL
Write-Host "正在更新 WSL (此过程可能需要几分钟)..."
$output =  wsl --update
if ($LASTEXITCODE -eq 0) {
    Write-Host "WSL 内核已更新 (或已是最新)。"
} else {
    Write-Host "WSL 内核更新失败。错误详情: $output" -ForegroundColor RED
    Write-Host "可能原因: 网络连接问题，或 WSL 组件需要修复。" -ForegroundColor RED
    # 考虑脚本处理
    Write-Warning "建议: 尝试手动从以下链接下载并安装 WSL2 Linux 内核更新包："
    Write-Warning "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    Write-Warning "安装后再尝试手动运行 'wsl --update' 命令。"
}

# 设置 WSL 默认版本为 2
Write-Host "正在设置 WSL 默认版本为 2..."
$output = wsl --set-default-version 2
if ($LASTEXITCODE -eq 0) {
    Write-Host "WSL 默认版本已成功设置为 2。"
} else {
    Write-Host "设置 WSL 默认版本为 2 失败。错误输出: $output" -ForegroundColor RED
    Write-Warning "常见原因："
    Write-Warning "  - WSL 内核未成功安装或更新 (请检查上一步 'wsl --update' 的结果)。"
    Write-Warning "  - 您的 Windows 版本可能不支持 WSL2 或未完全更新。"
    Write-Warning "  - 请确保在 BIOS/UEFI 中已启用 CPU 虚拟化技术 (如 Intel VT-x 或 AMD-V)。"
}

if (-not (Test-Path -Path $WorkDir -PathType Container)) {
    try {
        New-Item -ItemType Directory -Path $WorkDir -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-Error "无法创建工作目录 '$WorkDir'。错误信息: $($_.Exception.Message)"
        return $null
    }
}

# 获取 tarball 文件
try {
    $result = Download-WslDistroZip -AkaMsLink $DebianLink -OutputFilePath $DistroFilePath
    if (-not $result) {
        Throw "文件下载失败：'$DebianLink'"
    }
    $result = Extract-FileFromArchive -ArchivePath "$DistroFilePath" -EntryPathRegexPattern ".*_${Global:ArchString}.appx" -DestinationFilePath "$AppxFilePath"
    if (-not $result) {
        Throw "文件提取失败"
    }
    $result = Extract-FileFromArchive -ArchivePath "$AppxFilePath" -EntryPathRegexPattern "install.tar.gz" -DestinationFilePath "$TarballFilePath"
    if (-not $result) {
        Throw "文件提取失败：'install.tar.gz'"
    }
} catch {
    $($_.Exception.Message)
}

# 导入 WSL
$output = wsl.exe --import $DistroName $DistroInstallLocation $TarballFilePath 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "WSL 发行版 '$DistroName' 导入成功。" -ForegroundColor Green
} else {
    Write-Error "WSL 发行版 '$DistroName' 导入失败!"
    Write-Host "--- 失败原因 (来自 wsl.exe 输出) ---" -ForegroundColor Yellow
    if ($output) {
        $output | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Red
        }
    }
    Confirm-ExitWithEnter 1
}

# 定制
$newUserName = "nekro"
$createUserCommand = "useradd -m -s /bin/bash $newUserName && echo '${newUserName}:123456' | chpasswd"
$addToSudoCommand = "usermod -aG sudo $newUserName"

Write-Host "正在创建 'nekro' 用户，密码 123456"
Invoke-WslCommand -DistributionName $DistroName -Command $createUserCommand
Write-Host "正在将用户 'nekro' 添加至 sudo"
Invoke-WslCommand -DistributionName $DistroName -Command $addToSudoCommand

$wslConfContent = @"
[user]
default=$newUserName

[network]
hostname = Nekro-Agent

[interop]
enable = true
appendWindowsPath = false

[boot]
systemd = true
"@
$setWslConfCommand = "echo `'$wslConfContent`' | tee /etc/wsl.conf"
$setWslConfCommand = $setWslConfCommand -replace "`r`n", "`n"
Write-Host "正在写入 '/etc/wsl.conf'"
Invoke-WslCommand -DistributionName $DistroName -Command $setWslConfCommand

$null = wsl --terminate $DistroName

Write-Host "--------------------------------------------------------------------"
Write-Host "nekro-agent 已安装成功。"
Write-Host "可使用 'wsl -d nekro-agent' 启动"
Write-Host "用户 nekro 的密码为 123456"
Write-Host "若安装过程遇到错误请重新执行脚本"
Write-Host "或前往 Github/QQ 反馈"
Write-Host "--------------------------------------------------------------------"

Read-Host "脚本执行完毕。按 Enter 键关闭此窗口..."
