$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required but was not found on PATH."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$commonConfig = Join-Path $repoRoot "common/gitconfig"
$platformConfig = Join-Path $repoRoot "windows/gitconfig"
$localConfig = Join-Path $repoRoot "local/gitconfig"
$localExample = Join-Path $repoRoot "local/gitconfig.example"
$globalIgnoreSource = Join-Path $repoRoot "common/gitignore"
$globalIgnoreTarget = Join-Path $HOME ".gitignore"

if (-not (Test-Path $localConfig)) {
    Copy-Item $localExample $localConfig
    Write-Host "Created $localConfig"
}

function Remove-GitInclude {
    param([string]$Path)

    & git config --global --fixed-value --unset-all include.path $Path 2>$null
}

foreach ($configPath in @($commonConfig, $platformConfig, $localConfig)) {
    Remove-GitInclude $configPath
    & git config --global --add include.path $configPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to add Git include: $configPath"
    }
}

if (-not (Test-Path $globalIgnoreTarget)) {
    Copy-Item $globalIgnoreSource $globalIgnoreTarget
    Write-Host "Copied global ignore rules to $globalIgnoreTarget"
}
else {
    Write-Host "Kept existing $globalIgnoreTarget; merge common/gitignore manually if wanted."
}

Write-Host "Installed common, Windows, and local Git configuration."
Write-Host "Verify with: git config --global --includes --show-origin --list"
