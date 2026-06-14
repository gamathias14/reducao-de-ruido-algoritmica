# Historico auditado de incidentes da VM

## Escopo e limite da recuperacao

Este catalogo foi reconstruido a partir dos artefatos locais do projeto:

- `docs/checkpoints.md`;
- `docs/diario_tecnico.md`;
- `docs/auditoria_resultados.md`;
- READMEs e logs de `resultados/sysvad_checkpoint31` a
  `resultados/sysvad_checkpoint46_reopened`;
- scripts de orquestracao preservados;
- mensagens de continuidade dos checkpoints 31 a 46-R;
- threads historicas disponiveis no Codex, incluindo Checkpoints 35, 38, 39,
  40 e integracao RNNoise.

O catalogo nao depende da memoria de uma conversa. As threads disponiveis
foram lidas diretamente e cruzadas com os rastros locais. Chats indisponiveis
ou removidos so podem ser recuperados quando deixaram registro no workspace.

## Incidentes de infraestrutura

### VM no HD externo e desconexao de `E:`

- Origem: Checkpoints 31 e 33.
- Sintoma: API do VirtualBox e Guest Control bloqueados; ACPI sem resposta; VM
  terminou como `aborted`.
- Causa: desconexao do HD externo enquanto a VM mantinha disco ou metadados
  abertos.
- Correcao adotada: restaurar o snapshot anterior e descartar o delta.
- Prevencao:
  - manter `E:` conectado durante execucao, pausa, snapshot e shutdown;
  - verificar volume, sistema de arquivos e dirty bit antes da sessao;
  - usar o clone rapido no SSD para os ensaios;
  - manter a VM original em `poweroff`.
- Condicao de reboot: a sessao deve terminar e o snapshot deve ser restaurado;
  nao tentar continuar depois de uma falha de armazenamento.

### Clone rapido versus VM original

- Origem: Checkpoint 37.
- Sintoma: Guest Control da VM original no HD externo ficou preso em
  `starting` e retornou `VERR_TIMEOUT`.
- Causa observada: combinacao da VM historica no disco externo com estado
  degradado do Guest Control.
- Correcao adotada: clone consolidado
  `PTC3527-SYSVAD-LAB-FAST` no SSD interno.
- Prevencao: executar novos ensaios somente no clone rapido; preservar a VM
  original e sua arvore de snapshots como referencia.

### Chipset e boot inicial

- Origem: criacao da VM no Checkpoint 31.
- Sintoma: boot EFI travado com chipset ICH9.
- Correcao adotada: PIIX3.
- Prevencao: nao alterar chipset, firmware, TPM ou controladores durante
  ensaios de audio.

### Frontend `headless` altera a cadencia

- Origem: Checkpoints 37 e 39.
- Sintoma: captura MME desacelerada no modo `headless`.
- Controle: a mesma sonda em frontend GUI entregou 498 callbacks em 10 s.
- Correcao adotada: iniciar com `VBoxManage startvm ... --type gui` em qualquer
  ensaio que envolva audio ou temporizacao.
- Interpretacao: diferenca de frontend e fator de infraestrutura, nao efeito
  do DSP.

### Snapshot restaura configuracao da VM

- Origem: Checkpoint 33.
- Sintoma: restauracao de snapshot repos `audio_in=off`.
- Causa: configuracao da VM faz parte do estado restaurado.
- Correcao adotada: reabilitar a entrada e criar o snapshot aprovado com
  `audio_in=on`.
- Prevencao: depois de toda restauracao, validar `audio_in`, clipboard,
  drag-and-drop, NIC e snapshot atual antes de iniciar.

### Lock tardio do `VBoxSVC`

- Origem: integracao RNNoise e canal host-paced.
- Sintoma: comando seguinte falhou logo depois de shutdown ou restore.
- Mensagem observada: `The object is not ready` ou objeto ainda bloqueado.
- Correcao adotada: retry de `showvminfo` por pelo menos 15 s e espera entre
  desligamento, consulta e restauracao.
- Prevencao: nunca executar restauracao ou novo orquestrador concorrentemente.

### Cliente `VBoxManage` de consulta ficou preso

