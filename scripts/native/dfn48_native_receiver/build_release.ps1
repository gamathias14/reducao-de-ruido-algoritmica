$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$build = Join-Path $env:TEMP 'dfn48_native_receiver_build_nmake'
$binDir = Join-Path $root 'bin'
$exeDst = Join-Path $binDir 'dfn48_native_receiver.exe'
$vsBase = Join-Path ${env:ProgramFiles} 'Microsoft Visual Studio'
$vcvarsCandidates = @(
    (Join-Path $vsBase '18\Community\VC\Auxiliary\Build\vcvars64.bat'),
    (Join-Path $vsBase '17\Community\VC\Auxiliary\Build\vcvars64.bat')
)
$vcvars = $vcvarsCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

if ($vcvars) {
    New-Item -ItemType Directory -Force -Path $build | Out-Null
    cmd /c "`"$vcvars`" && cmake -S `"$root`" -B `"$build`" -G `"NMake Makefiles`" -DCMAKE_BUILD_TYPE=Release && cmake --build `"$build`""
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Copy-Item -Force (Join-Path $build 'dfn48_native_receiver.exe') $exeDst
} else {
    $gpp = (Get-Command g++ -ErrorAction Stop).Source
    & $gpp -std=c++17 -O2 -Wall -Wextra -Wpedantic `
        -DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -D_WINSOCK_DEPRECATED_NO_WARNINGS `
        -o $exeDst `
        (Join-Path $root 'src\main.cpp') `
        -lws2_32 -lbcrypt -lwinmm
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Built: $exeDst"
