# Plano VM DFN3 Transport 48 kHz

Data: 2026-06-29

## Reaproveitamento seguro

Dos scripts antigos, o reaproveitamento seguro ficou restrito a primitivas de
infraestrutura:

- `VBoxManage` com array de argumentos e separador literal `"--"`;
- `-EncodedCommand` para PowerShell remoto;
- preflight host-only antes do boot;
- espera por Guest Additions e usuario logado;
- copia `guestcontrol copyto/copyfrom`;
- JSON real como fonte de verdade, nao apenas exit code;
- shutdown normal, restore do snapshot e confirmacao de invariantes.

Nao foi reaproveitado o contrato antigo RNNoise:

- sem 16 kHz;
- sem 320 samples;
- sem metodos `capture_only`, `bypass` ou `rnnoise`;
- sem ponte PCM v1;
- sem SYSVAD.

## Menor plano de alteracao

1. Criar `scripts/audio/host_guest_pcm_stream_dfn48.py` com contrato fixo
   PCM16 mono, 48 kHz, 480 samples, 10 ms.
2. Criar `scripts/audio/analyze_dfn48_vm_transport.py` com gate de integridade,
   duracao, hash, jitter e classificacao `accepted/check/rejected`.
3. Criar `scripts/vm/Invoke-Dfn3TransportVm.ps1` para uma unica fase
   host-paced, usando o clone `PTC3527-SYSVAD-LAB-FAST` no snapshot
   `checkpoint45-causal-wpt-validated`.
4. Gerar artefatos em `resultados/dfn3_vm_transport_48k/`.
5. Bloquear qualquer acoplamento com DFN dentro da VM, ponte PCM v1 ou SYSVAD
   ate o transporte ficar limpo.

## Contrato resolvido

O handoff trazia uma inconsistencia: `480 samples @ 48 kHz` corresponde a
`10 ms`, logo a cadencia correta e `100 blocos/s`. `50 blocos/s` corresponderia
a 20 ms ou a 960 samples por bloco. A implementacao preservou o contrato de
10 ms usado pelo DeepFilterNet3.

## Resultado da primeira rodada

Rodada:

```text
resultados/dfn3_vm_transport_48k/
```

Classificacao:

```text
check
```

Motivo:

- integridade aceita: `6000/6000` blocos, perda zero, CRC zero, framing zero,
  sequencia sem gaps e WAV de `60,0 s`;
- hash de payload recebido igual ao de origem;
- jitter de recepcao ainda exige analise: p99 `18,722 ms`, max `442,938 ms`,
  um stall acima de `100 ms` e rajadas compensatorias.

Decisao:

- nao reabrir SYSVAD;
- nao reabrir ponte PCM v1;
- nao acoplar ainda o DeepFilterNet3 dentro da VM;
- repetir/instrumentar transporte se for necessario promover de `check` para
  `accepted`.

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

Foi criado um receptor nativo minimo em `scripts/native/dfn48_native_receiver/`,
com WinSock TCP, contrato `PTCDFN3`, ACK `PTCDAK3`, CRC32, hash SHA-256 via
BCrypt, temporizacao QPC e JSON compativel com
`scripts/audio/analyze_dfn48_vm_transport.py`. O build final usa runtime MSVC
estatico (`/MT`); a primeira tentativa na VM, em
`runs/20260629-150318-dfn3-transport-48k-r7-native-receiver`, falhou antes do
transporte por runtime DLL ausente (`-1073741515`) e nao foi considerada
resultado de transporte. O teardown dessa tentativa foi limpo.

Validacao local host-only do receptor nativo: gate `accepted`, sem warnings,
`6000/6000` blocos, perda zero, sequencia zero, CRC zero, framing zero, hash
`e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`,
recepcao p99 `10,107 ms` e max `13,764 ms`.

A rodada valida na VM foi
`runs/20260629-150919-dfn3-transport-48k-r7-native-receiver`. O cliente usou
`ClientImplementation=Native`, `sink=memory`, `BlocksPerPacket=1`, sem SYSVAD,
sem ponte PCM v1, sem RNNoise e sem DeepFilterNet3 dentro da VM.

Integridade novamente perfeita: `6000/6000` blocos, perda zero, sequencia zero,
CRC zero, framing zero, duracao logica `60,0 s` e hash
`e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.

O host/send ficou limpo: p99 `10,018 ms`, max `10,482 ms`, lateness max
`0,488 ms`, sem stall acima de `20 ms`. A recepcao nativa no convidado melhorou
fortemente o p99: `14,936 ms`, com max `186,643 ms`, `7` stalls acima de
`20 ms`, `1` acima de `50 ms` e `1` acima de `100 ms`.

Correlacao: o unico stall acima de `50 ms` ocorreu no bloco `2246`, concentrado
em `header_wait_ms` (`186,609 ms`), com envio host normal (`9,997 ms`) e sem gap
de scheduler acima de `30 ms` na janela. Classificacao:
`unaccounted_receive_or_nat`.

Interpretacao: remover Python do receptor reduziu bastante o jitter geral, mas
nao eliminou completamente o outlier de `header_wait`. A causa restante continua
antes do DSP e mais proxima de `recv`/NAT/entrega TCP do convidado do que de
Python, WAV, CRC, hash, servidor host ou DeepFilterNet3.

Decisao: manter a fase em `check`; nao acoplar DeepFilterNet3 dentro da VM,
ponte PCM v1 ou SYSVAD ainda. Proximo passo recomendado: testar transporte
alternativo que evite/controle o comportamento TCP/NAT, por exemplo UDP com
sequencia/CRC/hash e jitter buffer diagnostico minimo, ou repetir R7 para medir
variancia antes de mudar o transporte.

## R8 UDP diagnostic - 2026-06-29

Foi implementado transporte UDP diagnostico mantendo o mesmo contrato logico
DFN48. O controle permanece TCP para preambulo e ACK final; os dados seguem por
UDP com sequencia, CRC32 e hash SHA-256 no receptor nativo. O orquestrador agora
aceita `-Transport tcp|udp`, com `tcp` como padrao, e o analisador marca UDP
como diagnostico por design via warning
`udp_transport_diagnostic_not_realtime_gate`.

Artefatos de codigo atualizados:

- `scripts/audio/host_guest_pcm_stream_dfn48.py`;
- `scripts/audio/analyze_dfn48_vm_transport.py`;
- `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
- `scripts/native/dfn48_native_receiver/src/main.cpp`.