- Origem: Checkpoint 35, recuperado do chat historico.
- Sintoma: `showvminfo` manteve um pedido de lock embora nenhuma VM estivesse
  em execucao.
- Correcao adotada: confirmar `list runningvms` vazio, encerrar somente o
  processo cliente `VBoxManage` travado e preservar `VBoxSVC`.
- Regra: nao reciclar `VBoxSVC` antes de excluir um cliente de consulta preso.
  Reciclar o servico apenas quando nao houver VM nem cliente ativo e o lock
  orfao estiver confirmado.

## Incidentes de Guest Control

### Guest Additions ou logon ainda indisponiveis

- Origem: Checkpoints 32, 37 e integracao RNNoise.
- Sintoma: primeira chamada Guest Control falhou ou ficou presa durante boot.
- Causa: Guest Additions ou sessao interativa ainda nao prontos.
- Correcao adotada:
  - esperar `/VirtualBox/GuestAdd/Version`;
  - esperar `/VirtualBox/GuestInfo/OS/LoggedInUsers` maior que zero;
  - executar comando de sanidade antes da implantacao.
- Prevencao: prazo de ate sete minutos em boot frio; nao usar sleep fixo como
  unica condicao de prontidao.

### Primeiro PowerShell convidado excede probe curto

- Origem: Checkpoint 39, recuperado do chat historico.
- Sintoma: sonda de 45 s declarou Guest Control bloqueado.
- Causa: a primeira inicializacao de modulos PowerShell levou cerca de 53 s.
- Correcao adotada: ampliar o timeout de inicializacao sem ampliar a matriz
  indiscriminadamente.
- Prevencao: distinguir prazo de warm-up do prazo de cada cenario e registrar
  quanto tempo a sonda simples levou.

### Separador literal `--` perdido

- Origem: auditoria de backends e canal host-paced.
- Sintoma: `VBoxManage` tentou interpretar `-NoProfile` como opcao propria.
- Causa: expansao direta dos argumentos PowerShell consumiu ou reposicionou o
  separador do executavel convidado.
- Correcao adotada: montar array completo e incluir `"--"` como elemento
  literal antes do splatting.
- Prevencao: nao escrever `Invoke-VBox guestcontrol ... -- -NoProfile ...`
  diretamente.

### Sessoes presas em `starting`, `VERR_TIMEOUT`

- Origem: Checkpoint 37.
- Sintoma: comandos nao iniciavam e nao havia WAV ou JSON completo.
- Causa: estado degradado do canal Guest Control; nao foi demonstrada falha do
  produto.
- Correcao adotada: diagnosticar sessoes e processos, fechar sessoes orfas,
  aguardar Guest Additions e repetir uma unica sonda.
- Prevencao: nao iniciar comandos fragmentados em paralelo; usar um
  orquestrador completo e timeouts coerentes.
- Evidencia: tentativas nessas condicoes sao automacao invalida.

### `VERR_DUPLICATE` depois do shutdown

- Origem: Checkpoint 39 e integracao RNNoise.
- Sintoma: nova sessao rejeitada embora a listagem nao mostrasse sessao ativa.
- Causa: shutdown encerrou o canal antes de o VirtualBox concluir o retorno e
  deixou estado orfao.
- Correcao adotada:
  - validar desligamento por `VMState=poweroff`;
  - nao usar exit code da sessao que executa shutdown como confirmacao;
  - `closesession --all`, espera e nova sonda somente se a VM continuar
    ligada.

### Pausa longa do Guest Control invalida matriz

- Origem: Checkpoint 34.
- Sintoma: capturador terminou antes do produtor, zero consumo e
  `input overflow`.
- Causa: pausa anormal da orquestracao, nao configuracao da fila.
- Correcao adotada: descartar a matriz e nao usa-la na decisao.
- Prevencao:
  - iniciar consumidor antes do produtor;
  - usar heartbeat e resultado atomico;
  - dar margem de timeout maior que a duracao experimental;
  - separar timeout da casca de falha do algoritmo.

### `MainWindowHandle` invisivel

