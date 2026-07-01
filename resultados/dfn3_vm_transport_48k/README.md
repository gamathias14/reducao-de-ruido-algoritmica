# VM-DFN3-TRANSPORT-48K

Data: 2026-06-29

## Escopo

Esta rodada validou somente o transporte host -> guest para o candidato
DeepFilterNet3, sem SYSVAD, sem ponte PCM v1, sem driver e sem RNNoise.

Caminho testado:

```text
host WAV B3 48 kHz PCM16 mono
-> TCP/NAT host-paced
-> guest receiver
-> WAV reconstruido + JSON/hash/traces
```

Input:

```text
tmp/dfn_native/wasapi_worker_bench/b3_inputs/mixed_60s_capi_input48.wav
```

O arquivo de audio nao foi copiado para o convidado. Apenas blocos enquadrados
foram transmitidos.

## Contrato

- formato: PCM16 little-endian;
- canais: mono;
- sample rate: `48.000 Hz`;
- frame: `480 samples`;
- duracao por bloco: `10 ms`;
- cadencia fisicamente coerente: `100 blocos/s`.

Observacao: o handoff citava simultaneamente `480 samples @ 48 kHz = 10 ms` e
`50 blocos/s`. Esses requisitos sao incompativeis. A rodada seguiu o contrato
do DeepFilterNet3 de 10 ms, portanto `100 blocos/s`.

## Artefatos

- `preflight_before.json`;
- `deployment_manifest.json`;
- `server.json`;
- `server_trace.json`;
- `client.json`;
- `client_trace.json`;
- `received.wav`;
- `received_payload_hash.json`;
- `vm_transport_gate.json`;
- `transport_summary.json`;
- `teardown_result.json`;
- `host_result.json`;
- `recovery_*`.

## Resultado

Classificacao final:

```text
check
```

Integridade do transporte:

- blocos enviados/recebidos: `6000/6000`;
- amostras reconstruidas: `2.880.000`;
- duracao reconstruida: `60,0 s`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- hash de payload origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- WAV reconstruido SHA-256:
  `ea70d6f888f089487e6277d7943576c215dfc331de710201dd90a001d1f668eb`.

Timing observado:

- envio host p99: `13,447 ms`;
- envio host max: `36,280 ms`;
- recepcao guest p99: `18,722 ms`;
- recepcao guest max: `442,938 ms`;
- stalls de recepcao acima de `100 ms`: `1`;
- rajadas abaixo de `5 ms`: `188`.

## Interpretacao

O gate nao foi rejeitado porque o transporte logico passou: nao houve perda,
duplicacao, CRC errado, framing errado, mudanca de duracao ou divergencia de
hash. A classificacao ficou em `check` porque houve jitter relevante de chegada
no convidado, incluindo uma lacuna de aproximadamente `443 ms` seguida de
rajadas compensatorias.

Esse resultado valida a integridade do canal para transportar exatamente o
payload DFN48, mas ainda nao promove a fase seguinte com processamento DFN
dentro da VM nem reabre SYSVAD. O proximo passo deve investigar/repetir o
transporte com instrumentacao de jitter antes de acoplar o motor ou endpoint.

## Teardown

O orquestrador automatico atingiu timeout aguardando `poweroff`, mas a matriz
experimental ja estava completa. A recuperacao posterior encontrou zero sessoes
ou processos Guest Control ativos, restaurou `checkpoint45-causal-wpt-validated`
e confirmou:

- VM em `poweroff`;
- snapshot atual `checkpoint45-causal-wpt-validated`;
- `audio_in=on`;
- clipboard desabilitado;
- drag-and-drop desabilitado;
- NIC NAT.

O timeout de teardown foi classificado como falha de automacao recuperada, nao
como falha de transporte.

## R2 jitter - 2026-06-29

A repeticao `runs/20260629-134254-dfn3-transport-48k-r2-jitter` manteve o gate em `check`.

Integridade continuou perfeita: `6000/6000` blocos, perda zero, sequencia zero, CRC zero, framing zero, WAV reconstruido com `60,0 s` e hash de payload `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

O jitter foi reproduzido: recepcao p99 `20,646 ms`, max `110,346 ms`, tres stalls acima de `50 ms` e um acima de `100 ms`. A nova sonda interna de scheduler do convidado registrou 37 gaps acima de `30 ms`, dois acima de `100 ms` e max `569,455 ms`. Apenas um dos tres stalls de recepcao acima de `50 ms` coincidiu com gap de scheduler acima de `30 ms` na mesma janela.

Interpretacao: o transporte logico esta integro, mas a cadencia segue em `check`. A causa do jitter parece mista ou incompletamente isolada entre host/send, scheduler do convidado e acumulacao TCP/NAT.

Teardown: o Windows convidado ficou preso em `Desligando`. Shutdown normal e ACPI nao concluiram; com autorizacao do usuario foi usado `VBoxManage controlvm poweroff`, seguido de restore imediato de `checkpoint45-causal-wpt-validated`. Estado final confirmado: `poweroff`, `audio_in=on`, clipboard/drag-and-drop desabilitados e NIC NAT.

## R4 host-send - 2026-06-29

A rodada `runs/20260629-141223-dfn3-transport-48k-r4-hostsend` manteve o gate em `check`, mas isolou melhor a causa do jitter.

O servidor host foi executado com prioridade `High`. O envio ficou limpo: p99 `10,015 ms`, max `10,532 ms`, lateness p99 `0,023 ms`, lateness max `0,542 ms`, sem stalls acima de `20 ms`.

A integridade permaneceu perfeita: `6000/6000` blocos, perda zero, sequencia zero, CRC zero, framing zero, WAV `60,0 s` e hash `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