Validacoes antes da VM:

- compileall dos scripts Python;
- parse do orquestrador PowerShell;
- build nativo Release com runtime estatico (`/MT`);
- teste host-only UDP curto: `100/100` blocos, perda zero, sequencia zero, CRC
  zero, framing zero e hash correto;
- preflight VM: `ready=true`, `failures=0`, `warnings=0`, snapshot
  `checkpoint45-causal-wpt-validated`, runtime
  `C:\PTC3527-Private\vm_runtime`.

Rodada VM:

```text
resultados/dfn3_vm_transport_48k/runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver
```

Resultado:

- gate: `check`;
- warning deliberado: `udp_transport_diagnostic_not_realtime_gate`;
- integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`,
  framing `0`;
- hash payload origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,044 ms`, max `10,387 ms`, lateness max `0,413 ms`;
- guest receive p99 `14,400 ms`, max `70,537 ms`;
- stalls acima de `100 ms`: `0`;
- stalls acima de `50 ms`: `1`, bloco `5107`;
- classificacao do stall: `unaccounted_receive_or_nat`.

Interpretacao: UDP reduziu o pior outlier em relacao a R7 TCP e manteve
integridade perfeita, mas ainda deixou um stall de chegada relevante antes do
DSP. A fase segue em `check`: nao acoplar DeepFilterNet3 dentro da VM, ponte PCM
v1 ou SYSVAD.

Proximo passo recomendado: repetir R8 para variancia e/ou adicionar jitter
buffer diagnostico minimo ao receptor UDP para separar atraso de chegada de
viabilidade de consumo em cadencia de `10 ms`.

## R8 jitter-buffer posthoc e repeticao UDP - 2026-06-29

O analisador passou a incluir uma simulacao posthoc de jitter buffer diagnostico
baseada em `client_trace.json`. A simulacao nao altera o transporte nem o gate
de integridade; ela calcula, para buffers de `1,2,4,6,8,12,16` blocos, quantos
underflows ocorreriam se o consumo ordenado comecasse `buffer_ms` depois do
primeiro bloco recebido.

Aplicacao sobre a primeira R8 UDP:

- run: `runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver`;
- integridade: `6000/6000`, sem perdas;
- max phase error: `58,789 ms`;
- buffer de `1` bloco: `20` underflows;
- buffer de `2` blocos: `8` underflows;
- buffer de `4` blocos: `2` underflows;
- buffer de `6` blocos (`60 ms`): `0` underflows;
- interpretacao: aquela rodada especifica era absorvivel com cerca de `60 ms`
  de buffer, mas isso adicionaria latencia diagnostica grande para um caminho
  de microfone em tempo real.

Repeticao UDP:

- run: `runs/20260629-190754-dfn3-transport-48k-r8-udp-native-receiver`;
- gate: `rejected`;
- integridade: `5913/6000` blocos, `87` perdas, `1` erro de sequencia, CRC e
  framing zero;
- hash recebido diferente do hash de origem;
- host/send continuou limpo: p99 `10,018 ms`, max `13,107 ms`;
- guest receive max: `1554,858 ms`;
- stall dominante no bloco `2607`, `header_wait_ms=1554,840 ms`, envio host
  normal, sem gap de scheduler acima de `30 ms` na janela;
- jitter buffer posthoc: nenhum buffer testado ate `16` blocos absorveu; o
  minimo teorico pelo maior atraso seria `155` blocos, e ainda assim nao
  recuperaria os `87` datagramas ausentes.

Teardown da repeticao: o orquestrador falhou na consulta final de `VMState`, mas
auditoria posthoc confirmou VM em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados, NIC NAT e sem poweroff forcado.

Conclusao atual: UDP puro nao deve ser caminho de promocao. Ele pode reduzir
head-of-line blocking em uma rodada boa, mas introduz perda real sob o mesmo
ambiente NAT/guest receive. O proximo passo tecnicamente mais honesto e voltar
para transporte confiavel e reduzir a sensibilidade ao jitter por desenho:
fila/ring buffer no lado guest, thread de recepcao separada do consumidor de
10 ms, metricas de backlog/underflow e, se necessario, testar interface de rede
menos dependente de NAT antes de qualquer SYSVAD ou DFN dentro da VM.

## R9 TCP queue diagnostic - 2026-06-29

Foi implementada no receptor nativo uma fila diagnostica com consumidor
separado:

- `--queue-diagnostic`;
- `--queue-buffer-blocks N`;
- `--consumer-trace <path>`.

A thread de recepcao continua validando sequencia, CRC e hash. A consumer thread
comeca apos o prebuffer configurado e consome um bloco logico a cada `10 ms`,
registrando profundidade da fila e underflows. O orquestrador ganhou
`-QueueDiagnostic` e `-QueueBufferBlocks`.

