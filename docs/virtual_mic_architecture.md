# Arquitetura do Virtual Microphone proprio

Data-base: 2026-06-08

Objetivo: especificar uma trilha propria para que aplicativos externos do
Windows enxerguem um endpoint de captura do tipo `PTC Noise Reduction
Microphone`, alimentado pelo pipeline STFT causal adaptativo ja validado no PC.
Este documento abre o Checkpoint 29. Ele ainda nao implementa driver, nao liga
o SYSVAD ao DSP e nao promete distribuicao real sem assinatura.

## Fontes oficiais consultadas

- SYSVAD Virtual Audio Device Driver Sample:
  https://learn.microsoft.com/en-us/samples/microsoft/windows-driver-samples/sysvad-virtual-audio-device-driver-sample/
- Sample Audio Drivers:
  https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/sample-audio-drivers
- Driver signing:
  https://learn.microsoft.com/en-us/windows-hardware/drivers/install/driver-signing
- Test-signing:
  https://learn.microsoft.com/en-us/windows-hardware/drivers/install/introduction-to-test-signing
- Partner Center for Windows Hardware:
  https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/

## Decisao arquitetural inicial

A arquitetura-alvo fica separada em duas partes:

- Processo ou servico de usuario:
  - captura o microfone fisico;
  - converte para mono 16 kHz quando necessario;
  - processa blocos de 20 ms com `CausalSTFTProcessor`;
  - publica audio processado em um buffer local.
- Driver virtual de captura:
  - expoe um endpoint de microfone para aplicativos externos;
  - consome o audio processado vindo do processo de usuario;
  - entrega blocos em formato aceito pelo motor de audio do Windows;
  - deve se comportar de forma previsivel quando o processo de usuario para ou
    quando o buffer esvazia.

Separar DSP em usuario e endpoint em driver reduz risco: o algoritmo validado
continua testavel em Python/C++ de usuario, enquanto o driver fica responsavel
por expor o dispositivo e transportar amostras.

## Alternativas

### Driver virtual baseado em SYSVAD

Caminho principal para prototipo proprio. O SYSVAD e o sample oficial da
Microsoft para driver virtual de audio WDM/WaveRT e serve como ponto de partida
para expor endpoints virtuais. A primeira meta nao e alterar DSP, mas compilar
e instalar o sample sem modificacoes.

Vantagens:

- endpoint proprio visivel para apps externos;
- base oficial de driver de audio;
- caminho tecnicamente alinhado ao objetivo final.

Riscos:

- complexidade de kernel-mode/driver;
- dependencia de Visual Studio, SDK, WDK e ambiente Windows;
- instalacao exige administrador e assinatura/test-signing;
- distribuicao real exige processo Microsoft.

### APO

Um Audio Processing Object pode processar audio em endpoints existentes. E uma
rota relevante se o objetivo virar aplicar DSP sobre um endpoint ja instalado.
Ela nao resolve sozinha o desejo principal de expor um novo microfone proprio
alimentado por audio processado.

### VB-Cable como controle temporario

VB-Cable ou equivalente pode continuar util como controle experimental ou MVP
de comparacao, mas nao e a solucao final da trilha propria. A documentacao e a
defesa devem deixar isso explicito.

## Requisitos do Checkpoint 30

- Visual Studio instalado com carga de trabalho C++.
- Windows SDK compativel.
- Windows Driver Kit (WDK).
- Repositorio `Windows-driver-samples` com submodulos inicializados.
- Acesso ao sample `audio/sysvad`.
- Build do SYSVAD sem modificacoes.
- Registro de versoes, erros e dependencias.

Comandos esperados para preparar o repositorio de samples:

```powershell
git clone https://github.com/microsoft/Windows-driver-samples.git
cd Windows-driver-samples
git submodule update --init
```

O build deve ser feito inicialmente pelo Visual Studio, abrindo a solucao do
SYSVAD e garantindo configuracao/plataforma consistente para todos os projetos.

