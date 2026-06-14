# Laboratorio virtual do SYSVAD

Para automacao de sessoes, ler primeiro
`docs/runbook_automacao_vm.md`. Ele consolida separador `--`, comandos
remotos, Guest Control, PowerShell 5.1, restauracao e criterios de evidencia.
Consultar tambem `docs/historico_incidentes_vm.md` para a origem de cada
regra, a matriz de recuperacao sem reboot e os casos que exigem restauracao.

## Arquitetura

- Hipervisor: Oracle VirtualBox 7.2.8.
- Convidado: Windows 11 Pro 25H2 x64, imagem oficial multi-edicao.
- Nome: `PTC3527-SYSVAD-LAB`.
- Recursos: 8 GiB de RAM, 4 vCPUs e VDI dinamico de 128 GiB.
- Chipset: PIIX3. O ICH9 travou a inicializacao EFI neste host.
- Armazenamento esperado: `E:\PTC3527-VM`.
- Rede: NAT.
- Firmware: EFI com TPM 2.0 e Secure Boot do convidado desativado.
- Integracoes host/convidado inicialmente desativadas: clipboard e arrastar/soltar.

O modo de teste e qualquer driver SYSVAD devem ser habilitados somente dentro
do Windows convidado. O host deve permanecer com Secure Boot, VBS e HVCI ativos.

O HD externo deve permanecer conectado enquanto a VM estiver ligada, pausada,
salvando snapshot ou desligando. Remova a unidade somente com a VM em
`poweroff` e depois de usar a remocao segura do Windows.

## Criacao

Conecte o HD externo como `E:` e use a ISO oficial do Windows 11. O indice 4
da imagem em portugues do Brasil corresponde ao Windows 11 Pro. Execute:

```powershell
$password = Read-Host 'Senha do usuario ptc3527' -AsSecureString
.\scripts\vm\New-SysvadLabVm.ps1 -IsoPath 'E:\ISO\Windows11Enterprise.iso' -Password $password
```

## Operacao por CLI

```powershell
.\scripts\vm\Manage-SysvadLabVm.ps1 -Action status
.\scripts\vm\Manage-SysvadLabVm.ps1 -Action start
.\scripts\vm\Manage-SysvadLabVm.ps1 -Action stop
.\scripts\vm\Manage-SysvadLabVm.ps1 -Action snapshot -SnapshotName 'base-limpa'
.\scripts\vm\Manage-SysvadLabVm.ps1 -Action snapshots
```

`poweroff` deve ser usado apenas quando o desligamento normal falhar.

Snapshots confirmados em 2026-06-11:

- `base-limpa`;
- `pre-sysvad`;
- `testsigning-pronto`;
- `sysvad-instalado`;
- `checkpoint31-revertido`.

Em 2026-06-12, antes do Checkpoint 33:

- VM confirmada em `poweroff`;
- snapshot atual `checkpoint32-revertido`;
- entrada de audio do VirtualBox alterada de `off` para `on`;
- saida de audio permaneceu habilitada;
- nenhum snapshot foi restaurado e nenhum driver foi carregado nessa etapa.

O Checkpoint 33 deve partir de `checkpoint32-functional-validated-v2`, pois
esse snapshot preserva a ponte PCM funcional. Antes de instalar dependencias
ou copiar o produtor Python, criar um novo snapshot
`checkpoint33-pre-dsp-user`.

Estado efetivamente preparado:

- `checkpoint32-functional-validated-v2` restaurado;
- `checkpoint33-pre-dsp-user` criado;
- a restauracao repôs `audio_in=off`;
- `audio_in` reabilitado;
- snapshot atual `checkpoint33-pre-dsp-user-audio-in`;
- VM em `poweroff`.

## Estado após o Checkpoint 35

- snapshot pré-UI:
  - `checkpoint35-pre-control-ui`;
  - UUID `a2242464-5d2e-4071-b65a-430e8e42ebe1`;
- snapshot funcional:
  - `checkpoint35-control-ui-validated`;
  - UUID `17eae767-97b4-4b16-89ba-6e4af54310f0`;
- VM em `poweroff`;
- `audio_in=on`;
- interface de controle implantada em `C:\PTC3527\checkpoint35\app`;
- configuração persistida no perfil do usuário convidado;
- cliente externo, três ciclos, fechamento ativo e contenção validados.

O VirtualBox marcou a instância como `aborted` depois do desligamento normal.
O snapshot funcional foi restaurado imediatamente, descartando o delta
terminal suspeito e normalizando o estado para `poweroff`.

## Estado após o Checkpoint 36

- HyperX identificado no host como `HyperX Quadcast`, endpoint
  `Microfone (USB Audio Device)`;
- snapshot pré-ensaio:
  - `checkpoint36-pre-hyperx-acoustic`;
  - UUID `c2c8b093-0b58-4053-8df1-a66d7abcb4c8`;