Validacao local host-only TCP de `1 s`: gate `accepted`, perda zero,
`consumer_underflows=0`, profundidade minima `1` bloco e
`consumer_trace.json` gerado.

Rodada valida:

```text
resultados/dfn3_vm_transport_48k/runs/20260629-193111-dfn3-transport-48k-r9-tcp-native-receiver-queue20-diagnostic
```

Resultado:

- gate: `accepted`;
- integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash payload origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- transporte: TCP, receptor nativo, `BlocksPerPacket=1`;
- prebuffer: `20` blocos (`200 ms`);
- consumer checked blocks: `6000`;
- consumer underflows: `0`;
- profundidade minima antes do consumo: `1` bloco;
- profundidade media antes do consumo: `22,113` blocos;
- profundidade maxima antes do consumo: `105` blocos;
- guest receive p99 `13,794 ms`, max `73,402 ms`;
- um stall acima de `50 ms`, correlacionado a gap de scheduler do convidado.

Interpretacao: a separacao recepcao/consumo com fila absorveu o jitter desta
rodada sem perda e sem underflow. O resultado valida a arquitetura como
mitigacao de transporte confiavel, mas `200 ms` de prebuffer e uma margem alta
para microfone em tempo real; ainda nao e motivo para acoplar SYSVAD ou DFN
dentro da VM.

Tentativa abortada:

```text
resultados/dfn3_vm_transport_48k/runs/20260629-193509-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic
```

Objetivo: testar prebuffer menor de `8` blocos (`80 ms`). O servidor host
transmitiu, mas falhou aguardando ACK final (`TimeoutError: timed out`) e a
execucao externa atingiu timeout antes do teardown do orquestrador. Nao houve
`client.json`, `consumer_trace.json`, hash nem gate; portanto a tentativa nao e
resultado experimental. Recuperacao: ACPI shutdown sem poweroff forcado, restore
do snapshot `checkpoint45-causal-wpt-validated` e invariantes finais confirmados.

Proximo passo recomendado: depurar a tentativa queue8 em host-only longo ou
adicionar timeout/telemetria de progresso no guest antes de nova VM com buffer
menor. A promocao deve exigir repeticoes sem underflow com prebuffer aceitavel e
teardown limpo.

## R9 progress telemetry e sweep queue8/7/6 - 2026-06-29

Foi adicionada telemetria de progresso ao receptor nativo:

- `--progress-output <path>`;
- `--progress-interval-blocks N`.

O arquivo `progress.json` e escrito de forma atomica e registra estagio,
blocos recebidos, sequencia esperada, erros, profundidade da fila, estado do
consumer e linhas consumidas. O orquestrador passou a aceitar
`-ProgressIntervalBlocks` e `-GuestLaunchMode Run|Start`. O modo `Start`
inicia o receptor nativo como processo destacado no convidado e espera
`guest_exit.json` antes de copiar artefatos, reduzindo dependencia de uma
sessao Guest Control longa.

Tentativas operacionais nao experimentais:

- `runs/20260629-200352-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  modo `Run` falhou ao fechar a sessao Guest Control (`VERR_TIMEOUT`), sem
  `client.json`/gate;
- `runs/20260629-202446-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  falha antes do transporte por separador `--` do `guestcontrol start`;
- `runs/20260629-203639-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
  mostrou corrida de copia; o servidor recebeu ACK perfeito e `progress.json`
  terminou em `completed`, mas `client.json` ainda nao tinha sido copiado para
  o host. O orquestrador foi corrigido para aguardar `guest_exit.json`.

Rodada VM queue8 valida:

```text
runs/20260629-204534-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic
```

Classificacao:

```text
accepted
```

Resultado:

- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,016 ms`, max `10,251 ms`;
- guest receive p99 `16,784 ms`, max `38,016 ms`;
- stalls acima de `100 ms`: `0`;
- prebuffer `8` blocos (`80 ms`);
- consumer underflows `0`;
- profundidade minima/media/maxima: `1` / `10,313` / `86` blocos;
- `progress.json`: `completed`;
- `guest_exit_code=0`;
- teardown limpo, sem poweroff forcado.

Sweep de prebuffer menor:

- queue6:
  `runs/20260629-205157-dfn3-transport-48k-r9-tcp-native-receiver-queue6-diagnostic`;
  integridade perfeita, mas gate `check`, guest receive max `187,201 ms`,
  `2` stalls acima de `100 ms`, `12` underflows;
- queue7:
  `runs/20260629-205700-dfn3-transport-48k-r9-tcp-native-receiver-queue7-diagnostic`;
  integridade perfeita, mas gate `check`, guest receive max `147,170 ms`,
  `2` stalls acima de `100 ms`, `7` underflows.

Conclusao: a arquitetura TCP confiavel com recepcao separada e fila e a melhor
linha ate aqui. Nesta amostra, `80 ms` foi o menor prebuffer VM observado sem
underflow; `60 ms` e `70 ms` mantiveram o payload correto, mas nao sustentaram
playout continuo de `10 ms`. Ainda nao acoplar DeepFilterNet3 dentro da VM,
ponte PCM v1 ou SYSVAD. Proximo gate recomendado: repetir queue8 para variancia
e transformar a fila diagnostica em desenho de ring buffer real com margem
configuravel.

## R9 repeticao queue8 - 2026-06-29

A repeticao VM de queue8 foi executada em:

```text
runs/20260629-213620-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic
```

