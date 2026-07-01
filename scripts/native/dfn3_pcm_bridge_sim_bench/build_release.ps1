$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$build = Join-Path $env:TEMP 'dfn3_pcm_bridge_sim_bench_scripts_build_nmake'
$binDir = Join-Path $root 'bin'
$exeSrc = Join-Path $build 'dfn3_pcm_bridge_sim_bench.exe'
$exeDst = Join-Path $binDir 'dfn3_pcm_bridge_sim_bench.exe'
$vsBase = Join-Path ${env:ProgramFiles} 'Microsoft Visual Studio'
$vcvars = Join-Path $vsBase '18\Community\VC\Auxiliary\Build\vcvars64.bat'

if (!(Test-Path $vcvars)) {
    throw "vcvars64.bat not found: $vcvars"
}

New-Item -ItemType Directory -Force -Path $build | Out-Null
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

cmd /c "`"$vcvars`" && cmake -S `"$root`" -B `"$build`" -G `"NMake Makefiles`" -DCMAKE_BUILD_TYPE=Release && cmake --build `"$build`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Copy-Item -Force $exeSrc $exeDst
Write-Host "Built: $exeDst"
