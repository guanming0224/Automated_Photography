[CmdletBinding()]
param(
    [string]$PythonExe = "",
    [string]$AppName = "AutomatedPhotography",
    [switch]$SkipInstall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$AppSrc = Join-Path $ProjectRoot "app\src"
$EntryPoint = Join-Path $AppSrc "automated_photography\main.py"
$IconPath = Join-Path $ProjectRoot "picture\picture.ico"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
$DistPath = Join-Path $ProjectRoot "dist"
$BuildPath = Join-Path $ProjectRoot "build"
$SpecPath = $BuildPath

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function New-PythonCommand {
    param(
        [string]$Command,
        [string[]]$Arguments = @()
    )

    return @{
        Command = $Command
        Arguments = @($Arguments)
    }
}

function Resolve-PythonCommand {
    if (-not [string]::IsNullOrWhiteSpace($PythonExe)) {
        $resolved = Get-Command $PythonExe -ErrorAction SilentlyContinue
        if ((Test-Path -LiteralPath $PythonExe) -or $resolved) {
            return New-PythonCommand -Command $PythonExe
        }
        throw "Python executable not found: $PythonExe"
    }

    $preferredPython = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\python.exe"
    if (Test-Path -LiteralPath $preferredPython) {
        return New-PythonCommand -Command $preferredPython
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return New-PythonCommand -Command $pyLauncher.Source -Arguments @("-3.14")
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return New-PythonCommand -Command $pythonCommand.Source
    }

    throw "No Python executable found. Pass -PythonExe with a full path."
}

function Invoke-SelectedPython {
    param(
        [string[]]$Arguments
    )

    $allArguments = @()
    $allArguments += $script:PythonCommand["Arguments"]
    $allArguments += $Arguments

    & $script:PythonCommand["Command"] @allArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

Assert-PathExists -Path $AppSrc -Label "Application source directory"
Assert-PathExists -Path $EntryPoint -Label "Application entry point"
Assert-PathExists -Path $IconPath -Label "Application icon"
Assert-PathExists -Path $RequirementsPath -Label "Requirements file"

$script:PythonCommand = Resolve-PythonCommand

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onefile",
    "--name", $AppName,
    "--icon", $IconPath,
    "--paths", $AppSrc,
    "--distpath", $DistPath,
    "--workpath", $BuildPath,
    "--specpath", $SpecPath,
    $EntryPoint
)

Write-Host "Project root: $ProjectRoot"
Write-Host "Python: $($script:PythonCommand["Command"]) $($script:PythonCommand["Arguments"] -join ' ')"
Write-Host "Icon: $IconPath"
Write-Host "App source: $AppSrc"

if ($DryRun) {
    Write-Host "Dry run only. PyInstaller arguments:"
    $pyInstallerArgs | ForEach-Object { Write-Host "  $_" }
    exit 0
}

if (-not $SkipInstall) {
    Write-Host "Installing requirements..."
    Invoke-SelectedPython -Arguments @("-m", "pip", "install", "-r", $RequirementsPath)
}

Write-Host "Building executable..."
Invoke-SelectedPython -Arguments $pyInstallerArgs

$outputExe = Join-Path $DistPath ($AppName + ".exe")
if (Test-Path -LiteralPath $outputExe) {
    Write-Host "Build completed: $outputExe"
} else {
    throw "Build finished, but output executable was not found: $outputExe"
}