Parametros: `Transport=tcp`, `ClientImplementation=Native`,
`ClientSink=memory`, `BlocksPerPacket=1`, `QueueDiagnostic`,
`QueueBufferBlocks=8`, `ProgressIntervalBlocks=100` e
`GuestLaunchMode=Start`.

Resultado:

- gate: `check`;
- warning: `client_receive_stall_over_100ms`;
- integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,291 ms`, max `10,919 ms`;
- guest receive p99 `14,588 ms`, max `184,038 ms`;
- stall dominante no bloco `796`, concentrado em `header_wait_ms=184,005 ms`,
  com envio host normal e sem gap de scheduler acima de `30 ms` na janela;
- classificacao: `unaccounted_receive_or_nat`;
- prebuffer `8` blocos (`80 ms`);
- consumer underflows `6`, profundidade minima `0`.

O transporte logico permaneceu correto, mas a repeticao nao confirmou `80 ms`
como margem estavel. A tela de atualizacao/desligamento do Windows exigiu
`forced_poweroff` no teardown; a auditoria final confirmou VM em `poweroff`,
snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
drag-and-drop desabilitados e NIC NAT.

Decisao: nao promover queue8 ainda e nao acoplar DeepFilterNet3 dentro da VM,
ponte PCM v1 ou SYSVAD. A proxima etapa deve tratar `80 ms` como margem
candidata fragil e desenhar/testar ring buffer real com margem configuravel,
registrando underflows, profundidade e politicas de recuperacao.

## R9 queue12 - 2026-06-29

Primeira tentativa:

```text
runs/20260629-224057-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic
```

Nao conta como experimento. A VM nao chegou a usuario logado/Guest Additions
pronto (`Guest Additions or interactive logon did not become ready`) e nao houve
`server.json`, `client.json`, traces, hash ou gate. A recuperacao restaurou o
snapshot `checkpoint45-causal-wpt-validated`.

Rodada valida:

```text
runs/20260629-225852-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic
```

Parametros: `Transport=tcp`, `ClientImplementation=Native`,
`ClientSink=memory`, `BlocksPerPacket=1`, `QueueDiagnostic`,
`QueueBufferBlocks=12`, `ProgressIntervalBlocks=100` e
`GuestLaunchMode=Start`.

Resultado:

- gate: `check`;
- warning: `client_receive_stall_over_100ms`;
- integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send p99 `10,035 ms`, max `10,279 ms`;
- guest receive p99 `17,611 ms`, max `593,981 ms`;
- stall dominante no bloco `2892`, concentrado em `header_wait_ms=593,950 ms`,
  com envio host normal e sem gap de scheduler acima de `30 ms` na janela;
- classificacao: `unaccounted_receive_or_nat`;
- prebuffer `12` blocos (`120 ms`);
- consumer underflows `0`;
- profundidade minima/media/maxima: `1` / `13,713` / `75` blocos;
- teardown limpo, sem poweroff forcado.

Interpretacao: aumentar o prebuffer para `120 ms` evitou underflows nessa
rodada, mas a fila diagnostica absorveu um outlier grande acumulando backlog
maximo de `75` blocos. Isso valida a necessidade de desacoplar recepcao e
consumo, mas nao valida uma fila sem limite como arquitetura final de microfone.

Decisao: nao promover queue12 diretamente. Proximo passo recomendado: desenhar
ring buffer real com limite de profundidade, politica explicita para atraso
excessivo/drop/recovery e telemetria de latencia efetiva antes de qualquer
acoplamento com DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## R10 ring buffer diagnostico - 2026-06-30

Foi implementado um modo diagnostico de ring buffer real no receptor nativo,
sem acoplar DeepFilterNet3, SYSVAD, ponte PCM v1, driver ou RNNoise.

Novos parametros:

- `--ring-diagnostic`;
- `--ring-capacity-blocks N`;
- `--ring-prebuffer-blocks N`;
- `-RingDiagnostic`, `-RingCapacityBlocks` e `-RingPrebufferBlocks` no
  orquestrador PowerShell.

Semantica:

- o producer de recepcao TCP continua validando sequencia, CRC e hash;
- o consumer consome a cada `10 ms` apos o prebuffer configurado;
- a capacidade e fixa em blocos;
- overflow/atraso excessivo aplica `drop_oldest`, descartando o bloco mais
  antigo e preservando dados recentes;
- underflow aplica `recover_with_silence` diagnostico, contado como recovery;
- o gate marca ring como diagnostico por design e fica em `check` mesmo quando
  a integridade esta perfeita.

Telemetria nova:

- capacidade, prebuffer e limite de latencia;
- fill level minimo/medio/maximo antes do consumo;
- drops de overflow;
- recoveries/underflows;
- latencia efetiva de playout (`ring_playout_latency_ms_*`);
- lateness do deadline do consumer;
- trace por bloco em `consumer_trace.json`.

Smoke host-only:

```text
tmp/dfn48_ring_local_smoke
```

Resultado do smoke com `capacity=12` e `prebuffer=8`:

- gate `check`, apenas com warning deliberado
  `ring_buffer_diagnostic_not_realtime_gate`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash origem/recebido
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- drops de overflow `0`;
- recoveries/underflows `0`;
- fill minimo/medio/maximo `1` / `8,994` / `9` blocos;
- latencia de playout p99 `81,603 ms`, maxima `82,142 ms`;
- consumer deadline lateness p99 `0,412 ms`, max `0,997 ms`.

Decisao: o ring esta pronto para uma rodada VM conservadora, mas ainda nao
promove a fase. A proxima VM deve manter `Transport=tcp`,
`ClientImplementation=Native`, `sink=memory`, `BlocksPerPacket=1`,
`GuestLaunchMode=Start` e usar parametros conservadores como
`RingCapacityBlocks=12`, `RingPrebufferBlocks=8`, com promocao bloqueada se
houver latencia acumulada, drops ou recoveries.

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
- warnings: `ring_buffer_diagnostic_not_realtime_gate`,
  `ring_buffer_overflow_drops`, `ring_buffer_recoveries`,
  `ring_buffer_underflows`, `ring_buffer_reached_latency_cap`;
- integridade perfeita: `6000/6000`, perda `0`, sequencia `0`, CRC `0`,
  framing `0`;
- hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send limpo: p99 `10,180 ms`, max `10,569 ms`;
- guest receive p99 `13,822 ms`, max `70,085 ms`;
- stalls de recepcao acima de `100 ms`: `0`;
- ring: `103` drops de overflow, `103` recoveries/underflows, profundidade
  maxima `12/12`;
- latencia de playout p99 `87,842 ms`, max `120,139 ms`;
- lateness do consumer p99 `152,040 ms`, max `394,744 ms`.

Interpretacao: o transporte logico continuou correto, mas o ring real revelou
um segundo problema que a simulacao posthoc de chegada nao capturava: o consumer
no convidado tambem sofre pausas de scheduler. Quando acorda atrasado, ele tenta
executar deadlines ja vencidos em rajada, drena o ring e produz recoveries,
enquanto o producer ja descartou blocos antigos para respeitar a capacidade.
Assim, `capacity=12/prebuffer=8` nao e promovido.

Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao acoplar DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo passo
tecnico recomendado: adicionar uma politica diagnostica de ressincronizacao do
consumer quando `deadline_lateness_ms` exceder um limite explicito, para evitar
catch-up em rajada; medir separadamente recepcao, drops do ring e falhas de
cadencia do consumer.

## R10 ring resync diagnostic - 2026-06-30

Foi adicionada politica opt-in de ressincronizacao do consumer:

- `--ring-resync-lateness-ms N` no receptor nativo;
- `-RingResyncLatenessMs N` no orquestrador VM;
- politica registrada como `shift_schedule_to_now`.

A politica desloca os proximos deadlines quando o consumer acorda com lateness
acima do limite configurado, evitando catch-up em rajada. O modo default continua
`0 ms`, isto e, desabilitado, para preservar comparabilidade.

Smoke host-only com `RingCapacityBlocks=12`, `RingPrebufferBlocks=8` e
`RingResyncLatenessMs=40`:

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
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send continuou limpo;
- guest receive p99 `16,561 ms`, max `181,180 ms`, `1` stall acima de
  `100 ms`;
- ring overflow drops `260`;
- recoveries/underflows `260`;
- consumer resyncs `26`;
- profundidade maxima `12/12`;
- latencia de playout p99 `115,709 ms`, max `125,275 ms`;
- consumer deadline lateness p99 caiu para `25,556 ms`, max `393,831 ms`.

Interpretacao: a ressincronizacao reduziu o p99 de lateness do consumer em
relacao a rodada sem resync (`152,040 ms` para `25,556 ms`), mas nao resolveu a
viabilidade de playout. Os resyncs ocorreram quando o ring ja estava cheio,
logo o producer precisou descartar blocos antigos para manter o limite de
latencia. Como o teste tem duracao finita, deslocar a agenda tambem empurrou o
playout para alem do fim da transmissao, gerando recoveries de cauda. Portanto,
`resync40` tambem nao e promovido.

Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: ainda nao acoplar DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo
passo recomendado: isolar a causa do atraso do consumer, antes de mudar margem
de buffer. Alternativas candidatas: elevar prioridade da thread/processo do
consumer no receptor nativo, medir consumer com `WaitableTimer`, e/ou adicionar
modo diagnostico de stream continuo por janela temporal em vez de exigir
exatamente `6000` callbacks apos resync.

## R10 consumer wait timer diagnostic - 2026-07-01

Foi adicionada instrumentacao opt-in no receptor nativo e no orquestrador para
testar a cadencia do consumer independentemente do transporte:

- `--consumer-wait-mode hybrid|waitable_timer`;
- `--consumer-thread-priority normal|above_normal|highest|time_critical`;
- `-ConsumerWaitMode` e `-ConsumerThreadPriority` no orquestrador VM;
- telemetria em `progress.json` para confirmar se a prioridade e o timer foram
  aplicados.

Smoke host-only com `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
`RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer` e
`ConsumerThreadPriority=highest`:

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

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
`RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
`RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
`ConsumerThreadPriority=highest`, `ProgressIntervalBlocks=100`,
`GuestLaunchMode=Start`.