O gate continuou `check` por recepcao no convidado: p99 `21,297 ms`, max `428,577 ms`, dois stalls acima de `50 ms` e um acima de `100 ms`. Os dois stalls ocorreram no `header_wait_ms`, com envio host normal no mesmo bloco e sem correlacao com gap de scheduler acima de `30 ms` na janela medida.

Classificacao conservadora: `guest_receive_or_nat_jitter`. Proxima etapa recomendada: isolar o caminho `recv`/NAT com receptor receive-only em memoria ou receptor nativo simples, ainda sem DeepFilterNet3, ponte PCM v1 ou SYSVAD.

## R5 receive-only - 2026-06-29

A rodada `runs/20260629-142556-dfn3-transport-48k-r5-receive-only` manteve o gate em `check`, mas confirmou que a escrita WAV nao era a causa principal dos stalls.

O cliente foi executado com `sink=memory`: validou sequencia, CRC, framing e hash sem gravar `received.wav` no loop. A integridade permaneceu perfeita: `6000/6000` blocos, perda zero, sequencia zero, CRC zero, framing zero e hash `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

O envio host continuou limpo com prioridade `High`: p99 `10,023 ms`, max `10,789 ms`, sem stall acima de `20 ms`.

A recepcao melhorou no p99 (`16,896 ms`), mas ainda teve dois stalls acima de `100 ms`, ambos concentrados em `header_wait_ms`: `473,633 ms` e `104,489 ms`. Payload read e CRC ficaram baixos. Os stalls nao coincidiram com gap de scheduler acima de `30 ms` na janela medida.

Classificacao atual: `guest_recv_or_nat_header_wait_jitter`.

Status de saude: a trilha esta saudavel. Nao ha corrupcao, perda, erro de contrato, regressao de snapshot ou envolvimento indevido de SYSVAD/RNNoise. O bloqueio restante e especifico da cadencia de transporte no recebimento/NAT, antes de qualquer DSP.

## R6 batch4 diagnostic - 2026-06-29

A rodada `runs/20260629-143939-dfn3-transport-48k-r6-batch4-diagnostic` manteve o gate em `check`. Esta rodada e diagnostica por design: o contrato logico continuou DFN48 (`480` amostras, `10 ms`, `100 blocos/s`), mas o transporte TCP empacotou `4` blocos por pacote para reduzir wakeups/NAT.

Integridade novamente perfeita: `6000/6000` blocos, perda zero, sequencia zero, CRC zero, framing zero, duracao logica `60,0 s` e hash `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

O host/send ficou limpo no nivel de pacote: p99 `40,020 ms`, max `40,513 ms`, lateness max `0,528 ms`. No convidado, o packet receive teve p99 `49,413 ms` e max `138,401 ms`. Ainda houve `15` stalls acima de `50 ms` e `1` acima de `100 ms`, concentrados em `header_wait_ms`.

Correlacao: `12/15` stalls acima de `50 ms` ficaram como `unaccounted_receive_or_nat`; `3/15` coincidiram com gap de scheduler do convidado. Nao houve stall correlacionado ao envio host.

Interpretacao: o batching reduziu o pior outlier visto na R5, mas nao removeu o jitter de recepcao. A causa restante continua antes do DSP e mais proxima do caminho `recv`/NAT/scheduler do convidado do que de WAV, CRC, hash, servidor host ou DeepFilterNet3.

Decisao: nao promover a fase a `accepted` por batching. O proximo passo saudavel e remover Python do receptor com um receptor nativo minimo ou testar transporte alternativo, ainda sem acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## R7 native receiver - 2026-06-29

Rodada valida:

```text
runs/20260629-150919-dfn3-transport-48k-r7-native-receiver
```

Objetivo: remover Python do receptor no convidado e medir `recv`/framing/hash
com um cliente nativo minimo. O servidor host continuou sendo
`scripts/audio/host_guest_pcm_stream_dfn48.py`, com prioridade `High`. O cliente
usou `ClientImplementation=Native`, `sink=memory`, `BlocksPerPacket=1`.

