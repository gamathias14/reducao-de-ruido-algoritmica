# Runbook de automacao da VM

## Escopo

Este documento consolida os problemas recorrentes observados na automacao da
VM `PTC3527-SYSVAD-LAB-FAST` e as praticas que devem ser reutilizadas nos
proximos ensaios.

Scripts de referencia atuais:

- `scripts/vm/Invoke-RNNoiseIntegrationVm.ps1`;
- `scripts/vm/Invoke-InputCadenceBackendAuditVm.ps1`;
- `scripts/vm/Invoke-HostPacedPcmVm.ps1`.

Novos orquestradores devem copiar as funcoes ja estabilizadas desses scripts,
em vez de reconstruir chamadas `VBoxManage` de memoria.

Os scripts sao referencia de primitivas, nao modelos integrais para copia:

- `Invoke-Checkpoint37PopDiagnostics.ps1` usa `headless`, pasta compartilhada
  e fallback de `poweroff`; esta obsoleto para audio;
- `Invoke-RNNoiseIntegrationVm.ps1` ainda conserva `poweroff` no fallback
  terminal; usar somente quando a VM ja estiver irrecuperavel;
- `Invoke-InputCadenceBackendAuditVm.ps1` e
  `Invoke-HostPacedPcmVm.ps1` encerram a sessao no `finally` depois de uma
  excecao nao tratada; a recuperacao em sessao deve ocorrer antes de deixar o
  bloco principal;
- `Manage-SysvadLabVm.ps1` inicia em `headless` e nao deve iniciar runs de
  audio;
- `New-SysvadLabVm.ps1` usa `headless` apenas para instalacao inicial, nao
  como precedente para ensaios de cadencia.

O registro historico, com origem e causa de cada regra, esta em
`docs/historico_incidentes_vm.md`.

## Economia de boots

Um boot da VM e um recurso experimental. Erros de sintaxe, caminhos, hashes,
argumentos e schema devem ser eliminados no host antes de iniciar a VM.

### Fase 1 - preflight sem ligar a VM

Confirmar:

- parse de todos os scripts PowerShell que serao usados;
- `compileall` ou testes dos modulos Python alterados;
- existencia e hash dos bundles, DLLs, executaveis e analisadores;
- portas, diretorios de resultado e espaco disponivel;
- estado, snapshot e configuracao do clone ativo no SSD;
- integridade do runtime local e ausencia de orquestrador concorrente;
- VM original desligada e inalterada, quando `E:` estiver conectado;
- endpoint de captura padrao do host;
- ausencia de helper antigo usando a porta ou o dispositivo.
- Python/venv que executara a suite e dependencias criticas;
- estilo de fim de linha dos documentos historicos que serao editados.

Executar o preflight somente-leitura antes de cada orquestrador de audio:

```powershell
.\scripts\vm\Test-VmAutomationPreflight.ps1 `
    -OrchestratorPath scripts\vm\Invoke-HostPacedPcmVm.ps1 `
    -AudioRun
```

O script nao inicia, desliga, restaura ou modifica a VM. Ele valida parse,
estado, snapshot, `audio_in`, clipboard, drag-and-drop, NIC, runtime SSD,
captura padrao, variaveis reservadas, separador Guest Control e uso de GUI.
A auditoria da VM original e informativa quando o disco externo nao esta
conectado e obrigatoria quando a fonte historica esta disponivel.

### Fase 2 - uma unica sessao GUI

Dentro de uma sessao experimental:

1. iniciar a VM uma vez em GUI;
2. esperar Guest Additions, logon e comando de sanidade;
3. implantar o bundle uma vez;
4. executar smoke curto;
5. executar cenarios pareados sem reboot entre eles;
6. coletar e validar JSON depois de cada cenario;
7. manter heartbeat e ownership dos processos;
8. limpar, desligar e restaurar uma vez ao final.

Nao restaurar entre cenarios quando nenhum estado persistente foi alterado e
o protocolo exige a mesma sessao para o pareamento.

### Fase 3 - recuperacao em sessao

Uma falha de comando nao implica desligamento imediato. Antes de encerrar:

1. registrar `VMState`, Guest Properties, sessoes e processos;
2. parar somente os PIDs iniciados pelo cenario;
3. preservar stdout, stderr, heartbeat e JSON parcial;
4. testar Guest Control com comando simples;
5. fechar sessoes orfas e aguardar quando aplicavel;
6. limpar apenas o diretorio temporario do cenario;
7. corrigir no host, reimplantar e executar um smoke.