## Achados de ambiente do Checkpoint 30

Auditoria concluida em 2026-06-11:

- Visual Studio Community 2026 `18.7.0` e MSBuild `18.7.1.23011`;
- Windows SDK `10.0.28000.1721`;
- WDK `10.1.28000.1839`;
- toolsets `WindowsApplicationForDrivers10.0` e
  `WindowsKernelModeDriver10.0` integrados em `v180`;
- bibliotecas Spectre x64 de ATL, ATL/MFC e runtime instaladas;
- build `Debug|x64` do SYSVAD oficial concluido sem retarget ou edicao;
- host aprovado:
  `MSBuild\Current\Bin\amd64\MSBuild.exe`;
- pasta gerada:
  `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad\x64\Debug\package`;
- clone oficial permaneceu limpo.

O MSBuild x86 do comando inicial nao e adequado ao WDK 28000 instalado:
`InfVerif.dll` e fornecido para x64/ARM64, e a validacao com as ferramentas
x86 falhou. O host amd64 concluiu compilacao, validacao de assinatura, geracao
de catalogo e assinatura de teste.

O certificado de teste foi gerado, mas nao foi instalado. A assinatura aparece
como raiz nao confiavel no host, comportamento esperado antes da preparacao do
Checkpoint 31.

A instalacao local do driver, test-signing, alteracoes de boot e integracao do
DSP continuam fora do Checkpoint 30. Depois da reinicializacao, o Visual Studio
foi validado como completo, inicializavel e sem reboot pendente. Um novo build
`Debug|x64` pelo MSBuild amd64 terminou sem erros nem avisos.

Na pre-auditoria do Checkpoint 31, o Secure Boot foi identificado como
habilitado. O estado do BitLocker nao pode ser consultado sem elevacao e
permanece desconhecido. Nenhuma alteracao de firmware, boot, certificado ou
driver deve ocorrer antes dessa auditoria administrativa e do registro do plano
de reversao.

## Requisitos do Checkpoint 31

- Maquina de teste, idealmente separada da maquina principal.
- Permissao administrativa.
- Test-signing habilitado somente para desenvolvimento:

```powershell
bcdedit /set TESTSIGNING ON
```

- Reboot apos habilitar test-signing.
- Certificado de teste instalado conforme pacote gerado.
- Ferramenta `devcon.exe` localizada no WDK.
- Plano de reversao:

```powershell
bcdedit /set TESTSIGNING OFF
```

e reboot.

Tambem registrar qualquer interacao com BitLocker, Secure Boot ou politica de
seguranca local antes de alterar boot/test-signing.

### Auditoria de abertura do Checkpoint 31

Em 2026-06-11, a auditoria elevada confirmou:

- Secure Boot habilitado;
- BitLocker desligado e `C:` totalmente descriptografado;
- VBS e Integridade de memoria/HVCI ativos;
- `TESTSIGNING` ainda ausente;
- nenhum ponto de restauracao, copia de sombra ou Windows Backup;
- Windows Recovery Environment habilitado;
- apenas `11,37 GiB` livres em `C:`;
- nenhum dispositivo, pacote identificado ou certificado SYSVAD instalado.

O Checkpoint 31 permanece antes da instalacao. A maquina principal nao deve
avancar para a alteracao de Secure Boot sem uma estrategia de recuperacao
aceita pelo usuario. HVCI deve permanecer habilitada na primeira tentativa;
qualquer proposta de desabilita-la exige uma auditoria e um consentimento
separados.

Apos autorizacao, foi criado o ponto de restauracao
`PTC3527 Checkpoint 31 pre-SYSVAD`, sequencia `281`, e o BCD foi exportado
antes de qualquer mudanca. A assinatura do driver e do catalogo usa page
hashes (`/ph`) e SHA-256. Esses controles reduzem o risco, mas nao substituem
um backup completo nem revertem automaticamente configuracoes de firmware.