Observacao operacional: a tentativa anterior
`runs/20260629-150318-dfn3-transport-48k-r7-native-receiver` falhou antes do
transporte porque o primeiro build do receptor dependia do runtime MSVC no
convidado (`-1073741515`). O binario foi recompilado com runtime estatico
(`/MT`) e a tentativa abortada teve teardown limpo; ela nao e resultado de
transporte.

Preflight da rodada valida: `ready=true`, zero falhas e zero avisos, snapshot
`checkpoint45-causal-wpt-validated`, runtime
`C:\PTC3527-Private\vm_runtime`.

Classificacao final:

```text
check
```

Integridade:

- blocos enviados/recebidos: `6000/6000`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- duracao logica: `60,0 s`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- `received.wav` nao foi gerado na rodada valida porque `sink=memory` valida o
  payload por hash.

Timing:

- host/send p99: `10,018 ms`;
- host/send max: `10,482 ms`;
- host lateness max: `0,488 ms`;
- guest receive p99: `14,936 ms`;
- guest receive max: `186,643 ms`;
- stalls acima de `20 ms`: `7`;
- stalls acima de `50 ms`: `1`;
- stalls acima de `100 ms`: `1`.

Correlacao:

- o unico stall acima de `50 ms` ocorreu no bloco `2246`;
- `header_wait_ms`: `186,609 ms`;
- payload read: `0,023 ms`;
- CRC: `0,004 ms`;
- envio host no bloco: normal (`9,997 ms`);
- scheduler guest: sem gap acima de `30 ms` na janela;
- classificacao: `unaccounted_receive_or_nat`.

Interpretacao: o receptor nativo reduziu muito o jitter geral em relacao as
rodadas Python, mas nao eliminou totalmente o outlier de chegada. O problema
restante segue antes do DSP e mais proximo de `recv`/NAT/entrega TCP do
convidado do que de Python, WAV, CRC, hash, host/send ou DeepFilterNet3.

Teardown da rodada valida: limpo, VM em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados, NIC NAT, sem poweroff forcado.

Decisao: nao promover a fase. Ainda nao acoplar DeepFilterNet3 dentro da VM,
ponte PCM v1 ou SYSVAD. Proximo passo recomendado: transporte alternativo
diagnostico, preferencialmente UDP com sequencia/CRC/hash e jitter buffer
minimo, ou repeticao da R7 para medir variancia.

## R8 UDP diagnostic - 2026-06-29

Rodada:

```text
runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver
```

Objetivo: testar transporte alternativo diagnostico com dados em UDP, mantendo
o mesmo contrato logico DFN48: PCM16 mono 48 kHz, `480` amostras/bloco,
`10 ms/bloco`, `100 blocos/s`, `BlocksPerPacket=1`, `sink=memory`, sem SYSVAD,
sem ponte PCM v1, sem RNNoise e sem DeepFilterNet3 dentro da VM.

Implementacao: o controle continua em TCP para preambulo e ACK final; os blocos
PCM sao enviados por UDP com sequencia, CRC32 e hash SHA-256 no receptor nativo.
O gate marca UDP como diagnostico por design e nao permite promocao automatica
a `accepted`.

Validacoes antes da VM:

- `python -m compileall scripts/audio/host_guest_pcm_stream_dfn48.py scripts/audio/analyze_dfn48_vm_transport.py`;
- parse de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
- build nativo Release com runtime estatico (`/MT`);
- teste host-only UDP de `1 s`: `100/100` blocos, perda zero, sequencia zero,
  CRC zero, framing zero e hash origem/recebido igual;
- preflight VM: `ready=true`, `failures=0`, `warnings=0`, snapshot
  `checkpoint45-causal-wpt-validated`, runtime
  `C:\PTC3527-Private\vm_runtime`.

Classificacao final:

```text
check
```

Integridade:

- blocos enviados/recebidos: `6000/6000`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- duracao logica: `60,0 s`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- `received.wav` nao foi gerado porque `sink=memory` valida o payload por hash.

Timing:

- host/send p99: `10,044 ms`;
- host/send max: `10,387 ms`;
- host lateness max: `0,413 ms`;
- guest receive p99: `14,400 ms`;
- guest receive max: `70,537 ms`;
- stalls acima de `20 ms`: `14`;
- stalls acima de `50 ms`: `1`;
- stalls acima de `100 ms`: `0`;
- rajadas abaixo de `5 ms`: `71`.

Correlacao:

- o unico stall acima de `50 ms` ocorreu no bloco `5107`;
- `header_wait_ms`: `70,526 ms`;
- payload read: `0,000 ms` por datagrama UDP;
- CRC: `0,011 ms`;
- envio host no bloco: normal (`10,001 ms`, lateness `0,028 ms`);
- scheduler guest: sem gap acima de `30 ms` na janela;
- classificacao: `unaccounted_receive_or_nat`.

