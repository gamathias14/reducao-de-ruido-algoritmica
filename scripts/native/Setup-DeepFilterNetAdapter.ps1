[CmdletBinding()]
param(
    [string]$CacheRoot = (Join-Path $HOME ".cache\ptc3527-benchmark"),
    [string]$SystemPython = "python"
)

$ErrorActionPreference = "Stop"
$version = "0.5.6"
$sourceCommit = "978576aa8400552a4ce9730838c635aa30db5e61"
$modelArchiveSha256 = "49C52EDC8947AE1F9BF50D81530BEAF3A2C3245AEAF34B6F31FF535CD22284D2"
$venv = Join-Path $CacheRoot "deepfilternet-0.5.6-venv"
$modelRoot = Join-Path $CacheRoot "deepfilternet-v0.5.6"
$modelArchive = Join-Path $modelRoot "DeepFilterNet3.zip"
$modelDir = Join-Path $modelRoot "DeepFilterNet3"
$sourceDir = Join-Path $CacheRoot "deepfilternet-source-v0.5.6"

New-Item -ItemType Directory -Force -Path $CacheRoot, $modelRoot | Out-Null
if (-not (Test-Path (Join-Path $sourceDir ".git"))) {
    git clone --branch "v$version" --depth 1 `
        https://github.com/Rikorose/DeepFilterNet.git $sourceDir
}
$actualCommit = (git -C $sourceDir rev-parse HEAD).Trim()
if ($actualCommit -ne $sourceCommit) {
    throw "Commit DeepFilterNet inesperado: $actualCommit"
}

if (-not (Test-Path $modelArchive)) {
    Invoke-WebRequest `
        -Uri "https://github.com/Rikorose/DeepFilterNet/raw/v$version/models/DeepFilterNet3.zip" `
        -OutFile $modelArchive
}
$actualModelHash = (Get-FileHash $modelArchive -Algorithm SHA256).Hash
if ($actualModelHash -ne $modelArchiveSha256) {
    throw "Hash do modelo DeepFilterNet3 inesperado: $actualModelHash"
}
if (-not (Test-Path $modelDir)) {
    Expand-Archive -LiteralPath $modelArchive -DestinationPath $modelRoot
}

& $SystemPython -m venv --system-site-packages --upgrade $venv
$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check `
    --only-binary=:all: "deepfilternet==$version"
if ($LASTEXITCODE -ne 0) {
    throw "Instalacao DeepFilterNet falhou com codigo $LASTEXITCODE"
}
& $venvPython -m pip install --disable-pip-version-check `
    --only-binary=:all: "torchaudio==2.0.2" `
    --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    throw "Instalacao torchaudio falhou com codigo $LASTEXITCODE"
}

& $venvPython -c (
    "import torch, torchaudio, df, libdf; " +
    "assert torch.__version__ == '2.0.1+cpu'; " +
    "assert torchaudio.__version__ == '2.0.2+cpu'"
)
if ($LASTEXITCODE -ne 0) {
    throw "Validacao do ambiente DeepFilterNet falhou"
}

$checkpoint = Join-Path $modelDir "checkpoints\model_120.ckpt.best"
$config = Join-Path $modelDir "config.ini"
$libdf = Join-Path $venv "Lib\site-packages\libdf\libdf.cp311-win_amd64.pyd"
[ordered]@{
    source_commit = $actualCommit
    model_archive_sha256 = $actualModelHash
    checkpoint_sha256 = (Get-FileHash $checkpoint -Algorithm SHA256).Hash
    config_sha256 = (Get-FileHash $config -Algorithm SHA256).Hash
    libdf_sha256 = (Get-FileHash $libdf -Algorithm SHA256).Hash
    python = $venvPython
    model_dir = $modelDir
} | ConvertTo-Json
