# Build external\dist\node_launcher.exe and external\dist\reader.exe

$ErrorActionPreference = "Stop"

$ExternalDir = $PSScriptRoot
$ProjectDir = Split-Path -Parent $ExternalDir
$DistDir = Join-Path $ExternalDir "dist"
$BuildDir = Join-Path $ExternalDir "build"
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"

# Project files each .exe needs, as "source;folder inside the .exe".
# The servers and the benchmark load these by path, so they ship as data.
$NodeFiles = @(
    "Origin\app.py;Origin",
    "Origin\files\*.bin;Origin\files",
    "edge\app_edge.py;edge",
    "edge\lru.py;edge",
    "edge\popularity.py;edge"
)

$ReaderFiles = @(
    "client\run_all_tests.py;client",
    "client\workload.py;client"
)

function Invoke-Tool($Command, $Arguments) {
    # These tools log to stderr, so judge them by their exit code only
    $ErrorActionPreference = "Continue"

    & $Command @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Failed with exit code ${LASTEXITCODE}: $Command $Arguments"
    }
}

function Build-Exe($Name, $ProjectFiles) {

    Write-Host "`n=== Building $Name.exe ===" -ForegroundColor Cyan

    $arguments = @(
        "-B", "-m", "PyInstaller",
        "--onefile", "--console", "--noconfirm", "--clean",
        "--name", $Name,
        "--distpath", $DistDir,
        "--workpath", $BuildDir,
        "--specpath", $BuildDir
    )

    foreach ($entry in $ProjectFiles) {
        $arguments += "--add-data", "$ProjectDir\$entry"
    }

    $arguments += Join-Path $ExternalDir "$Name.py"

    Invoke-Tool $Python $arguments
}

if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment in $VenvDir"
    Invoke-Tool "python" @("-m", "venv", $VenvDir)
}

Write-Host "Installing build requirements..."
Invoke-Tool $Python @(
    "-m", "pip", "install",
    "-r", (Join-Path $ExternalDir "requirements_external.txt")
)

Build-Exe "node_launcher" $NodeFiles
Build-Exe "reader" $ReaderFiles

Write-Host "`nBuild succeeded:" -ForegroundColor Green

foreach ($name in "node_launcher", "reader") {
    $exe = Get-Item (Join-Path $DistDir "$name.exe")
    Write-Host ("  {0}  ({1:N1} MB)" -f $exe.FullName, ($exe.Length / 1MB))
}
