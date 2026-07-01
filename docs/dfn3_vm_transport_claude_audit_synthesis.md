# Sintese da auditoria Claude - DFN3 VM transport

Data: 2026-07-01

Arquivo de entrada enviado ao Claude:

- `prompt_auditoria_claude_dfn3_vm_transport.md`

Resposta salva:

- `resposta_claude_auditoria_dfn3_vm_transport.md`

## Pontos confirmados

- A integridade funcional do transporte TCP nativo esta validada: blocos,
  sequencia, CRC, framing e hash permanecem corretos nas rodadas relevantes.
- O problema principal nao e corrupcao, mas timing.
- A auditoria destacou um ponto que estava subenfatizado: `consumer_interval_max`
  chegou a aproximadamente `1508 ms` em uma rodada recente, com
  `scheduler_probe_max` aproximadamente igual. Isso aponta para pausa ampla do
  ambiente convidado, nao apenas jitter de rede.
- A taxa de underflow/drops do ring nas rodadas recentes, tipicamente de 7% a
  13,5%, e incompatível com audio continuo.
- A rota host-only e diagnostica util: removeu `unaccounted_receive_or_nat` na
  rodada testada, mas ainda deixou stall `guest_scheduler_correlated`.
- O gate `check` em rodadas com ring e esperado por desenho, pois o ring
  diagnostico nunca deve ser promovido automaticamente.

## Ajustes de interpretacao

- Nao tratar diferencas de uma rodada para outra como prova estatistica de
  melhoria; a variabilidade run-to-run e alta.
- Dizer que afinidade/prioridade "melhorou" deve ficar limitado a "observou-se
  melhora naquela rodada", nao como conclusao geral.
- `unaccounted_receive_or_nat` deve ser tratado como bucket residual, nao como
  causa fechada.
- A latencia de playout com ring inclui prebuffer estrutural de 80 ms, entao
  nao deve ser lida como latencia pura do transporte.

## Decisao tecnica recomendada

Encerrar ou congelar a fase VM como:

> Integridade funcional validada; tempo real de baixa latencia inconclusivo ou
> descartado no VirtualBox/NEM por limitacao estrutural de scheduler/rede do
> ambiente.

Nao promover nenhuma configuracao de VM como validada para tempo real.
Nao acoplar DeepFilterNet3 dentro da VM/SYSVAD com base nesses resultados.

## Proximo experimento decisivo

Executar baseline nativo no host Windows, sem VM:

1. servidor Python envia para `127.0.0.1`;
2. receptor nativo C++ roda no host;
3. manter `sink=memory`, hash, trace, scheduler probe e, se possivel, ring
   diagnostico;
4. repetir pelo menos uma rodada inicial e, se passar, executar N=10 para
   baseline estatistico.

Critério de decisao:

- Se loopback nativo falhar com stalls/drops semelhantes, ha problema no codigo
  ou no host/sender que precisa ser corrigido.
- Se loopback nativo passar com `receive_max` baixo e drops aproximadamente
  zero, a fase VM pode ser encerrada com fundamento: o bloqueio era do
  ambiente VirtualBox/NEM.

## Resultado do experimento decisivo

O baseline nativo foi executado em 2026-07-01, em user-mode, sem VM, sem driver
e sem alteracao de BIOS/Secure Boot/Hyper-V.

Artefatos:

```text
C:\PTC3527-Private\local_loopback_runs\
```

Transport-only:

- rodada `20260701-020331-dfn3-local-loopback-transport-only`;
- gate `accepted`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- receive p99 `10,152 ms`;
- receive max `11,052 ms`;
- stalls acima de `20/50/100 ms`: `0/0/0`;
- scheduler max `4,500 ms`.

Ring diagnostic:

- rodada `20260701-020131-dfn3-local-loopback-ring12-pre8-resync40`;
- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- integridade perfeita;
- receive p99 `10,153 ms`;
- receive max `10,819 ms`;
- drops/recoveries/underflows/resyncs `0`;
- consumer interval max `11,507 ms`;
- scheduler max `4,413 ms`.

Conclusao apos o experimento: o baseline nativo passou. Portanto, a decisao de
congelar a fase VM fica fortalecida: os outliers observados na VM eram do
ambiente VirtualBox/NEM/scheduler/rede, nao uma falha basica do
transporte/receptor/ring.

## Experimentos VM que ainda podem valer, mas nao sao prioridade

- Rodada sem consumer/ring, `sink=memory`, para medir transporte puro.
- `FIONREAD` antes de `recv`, para confirmar batch delivery TCP.
- Host-only isolado sem prioridades extras, apenas se ainda houver duvida sobre
  a contribuicao do NAT.

Esses testes ajudam a explicar melhor a VM, mas nao mudam tanto a decisao quanto
o loopback nativo.

## Seguimento: DFN3 local inline

A etapa seguinte tambem foi executada em 2026-07-01, ainda no host Windows e em
user-mode. A bancada `wasapi_worker_bench` processou o input composto de `60 s`
com DeepFilterNet3 C API persistente em worker/ring.

Artefatos:

```text
tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\
resultados\dfn3_local_dfn_inline\README.md
```

Resultado estavel:

- gate `PASS`;
- worker p99 `2,188 ms`;
- worker p999 `2,598 ms`;
- worker max `3,957 ms`;
- callback p99 `0,043 ms`;
- underflow `0`;
- ring minimo antes do callback `480` amostras.

Conclusao complementar: alem do transporte local ter passado, o custo basico do
DeepFilterNet3 C API tambem passou em user-mode. Isso reforca que a VM nao deve
ser usada como criterio de baixa latencia para decidir se DFN3/SYSVAD e viavel.