Interpretacao: UDP eliminou o outlier acima de `100 ms` visto na R7 TCP e
manteve integridade perfeita, mas ainda preservou um stall relevante antes do
DSP, classificado como `unaccounted_receive_or_nat`. Isso sugere que parte do
problema nao era exclusiva do framing TCP/Python, mas sim do caminho de entrega
NAT/guest receive ou de wakeups nao capturados pela sonda atual.

Teardown: limpo, VM em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados, NIC NAT, sem poweroff forcado.

Decisao: nao promover a fase. Ainda nao acoplar DeepFilterNet3 dentro da VM,
ponte PCM v1 ou SYSVAD. Proximo passo recomendado: repetir R8 para medir
variancia e/ou implementar um jitter buffer diagnostico minimo no receptor UDP
para separar atraso de chegada de viabilidade de consumo em cadencia de 10 ms.

## R8 jitter-buffer posthoc e repeticao UDP - 2026-06-29

O analyzer foi atualizado para incluir `jitter_buffer_diagnosis`, uma simulacao
posthoc baseada em `client_trace.json`. Ela testa buffers de
`1,2,4,6,8,12,16` blocos DFN48 e estima underflows de um consumidor ordenado a
cada `10 ms`.

Na primeira R8 UDP:

- run: `runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver`;
- max phase error: `58,789 ms`;
- buffer `1` bloco: `20` underflows;
- buffer `2` blocos: `8` underflows;
- buffer `4` blocos: `2` underflows;
- buffer `6` blocos (`60 ms`): `0` underflows.

Repeticao UDP:

```text
runs/20260629-190754-dfn3-transport-48k-r8-udp-native-receiver
```

Classificacao:

```text
rejected
```

Integridade:

- blocos recebidos: `5913/6000`;
- perdas: `87`;
- erros de sequencia: `1`;
- erros de CRC: `0`;
- erros de framing: `0`;
- hash recebido:
  `0af1b084a4f1e675b4bc5c77bc38fe934b55c68f023e9358adff588f3432bced`;
- hash origem:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

Timing:

- host/send p99: `10,018 ms`;
- host/send max: `13,107 ms`;
- guest receive p99: `17,813 ms`;
- guest receive max: `1554,858 ms`;
- stalls acima de `100 ms`: `1`;
- rajadas abaixo de `5 ms`: `241`.

Jitter buffer posthoc da repeticao:

- blocos observados: `5913`;
- max phase error: `1545,294 ms`;
- nenhum buffer testado ate `16` blocos absorveu;
- minimo teorico pelo maior atraso: `155` blocos, ainda sem recuperar os
  `87` datagramas ausentes.

Teardown da repeticao: houve falha do orquestrador na consulta final de
`VMState`, mas auditoria posthoc confirmou VM em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados, NIC NAT e sem poweroff forcado.

Conclusao: UDP puro fica descartado como caminho de promocao. Ele segue util
como diagnostico, mas a repeticao mostrou perda real de datagramas no caminho
NAT/guest receive. Proximo passo recomendado: transporte confiavel com recepcao
e consumo separados no convidado por fila/ring buffer, medindo backlog e
underflow.

## R9 TCP queue diagnostic - 2026-06-29

Foi adicionada fila diagnostica ao receptor nativo, com uma thread de recepcao
e uma consumer thread separada consumindo a cada `10 ms`.

Rodada valida:

```text
runs/20260629-193111-dfn3-transport-48k-r9-tcp-native-receiver-queue20-diagnostic
```

Classificacao:

```text
accepted
```

Integridade:

- blocos recebidos: `6000/6000`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

Fila/consumer:

- prebuffer: `20` blocos (`200 ms`);
- blocos consumidos: `6000`;
- underflows: `0`;
- profundidade minima antes do consumo: `1` bloco;
- profundidade media antes do consumo: `22,113` blocos;
- profundidade maxima antes do consumo: `105` blocos.

Timing:

- host/send p99: `10,042 ms`;
- host/send max: `10,551 ms`;
- guest receive p99: `13,794 ms`;
- guest receive max: `73,402 ms`;
- stalls acima de `50 ms`: `1`;
- stalls acima de `100 ms`: `0`.

Interpretacao: a arquitetura TCP confiavel com recepcao separada e fila absorveu
o jitter desta rodada sem perda e sem underflow. O prebuffer de `200 ms` e
diagnostico/conservador; ainda nao e alvo final para microfone em tempo real.

Tentativa abortada:

```text
runs/20260629-193509-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic
```

Objetivo: testar prebuffer de `8` blocos (`80 ms`). O servidor host falhou
aguardando ACK final (`TimeoutError: timed out`) e nao houve artefatos de
cliente/gate/hash. A tentativa nao deve ser usada como resultado experimental.
Recuperacao por ACPI shutdown, restore do snapshot 45, sem poweroff forcado.

Proximo passo: depurar a variante de menor prebuffer em host-only longo ou
adicionar telemetria de progresso no guest antes de nova VM com latencia menor.