### Resultado do Checkpoint 31 em alvo virtual

A tentativa na maquina principal foi encerrada depois do bugcheck no caminho
Bluetooth HFP do build Debug. A validacao foi retomada em uma VM Windows 11
separada, protegida por snapshots e armazenada no HD externo.

No convidado, o SYSVAD oficial foi instalado sem alteracoes e apareceu como
`SYSVAD (with APO Extensions)`. O dispositivo `ROOT\MEDIA\0000`, o servico
kernel e os endpoints virtuais permaneceram iniciados depois de um novo boot.
Nao ocorreu tela azul na VM.

A reversao removeu os pacotes `oem5.inf`, `oem6.inf` e `oem7.inf`, o
dispositivo, o certificado de teste e `TESTSIGNING`. A ausencia de residuos foi
confirmada depois de novo boot. O snapshot atual e `checkpoint31-revertido`;
`sysvad-instalado` preserva o estado funcional para o Checkpoint 32.

O disco virtual depende de conexao continua com o HD externo. A unidade nao
pode ser desconectada enquanto a VM estiver ligada, pausada, salvando snapshot
ou desligando.

## Requisitos do Checkpoint 32

Definir a ponte entre processo de usuario e driver antes de capturar microfone
real. Candidatos:

- ring buffer em memoria compartilhada;
- IPC local com fila de blocos;
- servico local que mantenha o buffer vivo;
- sinal sintetico como primeira fonte.

Regras iniciais:

- prototipar com tom ou ruido sintetico;
- medir underrun/overrun do buffer;
- definir comportamento de fallback para silencio, ultimo bloco ou tom de teste;
- documentar formato de amostra, tamanho de bloco, taxa e timestamps.

### Decisao implementada no Checkpoint 32

Foi escolhida uma interface de dispositivo explicita com IOCTLs
`METHOD_BUFFERED` e ring buffer nao paginado. A interface usa o GUID
`{E9342D3D-0B9A-4C94-A786-46D97A44A1A2}` e contrato binario versao `1`.

O endpoint escolhido e o `MicIn` (`External Microphone Headphone`), pois sua
tabela nativa ja anuncia PCM mono de 16 bits a 16 kHz. O bloco tem 320 frames,
640 bytes e 20 ms. A fila comporta 50 blocos, equivalentes a 1 segundo.

O produtor e o consumidor compartilham estado protegido por spin lock. Isso e
necessario porque a escrita via IOCTL ocorre no contexto da requisicao, enquanto
o consumo de captura pode ocorrer no callback do timer WaveRT em
`DISPATCH_LEVEL`. A fila e seus dados ficam somente em memoria nao paginada.

Politicas:

- underrun: preencher a regiao WaveRT solicitada com zeros;
- overrun: rejeitar e descartar o bloco novo;
- sequencia: monotona e estrita depois do primeiro bloco;
- produtor: um unico `FILE_OBJECT` por vez;
- desconexao/cleanup: liberar o produtor, esvaziar a fila e voltar a silencio;
- escopo: somente `MicIn` no formato exato de 16 kHz usa a ponte.

Alternativas rejeitadas nesta etapa:

- propriedade KS customizada: acopla o transporte a um handle de filtro;
- memoria compartilhada: aumenta a complexidade de mapeamento e vida util;
- fila de escritas pendentes: exige cancelamento e gerenciamento de IRPs;
- tom interno: nao demonstra a ponte usuario/driver.

O ponto de consumo permanece em
`CMiniportWaveRTStream::WriteBytes`, substituindo `GenerateSine` apenas no alvo
e formato selecionados. Outros endpoints e formatos mantem o comportamento
baseline do SYSVAD.

### Resultado funcional do Checkpoint 32