Resultado:

- preflight `ready=true`, falhas `0`, warnings `0`;
- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- `progress.json` confirmou `consumer_priority_applied=true` e
  `consumer_waitable_timer_created=true`;
- host/send limpo: p99 `10,030 ms`, max `10,657 ms`;
- guest receive p99 `15,237 ms`, max `552,461 ms`, `1` stall acima de
  `100 ms`;
- stalls de recepcao classificados como `unaccounted_receive_or_nat`;
- ring overflow drops `585`;
- recoveries/underflows `585`;
- consumer resyncs `55`;
- profundidade maxima `12/12`;
- latencia de playout p99 `118,874 ms`, max `132,298 ms`;
- consumer deadline lateness p99 `32,449 ms`, max `552,801 ms`.

Interpretacao: o timer dedicado e a prioridade `highest` foram aplicados, mas
nao resolveram a viabilidade de playout dentro de `120 ms`. O maior evento foi
um stall de recepcao/NAT de aproximadamente `552 ms`; com ring limitado, o
comportamento correto e descartar blocos antigos e recuperar com silencio em
vez de acumular latencia. Portanto a rodada e util para diagnostico, mas nao e
promovida.

Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao acoplar DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo passo
tecnico recomendado: investigar o stall `unaccounted_receive_or_nat` antes de
aumentar buffers, por exemplo comparando modo de guest launch/processo, afinidade
ou outra rota de transporte; manter o ring como diagnostico de limite de
latencia, nao como gate de promocao.

