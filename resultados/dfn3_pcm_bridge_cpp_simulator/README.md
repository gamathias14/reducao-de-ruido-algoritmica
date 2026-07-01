# DFN3 PCM bridge simulator C++ native - R15

Data: 2026-07-01

## Escopo

Bancada nativa C++ no host Windows, em user-mode, sem VM, sem driver, sem
SYSVAD e sem abrir a ponte PCM v1 real.

Objetivo: aproximar mais o fluxo final que o R13, removendo o pacing Python e
executando no mesmo processo:

```text
WAV 48 kHz -> DeepFilterNet3 C API persistente
-> worker thread + ring float 48 kHz
-> adaptacao 48 kHz/960 samples para PCM v1 16 kHz/320 samples
-> simulador de driver PCM v1 com target depth e consumidor a cada 20 ms
```

Esta rodada nao instala driver, nao modifica SYSVAD, nao altera BIOS, Secure
Boot, Hyper-V, TESTSIGNING ou configuracao de boot.

## Implementacao

Artefatos de bancada:

```text
scripts\native\dfn3_pcm_bridge_sim_bench\
```

Arquivos principais:

- `src\main.cpp`: bench C++ R15;
- `CMakeLists.txt`: build CMake/NMake;
- `build_release.ps1`: build Release via Visual Studio;
- `bin\dfn3_pcm_bridge_sim_bench.exe`: executavel gerado.

O bench reutiliza os componentes C++ ja existentes de carregamento da C API do
DeepFilterNet3 e leitura/escrita WAV, sem alterar o bench R12.

## Comandos

Build da fonte versionavel:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\native\dfn3_pcm_bridge_sim_bench\build_release.ps1
```

Smoke curto:

```powershell
scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe --max-bridge-blocks 100 --output-dir tmp\dfn3_pcm_bridge_cpp_smoke_versioned
```

Rodada principal:

```powershell
scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe --output-dir resultados\dfn3_pcm_bridge_cpp_simulator
```

Repeticao de confirmacao:

```powershell
scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe --output-dir resultados\dfn3_pcm_bridge_cpp_simulator_repeat1
```

## Artefatos

Rodada principal:

```text
resultados\dfn3_pcm_bridge_cpp_simulator\
```

Repeticao:

```text
resultados\dfn3_pcm_bridge_cpp_simulator_repeat1\
```

Arquivos por rodada:

- `summary.json`: gate, metricas DFN3, metricas de bridge e hash do payload;
- `worker_metrics.csv`: custo por frame DFN3 e espera no ring;
- `bridge_sim_metrics.csv`: escrita por bloco PCM v1, intervalo e profundidade;
- `bridge_input_pcm16_16k.wav`: payload PCM16 16 kHz submetido ao simulador.

## Smoke

A fonte versionavel em `scripts\native\dfn3_pcm_bridge_sim_bench\` tambem foi
validada com smoke de `100` blocos apos a copia mecanica do prototipo criado em
`tmp\`.

Smoke inicial do prototipo:

- gate `PASS`;
- blocos PCM v1 aceitos `100/100`;
- underruns `0`;
- profundidade final `2`;
- worker p99 `0,699 ms`;
- worker max `3,734 ms`.

Smoke da fonte versionavel:

- gate `PASS`;
- blocos PCM v1 aceitos `100/100`;
- underruns `0`;
- profundidade final `2`;
- worker p99 `0,753 ms`;
- worker max `0,787 ms`.

## Rodada principal

Resultado funcional:

- blocos PCM v1 esperados/aceitos: `3000/3000`;
- worker frames: `6000`;
- underruns `0`;
- overruns `0`;
- rejeicoes `0`;
- erros de sequencia `0`;
- profundidade final do simulador: `2`;
- profundidade maxima: `2`;
- hash PCM16:
  `144017e02a1731141f1abc0f44571f4c635a2cb24ef5af197922daf2773aa227`.

Metricas:

- wall time `59,966 s`;
- worker mean `1,028 ms`;
- worker p95 `2,543 ms`;
- worker p99 `2,943 ms`;
- worker p999 `3,851 ms`;
- worker max `11,786 ms`;
- frames acima de `4 ms`: `6`;
- frames acima de `8 ms`: `1`;
- frames acima de `10 ms`: `1`;
- bridge write p99 `0,002 ms`;
- bridge write max `0,178 ms`;
- bridge write interval p99 `20,261 ms`;
- bridge write interval max `20,766 ms`;
- consumer lateness p99/max `0,993 / 1,188 ms`.

Gate:

```text
CHECK
```

Motivo:

```text
worker_max_over_10ms
```

Interpretacao: a integridade, a cadencia da ponte simulada e a protecao por
ring passaram. O `CHECK` veio de um unico outlier bruto de processamento DFN3 no
frame `285`, com `11,786 ms`. Esse outlier foi absorvido pelo ring e nao gerou
underrun, drop, rejeicao, erro de sequencia ou erro de hash.

## Repeticao de confirmacao

Resultado:

- gate `PASS`;
- blocos PCM v1 aceitos `3000/3000`;
- worker frames `6000`;
- underruns `0`;
- overruns `0`;
- rejeicoes `0`;
- erros de sequencia `0`;
- profundidade final `2`;
- worker mean `1,060 ms`;
- worker p95 `2,583 ms`;
- worker p99 `3,093 ms`;
- worker p999 `3,807 ms`;
- worker max `6,234 ms`;
- frames acima de `4 ms`: `5`;
- frames acima de `8 ms`: `0`;
- frames acima de `10 ms`: `0`;
- bridge write interval p99/max `20,247 / 20,881 ms`;
- hash PCM16 igual ao da rodada principal.

## Decisao

R15 aprova o proximo ensaio adicional possivel sem instalar driver: DFN3 real
C++ nativo, worker/ring e simulador PCM v1 com consumidor de `20 ms`. A rodada
principal mostrou um outlier bruto isolado de scheduler/CPU acima de `10 ms`,
mas sem impacto funcional; a repeticao passou no gate rigido.

Com R11, R12, R13 e R15, nao ha evidencia para atribuir risco principal ao
protocolo local, ao custo basico do DFN3, ao ring user-mode ou ao empacotamento
PCM v1 simulado. O proximo salto que valida SYSVAD/ponte real de ponta a ponta
continua dependendo de uma instalacao Windows nativa/lab dedicada ou de um
ambiente virtual com garantias temporais melhores.