A abertura direta da interface pelo PortCls exigiu uma referencia explicita.
A versao final registra a interface como
`\\?\root#media#0000#{E9342D3D-0B9A-4C94-A786-46D97A44A1A2}\ptcpcm` e
intercepta `CREATE`, `CLOSE`, `CLEANUP` e os IOCTLs apenas para
`FileName == \ptcpcm`. Isso evita interferencia com os fluxos KS normais.

O capturador WASAPI usa modo exclusivo de 16 kHz com polling do
`IAudioCaptureClient`; o endpoint SYSVAD nao sinalizou de forma confiavel o
modo orientado a evento na VM.

Validacao na VM:

- WAV de 12,0 s, mono, 16 bits, 16 kHz e 192.000 frames;
- pico `0,25`, RMS global `0,1462` e frequencia dominante `440,0 Hz`;
- cauda de silencio confirmada depois da parada do produtor;
- overrun, underrun, versao/tamanho invalidos e erro de sequencia observados
  nos contadores;
- exclusividade de produtor confirmada por `ERROR_BUSY (170)`;
- reconexao e novo boot aprovados.

O ritmo efetivo do consumidor na VM ficou abaixo dos 50 blocos/s nominais em
alguns ensaios, produzindo overrun mesmo com `pace=1`. Esse resultado deve ser
tratado no Checkpoint 33 com pacing orientado ao nivel da fila, em vez de
temporizacao fixa do produtor.

## Requisitos do Checkpoint 33

- Capturar microfone real no processo de usuario.
- Processar com `CausalSTFTProcessor`.
- Alimentar o endpoint virtual.
- Validar com um app externo simples, como Gravador do Windows, navegador ou
  ferramenta de chamada.
- Registrar latencia estimada, falhas de buffer, glitches audiveis e logs.

### Implementacao host-side aberta em 2026-06-12

O driver e o protocolo v1 permanecem congelados. A integracao foi adicionada
ao processo Python em `realtime_audio/ptc_pcm_bridge.py` e
`realtime_audio/windows_realtime.py`.

Fluxo:

1. `sounddevice.InputStream` captura mono a 16 kHz em blocos de 20 ms;
2. `RealtimeBlockProcessor` usa o mesmo `CausalSTFTProcessor` ja validado;
3. a saida `float32` e limitada a `[-1, 1]` e convertida para PCM16;
4. uma fila limitada desacopla o callback de audio dos IOCTLs;
5. uma thread consulta `IOCTL_PTC_PCM_GET_STATS`;
6. novos blocos sao enviados apenas abaixo da profundidade alvo;
7. os contadores do processo e do driver sao gravados no JSON final.

O controle por profundidade responde ao achado do Checkpoint 32 de que o
consumidor WaveRT da VM nem sempre manteve exatamente 50 blocos/s. O produtor
nao usa mais apenas um temporizador fixo. Para limitar latencia, a fila de
usuario descarta o bloco mais antigo quando cheia; a sequencia monotona e
atribuida somente ao retirar o bloco para envio.

O contrato foi conferido por testes host-side:

- configuracao: 24 bytes;
- bloco: 664 bytes, incluindo 640 bytes de PCM;
- estatisticas: 112 bytes;
- sequencias comecam em zero e crescem apenas em escritas enviadas;
- ausencia da interface no host falha sem instalar ou alterar componentes.

A suite terminou com `53 passed` e `11 subtests passed`. A validacao funcional
na VM ainda deve comparar `bypass` e `stft_subtraction`, capturar o endpoint
por um aplicativo externo e registrar underrun, overrun, descarte local e
latencia estimada.

## Nota de renumeracao apos o Checkpoint 33

O fechamento do Checkpoint 33 priorizou nivel controlado e refinamento de
latencia no Checkpoint 34. A interface minima descrita abaixo foi adiada para o
proximo checkpoint de produto; esta secao permanece como especificacao da UI,
nao como registro do Checkpoint 34 executado.

## Requisitos da interface minima

Interface minima esperada:

