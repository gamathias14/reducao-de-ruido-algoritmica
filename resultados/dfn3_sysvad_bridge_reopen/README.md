# DFN3/SYSVAD bridge reopen - R14

Data: 2026-07-01

## Escopo

Reabertura controlada da ponte PCM v1 real dentro do clone
`PTC3527-SYSVAD-LAB-FAST`, ainda sem DeepFilterNet3 dentro da VM e sem
alterar driver/SYSVAD.

O host fisico permaneceu sem instalacao de driver, sem TESTSIGNING, sem
alteracao de BIOS, Secure Boot, Hyper-V ou configuracao de boot.

## Preflight

O preflight read-only passou usando o runtime externo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Test-VmAutomationPreflight.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -OrchestratorPath scripts\vm\Invoke-HostPacedPcmVm.ps1 -AudioRun
```

Resultado:

- `ready=true`;
- falhas `0`;
- warnings `0`;
- clone em `poweroff`;
- snapshot `checkpoint45-causal-wpt-validated`;
- `audio_in=on`;
- clipboard e drag-and-drop desabilitados;
- NIC1 em NAT.

## Ajuste operacional

`scripts\vm\Invoke-HostPacedPcmVm.ps1` e
`scripts\vm\guest\Invoke-HostPacedEndpointScenario.ps1` foram ajustados para
nao exigir a DLL `ptc3527-rnnoise-v0.2.dll` em cenarios que usam apenas
`bypass`. Isso remove uma dependencia falsa da bancada minima de ponte real; os
cenarios RNNoise continuam exigindo a DLL e o hash congelado.

Validacao:

```powershell
# parse PowerShell limpo nos dois scripts
```

## Rodada EndpointDiagnostic

Comando:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointDiagnostic -DurationSeconds 20
```

Run:

```text
resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-101012-host-paced-endpointdiagnostic
```

Resultado host:

- `succeeded=true`;
- `bridge_exercised=true`;
- `pipeline_modified=false`;
- host default capture unchanged `true`;
- clone final em `poweroff`;
- snapshot restaurado para `checkpoint45-causal-wpt-validated`.

Integridade do transporte ate o cliente:

- servidor: `1000` blocos;
- cliente: `1000/1000` blocos;
- erro de sequencia `0`;
- erro de CRC `0`;
- erro de framing `0`;
- processamento bypass p99 `1,728 ms`, max `5,235 ms`.

Ponte real:

- blocos submetidos ao writer: `1000`;
- blocos enviados/aceitos pela ponte: `831/831`;
- drops locais: `169`;
- write errors `0`;
- rejected requests `0`;
- sequence errors do driver `0`;
- underruns reportados pelo driver: `147`;
- classificacao do gate: `transient_scheduling_pauses_with_queue_overflow`.

Interpretacao: a ponte real abriu e aceitou blocos sem erro de contrato, mas a
cadencia em VM gerou pausas transitórias e overflow da fila local. A rodada nao
promove tempo real.

## Rodada EndpointCaptureEvent

Comando:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointCaptureEvent -DurationSeconds 20
```

Run:

```text
resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-101500-host-paced-endpointcaptureevent
```

Resultado:

- `succeeded=true`;
- clone final restaurado para `poweroff` no snapshot aprovado;
- gate `completed`;
- classificacao `capture_event_not_confirmed`.

Resumo por perna:

| cenario | estrategia captura | enviados/1000 | drops | underruns driver |
|---|---:|---:|---:|---:|
| `01-yield-control-a` | `yield` | `998` | `2` | `33` |
| `02-event-a` | `event` | `953` | `47` | `124` |
| `03-event-b` | `event` | `969` | `31` | `67` |
| `04-yield-control-b` | `yield` | `998` | `2` | `23` |

Interpretacao: a estrategia event-driven do capturador nao foi confirmada como
melhoria nesta repeticao; as pernas `event` foram piores que os controles
`yield`.

## Rodada EndpointScheduling

Comando:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointScheduling -DurationSeconds 20
```

Run:

```text
resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-102253-host-paced-endpointscheduling
```

Resultado:

- `succeeded=true`;
- clone final restaurado para `poweroff` no snapshot aprovado;
- gate `completed`;
- classificacao `writer_wakeup_mitigated_consumer_cadence_deficit_remains`.

Resumo por perna:

| cenario | writer | enviados/1000 | drops | underruns driver |
|---|---:|---:|---:|---:|
| `01-baseline-a` | `normal` | `867` | `133` | `165` |
| `02-mitigated-a` | `mmcss` | `961` | `39` | `141` |
| `03-mitigated-b` | `mmcss` | `973` | `27` | `122` |
| `04-baseline-b` | `normal` | `968` | `32` | `106` |

Interpretacao: MMCSS reduziu parte dos problemas de wakeup do writer, mas o
deficit de cadencia do consumidor/endpoint permaneceu. A ponte real nao deve
ser usada como gate de baixa latencia dentro desta VM VirtualBox/NEM.

## Decisao

- A ponte PCM v1 real foi reaberta com sucesso dentro do lab e aceitou blocos
  sem erros de sequencia, CRC, framing, rejeicao ou escrita.
- O gargalo observado nas rodadas esta em cadencia/scheduler/endpoint na VM,
  nao em corrupcao do protocolo.
- Nao acoplar DeepFilterNet3 a ponte real nesta VM como criterio de promocao de
  tempo real.
- Proximo passo recomendado: para testar a integracao final, usar uma
  instalacao Windows nativa/lab dedicada ou uma VM com garantias temporais
  melhores. Ate la, manter como aprovados apenas os gates host-native
  user-mode: R11, R12 e R13.