Continuar somente quando o estado do convidado estiver completamente
determinado. A matriz detalhada de continuar/restaurar esta em
`docs/historico_incidentes_vm.md`.

Implementar a recuperacao dentro do loop de cenarios. Se a excecao escapar
para o `finally` externo, a politica continua sendo limpar, desligar e
restaurar.

## Invariantes antes da sessao

Confirmar antes de iniciar a VM:

- clone em `poweroff`;
- snapshot atual `checkpoint45-causal-wpt-validated`;
- VM original em `poweroff`;
- `audio_in=on`;
- `clipboard=disabled`;
- NIC existente preservada em NAT;
- captura padrao do host registrada;
- hashes dos artefatos de implantacao registrados;
- audio privado fora do repositorio.
- runtime `C:\PTC3527-Private\vm_runtime` integro e com ACL restrita;
- volume `E:` conectado somente quando a VM original ou outro artefato
  historico precisar ser operado ou auditado diretamente.

Executar a VM com frontend GUI quando houver audio. O modo `headless` ja
alterou a cadencia de captura.

Os orquestradores ativos leem credencial e referencia da configuracao no SSD.
O volume `E:` pode permanecer desconectado nesses runs. Nao desconecta-lo
enquanto a VM original estiver ligada, pausada ou com operacao pendente.

## Runtime local no SSD

Inicializar ou atualizar o runtime somente com as duas VMs desligadas:

```powershell
.\scripts\vm\Initialize-VmSsdRuntime.ps1
```

O inicializador:

- copia apenas a credencial de automacao e uma referencia da configuracao;
- registra origem, tamanho, snapshots e SHA-256 em `manifest.json`;
- restringe a pasta ao usuario atual, `SYSTEM` e administradores;
- nao copia VDI, NVRAM, snapshots ou audio;
- nao altera nem remove nenhum arquivo do disco externo.

A VM original completa permanece como arquivo historico em `E:`. Copia-la
para o SSD nao faz parte do fluxo ativo, pois o clone rapido ja reside no SSD
e a duplicacao consumiria aproximadamente 51 GiB.

Se o runtime local for perdido, corrompido ou precisar ser revertido,
reconectar `E:`, confirmar as duas VMs em `poweroff` e executar novamente
`Initialize-VmSsdRuntime.ps1`. Como a fonte externa nao foi alterada, essa
reconstrucao restaura credencial, referencia e manifesto sem recuperar discos
virtuais nem snapshots.

## Chamadas VBoxManage

### Separador de argumentos Guest Control

Problema:

- chamadas PowerShell expandidas consumiram o separador `--`;
- `VBoxManage` interpretou `-NoProfile` como opcao propria.

Regra:

- construir sempre um array de argumentos;
- incluir `"--"` como elemento literal do array;
- chamar o wrapper com splatting.

Padrao aprovado:

```powershell
$arguments = @(
    "guestcontrol", $VmName, "run",
    "--exe", "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "--username", $Username,
    "--passwordfile=$PasswordFile",
    "--timeout=$TimeoutMilliseconds",
    "--wait-stdout", "--wait-stderr", "--",
    "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
    "-EncodedCommand", $encoded
)
Invoke-VBox @arguments
```

Nao chamar `Invoke-VBox guestcontrol ... -- -NoProfile ...` diretamente.

### Comandos remotos

Problema:

- continuadores de linha com acento grave dentro de here-strings perderam o
  efeito depois da codificacao e execucao remota;
- parametros como `--host` passaram a ser analisados como operadores
  PowerShell;
- `Expand-Archive` em duas linhas tentou executar `-DestinationPath` como
  comando.

Regras:

- usar `-EncodedCommand` em UTF-16LE/Base64;
- comandos curtos devem ser uma unica instrucao;
- comandos longos devem ser copiados como arquivo `.ps1` ao convidado;
- nao depender de acento grave em comando remoto gerado dinamicamente;
- preferir arrays de argumentos dentro do script convidado.

### Saida nativa e ErrorActionPreference

Problema:

- stderr de `VBoxManage` pode virar `ErrorRecord` no Windows PowerShell 5.1 e
  interromper a captura do exit code quando a preferencia global e `Stop`.