- seletor de microfone fisico;
- iniciar/parar;
- preset ou agressividade;
- medidor de nivel;
- status do endpoint virtual;
- blocos processados, blocos perdidos e latencia estimada;
- persistencia da ultima configuracao.

Essa UI deve ser utilitaria: controle de operacao, nao landing page.

### Implementação concluída no Checkpoint 35

A interface mínima foi implementada em Python com `tkinter`. A camada visual
não possui captura, DSP ou IOCTL: essas operações pertencem ao
`VirtualMicController`, que publica snapshots imutáveis para atualização da
janela.

O controlador reutiliza `RealtimeBlockProcessor`, `PtcPcmBridgeClient` e
`BridgePacedWriter`. O caminho principal continua em STFT causal adaptativa,
16 kHz e blocos de 20 ms. A profundidade do driver permanece em `2` e a fila
local em `4`.

O fechamento solicita stop e aguarda até três segundos. Erros da ponte ou da
captura aparecem como estado de erro. O medidor usa RMS suavizado e não
armazena áudio. A preferência do usuário fica em
`%LOCALAPPDATA%\PTC3527\virtual_mic_ui.json`.

Na VM, três ciclos de operação, cliente externo, persistência, fechamento
ativo e contenção por segundo produtor foram aprovados. A latência continua
rotulada como estimativa por componentes, não como medição física ponta a
ponta.

## Requisitos da etapa de distribuicao

Separar duas narrativas:

- Prototipo academico:
  - test-signing;
  - instalacao local;
  - sem promessa de distribuicao para terceiros.
- Distribuicao real:
  - driver kernel-mode assinado;
  - conta no Hardware Dev Center/Partner Center;
  - certificado EV associado;
  - possivel attestation ou HLK;
  - instalador, desinstalador, atualizacao e suporte.

Pela documentacao Microsoft consultada, drivers kernel-mode em Windows moderno
precisam de assinatura para carregar, e o fluxo de release passa pelo dashboard
de hardware para publicacao/certificacao. Test signatures sao apenas para
desenvolvimento e teste.

## Entregaveis da trilha

- Checkpoint 30: SYSVAD baseline compilado, sem DSP.
- Checkpoint 31: endpoint virtual de exemplo instalado em modo de teste.
- Checkpoint 32: buffer/IPC validado com sinal sintetico.
- Checkpoint 33: STFT causal alimentando endpoint virtual.
- Checkpoint 34: nivel controlado, telemetria e refinamento de latencia.
- Proximo checkpoint de produto: UI minima de controle.
- Etapa posterior: auditoria de assinatura, custos e distribuicao.

## Nao afirmar ainda

- Que existe driver de produção `PTC Noise Reduction Microphone` pronto.
- Que o driver pode ser distribuido sem assinatura.
- Que o modo de teste e aceitavel para usuarios finais.
- Que a latencia fisica ponta a ponta foi medida.

## Resultado acústico do Checkpoint 36

O caminho físico completo foi confirmado com um HyperX Quadcast:

```text
HyperX -> captura da VM -> STFT adaptativa -> ponte PCM v1
       -> endpoint SYSVAD -> cliente externo
```

O cliente externo recebeu áudio processado não nulo. A arquitetura, portanto,
está funcional como transporte e integração.

O resultado perceptual, entretanto, expôs uma limitação operacional:

- 4.491 descartes locais e 10.626 underruns em 630 s;
- pipocos audíveis no bruto e, principalmente, no processado;
- preferência clara pelo bruto nos cenários limpo e ruidoso;
- redução de ruído marrom de aproximadamente `2,75 dB RMS`.

Esses dados sugerem que o próximo trabalho técnico deve priorizar continuidade
do consumidor e investigação do fluxo de buffers, sem reotimizar o DSP antes
de isolar a origem dos artefatos. A latência de `211,4 ms` exibida ao final
continua sendo estimativa por componentes.