## R10 NAT/scheduler diagnostics - 2026-07-01

Analise da janela do stall da rodada `waitable_timer/highest` mostrou que o host
continuou enviando a cada `10 ms`, enquanto o guest ficou aproximadamente
`552 ms` sem receber cabecalhos TCP e depois drenou dezenas de blocos em rajada.
`TCP_NODELAY` ja estava ativo nos dois lados, portanto a hipotese principal
passou a ser entrega/NAT e/ou pausa do scheduler do convidado.

Rodada diagnostica com menos pacotes:

```text
runs/20260701-002426-dfn3-transport-48k-r9-tcp-native-receiver-batch2-diagnostic-ring12-pre8-resync40-waitwaitabletimer-priohighest-diagnostic
```

Parametros iguais aos da rodada anterior, exceto `BlocksPerPacket=2`.

- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- max receive interval caiu para `96,693 ms`, sem stall acima de `100 ms`;
- ainda houve `3` stalls acima de `50 ms`;
- classes: `1` `guest_scheduler_correlated`, `2` `unaccounted_receive_or_nat`;
- ring overflow drops `328`, recoveries/underflows `328`, resyncs `49`;
- latencia de playout p99 `116,508 ms`, max `611,530 ms`;
- consumer deadline lateness p99 `33,304 ms`, max `723,548 ms`;
- teardown limpo, sem poweroff forcado.

Interpretacao: reduzir a taxa de pacotes melhorou bastante o pior stall de
recepcao, mas nao estabilizou o playout. A rodada permanece diagnostica porque
`BlocksPerPacket=2` altera a granularidade de transporte e ainda produz
drops/recoveries.

Em seguida foi adicionada prioridade de processo opt-in no receptor nativo:

- `--process-priority normal|above_normal|high|realtime`;
- `-ReceiverProcessPriority` no orquestrador VM;
- telemetria `process_priority` e `process_priority_applied` em
  `progress.json` e `client.json`.

Smoke host-only com `process_priority=high`:

- gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
- drops/recoveries/underflows/resyncs `0`;
- `process_priority_applied=true`;
- latencia de playout p99 `81,755 ms`;
- consumer deadline lateness p99 `1,236 ms`.

Rodada VM direta com `BlocksPerPacket=1` e `ReceiverProcessPriority=high`:

```text
runs/20260701-003416-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic
```

- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- `process_priority=high` e `process_priority_applied=true`;
- guest receive p99 `14,997 ms`, max `290,142 ms`, `2` stalls acima de
  `100 ms`;
- classes: `1` `guest_scheduler_correlated`, `1` `unaccounted_receive_or_nat`;
- ring overflow drops `565`, recoveries/underflows `565`, resyncs `36`;
- latencia de playout p99 `118,036 ms`, max `399,763 ms`;
- consumer deadline lateness p99 `27,456 ms`, max `620,868 ms`;
- teardown limpo, sem poweroff forcado.

Decisao: prioridade de processo `high` tambem nao promove a fase. A trilha TCP
nativo segue promissora por preservar integridade perfeita, mas a baixa latencia
na VM ainda e bloqueada por outliers de scheduler/recepcao. Proximo passo
recomendado: testar afinidade/isolamento do processo da VM ou uma rota de
transporte alternativa ao NAT antes de aumentar buffer ou acoplar DFN/SYSVAD.

## R10 VM process affinity diagnostic - 2026-07-01

Foi adicionada instrumentacao opt-in no orquestrador para testar isolamento do
processo da VM sem alterar o receptor, SYSVAD, ponte PCM v1 ou DFN:

- `-VmProcessAffinityMask`, aceitando mascara decimal ou hexadecimal;
- `-VmProcessPriority unchanged|Normal|AboveNormal|High|RealTime`;
- artefato `vm_process_scheduling.json`, com PID, prioridade/afinidade
  solicitadas, valores efetivos e erro, quando houver;
- registro dos parametros em `deployment_manifest.json` e `host_result.json`.

Rodada diagnostica:

```text
runs/20260701-005021-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic
```

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
`RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
`RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
`ConsumerThreadPriority=highest`, `ReceiverProcessPriority=high`,
`VmProcessAffinityMask=0xF0000`, `VmProcessPriority=High`,
`GuestLaunchMode=Start`.

Resultado:

- afinidade/prioridade aplicadas ao processo `VirtualBoxVM`:
  `effective_affinity_mask=0xF0000`, `effective_priority=High`;
- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- hash correto:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- host/send limpo: p99 `10,029 ms`, max `10,898 ms`;
- guest receive p99 `20,648 ms`, max `76,382 ms`, `0` stalls acima de
  `100 ms`, `2` acima de `50 ms`;
- classes dos stalls acima de `50 ms`: `1` `guest_scheduler_correlated`,
  `1` `unaccounted_receive_or_nat`;
- ring overflow drops `453`;
- recoveries/underflows `453`;
- consumer resyncs `57`;
- latencia de playout p99 `119,088 ms`, max `154,464 ms`;
- consumer deadline lateness p99 `37,635 ms`, max `480,843 ms`.

