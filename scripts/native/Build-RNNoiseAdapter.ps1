[CmdletBinding()]
param(
    [string]$CacheRoot = (Join-Path $HOME ".cache\ptc3527-benchmark"),
    [string]$GccPath = "C:\Program Files\GNU Octave\Octave-9.2.0\mingw64\bin\gcc.exe",
    [switch]$RebuildExecutable,
    [switch]$RebuildLibrary
)

$ErrorActionPreference = "Stop"
$commit = "904a876dce1f9ab8860c0a5000ed151f9f6eef58"
$modelVersion = "0b50c45"
$modelSha256 = "4AC81C5C0884EC4BD5907026AAAE16209B7B76CD9D7F71AF582094A2F98F4B43"
$expectedExecutableSha256 = "6D35F2465B5A8C1E1E87F0F54418BFDF3F84D0105067E6204748987989ECF7CB"
$repo = Join-Path $CacheRoot "rnnoise-v0.2"
$outputDir = Join-Path $CacheRoot "bin"
$output = Join-Path $outputDir "ptc3527-rnnoise-v0.2.exe"
$library = Join-Path $outputDir "ptc3527-rnnoise-v0.2.dll"
$wrapper = Join-Path $PSScriptRoot "rnnoise_adapter.c"
$realtimeWrapper = Join-Path $PSScriptRoot "rnnoise_realtime_adapter.c"

New-Item -ItemType Directory -Force -Path $CacheRoot, $outputDir | Out-Null
if (-not (Test-Path $repo)) {
    git clone --branch v0.2 --depth 1 https://github.com/xiph/rnnoise.git $repo
}
$actualCommit = (git -C $repo rev-parse HEAD).Trim()
if ($actualCommit -ne $commit) {
    throw "RNNoise commit inesperado: $actualCommit"
}

$archiveName = "rnnoise_data-$modelVersion.tar.gz"
$archive = Join-Path $repo $archiveName
if (-not (Test-Path $archive)) {
    Invoke-WebRequest `
        -Uri "https://media.xiph.org/rnnoise/models/$archiveName" `
        -OutFile $archive
}
$actualModelHash = (Get-FileHash $archive -Algorithm SHA256).Hash
if ($actualModelHash -ne $modelSha256) {
    throw "Hash do modelo RNNoise inesperado: $actualModelHash"
}
if (-not (Test-Path (Join-Path $repo "src\rnnoise_data.c"))) {
    tar -xf $archive -C $repo
}
if (-not (Test-Path $GccPath)) {
    throw "GCC nao encontrado em $GccPath"
}

$sources = @(
    $wrapper,
    "src\denoise.c",
    "src\rnn.c",
    "src\pitch.c",
    "src\kiss_fft.c",
    "src\celt_lpc.c",
    "src\nnet.c",
    "src\nnet_default.c",
    "src\parse_lpcnet_weights.c",
    "src\rnnoise_data.c",
    "src\rnnoise_tables.c"
)
Push-Location $repo
try {
    if ($RebuildExecutable -or -not (Test-Path $output)) {
        & $GccPath `
            -O3 `
            -DNDEBUG `
            -DRNNOISE_BUILD `
            -Iinclude `
            -Isrc `
            @sources `
            -o $output `
            -lm
        if ($LASTEXITCODE -ne 0) {
            throw "Compilacao RNNoise falhou com codigo $LASTEXITCODE"
        }
    }
    elseif ((Get-FileHash $output -Algorithm SHA256).Hash -ne $expectedExecutableSha256) {
        throw (
            "Executavel RNNoise existente diverge do artefato aprovado. " +
            "Use -RebuildExecutable somente para uma nova auditoria."
        )
    }
    if ($RebuildLibrary -or -not (Test-Path $library)) {
        & $GccPath `
            -O3 `
            -DNDEBUG `
            -DRNNOISE_BUILD `
            -DDLL_EXPORT `
            -shared `
            -Iinclude `
            -Isrc `
            $realtimeWrapper `
            @($sources | Where-Object { $_ -ne $wrapper }) `
            -o $library `
            -lm
        if ($LASTEXITCODE -ne 0) {
            throw "Compilacao da DLL RNNoise falhou com codigo $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}

$binaryHash = (Get-FileHash $output -Algorithm SHA256).Hash
$libraryHash = (Get-FileHash $library -Algorithm SHA256).Hash
[ordered]@{
    source_commit = $actualCommit
    model_version = $modelVersion
    model_archive_sha256 = $actualModelHash
    executable = $output
    executable_sha256 = $binaryHash
    executable_matches_approved_hash = ($binaryHash -eq $expectedExecutableSha256)
    library = $library
    library_sha256 = $libraryHash
} | ConvertTo-Json