Estado da implementação PC:
**Protótipo funcional, com validação perceptual pendente**.

## Instrumentação de continuidade

O Checkpoint 37 adicionou observabilidade sem alterar a STFT nem o protocolo
PCM v1:

- índices de blocos da captura até a fila local;
- timestamps monotônicos e intervalos entre callbacks;
- status do `sounddevice`;
- eventos de submissão, descarte local e envio pela ponte;
- polling configurável do escritor e do cliente de diagnóstico;
- detector de saltos, zeros, blocos repetidos ou ausentes e descontinuidades
  entre fronteiras;
- marcador JSON atômico do ciclo de vida do stream.

A matriz na VM não foi concluída por instabilidade do Guest Control. Portanto,
essa instrumentação ainda não autoriza localizar a fronteira dominante dos
pipocos. O próximo ensaio deve começar pela captura bruta em sessão interativa
estável e só depois avançar para bypass, STFT e endpoint.

## Fronteira localizada no Checkpoint 37

A retomada interativa mostrou:

```text
fonte -> captura MME -> DSP pré-ponte
       sem falhas objetivas

fila local -> ponte -> endpoint -> consumidor
       descartes + underruns + silêncio adicional
```

No bypass, reduzir o polling do consumidor de 10 ms para 2 ms diminuiu
fortemente descartes, underruns e silêncio adicional. Na STFT, a melhoria não
foi monotônica em uma única repetição. Assim, a arquitetura deve manter:

- DSP e protocolo PCM v1 congelados;
- baseline documentado em polling de 10 ms;
- polling de 2 ms como candidato experimental;
- novas repetições pareadas antes de alterar defaults;
- retorno ao HyperX somente após confirmar a mitigação.

## Confirmação do polling e retorno ao HyperX

O Checkpoint 38 confirmou em três pares de 60 s que o polling de 2 ms no
capturador externo reduz de forma consistente descartes, underruns e silêncio
adicional em relação a 10 ms. Ele passa a ser o valor preferido para ensaios
do consumidor de diagnóstico.

No retorno privado ao HyperX, os pipocos desapareceram no bruto e no
processado. Entretanto, o processado introduziu chiado, apresentou mais ruído
de fundo e continuou não preferido. Também foram percebidos travamentos nas
bordas dos dois WAVs.

Consequências arquiteturais:

- manter driver, protocolo PCM v1 e DSP congelados;
- usar polling de 2 ms no consumidor de diagnóstico;
- investigar separadamente transientes de abertura/fechamento;
- localizar a origem do chiado entre captura, estimador/DSP, ponte e
  alinhamento/reprodução;
- não promover qualidade perceptual enquanto B permanecer não preferido.

## Fronteira de qualidade no Checkpoint 39

A matriz determinística separou bruto, saída imediata do DSP e endpoint. A
STFT pré-bridge reduziu o piso total e a energia de 4–8 kHz nas métricas
agregadas, enquanto o endpoint voltou a elevar ambos.

```text
captura -> STFT pré-bridge
    redução agregada de piso, mas musical noise durante fala não excluído

fila local -> ponte -> driver/endpoint -> capturador
    drops, underruns e elevação agregada de piso
```

A revisão causal mostrou que um alinhamento global por envelope é inválido
diante de perdas não uniformes e não explica chiado percebido durante fala a
partir de janelas de ruído. O próximo refinamento deve:

- comparar auditivamente raw, pré-bridge e endpoint da mesma tomada;
- usar IDs de bloco para reconstruir a sequência efetivamente enviada;
- medir preservation rate por fala/ruído;
- comparar amostras preservadas entre pré-bridge e endpoint;
- medir spectral flatness, picos tonais e PSD condicionada a fala;
- contar transições zero-sinal e descontinuidades em lacunas.

Somente depois disso uma política de descarte ou outra mitigação de transporte
pode ser testada contra o baseline.