Interpretacao: isolar o processo da VM em quatro processadores logicos e elevar
sua prioridade reduziu o pior stall de recepcao frente a rodada direta com
prioridade de processo (`290,142 ms` para `76,382 ms`) e eliminou stalls acima
de `100 ms`, mas nao estabilizou o playout. O scheduler do convidado ainda
registrou gaps grandes e o ring limitado continuou exigindo drops/recoveries.

Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`, snapshot
`checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
desabilitados e NIC NAT.

Decisao: nao promover afinidade `0xF0000`/prioridade `High`; nao acoplar
DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo passo tecnico recomendado:
comparar outra rota de transporte sem NAT ou testar uma matriz pequena de
afinidades, mas sempre como diagnostico e sem aumentar buffers para mascarar o
outlier.

## R10 pre-read gap and receiver priority diagnostic - 2026-07-01

Foi adicionada instrumentacao para separar dois casos que antes ficavam juntos
em `unaccounted_receive_or_nat`:

- `read_start_qpc_ns` e `pre_read_gap_ms` no `client_trace.json`;
- estatisticas `pre_read_gap_ms_*` no `client.json`;
- classificacao `client_receiver_thread_pre_recv_gap` no analisador, quando a
  pausa acontece antes da thread entrar em `recv`;
- `-ReceiverThreadPriority normal|above_normal|highest|time_critical` no
  orquestrador, exposto ao receptor nativo como `--receiver-thread-priority`.

A reanalise da rodada com afinidade `0xF0000` mostrou que um stall previamente
classificado como `unaccounted_receive_or_nat` era, na verdade, pausa da thread
de recepcao antes de chamar `recv`:

- sequencia `3800`;
- intervalo de recepcao `76,382 ms`;
- `client_header_wait_ms=0,011 ms`;
- `client_pre_read_gap_ms=76,362 ms`;
- nova classe: `client_receiver_thread_pre_recv_gap`.

Rodada VM com a nova telemetria, mantendo afinidade/prioridade do processo da
VM:

```text
runs/20260701-010404-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic
```

Resultado:

- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- guest receive p99 `14,734 ms`, max `69,195 ms`, `0` stalls acima de
  `100 ms`, `2` acima de `50 ms`;
- `pre_read_gap_ms` p99 `0,704 ms`, max `63,254 ms`;
- classes: `1` `client_receiver_thread_pre_recv_gap`, `1`
  `unaccounted_receive_or_nat`;
- ring drops/recoveries `810`, resyncs `65`;
- teardown limpo, sem poweroff forcado.

Tentativa seguinte com `ReceiverThreadPriority=highest` mais afinidade da VM
abortou antes da rodada porque o Windows negou `ProcessorAffinity` para o
`VirtualBoxVM`. O teardown foi limpo e o snapshot foi restaurado.

Rodada VM sem afinidade de processo da VM, isolando apenas
`ReceiverThreadPriority=highest`:

```text
runs/20260701-011440-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-rxpriohighest-prochigh-diagnostic
```

Resultado:

- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- guest receive p99 `13,664 ms`, max `154,765 ms`;
- `6` stalls acima de `50 ms`, `3` acima de `100 ms`;
- `pre_read_gap_ms` p99 `0,779 ms`, max `57,141 ms`;
- classes: `1` `client_receiver_thread_pre_recv_gap`, `2`
  `guest_scheduler_correlated`, `3` `unaccounted_receive_or_nat`;
- ring drops/recoveries `469`, resyncs `31`;
- teardown limpo, sem poweroff forcado.

Interpretacao: a nova telemetria e util e deve permanecer. Ela mostrou que
parte dos outliers vem de atraso da thread de recepcao antes de chamar `recv`,
mas a prioridade `highest` da thread de recepcao, sem isolamento do processo da
VM, nao estabilizou o transporte e piorou o pior stall observado. Tambem
permanece ao menos um caso de espera real por cabecalho TCP/NAT sem gap global
do scheduler.

Decisao: nao promover `ReceiverThreadPriority=highest`; nao acoplar
DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo passo recomendado: nao insistir
em prioridade isolada; comparar rota sem NAT ou repetir afinidade apenas se a
alteracao de afinidade estiver permitida no host.

## R10 host-only transport route diagnostic - 2026-07-01

Foi adicionada ao orquestrador uma rota diagnostica sem NAT:

- `-GuestConnectHost`, para substituir `10.0.2.2` por outro endereco visto pelo
  convidado;
- `-TemporaryHostOnlyAdapterName`, que ativa temporariamente a NIC2 como
  host-only antes da partida da VM;
- registro de `guest_connect_host`, `temporary_hostonly_adapter_name` e `nic2`
  nos artefatos de host/teardown.

Ambiente detectado: `VirtualBox Host-Only Ethernet Adapter`, host
`192.168.56.1`, DHCP host-only ativo em `192.168.56.101-254`. A VM base seguia
com `nic1=nat` e `nic2=none`.

Rodada VM:

```text
runs/20260701-012549-dfn3-transport-48k-r9-tcp-native-receiver-guesthost192p168p56p1-hostonly-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic
```

Parametros: TCP, receptor nativo, `sink=memory`, `GuestConnectHost=192.168.56.1`,
`TemporaryHostOnlyAdapterName=VirtualBox Host-Only Ethernet Adapter`,
`BlocksPerPacket=1`, `RingDiagnostic`, `RingCapacityBlocks=12`,
`RingPrebufferBlocks=8`, `RingResyncLatenessMs=40`,
`ConsumerWaitMode=waitable_timer`, `ConsumerThreadPriority=highest`,
`ReceiverProcessPriority=high`, `GuestLaunchMode=Start`.