## R9 progress telemetry e prebuffer sweep - 2026-06-29

O receptor nativo ganhou `progress.json` (`--progress-output`) e o orquestrador
ganhou `-GuestLaunchMode Start`, que inicia o receptor no convidado como
processo destacado e aguarda `guest_exit.json` antes de copiar artefatos.

Validacoes host-only:

- `runs/20260629-200210-dfn3-transport-48k-r9-local-tcp-native-receiver-queue8-progress`:
  queue8, gate `check`, `6000/6000`, underflows `0`;
- `runs/20260629-205039-dfn3-transport-48k-r9-local-tcp-native-receiver-queue6-progress`:
  queue6, gate `accepted`, `6000/6000`, underflows `0`.

Rodadas VM validas:

- `runs/20260629-204534-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  gate `accepted`, `6000/6000`, perda/seq/CRC/framing `0`, hash correto,
  guest receive p99 `16,784 ms`, max `38,016 ms`, prebuffer `80 ms`,
  underflows `0`, teardown limpo;
- `runs/20260629-205157-dfn3-transport-48k-r9-tcp-native-receiver-queue6-diagnostic`:
  gate `check`, integridade perfeita, guest receive max `187,201 ms`,
  `12` underflows com prebuffer `60 ms`, teardown limpo;
- `runs/20260629-205700-dfn3-transport-48k-r9-tcp-native-receiver-queue7-diagnostic`:
  gate `check`, integridade perfeita, guest receive max `147,170 ms`,
  `7` underflows com prebuffer `70 ms`, teardown limpo.

Tentativas nao experimentais:

- `runs/20260629-200352-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  modo `Run` falhou no fechamento da sessao Guest Control (`VERR_TIMEOUT`);
- `runs/20260629-202446-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  falha antes do transporte por chamada incorreta do `guestcontrol start`;
- `runs/20260629-203639-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  corrida de copia corrigida depois; havia ACK perfeito e `progress=completed`,
  mas sem `client.json`/gate.

Conclusao atual: `80 ms` e o menor prebuffer observado sem underflow na VM nesta
serie. `60 ms` e `70 ms` preservam integridade, mas nao sustentam consumo
continuo. Ainda nao usar SYSVAD, ponte PCM v1 ou DeepFilterNet3 dentro da VM.

## R9 queue8 repeat - 2026-06-29

Repeticao VM:

```text
runs/20260629-213620-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic
```

Classificacao:

```text
check
```

Integridade:

- blocos recebidos: `6000/6000`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

Timing e fila:

- host/send p99: `10,291 ms`;
- host/send max: `10,919 ms`;
- guest receive p99: `14,588 ms`;
- guest receive max: `184,038 ms`;
- stalls acima de `100 ms`: `1`;
- stall dominante: bloco `796`, `header_wait_ms=184,005 ms`, envio host normal;
- classificacao do stall: `unaccounted_receive_or_nat`;
- prebuffer `8` blocos (`80 ms`);
- underflows do consumer: `6`.

Teardown: Windows entrou em tela de atualizacao/desligamento e o orquestrador
usou `forced_poweroff`; a auditoria final confirmou VM em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Conclusao: queue8 nao deve ser promovido com base em uma unica rodada aceita. A
repeticao preservou integridade perfeita, mas um outlier de recepcao/NAT acima
de `100 ms` consumiu a margem de `80 ms` e gerou underflows. Ainda nao acoplar
DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD. Proximo passo recomendado:
tratar `80 ms` como candidato fragil, testar margem superior ou desenhar ring
buffer real com telemetria/backpressure antes do DSP.

## R9 queue12 - 2026-06-29

Tentativa operacional abortada:

```text
runs/20260629-224057-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic
```

Essa tentativa nao conta como experimento: falhou antes do transporte por
`Guest Additions or interactive logon did not become ready`, sem `server.json`,
`client.json`, traces, hash ou gate. A recuperacao deixou a VM em `poweroff` no
snapshot `checkpoint45-causal-wpt-validated`.

Rodada valida:

```text
runs/20260629-225852-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic
```

Classificacao:

```text
check
```

Integridade:

- blocos recebidos: `6000/6000`;
- perdas: `0`;
- erros de sequencia: `0`;
- erros de CRC: `0`;
- erros de framing: `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

Timing e fila:

- host/send p99: `10,035 ms`;
- host/send max: `10,279 ms`;
- guest receive p99: `17,611 ms`;
- guest receive max: `593,981 ms`;
- stalls acima de `100 ms`: `1`;
- stall dominante: bloco `2892`, `header_wait_ms=593,950 ms`, envio host normal;
- classificacao do stall: `unaccounted_receive_or_nat`;
- prebuffer `12` blocos (`120 ms`);
- underflows do consumer: `0`;
- profundidade minima/media/maxima: `1` / `13,713` / `75` blocos.

Teardown: limpo, sem poweroff forcado, VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Conclusao: queue12 sustentou playout sem underflow nessa rodada, mas o gate
permaneceu `check` por outlier de recepcao/NAT acima de `100 ms`. A profundidade
maxima de `75` blocos mostra que a fila diagnostica absorve jitter acumulando
latencia; por isso queue12 tambem nao deve ser promovido diretamente. Proximo
passo: desenhar ring buffer real com limite de profundidade, politica de
recuperacao/drop e telemetria de latencia antes do DSP.

## R10 ring buffer diagnostico host-only - 2026-06-30

Foi adicionada uma variante diagnostica de ring buffer real ao receptor nativo.
Ela e opt-in e nao altera os resultados R9:

- `--ring-diagnostic`;
- `--ring-capacity-blocks`;
- `--ring-prebuffer-blocks`;
- `-RingDiagnostic`, `-RingCapacityBlocks` e `-RingPrebufferBlocks` no
  orquestrador VM.

Politica do ring:

- capacidade fixa em blocos;
- consumer separado em cadencia de `10 ms`;
- overflow/atraso excessivo: `drop_oldest`;
- underflow: `recover_with_silence`;
- telemetria de fill level, drops, recoveries, underflows, latencia de playout
  e lateness do consumer.

Smoke host-only:

```text
tmp/dfn48_ring_local_smoke
```

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
`RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`.

Resultado:

- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- overflow drops `0`;
- recoveries/underflows `0`;
- fill minimo/media/maximo `1` / `8,994` / `9` blocos;
- latencia de playout p99 `81,603 ms`, max `82,142 ms`;
- consumer deadline lateness p99 `0,412 ms`, max `0,997 ms`.

Decisao: pronto para uma rodada VM conservadora, mas ainda sem promocao. A
rodada VM deve ser considerada `check` se houver qualquer drop, recovery,
underflow ou latencia acumulada no limite do ring.

## R10 ring buffer VM - 2026-06-30

Rodada:

```text
runs/20260630-222946-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-diagnostic
```

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
`RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
`ProgressIntervalBlocks=100`, `GuestLaunchMode=Start`.

Resultado:

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,180 ms`, max `10,569 ms`;
- guest receive p99 `13,822 ms`, max `70,085 ms`;
- stalls de recepcao acima de `100 ms`: `0`;
- ring overflow drops `103`;
- consumer recoveries/underflows `103`;
- profundidade maxima `12/12`;
- latencia de playout p99 `87,842 ms`, max `120,139 ms`;
- consumer deadline lateness p99 `152,040 ms`, max `394,744 ms`.

Interpretacao: a rodada confirmou integridade do transporte, mas o ring real
expos atraso do consumer no convidado. A simulacao posthoc indicava que
`80 ms` absorveria a chegada observada, mas o consumer real teve pausas de
scheduler e acordou atrasado, executando deadlines vencidos em rajada. Isso
produziu drops e recoveries com o ring no limite de capacidade.

Teardown: limpo, sem poweroff forcado; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao promover ring12/pre8 e nao acoplar DeepFilterNet3/SYSVAD/ponte PCM
v1. Proximo passo: politica explicita de ressincronizacao do consumer em
lateness alto, para separar atraso de recepcao de atraso de consumo.

## R10 ring resync VM - 2026-06-30

Foi adicionada politica opt-in de ressincronizacao do consumer:
`RingResyncLatenessMs`. O valor `0` mantem o comportamento anterior; valores
positivos deslocam os proximos deadlines quando o consumer acorda atrasado
demais, evitando catch-up em rajada.

Smoke host-only com `RingResyncLatenessMs=40`:

- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- drops `0`;
- recoveries/underflows `0`;
- resyncs `0`;
- latencia de playout p99 `80,552 ms`, max `81,078 ms`.

Rodada VM:

```text
runs/20260630-224628-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-diagnostic
```

Resultado:

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- guest receive p99 `16,561 ms`, max `181,180 ms`, `1` stall acima de
  `100 ms`;
- ring overflow drops `260`;
- recoveries/underflows `260`;
- consumer resyncs `26`;
- profundidade maxima `12/12`;
- latencia de playout p99 `115,709 ms`, max `125,275 ms`;
- consumer deadline lateness p99 `25,556 ms`, max `393,831 ms`.

Interpretacao: resync reduziu o p99 de lateness do consumer, mas nao promoveu o
playout. O ring ainda chegou ao limite, houve drops, e os recoveries de cauda
apareceram porque o teste e finito e a agenda deslocada passou do fim da
transmissao.

Teardown: limpo, sem poweroff forcado; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao promover `resync40`. Proximo passo recomendado: diagnosticar a
cadencia do consumer com prioridade de thread/processo e/ou timer dedicado,
antes de aumentar margem de buffer ou acoplar DFN/SYSVAD.

## R10 consumer wait timer VM - 2026-07-01

Foram adicionados controles diagnosticos para isolar a cadencia do consumer:

- `ConsumerWaitMode=waitable_timer`;
- `ConsumerThreadPriority=highest`;
- confirmacao em `progress.json` de `consumer_priority_applied=true` e
  `consumer_waitable_timer_created=true`.

Smoke host-only com ring12/pre8/resync40/waitable timer/highest:

- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- drops `0`;
- recoveries/underflows `0`;
- resyncs `0`;
- latencia de playout p99 `82,625 ms`, max `83,869 ms`;
- consumer deadline lateness p99 `1,134 ms`, max `2,363 ms`.

Rodada VM:

```text
runs/20260701-001024-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-diagnostic
```

Resultado:

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,030 ms`, max `10,657 ms`;
- guest receive p99 `15,237 ms`, max `552,461 ms`, `1` stall acima de
  `100 ms`;