O laboratório também mostrou dependência operacional do frontend do
VirtualBox: a captura MME manteve cadência correta em GUI e desacelerou em
`headless`. Essa diferença deve ser tratada como propriedade do ambiente de
validação, não da arquitetura do produto.

## Separacao por blocos no Checkpoint 40

O caminho passa a ter observabilidade explicita:

```text
source_block_index -> fila local -> pcm_sequence -> driver
                   -> captura continua -> correspondencia deslizante
```

Blocos ativos e de ruido da fonte diagnostica possuem marcador
pseudoaleatorio reproduzivel. Isso permite localizar material preservado mesmo
quando underruns inserem lacunas nao uniformes.

O resultado separou dois mecanismos:

- pre-bridge: a STFT aumenta a densidade de picos tonais em atividade;
- pos-bridge: os blocos preservados permanecem equivalentes, enquanto perdas
  aparecem como lacunas e zeros.

A politica padrao continua `drop-oldest`. `drop-newest` permanece disponivel
somente como opcao diagnostica e foi rejeitada como mitigacao neste ambiente.

### Fronteira perceptual confirmada

A escuta privada confirmou:

```text
raw limpo
  -> STFT: chiado metalizado leve durante fala
  -> transporte/endpoint/captura: chiado consideravelmente mais intenso
```

Como os blocos recuperados no endpoint sao equivalentes ao pre-bridge, o
agravamento posterior nao deve ser modelado como uma resposta espectral
continua aplicada a todos os blocos. A arquitetura deve tratar separadamente:

- `musical noise` criado pelo ganho espectral do DSP;
- descontinuidades temporais e lacunas depois do DSP;
- possivel contribuicao do endpoint ou do capturador externo.

## Limite da suavizacao temporal no Checkpoint 41

O caminho causal passou a aceitar `gain_smoothing` como parametro diagnostico,
mas o default permanece `0.0`. A avaliacao privada offline mostrou que EMA de
`0.50` a `0.93` reduz muito pouco a densidade tonal e causa dano crescente a
envelope, energia e banda alta.

Consequencias arquiteturais:

- nao promover a suavizacao temporal para o fluxo ponta a ponta;
- manter transporte, driver e PCM v1 congelados;
- comparar o `stft_wiener` causal ja existente antes de criar nova
  infraestrutura de DSP;
- exigir gate objetivo pre-bridge e escuta privada antes de qualquer ensaio no
  endpoint.

## Limite do Wiener causal no Checkpoint 42

O `stft_wiener` existente tambem nao atingiu o gate pre-bridge. Pisos entre
`0.02` e `0.10` aumentaram a flatness e preservaram melhor a forma do bruto,
mas reduziram a densidade tonal em no maximo `2.13%`.

Consequencias arquiteturais:

- manter a subtracao espectral como baseline congelado, sem afirmar que ela
  atingiu qualidade perceptual;
- nao promover o Wiener ao endpoint;
- manter transporte, driver e PCM v1 inalterados;
- avaliar o proximo metodo existente primeiro offline e pre-bridge;
- corrigir futuramente a divergencia de implantacao de `gain_smoothing`
  somente quando um ensaio exigir essa opcao.

## Limite da Wavelet causal no Checkpoint 43

O `wavelet_soft` existente opera por janela causal de 832 amostras, formada
por 512 amostras de historico e o bloco corrente de 320 amostras. Com escala de
limiar 1.0, os niveis 3 a 5 reduziram picos tonais, mas removeram cerca de
`10.5 dB` adicionais em 4-8 kHz.

Consequencias arquiteturais:

- nao promover a configuracao Wavelet padrao ao endpoint;
- manter transporte, driver e PCM v1 congelados;
- testar escala de limiar menor somente offline;
- nao ampliar a configuracao persistente do app antes de existir um candidato
  objetivo;
- manter saneamento de nao finitos e registrar o aviso interno do PyWavelets.