Resultado:

- gate `check`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- host-only aplicado para a rodada; teardown restaurou `nic2=none`;
- guest receive p99 `14,845 ms`, max `116,378 ms`;
- `14` stalls acima de `20 ms`, `1` acima de `50 ms`, `1` acima de `100 ms`;
- `pre_read_gap_ms` p99 `1,143 ms`, max `23,591 ms`;
- `header_wait_ms` p99 `14,556 ms`, max `244,202 ms`;
- o unico stall acima de `50 ms` foi classificado como
  `guest_scheduler_correlated`: sequencia `961`, intervalo `116,378 ms`,
  `header_wait_ms=116,294 ms`, `pre_read_gap_ms=0,008 ms`,
  scheduler gap max `106,761 ms`;
- ring drops/recoveries `564`, resyncs `66`;
- latencia de playout p99 `119,022 ms`;
- consumer deadline lateness p99 `44,476 ms`;
- teardown limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`,
  clipboard/drag-and-drop desabilitados, `nic1=nat`, `nic2=none`.

Interpretacao: a rota host-only removeu, nesta rodada, a classe
`unaccounted_receive_or_nat`, mas nao resolveu a baixa latencia. O outlier
restante foi correlacionado ao scheduler do convidado e ainda bastou para o ring
atingir o teto. Assim, NAT nao e a unica causa do bloqueio.

Decisao: manter `GuestConnectHost`/`TemporaryHostOnlyAdapterName` como
ferramentas diagnosticas, mas nao promover host-only como solucao. Nao acoplar
DeepFilterNet3, ponte PCM v1 ou SYSVAD. Proximo passo recomendado: se for
preciso continuar na VM, focar em scheduler/afinidade quando permitida; para
decisao de produto, priorizar validacao fora do VirtualBox/NEM.

## R11 local Windows loopback baseline - 2026-07-01

Foi executado um baseline nativo no proprio host Windows, em modo user-mode:

- sem VM;
- sem SYSVAD;
- sem ponte PCM v1;
- sem driver;
- sem alteracao de BIOS, Secure Boot, Hyper-V ou configuracao de boot;
- servidor Python e receptor C++ nativo comunicando por TCP `127.0.0.1`.

Os artefatos foram gravados em caminho ASCII externo ao OneDrive para evitar
falha de `std::filesystem`/`argv` estreito do receptor nativo com caminho
acentuado:

```text
C:\PTC3527-Private\local_loopback_runs\
```

### Transport-only

Rodada:

```text
C:\PTC3527-Private\local_loopback_runs\20260701-020331-dfn3-local-loopback-transport-only
```

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`, sem
ring/consumer.

Resultado:

- gate `accepted`;
- integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
- receive p99 `10,152 ms`;
- receive max `11,052 ms`;
- stalls acima de `20/50/100 ms`: `0/0/0`;
- scheduler max `4,500 ms`.

### Ring diagnostic

Rodada:

```text
C:\PTC3527-Private\local_loopback_runs\20260701-020131-dfn3-local-loopback-ring12-pre8-resync40
```

Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
`RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
`RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
`ConsumerThreadPriority=highest`, `ReceiverProcessPriority=high`.

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

Interpretacao: removido o VirtualBox/NEM, o mesmo transporte/receptor nativo
mantem cadencia e ring estavel no Windows host. Isso confirma que os outliers
observados na VM sao do ambiente de virtualizacao/scheduler/rede, nao uma falha
basica do protocolo, do hash, do framing, do ring ou do receptor C++.

Decisao: congelar a fase VM como "integridade funcional validada; tempo real
nao validavel de forma confiavel no VirtualBox/NEM". Proximo passo tecnico:
usar o baseline nativo para medir DFN3 inline em user-mode antes de qualquer
retorno a SYSVAD/driver.

## R12 local DFN3 inline user-mode baseline - 2026-07-01

Foi repetida a bancada nativa `wasapi_worker_bench` com DeepFilterNet3 C API
persistente em worker/ring, ainda sem VM, sem SYSVAD, sem ponte PCM v1 e sem
driver.

Artefatos:

```text
tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\
resultados\dfn3_local_dfn_inline\README.md
```

Resultado bruto:

- gate `PASS`;
- duracao `60 s`;
- frames DFN3 `6000`, com frame de `480` amostras/`10 ms`;
- worker p99 `2,189 ms`;
- worker p999 `2,617 ms`;
- worker max `5,168 ms`;
- worker acima de `4/8/10 ms`: `1/0/0`;
- callback p99 `0,043 ms`;
- callback p999 `0,087 ms`;
- callback max `0,155 ms`;
- underflow `0`;
- ring minimo antes do callback `480` amostras.

Resultado estavel B3, ignorando apenas o frame inicial do worker conforme
criterio historico da bancada:

- gate estavel `PASS`;
- worker p99 `2,188 ms`;
- worker p999 `2,598 ms`;
- worker max `3,957 ms`;
- worker acima de `4/8/10 ms`: `0/0/0`;
- callback p99 `0,043 ms`;
- underflow `0`.

Interpretacao: o host Windows sustenta o custo do DeepFilterNet3 C API com
folga em user-mode. Combinado com R11, o bloqueio observado na VM nao deve ser
atribuido ao custo basico do DFN3, ao transporte local, ao receptor C++ ou ao
ring em si.

Decisao: fase nativa user-mode aprovada para transporte + custo DFN3. O retorno
a ponte PCM v1/SYSVAD deve ser tratado como nova fase, com cautela propria de
driver, e nao como continuacao direta da validacao temporal da VM.