- ring overflow drops `585`;
- recoveries/underflows `585`;
- consumer resyncs `55`;
- profundidade maxima `12/12`;
- latencia de playout p99 `118,874 ms`, max `132,298 ms`;
- consumer deadline lateness p99 `32,449 ms`, max `552,801 ms`.

Interpretacao: o waitable timer e a prioridade alta melhoraram o controle local
do consumer no smoke host-only, mas a VM ainda sofreu stall de recepcao/NAT
grande o bastante para violar o limite de latencia do ring. O resultado confirma
que o ring limitado esta fazendo o papel correto de conter latencia via
`drop_oldest`/`recover_with_silence`, mas a configuracao nao deve ser promovida.

Teardown: limpo, sem poweroff forcado; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao acoplar DFN/SYSVAD/ponte PCM v1. Proximo passo recomendado:
investigar o stall `unaccounted_receive_or_nat` antes de aumentar buffers ou
tratar ring12/pre8 como solucao de producao.

## R10 NAT/scheduler diagnostics - 2026-07-01

A janela do maior stall da rodada `waitable_timer/highest` confirmou envio host
regular e pausa no recebimento de cabecalhos TCP pelo guest, seguida de rajada
de blocos. Como `TCP_NODELAY` ja estava ativo, foram feitas duas verificacoes
diagnosticas.

### BlocksPerPacket=2

```text
runs/20260701-002426-dfn3-transport-48k-r9-tcp-native-receiver-batch2-diagnostic-ring12-pre8-resync40-waitwaitabletimer-priohighest-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- max receive interval `96,693 ms`, sem stall acima de `100 ms`;
- `3` stalls acima de `50 ms`;
- classes: `1` `guest_scheduler_correlated`, `2` `unaccounted_receive_or_nat`;
- ring drops `328`;
- recoveries/underflows `328`;
- resyncs `49`;
- playout latency p99 `116,508 ms`, max `611,530 ms`;
- consumer lateness p99 `33,304 ms`, max `723,548 ms`.

Reducao da taxa de pacotes melhorou o pior stall observado, mas nao estabilizou
o ring. A rodada continua diagnostica e nao promove o transporte.

### ReceiverProcessPriority=high

Foi adicionado suporte opt-in a prioridade de processo no receptor nativo:
`--process-priority normal|above_normal|high|realtime`, exposto no orquestrador
como `-ReceiverProcessPriority`.

Smoke host-only com `process_priority=high` confirmou aplicacao do parametro,
com drops/recoveries/underflows/resyncs `0`, p99 de playout `81,755 ms` e p99
de lateness do consumer `1,236 ms`.

Rodada VM:

```text
runs/20260701-003416-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- `process_priority=high`, `process_priority_applied=true`;
- guest receive p99 `14,997 ms`, max `290,142 ms`, `2` stalls acima de
  `100 ms`;
- classes: `1` `guest_scheduler_correlated`, `1` `unaccounted_receive_or_nat`;
- ring drops `565`;
- recoveries/underflows `565`;
- resyncs `36`;
- playout latency p99 `118,036 ms`, max `399,763 ms`;
- consumer lateness p99 `27,456 ms`, max `620,868 ms`.

Teardown das duas rodadas: limpo, sem poweroff forcado; VM final em `poweroff`,
snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`,
clipboard/drag-and-drop desabilitados e NIC NAT.

Decisao: nem `BlocksPerPacket=2` nem prioridade de processo `high` promovem a
fase. A integridade segue perfeita, mas baixa latencia ainda depende de eliminar
outliers de scheduler/recepcao ou trocar a rota NAT antes de acoplar DFN/SYSVAD.

## R10 VM process affinity - 2026-07-01

O orquestrador ganhou controles opt-in para diagnostico de isolamento do
processo da VM:

- `-VmProcessAffinityMask`;
- `-VmProcessPriority unchanged|Normal|AboveNormal|High|RealTime`;
- artefato `vm_process_scheduling.json`.

Rodada:

```text
runs/20260701-005021-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic
```

Parametros adicionais: `VmProcessAffinityMask=0xF0000`,
`VmProcessPriority=High`.

- afinidade/prioridade aplicadas ao `VirtualBoxVM`: mascara efetiva `0xF0000`,
  prioridade efetiva `High`;
- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,029 ms`, max `10,898 ms`;
- guest receive p99 `20,648 ms`, max `76,382 ms`;
- `0` stalls acima de `100 ms`, `2` stalls acima de `50 ms`;
- classes: `1` `guest_scheduler_correlated`, `1` `unaccounted_receive_or_nat`;
- ring drops `453`;
- recoveries/underflows `453`;
- resyncs `57`;
- playout latency p99 `119,088 ms`, max `154,464 ms`;
- consumer lateness p99 `37,635 ms`, max `480,843 ms`;
- teardown limpo, sem poweroff forcado.

