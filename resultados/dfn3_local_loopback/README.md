# DFN3 local loopback baseline

Rodadas user-mode no Windows host, sem VM, sem driver, sem SYSVAD e sem
alterar BIOS/Secure Boot/Hyper-V. O servidor Python e o receptor nativo C++
rodaram no proprio host e comunicaram via TCP `127.0.0.1`.

Os artefatos foram gravados fora da arvore do OneDrive porque o receptor nativo
usa `argv` estreito no Windows e falhou ao criar diretorios quando o caminho
continha acentos. Isso nao afeta o transporte testado.

Artefatos:

```text
C:\PTC3527-Private\local_loopback_runs\
```

## Transport-only - 2026-07-01

Rodada:

```text
C:\PTC3527-Private\local_loopback_runs\20260701-020331-dfn3-local-loopback-transport-only
```

Parametros: TCP, `127.0.0.1`, receptor nativo, `sink=memory`,
`BlocksPerPacket=1`, sem ring/consumer.

Resultado:

- gate `accepted`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- receive p99 `10,152 ms`;
- receive max `11,052 ms`;
- stalls acima de `20/50/100 ms`: `0/0/0`;
- scheduler max `4,500 ms`.

Interpretacao: o transporte TCP host-local com receptor C++ passa sem stalls
relevantes quando VirtualBox/NEM e removido.

## Ring diagnostic - 2026-07-01

Rodada:

```text
C:\PTC3527-Private\local_loopback_runs\20260701-020131-dfn3-local-loopback-ring12-pre8-resync40
```

Parametros: TCP, `127.0.0.1`, receptor nativo, `sink=memory`,
`BlocksPerPacket=1`, `RingDiagnostic`, `RingCapacityBlocks=12`,
`RingPrebufferBlocks=8`, `RingResyncLatenessMs=40`,
`ConsumerWaitMode=waitable_timer`, `ConsumerThreadPriority=highest`,
`ReceiverProcessPriority=high`.

Resultado:

- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- receive p99 `10,153 ms`;
- receive max `10,819 ms`;
- stalls acima de `20/50/100 ms`: `0/0/0`;
- ring drops `0`;
- recoveries/underflows `0`;
- resyncs `0`;
- playout latency p99 `80,987 ms`;
- consumer deadline lateness p99 `0,977 ms`;
- consumer interval max `11,507 ms`;
- scheduler max `4,413 ms`.

Interpretacao: o mesmo receptor/ring que sofria drops e pausas dentro da VM
permanece estavel no Windows host em loopback local. Isso fortalece a conclusao
de que as falhas temporais observadas na VM vem do ambiente VirtualBox/NEM e nao
de corrupcao, framing, hash, ring ou cadencia basica do receptor nativo.

## Decisao

O baseline nativo separa o problema:

- codigo/transporte local: validado no host Windows em user-mode;
- VM VirtualBox/NEM: integridade funcional validada, mas baixa latencia nao
  confiavel por scheduler/rede do ambiente.

Nao acoplar DeepFilterNet3/SYSVAD com base em validacao temporal da VM. Para
proximos passos, usar o baseline nativo como ponto de partida para medir custo
do DFN3 inline em user-mode antes de qualquer retorno ao driver/SYSVAD.

Seguimento executado:

```text
resultados\dfn3_local_dfn_inline\README.md
```

A rodada DFN3 local worker/ring de 60 s passou com worker p99 `2,188 ms`,
worker max estavel `3,957 ms`, callback p99 `0,043 ms` e underflow `0`.