- Origem: Checkpoint 35.
- Sintoma: processo Guest Control nao encontrou a janela da UI interativa.
- Causa: diferenca de desktop/sessao entre Guest Control e a area interativa.
- Correcao adotada: abandonar `MainWindowHandle` como mecanismo de controle.
- Prevencao: preferir CLI, JSON de estado e Guest Properties. Console e
  teclado virtual ficam restritos a recuperacao.

### Processo grafico herda handles ou prende a pasta implantada

- Origem: Checkpoint 35, recuperado do chat historico.
- Sintomas:
  - Guest Control excedeu o prazo depois de iniciar processo grafico;
  - a pasta `app` nao podia ser substituida;
  - o processo existia na sessao grafica, mas o controlador nao via a janela.
- Correcao adotada:
  - encerrar seletivamente processos do checkpoint antes de expandir bundle;
  - aguardar liberacao dos handles;
  - iniciar UI de modo assincrono;
  - nao esperar stdout/stderr de processo grafico de longa duracao.
- Regra: implantacao deve limpar processos antes de remover ou expandir a
  pasta, nunca depois.

### Teclado virtual sem foco ou tela bloqueada

- Origem: Checkpoints 35, 37 e 39.
- Sintoma: atalhos abriram dialogo sem foco ou nao dispensaram a lock screen.
- Correcao adotada: cancelar explicitamente dialogos acidentais e usar teclado
  virtual apenas como ultimo caminho de shutdown normal.
- Prevencao: nao basear runs nominais em automacao visual.

## Incidentes de PowerShell e programas nativos

### `stderr` nativo vira `NativeCommandError`

- Origem: Checkpoints 32 e 37.
- Sintoma: programa nativo funcional escreveu em stderr e o PowerShell 5.1
  interrompeu o wrapper sob `$ErrorActionPreference="Stop"`.
- Correcao adotada: usar `Continue` apenas ao redor da chamada nativa,
  capturar `2>&1` e `$LASTEXITCODE`, restaurar a preferencia e entao decidir.

### Colecao de um elemento vira escalar

- Origem: auditoria MME/DirectSound/WASAPI.
- Sintoma: `.Count` ou indexacao falhou sob `Set-StrictMode`.
- Correcao adotada: envolver resultados de pipeline em `@(...)` e validar
  quantidade antes de `[0]`.

### Variavel automatica `$Host`

- Origem: canal host-paced.
- Sintoma: atribuicao falhou porque `$Host` e somente leitura e nomes de
  variavel nao diferenciam maiusculas.
- Correcao adotada: nomes explicitos como `$targetAddress`,
  `$hostResultPath` e `$processId`.
- Prevencao: nao usar `$host`, `$input`, `$args`, `$error`, `$matches`,
  `$pid` ou `$home` para variaveis locais.

### `Start-Process.ExitCode` nulo

- Origem: canal host-paced.
- Sintoma: processo terminou, mas `ExitCode` permaneceu vazio no PowerShell
  5.1.
- Correcao adotada: preferir `Start-Process -Wait -PassThru`; quando ainda
  necessario, usar `WaitForExit()`, `Refresh()` e teste explicito de `$null`.
- Regra experimental: para probes com escrita atomica, o JSON
  `status=completed` e o contrato principal.

### Continuadores de linha em comando remoto

- Origem: canal host-paced.
- Sintomas:
  - `Expand-Archive -DestinationPath` foi analisado como novo comando;
  - `--host` do Python foi interpretado como operador;
  - trechos multiline perderam o acento grave durante geracao/codificacao.
- Correcao adotada: comando curto em uma instrucao; comando longo em arquivo
  `.ps1` copiado ao convidado; `-EncodedCommand` UTF-16LE.

### Caminho ou versao do Python variavel

- Origem: Checkpoints 33 a 46.
- Risco: `python` no PATH pode apontar para executavel diferente entre sessoes.
- Correcao adotada: caminho validado
  `C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe` quando
  a versao faz parte do ensaio; PATH somente depois de sonda.

### `finally` apaga a causa original

- Origem: revisao do Checkpoint 39.
- Sintoma: erro de cleanup ou shutdown substituiu a falha experimental
  original.
- Correcao adotada: preservar a primeira excecao, registrar erros de cleanup
  separadamente e fazer restore idempotente.