A afinidade reduziu o pior stall de recepcao observado frente ao teste
`ReceiverProcessPriority=high`, mas nao estabilizou o ring nem removeu o
gargalo de scheduler/recepcao. A rodada permanece diagnostica e nao promove o
transporte.

## R10 pre-read gap / receiver priority - 2026-07-01

Foi adicionada telemetria para separar atraso antes da chamada a `recv` de
atraso dentro do proprio `recv`:

- `read_start_qpc_ns` e `pre_read_gap_ms` no `client_trace.json`;
- estatisticas `pre_read_gap_ms_*` no `client.json`;
- classe `client_receiver_thread_pre_recv_gap` no gate;
- novo parametro `-ReceiverThreadPriority`, repassado como
  `--receiver-thread-priority` ao receptor nativo.

A reanalise da rodada `vmaffF0000/vmprioHigh` anterior mostrou que o stall da
sequencia `3800` era pre-read gap: intervalo `76,382 ms`,
`header_wait_ms=0,011 ms`, `pre_read_gap_ms=76,362 ms`.

Rodada com telemetria medida:

```text
runs/20260701-010404-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- receive p99 `14,734 ms`, max `69,195 ms`;
- `0` stalls acima de `100 ms`, `2` acima de `50 ms`;
- `pre_read_gap_ms` p99 `0,704 ms`, max `63,254 ms`;
- classes: `1` `client_receiver_thread_pre_recv_gap`, `1`
  `unaccounted_receive_or_nat`;
- ring drops/recoveries `810`, resyncs `65`;
- teardown limpo.

Uma tentativa com `ReceiverThreadPriority=highest` combinada com afinidade da VM
abortou antes da coleta porque o Windows negou `ProcessorAffinity` para o
`VirtualBoxVM`; o teardown foi limpo e o snapshot restaurado.

Rodada isolando apenas `ReceiverThreadPriority=highest`, sem afinidade da VM:

```text
runs/20260701-011440-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-rxpriohighest-prochigh-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- receive p99 `13,664 ms`, max `154,765 ms`;
- `6` stalls acima de `50 ms`, `3` acima de `100 ms`;
- `pre_read_gap_ms` p99 `0,779 ms`, max `57,141 ms`;
- classes: `1` `client_receiver_thread_pre_recv_gap`, `2`
  `guest_scheduler_correlated`, `3` `unaccounted_receive_or_nat`;
- ring drops/recoveries `469`, resyncs `31`;
- teardown limpo.

Decisao: manter a telemetria `pre_read_gap` como diagnostico, mas nao promover
`ReceiverThreadPriority=highest`. O gargalo segue misto: atrasos ocasionais da
thread de recepcao, scheduler do convidado e espera real por cabecalho TCP/NAT.

## R10 host-only route - 2026-07-01

O orquestrador passou a aceitar rota sem NAT para diagnostico:

- `-GuestConnectHost`;
- `-TemporaryHostOnlyAdapterName`.

No host local havia `VirtualBox Host-Only Ethernet Adapter` em `192.168.56.1`,
com DHCP host-only ativo. A VM base estava em `nic1=nat`, `nic2=none`.

Rodada:

```text
runs/20260701-012549-dfn3-transport-48k-r9-tcp-native-receiver-guesthost192p168p56p1-hostonly-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda/seq/CRC/framing `0`;
- `GuestConnectHost=192.168.56.1`;
- NIC2 host-only temporaria; teardown restaurou `nic2=none`;
- receive p99 `14,845 ms`, max `116,378 ms`;
- `14` stalls acima de `20 ms`, `1` acima de `50 ms`, `1` acima de `100 ms`;
- `pre_read_gap_ms` p99 `1,143 ms`, max `23,591 ms`;
- unico stall >50 ms: `guest_scheduler_correlated`;
- ring drops/recoveries `564`, resyncs `66`;
- playout latency p99 `119,022 ms`;
- teardown limpo, sem poweroff forcado.

A rota host-only eliminou a classe `unaccounted_receive_or_nat` nesta rodada,
mas nao estabilizou o ring: o outlier restante foi pausa de scheduler do
convidado. Portanto host-only fica como ferramenta diagnostica, nao como
promocao do transporte.