- cenários limpo e ruidoso concluídos;
- estabilidade de 630 s concluída;
- todos os WAVs e temporários removidos do convidado;
- zero processos residuais;
- desligamento normal concluído em `poweroff`;
- snapshot final:
  - `checkpoint36-hyperx-acoustic-validated`;
  - UUID `95b7a812-c34c-4967-9c7c-15415a31b980`;
- `audio_in=on`;
- `E:` saudável, operacional e não sujo;
- captura padrão do host restaurada para SteelSeries Sonar.

Os WAVs autorizados permanecem somente em diretório privado fora do
repositório e fora do snapshot da VM.

## Estado após a tentativa do Checkpoint 37

- snapshot de retorno:
  - `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
- VM em `poweroff`;
- `audio_in=on`;
- nenhuma pasta compartilhada temporária preservada na configuração;
- `E:` saudável, operacional e não sujo;
- captura padrão do host em `Microfone (USB Audio Device)`, HyperX direto;
- nenhuma instalação de SYSVAD, certificado ou `TESTSIGNING` no host.

O Guest Control apresentou sessões presas em `starting` e `VERR_TIMEOUT`.
Antes de retomar a matriz, abrir a VM interativamente, concluir o logon e
executar o script localmente. Não criar snapshot final do Checkpoint 37 antes
de obter a matriz bruto/pré-ponte/endpoint e testar uma mitigação.

## Clone rápido e fechamento do Checkpoint 37

- Clone consolidado: `PTC3527-SYSVAD-LAB-FAST`.
- Local: `C:\PTC3527-VM\PTC3527-SYSVAD-LAB-FAST`.
- Disco base único, dinâmico, marcado como SSD.
- Recursos preservados: 8 GiB de RAM, 4 vCPUs e `audio_in=on`.
- Limite de CPU ajustado de 90% para 100% somente no clone.
- Mídia auxiliar de instalação removida somente do clone.
- A VM original e toda sua árvore de snapshots permaneceram intactas em `E:`.
- A matriz foi concluída na sessão interativa do clone.
- Estado final:
  - VM original e clone em `poweroff`;
  - clone rápido no snapshot `checkpoint37-pop-diagnostics-validated`, UUID
    `f3f72efa-0aed-41db-b444-4fa06f1afd62`;
  - HyperX direto como captura padrão do host;
  - clipboard desabilitado;
  - nenhuma pasta compartilhada transitória ativa;
  - `E:` saudável, operacional e não sujo.

## Sequencia de seguranca

1. Instalar o Windows e as Guest Additions.
2. Aplicar as atualizacoes do Windows.
3. Executar `Initialize-SysvadLabGuest.ps1` como administrador no convidado.
4. Criar o snapshot `base-limpa`.
5. Instalar Visual Studio, WDK e ferramentas de diagnostico.
6. Criar o snapshot `toolchain-pronta`.
7. Habilitar modo de teste apenas no convidado.
8. Instalar e validar o SYSVAD.
9. Em caso de tela azul, restaurar `toolchain-pronta`.

O bootstrap desativa o UAC somente dentro desta VM isolada para permitir a
automacao por `VBoxManage guestcontrol`. Ele tambem desativa hibernacao e
suspensao e cria `C:\PTC3527`. Nao aplique esse script no Windows hospedeiro.

## Estado após o Checkpoint 38

- Guest Control voltou a responder no clone SSD em aproximadamente 7 s.
- A operação autônoma por `VBoxManage guestcontrol` deve ser tentada primeiro
  nos próximos ensaios.
- Os arquivos temporários e todo áudio privado foram removidos do convidado.
- O Windows convidado foi desligado normalmente por Guest Control.
- Clone rápido:
  - estado `poweroff`;
  - snapshot `checkpoint38-poll2-hyperx-validated`;
  - UUID `e74ea911-08a6-4778-a7a2-a5a4ab191480`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhuma pasta compartilhada transitória ativa.
- VM original:
  - estado `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - preservada sem alterações.
- Host com HyperX direto como captura padrão.
- `E:` saudável, operacional e não sujo.

## Estado após o Checkpoint 39

- A automação continuou por Guest Control, mas a VM precisou ser iniciada com
  frontend GUI para manter a cadência da captura MME.
- A matriz determinística concluiu e publicou `RESULT=OK`.
- O desligamento imediato encerrou o canal Guest Control antes do retorno. Uma
  nova sessão encontrou `VERR_DUPLICATE`, apesar de a listagem não mostrar
  sessões ativas.
- O orquestrador passou a validar desligamento por `VMState`, preferir ACPI e
  iniciar `shutdown.exe` diretamente sem depender do exit code da sessão.
- No fechamento concreto, o estado órfão não respondeu a ACPI. O comando de
  desligamento foi digitado autonomamente pelo teclado virtual do VirtualBox.
- Clone rápido:
  - `poweroff`;
  - snapshot `checkpoint39-quality-boundary-validated`;
  - UUID `21ad4f02-4dfa-48d1-b683-7a6e7b502160`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhuma pasta compartilhada transitória.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - sem alterações.