## Incidentes de processos e timeouts

### Ordem produtor/capturador incorreta

- Origem: Checkpoint 34.
- Sintoma: capturador encerrou antes de o produtor entregar a janela.
- Correcao: iniciar consumidor/capturador primeiro, aguardar prontidao e so
  entao iniciar produtor.

### Processo em background sem ownership

- Risco observado ao longo dos checkpoints: sinais ou servidores podem
  sobreviver a uma tentativa.
- Correcao adotada: guardar o objeto retornado por `Start-Process -PassThru`,
  redirecionar logs por cenario e encerrar apenas o PID iniciado pelo
  orquestrador.

### Timeout menor que a janela real

- Origem: matrizes dos Checkpoints 34, 37 e 46-R.
- Sintoma: casca encerrou processo ainda valido ou processo terminou sem coleta.
- Correcao adotada: timeout calculado como duracao nominal mais margem de
  boot, inicializacao, drenagem e coleta; heartbeat durante matrizes longas.

### Carga preparatoria compete com a VM

- Origem: Checkpoint 39, recuperado do chat historico.
- Sintoma: produtor recebeu apenas 350-400 callbacks em 75 s.
- Hipotese inicial incorreta: stream ou Guest Control travado.
- Causa parcial: gerador do host construia 300 s de arrays antes da reproducao;
  mesmo apos corrigi-lo, `headless` continuou sendo o fator dominante.
- Correcao: gerar sinal por callback/bloco e medir host e VM separadamente.
- Regra: nao executar alocacao ou preprocessamento pesado concorrente com
  sonda de cadencia.

### Shutdown abrupto prematuro

- Origem: scripts antigos dos Checkpoints 37 e RNNoise.
- Risco: `poweroff` forcado pode produzir `aborted`, perder evidencias e exigir
  outro boot.
- Escada aprovada:
  1. shutdown iniciado no convidado sem esperar stdout/stderr;
  2. validar `VMState`;
  3. ACPI;
  4. teclado virtual apenas para shutdown normal;
  5. `poweroff` somente quando a VM ja esta irrecuperavel;
  6. restaurar snapshot imediatamente depois de `poweroff`.

### Argumentos incorretos para `shutdown.exe`

- Origem: fechamento do Checkpoint 38, recuperado do chat historico.
- Sintoma: o convidado exibiu apenas a ajuda do `shutdown.exe`.
- Causa: argumentos foram traduzidos ou repassados no formato errado.
- Correcao adotada: passar `/s`, `/t`, `0` como argumentos nativos separados
  depois do separador literal do Guest Control.
- Prevencao: validar primeiro com `/s /t 5`, sem esperar streams, e confirmar
  apenas por `VMState`.

### Matriz valida seguida de falha no fechamento

- Origem: Checkpoint 39.
- Sintoma: `RESULT=OK`, seis cenarios e analise completa existiam, mas o
  shutdown rompeu Guest Control.
- Correcao adotada: preservar a matriz e recuperar apenas o fechamento.
- Regra: falha posterior a artefatos atomicos completos nao autoriza repetir a
  captura; classificar separadamente execucao e teardown.

## Incidentes de audio e interpretacao

### Indices de dispositivo mudam

- Origem: Checkpoints 33, 36 e auditoria de backends.
- Sintoma: indice observado mudou entre backend ou boot; nome MME apareceu
  truncado.
- Correcao adotada: enumerar em cada sessao e selecionar por nome, host API e
  descritor fisico; indice e apenas evidencia local.

### WASAPI rejeita 16 kHz

- Origem: Checkpoint 37.
- Sintoma: `Invalid sample rate`.
- Correcao adotada em sondas posteriores: modo compartilhado com
  `WasapiSettings(auto_convert=True)`.
- Limite: conversao compartilhada nao prova suporte nativo a 16 kHz.

### WASAPI event-driven nao sinaliza na VM

- Origem: Checkpoint 32.
- Sintoma: cliente de captura nao recebeu eventos como esperado.
- Correcao adotada: polling no capturador externo.
- Limite: polling e backend fazem parte da camada de consumo, nao do tempo do
  RNNoise.

### MME, DirectSound e WASAPI distorcem tempo