## Limite da escala Wavelet no Checkpoint 44

A reducao do limiar nao encontrou uma faixa operacional: escalas baixas nao
reduziram picos o suficiente, enquanto a escala `0.50` atingiu o gate tonal
com perda severa de medias-altas e agudos.

Consequencias arquiteturais:

- encerrar o shrinkage DWT global como mitigacao deste `musical noise`;
- nao expor `wavelet_threshold_scale` no app;
- manter o baseline STFT congelado;
- tratar a WPT em quadros atual como referencia offline nao causal;
- exigir estado rolante explicito, testes de prefixo e custo menor que 20 ms
  antes de considerar uma WPT para o caminho realtime.

## WPT causal no Checkpoint 45

A nova WPT causal permanece isolada do produto, mas agora satisfaz o contrato
necessario para futura integracao:

- API por bloco e estado fixo;
- ganho calculado somente com historico passado;
- contexto algoritmico de 40 ms;
- reset e prefixos deterministas;
- custo abaixo do bloco no host e na VM.

Ela passou o gate objetivo privado, mas a arquitetura nao muda ainda. A
promocao depende de escuta pre-bridge e depois de validacao separada no
endpoint.

## Limite temporal confirmado no Checkpoint 46-R

A trilha host-cadenciada separou entrada fisica, DSP, transporte, writer,
driver e capturador. O transporte externo e o RNNoise persistente passaram
seus gates, mas o consumo WaveRT no VirtualBox/NEM nao sustentou 50 blocos/s
sem pausas.

Foram rejeitados, sem alterar driver ou PCM v1:

- MMCSS, prioridade e afinidade;
- temporizador, yield e spin;
- 2, 3 e 4 vCPUs;
- lead de envio;
- captura exclusiva orientada a evento.

O ultimo gate mostrou que o evento foi sinalizado sem timeout ou erro, mas a
thread retornou depois de ate `220,532 ms`. Parte das pausas acompanhou o
scheduler geral e parte ocorreu sem atraso equivalente no writer ou probe.

Consequencias:

- o endpoint virtual continua prova funcional, nao prova de continuidade;
- o RNNoise nao deve ser responsabilizado pelas perdas posteriores ao DSP;
- nao liberar escuta ponta a ponta a partir de WAVs com lacunas;
- nao aumentar filas ou esconder underruns para produzir demonstracao;
- a validacao final requer Windows nativo em maquina fisica, com pacote de
  driver corretamente assinado e plano de reversao.

## Fechamento acadêmico em 14 de junho de 2026

A arquitetura final do protótipo deve ser lida em cinco camadas:

1. fonte de áudio ou replay controlado;
2. DSP causal em espaço de usuário, com RNNoise como candidato principal;
3. transporte por blocos PCM16 mono, 16 kHz e 20 ms;
4. interface PCM v1 e ring buffer não paginado no SYSVAD;
5. endpoint virtual consumido por um cliente Windows.

As camadas 1 a 4 passaram em gates separados de qualidade, custo, framing,
sequência, CRC, escrita e contadores. A camada 5 é funcional para sinal
sintético, mas não sustentou continuidade temporal confiável no
VirtualBox/NEM.

O contrafactual compartilhado orientado a evento comparou SYSVAD e HDA no
mesmo boot, em ordem ABBA. Ambos apresentaram sinais tardios repetidos e
descontinuidades. A classificação predefinida foi
`virtualbox_event_timing_supported`.

Consequências arquiteturais finais:

- o RNNoise não explica perdas posteriores ao DSP;
- o endpoint é uma prova funcional, não uma prova de continuidade;
- o HDA não constitui controle temporal limpo;
- o resultado não demonstra correção do driver SYSVAD;
- a demonstração acadêmica deve separar DSP audível, microfone virtual
  funcional e integração técnica;
- a validação temporal seguinte deve ocorrer em Windows nativo, em bancada
  isolada e recuperável.