- HyperX direto restaurado como captura padrão.
- `E:` saudável, operacional e não sujo.

## Estado apos o Checkpoint 40

- A matriz foi executada no clone SSD com frontend GUI e Guest Control.
- Nenhum compartilhamento transitorio foi usado.
- A fonte identificavel substituiu as amostras capturadas dentro do callback;
  nenhuma nova voz foi gravada.
- Os resultados brutos deterministas foram analisados fora do repositorio e
  removidos depois da publicacao de hashes e metricas.
- `drop-newest` foi testado e rejeitado; o padrao continua `drop-oldest`.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint40-transport-separated-validated`;
  - UUID `693e8851-f905-4e98-b526-671c904965e9`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhuma pasta compartilhada transitoria.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - configuracao e hash preservados.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.
- A escuta posterior nao exigiu novo boot nem nova gravacao:
  - A bruto limpo;
  - B pre-bridge com chiado metalizado leve durante fala;
  - C endpoint com agravamento consideravel do mesmo artefato.
- O snapshot e o estado seguro permanecem inalterados.

## Estado apos o Checkpoint 41

- A VM FAST foi usada apenas para validar compilacao e execucao deterministica
  da opcao de suavizacao; nenhuma captura de audio foi iniciada.
- Nenhum WAV privado foi copiado para o convidado.
- O parametro experimental ficou implantado no app com default `0.0`.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint41-musical-noise-limit-validated`;
  - UUID `12ea0826-47f6-48c1-a1b1-2701f000e19a`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhum compartilhamento transitorio.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - configuracao e hash preservados.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.

## Estado apos o Checkpoint 42

- A VM FAST foi usada somente para validacao sintetica do Wiener causal.
- Nenhuma captura de audio foi iniciada e nenhum WAV privado entrou no
  convidado.
- Os quatro pisos Wiener produziram saida finita e deterministica.
- O diretorio temporario `C:\PTC3527\checkpoint42` foi removido.
- O app persistente em `C:\PTC3527\checkpoint35\app` usa a assinatura anterior
  de `CausalProcessorConfig`, sem `gain_smoothing`.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint42-wiener-limit-validated`;
  - UUID `b9909e84-c1d7-4948-9c5f-21870ff57f69`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhum compartilhamento transitorio.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - configuracao e hash preservados.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.

## Estado apos o Checkpoint 43

- A VM FAST foi usada somente para validacao sintetica do `wavelet_soft`.
- Nenhuma captura foi iniciada e nenhum WAV privado entrou no convidado.
- Os niveis 3, 4 e 5 produziram saida finita e deterministica.
- O diretorio temporario `C:\PTC3527\checkpoint43` foi removido.
- O PyWavelets emitiu aviso durante threshold soft de coeficientes nulos; o
  processador realtime saneou a saida.
- O desligamento atingiu `poweroff`, mas o VirtualBox marcou posteriormente o
  clone como `aborted`. O snapshot terminal foi restaurado, descartando o
  delta e normalizando o estado.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint43-wavelet-limit-validated`;
  - UUID `2a530e40-1981-4321-839f-88060d78cc2c`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhum compartilhamento transitorio.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - configuracao e hash preservados.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.

## Estado apos o Checkpoint 44

- A VM FAST foi usada somente para validar o parametro de escala existente no
  nucleo offline.
- Nenhuma captura foi iniciada, nenhum WAV privado entrou no convidado e
  nenhuma configuracao persistente foi alterada.
- As escalas `0.10`, `0.25`, `0.50` e `0.75` produziram saidas finitas e
  deterministicas.
- O diretorio temporario `C:\PTC3527\checkpoint44` foi removido.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint44-wavelet-threshold-limit-validated`;
  - UUID `3024cc30-6a67-436b-9154-36d3b57529c8`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhum compartilhamento transitorio.
- VM original:
  - `poweroff`;
  - snapshot `checkpoint37-pre-pop-diagnostics`;
  - UUID `e47138eb-df0d-4d27-9948-e17503b7cc25`;
  - configuracao e hash preservados.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.

## Estado apos o Checkpoint 45

- A VM recebeu somente o modulo WPT causal e um validador sintetico
  temporarios.
- Nenhum audio privado entrou no convidado.
- A validacao confirmou reset, independencia do futuro, finitude, custo medio
  de `2.74 ms` e estado de 2.144 bytes.
- O diretorio `C:\PTC3527\checkpoint45` foi removido.
- Clone rapido:
  - `poweroff`;
  - snapshot `checkpoint45-causal-wpt-validated`;
  - UUID `2255a9ed-2bb7-43c5-8b2c-5d10a70c140d`;
  - `audio_in=on`;
  - clipboard desabilitado;
  - nenhum compartilhamento transitorio.
- VM original preservada no snapshot
  `e47138eb-df0d-4d27-9948-e17503b7cc25`.
- HyperX direto como captura padrao.
- `E:` saudavel, operacional e nao sujo.