Regra:

- dentro do wrapper nativo, trocar temporariamente
  `$ErrorActionPreference` para `Continue`;
- capturar `2>&1`, `$LASTEXITCODE` e restaurar a preferencia;
- somente depois decidir se deve lancar excecao.

## Estado do VirtualBox

### `The object is not ready`

Problema:

- logo depois de desligamento ou restauracao, `showvminfo` respondeu
  transitoriamente `The object is not ready`.

Regra:

- `Get-VmProperty` deve repetir por pelo menos 15 s, com intervalo de 500 ms;
- nunca concluir que a restauracao falhou por uma unica consulta.

### Guest Additions e logon

Problema:

- Guest Control foi acionado antes de Guest Additions e da sessao interativa
  estarem prontos.

Regra:

- aguardar simultaneamente uma versao valida em
  `/VirtualBox/GuestAdd/Version` e pelo menos um usuario logado;
- usar prazo de ate 7 min em boots frios;
- executar um comando simples de sanidade antes da implantacao longa.

### Sessoes orfas, `VERR_DUPLICATE` e `VERR_TIMEOUT`

Problema:

- shutdown rompeu a sessao antes do retorno;
- sessoes ficaram presas em `starting`;
- novas chamadas retornaram `VERR_DUPLICATE` ou `VERR_TIMEOUT`.

Regras:

- nao iniciar uma segunda sessao imediatamente apos shutdown;
- validar o desligamento por `VMState`, nao pelo exit code do Guest Control;
- em falha antes do shutdown, registrar:
  `guestcontrol <vm> list sessions` e `list processes`;
- tentar `guestcontrol <vm> closesession --all`, aguardar e testar novamente;
- se o Guest Control continuar indisponivel, usar ACPI;
- teclado virtual e recurso de recuperacao, nao caminho normal;
- nunca usar `poweroff` abrupto enquanto houver alternativa segura.

O primeiro erro Guest Control nao autoriza reboot. Reboot ou restore so ocorre
depois da coleta de estado e quando a sessao nao puder ser recuperada com
estado conhecido.

### Lock tardio do `VBoxSVC`

Problema:

- o processo do VirtualBox manteve lock por alguns segundos depois do
  desligamento.

Regra:

- aguardar `VMState=poweroff`;
- repetir consultas e restauracao em vez de disparar comandos concorrentes;
- nao abrir dois orquestradores para a mesma VM.

Se houver lock com `list runningvms` vazio, verificar primeiro processos
`VBoxManage` clientes presos. Encerrar somente o cliente confirmado. Reciclar
`VBoxSVC` apenas depois de confirmar ausencia de VM e de clientes ativos.

## PowerShell 5.1

### `StrictMode` e colecoes de um elemento

Problema:

- resultados de pipeline com um elemento viraram escalar e quebraram `.Count`
  ou indexacao sob `StrictMode`.

Regra:

- envolver resultados esperados como colecao em `@(...)`;
- validar quantidade antes de acessar `[0]`.

### Variaveis automaticas reservadas

Problema:

- `$Host` e somente leitura; PowerShell diferencia nomes sem considerar
  maiusculas/minusculas.

Regra:

- nao usar `$host`, `$input`, `$args`, `$error`, `$matches`, `$pid`, `$home`
  ou outros nomes automaticos como variaveis locais;
- usar nomes explicitos como `$hostResultPath`, `$targetAddress` e
  `$processId`.

### `Start-Process` e `ExitCode` nulo

Problema:

- no PowerShell 5.1, `ExitCode` permaneceu nulo mesmo depois de o processo
  encerrar.

Regras:

- preferir `Start-Process -Wait -PassThru` quando o exit code for necessario;
- `WaitForExit()` e `Refresh()` podem ser usados, mas nao garantem o campo
  nessa versao do PowerShell convidado;
- testar explicitamente `$null`;
- para probes que escrevem resultado atomico, preferir validar a existencia,
  o esquema e `status=completed` do JSON;
- nao converter exit code nulo em falha de produto.

### Processos em segundo plano

Regras:

- usar `Start-Process -WindowStyle Hidden` para helpers do host;
- redirecionar stdout e stderr para arquivos por cenario;
- manter referencia ao processo ativo;
- encerrar somente o processo iniciado pelo orquestrador no bloco `finally`.
- antes de substituir um bundle, encerrar os processos pertencentes a ele e
  aguardar a liberacao dos handles da pasta;