- Origem: Checkpoint 46-R/INT-VM-CAD.
- Sintoma: pausas, rajadas, subentrega e sobre-entrega apesar de callbacks de
  320 amostras.
- Controle: bypass e RNNoise pareados mostraram a mesma classe de falha.
- Conclusao: a anomalia esta na entrada virtualizada/backend/callback, antes de
  processamento, fila local, driver e endpoint.
- Contorno aceito: PCM cadenciado pelo host em blocos de 320 amostras a 50 Hz.

### Pausas de agendamento atribuidas indevidamente ao DSP

- Regra derivada dos Checkpoints 39 e 46-R:
  - nunca atribuir pausa ao RNNoise sem bypass na mesma sessao;
  - registrar separadamente callback, processamento, fila local, fila do
    driver e captura do endpoint;
  - preempcao de VM e falha de automacao nao sao regressao de produto.

### Captura fisica invalida por mute ou comprimento

- Origem: Checkpoints 36 e integracao RNNoise.
- Sintoma: rodada sem nivel util ou janela nominal diferente do audio entregue.
- Correcao: classificar como invalida antes de escuta; verificar clipping,
  RMS, blocos inteiros, comprimento e tempo real.

## Incidentes de resultado e privacidade

### Analisador assumiu schema JSON errado

- Origem: integracao RNNoise.
- Sintoma: gate falhou apesar de o probe ter produzido resultado.
- Causa: nomes ou hierarquia inferidos sem ler o JSON real.
- Correcao: validar um artefato real, tipos, campos obrigatorios, contagens e
  `status`.

### Arquivo parcial confundido com sucesso

- Risco recorrente em timeouts.
- Correcao: escrita em arquivo temporario e renome atomico; aceitar somente
  JSON completo com `status=completed`.

### Artefatos parciais de tentativa anterior

- Origem: Checkpoint 39.
- Risco: diagnosticos obsoletos serem misturados com a rodada aceita.
- Correcao: criar raiz unica por `run_id`; quando houver retomada na mesma
  raiz, remover somente artefatos daquela tentativa depois de validar o
  caminho absoluto.

### Fim de linha inflou o diff

- Origem: Checkpoints 38 e integracao RNNoise, recuperado dos chats.
- Sintoma: milhares de linhas apareceram alteradas apos uma pequena adicao.
- Causa: conversao CRLF/LF.
- Correcao: restaurar o estilo original sem perder o conteudo novo.
- Prevencao: verificar line endings antes e depois de editar documentos
  historicos grandes.

### Ambiente de testes errado

- Origem: fechamento da integracao RNNoise.
- Sintoma: suite falhou por ausencia de `psutil` em `.venv-checkpoint34`.
- Causa: ambiente antigo usado por engano.
- Correcao: executar com o ambiente atual do projeto e registrar a falha de
  ambiente separadamente.
- Prevencao: preflight deve imprimir Python, ambiente virtual e dependencias
  criticas antes da suite.

### Pasta compartilhada transitoria

- Origem: Checkpoint 37.
- Uso: preservou evidencia parcial quando Guest Control falhou.
- Limite: nao resolveu a execucao e aumentou a superficie de estado.
- Regra: nao usar em runs normais; se usada para recuperacao, remover antes do
  encerramento e confirmar que nao permaneceu ativa.

### Clipboard, credenciais e audio privado

- Regras consolidadas:
  - clipboard e drag-and-drop desabilitados;
  - senha somente em arquivo temporario UTF-8 sem BOM, removido no `finally`;
  - nunca registrar senha em log ou linha de comando persistida;
  - WAV/PCM privado somente em `C:\PTC3527-Private`;
  - copiar ao convidado apenas quando indispensavel;
  - remover audio e temporarios antes do shutdown;
  - nunca versionar audio privado.

### Arquivos de credencial antigos permaneceram em `%TEMP%`

- Origem: auditoria historica de 2026-06-14.
- Achado: tres arquivos de 16 bytes dos Checkpoints 39/RNNoise ainda estavam
  presentes, apesar do cleanup documentado.
- Acao: os tres arquivos foram removidos sem exibir o conteudo; logs
  `acpi`/`vminfo` foram preservados.
