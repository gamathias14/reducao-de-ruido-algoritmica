# DFN3 PCM bridge simulator user-mode

Rodada R13 no host Windows, em user-mode, sem VM, sem driver, sem SYSVAD e sem
abrir a ponte PCM v1 real.

Objetivo: aproximar o fluxo final depois dos baselines R11/R12, alimentando um
simulador da ponte PCM v1 com a saida real do DeepFilterNet3 ja gerada pela
bancada nativa.

Fluxo testado:

```text
DFN3 output 48 kHz mono
-> conversao deterministica 48 kHz/480 para 16 kHz/320
-> PtcPcmBridgeClient + BridgePacedWriter
-> backend simulado PCM v1 em memoria
-> consumidor de driver simulado a cada 20 ms
```

## Escopo

- Host Windows, user-mode.
- Sem VM.
- Sem driver.
- Sem SYSVAD.
- Sem IOCTL real para a ponte PCM v1.
- Sem alteracao de BIOS, Secure Boot, Hyper-V, test-signing ou boot.
- A ponte real em `realtime_audio/ptc_pcm_bridge.py` foi apenas reutilizada como
  contrato de cliente; nao foi modificada.

## Artefatos

Principal:

```text
resultados\dfn3_pcm_bridge_simulator\
```

Arquivos:

- `summary.json`: gate, hashes, metricas do writer e do backend simulado;
- `submitted_blocks.csv`: cadencia de submissao ao writer;
- `bridge_input_pcm16_16k.wav`: payload PCM16 16 kHz enviado ao simulador.

Variantes diagnosticas:

```text
resultados\dfn3_pcm_bridge_simulator_depth2_queue16\
resultados\dfn3_pcm_bridge_simulator_depth6\
```

## Comandos

Rodada principal, mantendo o contrato historico da ponte em profundidade alvo
2 e fila local 4:

```powershell
python scripts/audio/dfn3_pcm_bridge_simulator.py --output-dir resultados\dfn3_pcm_bridge_simulator
```

Variantes:

```powershell
python scripts/audio/dfn3_pcm_bridge_simulator.py --output-dir resultados\dfn3_pcm_bridge_simulator_depth2_queue16 --bridge-target-depth 2 --bridge-user-queue 16 --submit-p99-limit-ms 35 --submit-max-limit-ms 120
python scripts/audio/dfn3_pcm_bridge_simulator.py --output-dir resultados\dfn3_pcm_bridge_simulator_depth6 --bridge-target-depth 6 --bridge-user-queue 16 --submit-p99-limit-ms 45 --submit-max-limit-ms 150
```

## Resultado principal

Configuracao:

- entrada: `tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\output_full_raw48.wav`;
- duracao: `60 s`;
- blocos DFN3 de origem: `6000` blocos de `480` amostras a 48 kHz;
- blocos PCM v1: `3000` blocos de `320` amostras a 16 kHz;
- `bridge_target_depth=2`;
- `bridge_user_queue=4`;
- `bridge_poll_interval_ms=2`;
- `timeBeginPeriod(1)` aplicado;
- prioridade do processo: `high`, aplicada;
- prioridade da thread de submissao: `highest`, aplicada;
- writer thread com MMCSS aplicado.

Gate:

```text
PASS
```

Metricas principais:

- blocos submetidos: `3000`;
- blocos enviados pelo writer: `3000`;
- blocos aceitos pelo backend simulado: `3000`;
- blocos consumidos no instante final do snapshot: `2998`;
- profundidade final do backend: `2` blocos;
- drops da fila de usuario: `0`;
- underruns: `0`;
- overruns: `0`;
- rejeicoes: `0`;
- erros de sequencia: `0`;
- hash aceito igual ao payload PCM16 esperado;
- submit interval p99: `20,172 ms`;
- submit interval max: `25,001 ms`;
- submit call p99: `0,107 ms`;
- profundidade media/p95/max: `1,5 / 2 / 2` blocos;
- residencia p95/max na fila de usuario: `2,743 / 3,368 ms`;
- latencia estimada de ponte: `42,743 ms`;
- consumer lateness p99/max: `2,537 / 2,810 ms`.

## Variantes diagnosticas

Depth2/fila16:

- gate `PASS`;
- blocos enviados/aceitos `3000/3000`;
- drops/underruns/overruns/rejeicoes/erros de sequencia: `0`;
- submit interval p99/max: `20,884 / 23,576 ms`;
- latencia estimada de ponte: `42,676 ms`;
- hash aceito correto.

Depth6/fila16:

- gate `PASS`;
- blocos enviados/aceitos `3000/3000`;
- drops/underruns/overruns/rejeicoes/erros de sequencia: `0`;
- profundidade p95/max: `6 / 6` blocos;
- latencia estimada de ponte: `122,759 ms`;
- hash aceito correto.

## Interpretacao

A rodada principal mostra que, fora da VM e sem driver real, a cadeia
`DFN3 48 kHz -> adaptacao para PCM v1 16 kHz -> writer da ponte -> consumidor
simulado` fecha 60 s sem perda, sem underrun e com integridade de payload. Isso
reduz o risco da etapa de empacotamento/pacing em user-mode.

O teste nao valida SYSVAD, WaveRT, PortCls, IOCTL real, endpoint de captura ou
latencia fisica ponta a ponta. Ele valida somente o proximo incremento seguro
antes de reabrir a ponte real: o contrato PCM v1 e o pacing user-mode em um
backend controlado.

## Decisao

- Manter a fase VM congelada como integridade funcional, nao baixa latencia.
- Considerar R13 aprovado como stub user-mode pre-ponte.
- Proximo passo recomendado: mapear uma bancada controlada com backend real da
  ponte PCM v1 apenas dentro da VM/lab, quando houver decisao explicita de
  reabrir SYSVAD/driver.