- processos graficos devem ser iniciados de modo assincrono, sem aguardar seus
  streams pelo Guest Control.

### Janelas da sessao interativa

Problema:

- processos iniciados por Guest Control nao enxergaram de forma confiavel o
  `MainWindowHandle` de aplicativos da area de trabalho.

Regras:

- nao usar `MainWindowHandle` como mecanismo principal de automacao;
- preferir CLI, arquivos de status e propriedades Guest Additions;
- quando uma acao visual for inevitavel, usar o console/teclado virtual do
  VirtualBox e registrar que foi uma recuperacao.

### Python do convidado

Regra:

- preferir o caminho explicito ja validado
  `C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe`;
- somente usar `python` pelo `PATH` depois de uma sonda simples confirmar o
  executavel e a versao.

## Dispositivos e resultados

### Nomes e indices de audio

Problema:

- nomes MME apareceram truncados;
- indices mudam entre boots e backends;
- WASAPI recusou 16 kHz sem conversao explicita.

Regras:

- enumerar dispositivos em cada sessao;
- selecionar por nome exato mais host API quando possivel;
- nao persistir indice como identidade;
- declarar `WasapiSettings(auto_convert=True)` quando usado;
- registrar que conversao compartilhada nao equivale a suporte nativo.

### Esquema JSON

Problema:

- scripts assumiram nomes ou hierarquia de campos diferentes do JSON real.

Regras:

- ler um artefato real antes de escrever o analisador;
- validar `status`, campos obrigatorios, tipos e contagens;
- nao inferir sucesso apenas pelo exit code;
- separar tentativas de automacao de rodadas experimentais aceitas.

## Copia de arquivos

Regras:

- usar caminhos literais;
- criar o diretorio convidado antes de `copyto`;
- em `copyfrom`, converter o destino host para barras `/` quando exigido pelo
  `VBoxManage`;
- verificar hash antes da execucao;
- audio privado nao deve ser copiado como arquivo para o convidado quando o
  canal de replay puder transmitir apenas os blocos;
- remover bundle, DLL e temporarios do convidado antes do shutdown.

## Encerramento obrigatorio

Todo orquestrador deve usar `try/finally` e:

1. encerrar helpers iniciados pelo host;
2. tentar limpar o diretorio temporario do convidado;
3. solicitar shutdown normal;
4. aguardar `VMState=poweroff`;
5. restaurar `checkpoint45-causal-wpt-validated`;
6. remover o arquivo temporario de senha;
7. confirmar clone, snapshot, clipboard, NIC e `audio_in`;
8. confirmar captura padrao do host;
9. validar a referencia local da VM original e, se `E:` estiver conectado,
   registrar se configuracao e snapshot externos permaneceram inalterados.

Uma falha durante a matriz nao dispensa a restauracao.

O encerramento obrigatorio se aplica ao fim da sessao, nao a cada erro
recuperavel de comando dentro da mesma sessao. Corrigir e retomar sem reboot e
permitido quando driver, boot, dispositivo, configuracao e processos
permanecem conhecidos.

`poweroff` forcado e ultimo recurso. Se for inevitavel, registrar a causa,
restaurar imediatamente o snapshot aprovado e nao usar o delta como evidencia.

Passar argumentos de `shutdown.exe` como elementos nativos separados:

```powershell
@(
    "guestcontrol", $VmName, "start",
    "--exe", "C:\Windows\System32\shutdown.exe",
    "--username", $Username,
    "--passwordfile=$PasswordFile",
    "--ignore-orphaned-processes", "--",
    "/s", "/t", "5", "/d", "p:0:0"
)
```

Nao esperar stdout/stderr desse comando. Confirmar somente por `VMState`.

Se a matriz publicou JSON atomico completo e falhou apenas no shutdown,
preservar a evidencia e recuperar o teardown; nao repetir a matriz.

## Evidencia experimental

Uma rodada so e valida quando:

- todos os cenarios planejados terminaram;
- os JSONs esperados existem e passam pelo analisador;
- hashes e contagens conferem;
- o estado final foi verificado;
- a falha nao ocorreu apenas na casca de automacao.

Tentativas que falham antes da matriz devem permanecer registradas, mas
marcadas explicitamente como nao experimentais.