- Prevencao: o preflight agora falha se encontrar nomes de arquivo temporario
  de credencial conhecidos.

## Matriz de decisao para evitar boots desnecessarios

### Continuar na mesma sessao

Nao desligar automaticamente quando:

- o erro ocorreu no host antes de qualquer comando convidado;
- houve erro de parse, quoting, caminho ou argumento;
- um helper do host falhou e a VM continua `running`;
- um JSON de um cenario falhou, mas heartbeat, processos e estado convidado
  continuam conhecidos;
- Guest Control teve uma falha transitoria, mas Guest Additions, logon e
  `VMState` continuam saudaveis;
- o problema pode ser corrigido no bundle host e reimplantado sem alterar
  driver, boot, dispositivo ou configuracao da VM.

Antes de retomar:

1. parar apenas os processos pertencentes ao cenario;
2. preservar logs e marcar a tentativa como automacao;
3. executar sonda de Guest Control;
4. limpar o diretorio temporario do cenario;
5. reimplantar somente o artefato corrigido;
6. executar smoke curto;
7. continuar a matriz apenas se o estado for completamente conhecido.

### Encerrar e restaurar

Restaurar o snapshot quando:

- houve desconexao, erro ou suspeita de I/O no armazenamento;
- a VM entrou em `aborted`, travou ou exigiu `poweroff`;
- driver, BCD, instalacao, dispositivo ou configuracao persistente mudou;
- o estado de processos ou filas do convidado nao pode ser determinado;
- houve drift de clipboard, NIC, pasta compartilhada ou `audio_in`;
- cleanup de audio privado ou credenciais nao pode ser confirmado;
- ocorreu bugcheck, reboot inesperado ou shutdown anormal;
- a sessao experimental terminou, com sucesso ou falha.

## Lacunas conhecidas nos scripts preservados

Os scripts historicos devem continuar preservados como evidencia, mas nao
devem ser copiados integralmente:

- `Invoke-Checkpoint37PopDiagnostics.ps1` contem os caminhos obsoletos
  `headless`, shared folder e `poweroff`;
- `Manage-SysvadLabVm.ps1` inicia a VM em `headless`;
- `Invoke-RNNoiseIntegrationVm.ps1` usa `poweroff` depois de falha dos
  mecanismos normais;
- `Invoke-InputCadenceBackendAuditVm.ps1` e
  `Invoke-HostPacedPcmVm.ps1` nao possuem um loop geral de recuperacao em
  sessao: uma excecao que chega ao `finally` encerra e restaura;
- alguns scripts antigos usam sleeps fixos, indices de audio e comandos
  remotos longos; essas escolhas nao sao precedentes aprovados.

Para evitar um reboot por erro corrigivel, o novo orquestrador deve capturar a
falha dentro do cenario, executar diagnostico/cleanup/smoke e somente relancar
a excecao ao `finally` quando a retomada segura tiver sido rejeitada.

## Cobertura por checkpoint

| Faixa | Problemas recuperados |
|---|---|
| 31-32 | BSOD no host, isolamento em VM, chipset, disco externo, boot, Guest Additions, WASAPI polling |
| 33-36 | desconexao de `E:`, `audio_in`, matrizes invalidas, UI/desktop, `aborted`, dispositivos, privacidade |
| 37-39 | `VERR_TIMEOUT`, clone SSD, GUI versus headless, stderr nativo, `VERR_DUPLICATE`, shutdown por `VMState` |
| 40-45 | orquestradores completos, hashes, watchdogs, limpeza, snapshots e validacoes sem captura desnecessaria |
| 46-R/INT-VM | logon, `--`, `StrictMode`, JSON, lock do VBoxSVC, nomes MME, sessao orfa |
| 46-R/CAD-EXTCLK | `The object is not ready`, multiline remoto, `$Host`, `ExitCode` nulo, pacing externo |

## Regra de manutencao

Todo novo incidente operacional deve ser acrescentado aqui com:

- data e checkpoint;
- comando ou etapa;
- sintoma exato;
- causa confirmada ou hipotese;
- se exigiu reboot;
- correcao;
- teste que impede recorrencia.
