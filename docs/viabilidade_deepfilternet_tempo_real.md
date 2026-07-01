# Viabilidade do DeepFilterNet3 para tempo real no Windows

Data: 2026-06-29

Este documento registra a decisao tecnica apos a rejeicao perceptual do
RNNoise e a aprovacao perceptual inicial do DeepFilterNet3 default no audio
`teste_audio_augusto`. Ele nao altera relatorio final, questionario, assets
publicados ou Apps Script.

## Resumo executivo

O DeepFilterNet3 default passa a ser o candidato principal de qualidade para
substituir o RNNoise no pipeline futuro:

```text
microfone fisico -> captura WASAPI -> DeepFilterNet3 streaming -> PCM limpo -> microfone virtual Windows
```

A decisao nao vem de metricas objetivas isoladas. Ela vem de escuta: os arquivos
`dfn3_default_deepfilternet_loudnorm.wav` e
`dfn3_default_deepfilternet_presence_eq_loudnorm.wav` soaram muito bons, com
voz praticamente sem metalizacao e ruido residual quase imperceptivel. As
variantes `dfn3_atten18` e `dfn3_atten12` foram rejeitadas por trazerem de
volta metalizacao e ruido de fundo. Portanto, o candidato operacional e
DeepFilterNet3 default, sem `--atten-lim`.

O benchmark local mostra que ha margem computacional em Python/PyTorch CPU para
prototipo, mas nao o suficiente para tratar a CLI Python como arquitetura final.
O proximo passo correto e investigar runtime nativo: Rust/libDF, ONNX Runtime ou
OpenVINO.

## Evidencia perceptual local

Estado consolidado:

- RNNoise stock remove bem ruido, mas foi rejeitado por voz metalizada.
- Mistura parcial/adaptativa, reparos de mascara, reparos harmonicos, envelope,
  cauda/release e variantes internas do RNNoise tambem foram rejeitados.
- O veredito perceptual do usuario permanece soberano.
- DeepFilterNet3 default resolveu o problema perceptual principal nesta rodada.
- DeepFilterNet3 com limite de atenuacao de 18 dB e 12 dB nao resolveu; piorou
  naturalidade.

Documentos e artefatos relacionados:

- `docs/diagnostico_rnnoise_voz_metalizada.md`
- `tmp/dfn_aug/`
- `tmp/dfn_aug/dfn3_focus_6p9_8p4_montage.wav`
- `tmp/dfn_realtime_benchmark/README.md`
- `tmp/dfn_realtime_benchmark/dfn_realtime_stream_summary.csv`
- `tmp/dfn_realtime_benchmark/dfn_realtime_benchmark_results.json`
- `tmp/dfn_native/README.md`

## Como o pacote local processa audio

A instalacao atual usa:

- `DeepFilterNet==0.5.6`
- `torch==2.5.1+cpu`
- `torchaudio==2.5.1+cpu`
- `deep-filter-py.exe`
- `libdf.cp311-win_amd64.pyd`

O caminho Python funciona assim:

1. `df.enhance.init_df()` carrega configuracao, `df_state` e modelo PyTorch.
2. `df_state.analysis()` calcula STFT no loop real-time de `libdf`.
3. `erb_norm()` e `unit_norm()` geram features ERB e complexas.
4. O modelo `DfNet` roda em PyTorch.
5. `df_state.synthesis()` reconstrui PCM.

Parametros locais observados:

- taxa: 48 kHz;
- `fft_size`: 960 amostras;
- `hop_size`: 480 amostras, isto e, 10 ms;
- 32 bandas ERB;
- 96 bins de deep filtering;
- ordem DF 5;
- `df_lookahead=2`;
- `conv_lookahead=2`.

Uma chamada direta com apenas 10 ms falha no modelo PyTorch com
`narrow(): length must be non-negative`. Na simulacao local, blocos de captura
de 10 ms precisam ser acumulados para processamento minimo de 20 ms. Para o
pipeline real, isso significa que o contrato de audio deve ser pelo menos
20 ms por chamada de inferencia, mesmo que a captura chegue em pacotes de
10 ms.

## Benchmark local

Rodada:

```powershell
.\tmp\.venv_deepfilternet\Scripts\python.exe .\tmp\dfn_realtime_benchmark\benchmark_dfn_realtime.py
```

Entrada:

```text
tmp\dfn_aug\dfn3_default\wav\dfn3_default_deepfilternet_input_48000hz.wav
```

Resultados principais:

| modo | threads | captura | processamento minimo | RTF | media | p95 | p99 | pior caso | underruns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| streaming simulado | 1 | 10 ms | 20 ms | 0,575 | 11,49 ms | 16,30 ms | 18,75 ms | 21,50 ms | 1 |
| streaming simulado | 1 | 20 ms | 20 ms | 0,649 | 12,97 ms | 17,04 ms | 18,58 ms | 20,86 ms | 1 |
| streaming simulado | 2 | 10 ms | 20 ms | 0,661 | 13,21 ms | 16,27 ms | 17,59 ms | 20,49 ms | 1 |
| streaming simulado | 2 | 20 ms | 20 ms | 0,806 | 16,13 ms | 21,44 ms | 23,01 ms | 25,87 ms | 42 |
| streaming simulado | 4 | 10 ms | 20 ms | 0,567 | 11,34 ms | 15,08 ms | 17,78 ms | 20,03 ms | 1 |
| streaming simulado | 4 | 20 ms | 20 ms | 0,512 | 10,24 ms | 13,55 ms | 14,76 ms | 16,49 ms | 0 |

Outros achados:

- carregamento do modelo: aproximadamente 140 ms;
- warm-up de 20 ms: aproximadamente 18,8 ms;
- API offline em arquivo inteiro: RTF aproximadamente 0,067;
- CLI end-to-end: aproximadamente 6,56 s para audio de 8,47 s;
- gargalo principal: inferencia PyTorch, nao STFT/sintese.

Interpretacao:

- RTF menor que 1 indica chance computacional.
- Callback de audio precisa folga, jitter baixo e previsibilidade; RTF medio
  sozinho nao basta.
- Python/PyTorch serve para prototipo, comparacao e validacao perceptual.
- A CLI Python nao serve como motor final de microfone virtual.
- O runtime final deve ser nativo ou pelo menos desacoplado da CLI.

## Runtime nativo: achados de fontes primarias

O repositorio oficial do DeepFilterNet informa que o framework suporta Linux,
macOS e Windows, e separa:

- `libDF`: codigo Rust usado pelo framework;
- `DeepFilterNet`: codigo Python, avaliacao, treino e pesos;
- `pyDF`: wrapper Python do loop STFT/ISTFT de `libDF`;
- `ladspa`: plugin LADSPA para reducao de ruido em tempo real;
- `models`: modelos pre-treinados para Python ou `libDF/deep-filter`.

Fonte: https://github.com/Rikorose/DeepFilterNet

O mesmo README registra que ha versao real-time e plugin LADSPA, com binario
pre-compilado sem dependencias Python no formato `deep-filter audio-file.wav`.
As releases tambem registram uma versao Rust-only com loop real-time e, em
versao posterior, correcao de divergencia entre implementacao nativa e PyTorch.

Fonte: https://github.com/Rikorose/DeepFilterNet/releases

Ha ainda uma trilha OpenVINO publicada pela Intel com modelos IR para
DeepFilterNet2 e DeepFilterNet3, divididos em `enc`, `erb_dec` e `df_dec`.
Isso e relevante para Windows porque OpenVINO pode ser uma rota CPU otimizada,
mas exige reproduzir corretamente estado, features e streaming.

Fonte: https://huggingface.co/Intel/deepfilternet-openvino

Um downstream recente da SVT implementa filtro FFmpeg com DeepFilterNet3 via
`libdf`, sem Python e sem LibTorch, aceitando mono `float` a 48 kHz, hop de
480 amostras e lookahead de 20 ms no DFN3 padrao. Ele e evidencia pratica de
que `libdf` pode operar como nucleo nativo de processamento, embora nao seja
o nosso alvo de microfone virtual.

Fonte: https://github.com/svt/ffmpeg-filter-dnenhance

Tambem existe experimento de comunidade com Rust + ONNX Runtime para
DeepFilterNet em tempo real. Esse caminho e promissor como referencia de
arquitetura, mas deve ser tratado como experimental ate ser reproduzido
localmente.

Fonte: https://github.com/shimondoodkin/deepfilter-rt

## DFN-2: runtime nativo oficial offline

A pendencia inicial era a ausencia de `deep-filter.exe` no ambiente Python
local. Essa lacuna foi resolvida sem compilacao:

- binario oficial:
  `tmp/dfn_native/deep-filter-0.5.6-x86_64-pc-windows-msvc.exe`;
- modelo oficial para runtime nativo:
  `tmp/dfn_native/DeepFilterNet3_onnx.tar.gz`;
- resumo local:
  `tmp/dfn_native/README.md`.

Hashes registrados:

- `deep-filter-0.5.6-x86_64-pc-windows-msvc.exe`:
  `75E11FA16445F560CB6B021521DDB89E89270D13B83089705D98776F58FD7915`;
- `DeepFilterNet3_onnx.tar.gz`:
  `C94D91F70911001C946E0FABB4AA9ADC37045F45A03B56008CB0C8244CB63616`.

Smoke test offline:

- entrada:
  `tmp/dfn_aug/dfn3_default/wav/dfn3_default_deepfilternet_input_48000hz.wav`;
- modo sem `-D`: preserva `406527` amostras, mas fica atrasado em
  `1440` amostras contra a saida Python compensada;
- modo com `-D`: alinha com a saida Python, mas retorna `405087` amostras,
  isto e, `1440` amostras a menos;
- a correlacao alinhada contra a saida Python foi aproximadamente `0,995438`;
- a diferenca RMS alinhada ficou aproximadamente em `-34,87 dBFS`.

Benchmark repetido da CLI nativa no arquivo de `8,4693125 s`:

- RTF total sem `-D`: `0,1489`, `0,1716`, `0,1404`;
- RTF total com `-D`: `0,1769`, `0,1427`, `0,1474`.

Interpretacao:

- o runtime nativo oficial existe e funciona no Windows para arquivo offline;
- o tempo total ja inclui startup/carregamento, portanto o nucleo em processo
  persistente deve ter margem ainda melhor;
- a CLI nativa nao basta para microfone virtual, porque ainda processa arquivo
  inteiro;
- a proxima pendencia e achar ou construir uma chamada nativa persistente que
  preserve estado em blocos de 20 ms.

Inspecao do fonte oficial v0.5.6:

- fonte clonado em `tmp/dfn_native/DeepFilterNet-v0.5.6-source`;
- commit confirmado: `978576aa8400552a4ce9730838c635aa30db5e61`;
- `libDF/src/capi.rs` expoe C API com `df_create`,
  `df_get_frame_length`, `df_process_frame`, controles de atenuacao/post-filter
  e `df_free`;
- `df_process_frame` opera com buffers de tamanho `df_get_frame_length()`;
- `libDF/Cargo.toml` possui feature `capi`, mas o release oficial baixado
  trouxe a CLI e LADSPA, nao uma DLL C API pronta;
- `ladspa/src/lib.rs` confirma arquitetura de worker persistente usando
  `DfTract::process()` e filas, mas LADSPA nao e a melhor superficie para
  integrar com o pipeline Windows/SYSVAD deste projeto.

Status atualizado da pendencia tecnica:

- Rust/Cargo portatil `1.88.0` foi preparado em `tmp/dfn_native/`;
- `libDF` foi compilado com feature `capi` como DLL C API;
- DLL gerada: `tmp/t_release/x86_64-pc-windows-msvc/release/df.dll`;
- `df_process_frame` foi validado por harness Python `ctypes` antes de envolver
  VM, ponte PCM ou SYSVAD;
- `df_get_frame_length()` retornou `480` amostras, isto e, `10 ms` a 48 kHz;
- o processamento persistente do WAV de `8,4693125 s` teve RTF
  processing-only `0,071421`, p99 `1,422672 ms`, pior frame `1,960300 ms` e
  `0` frames acima do budget de `10 ms`;
- a saida C API compensada em `1440` amostras teve mesmo tamanho da CLI `-D`,
  correlacao `0,999214` e RMS da diferenca aproximado de `-47,23 dBFS`.

## Integracao com a VM de microfone virtual

A VM continua sendo o ambiente correto para qualquer etapa que toque SYSVAD,
endpoint virtual ou driver:

- VM rapida: `PTC3527-SYSVAD-LAB-FAST`;
- host nao deve receber driver SYSVAD nem alteracoes de test-signing;
- a VM original deve permanecer preservada;
- o clone rapido deve partir de snapshot controlado e voltar a `poweroff`;
- audio privado deve permanecer fora do repositorio e ser removido do convidado
  ao final das rodadas.

Licao dos checkpoints 46-R:

- entrada fisica virtualizada por MME/DirectSound/WASAPI nao e relogio
  confiavel dentro da VM;
- o caminho aceito foi host-cadenciado por TCP/NAT, com 50 blocos/s, sequencia,
  CRC e pacing absoluto no host;
- replay host-cadenciado foi aprovado;
- endpoint ainda foi rejeitado em rodada anterior por consumo incompleto do
  driver, nao por RNNoise.

Consequencia para DeepFilterNet3:

1. Nao iniciar pela VM com captura fisica livre.
2. Primeiro provar runtime DeepFilterNet3 no host, offline e streaming
   simulado.
3. Depois provar runtime host-cadenciado para o convidado, sem endpoint.
4. So depois reabrir ponte PCM v1 e endpoint SYSVAD.

## Plano incremental recomendado

### Fase DFN-1: documentacao e decisao

- Registrar que RNNoise fica como baseline historico negativo para este audio.
- Registrar que DeepFilterNet3 default e o novo candidato principal de
  qualidade.
- Registrar que `--atten-lim` deve permanecer fora do candidato principal.
- Manter os resultados em `tmp/` e documentacao tecnica isolada.

### Fase DFN-2: runtime nativo offline

Objetivo: reproduzir o resultado de qualidade do Python usando runtime nativo
fora do pipeline de microfone.

Status:

- binario oficial Windows obtido;
- modelo ONNX oficial obtido;
- smoke test offline aprovado;
- comparacao inicial contra saida Python aprovada numericamente.

Pendencias:

- comparar:
  - saida nativa com escuta manual;
  - saida nativa loudnorm/presence-eq se necessario, sem mudar o candidato
    principal;
  - comportamento em trechos focados como `dfn3_focus_6p9_8p4_montage.wav`;
- localizar API, biblioteca ou wrapper que permita loop persistente por bloco.

Gate:

- se a saida nativa soar pior ou diferir perceptualmente do Python default, nao
  avancar para VM antes de explicar a divergencia.

### Fase DFN-3: streaming nativo simulado

Objetivo: medir blocos em runtime nativo com estado preservado.

Status atualizado: C API persistente compilada e validada em host. O bloco
nativo confirmado foi `480` amostras, isto e, `10 ms` a 48 kHz. No WAV de
referencia, o RTF processing-only foi `0,071421`, com media `0,709438 ms`, p95
`1,276130 ms`, p99 `1,422672 ms`, pior frame `1,960300 ms` e `0` frames acima
do budget de `10 ms`. A comparacao C API compensada vs CLI `-D` teve correlacao
`0,999214` e RMS da diferenca aproximadamente `-47,23 dBFS`.

Medidas:

- tempo medio por bloco;
- p95, p99 e pior caso;
- jitter;
- backlog;
- underruns simulados;
- memoria;
- latencia algoritmica declarada e medida.

Gate:

- p99 abaixo de 20 ms com folga;
- zero underrun em replay longo;
- saida perceptualmente equivalente ao DeepFilterNet3 default offline.



### Atualização 2026-06-29: Fase A e Fase B1 nativas

A Fase A foi concluída com uma bancada C++ nativa cadenciada por QPC em:

```text
tmp/dfn_native/native_host_bench/
```

O objetivo foi remover Python da medição de cadência. Resultado: os três inputs `capi_input48.wav` passaram com p99 abaixo de `3 ms`, máximo abaixo de `5 ms`, zero frame acima do orçamento de processamento e zero deadline perdido. A Fase A confirmou que a dúvida anterior era da bancada Python/scheduler, não do DeepFilterNet3 C API.

A Fase B1 foi iniciada em:

```text
tmp/dfn_native/wasapi_render_bench/
```

O bench usa WASAPI render event-driven e MMCSS `Pro Audio`. O render é mudo por padrão, para validar o relógio real do Windows Audio Engine sem tocar áudio no alto-falante. O endpoint shared atual foi detectado como `48000 Hz`, estéreo, `float32`, período default `10 ms` e período mínimo `3 ms`.

Última suite B1 shared/muted/MMCSS via `run_shared_suite.ps1`, com gate estável ignorando apenas o frame 0 que fica dentro do preroll descartado:

| input | p99 proc | max proc | over budget | missed deadline | underflow | status |
|---|---:|---:|---:|---:|---:|---|
| dfn3_default | 2,813 ms | 11,941 ms | 1 | 1 | 0 | CHECK |
| clean_lufs16 | 2,582 ms | 3,348 ms | 0 | 0 | 0 | PASS |
| noisy_reference_lufs16 | 3,588 ms | 4,052 ms | 0 | 0 | 0 | CHECK |

Conclusão: a Fase B1 está implementada e funcional, mas a última suite não fecha gate final nos três inputs. Execuções individuais anteriores passaram nos três, então o caminho é promissor; a reexecução completa mostrou jitter/outlier real no desenho WASAPI shared síncrono.

O modo exclusive foi implementado, mas o endpoint/driver atual recusou os formatos 48 kHz estéreo testados (`float32`, `PCM16`, `PCM24`, `PCM32`) com `0x8889000E`. Isso bloqueia a validação exclusive neste endpoint específico, mas não reprova o DeepFilterNet3.

Próximo passo recomendado: B2 com separação entre thread WASAPI e worker DFN por ring buffer/fila, ou host-paced PCM sob relógio real, ainda sem SYSVAD e sem microfone virtual final.

### Atualização 2026-06-29: Fase B2 worker/ring buffer

A B2 foi implementada em:

```text
tmp/dfn_native/wasapi_worker_bench/
```

A arquitetura mudou de:

```text
WASAPI event thread -> df_process_frame() -> render
```

para:

```text
DFN worker thread -> SPSC ring buffer -> WASAPI event thread
```

O event thread agora apenas copia amostras já processadas para `IAudioRenderClient`. O processamento DeepFilterNet3 roda em worker separado com MMCSS.

Nesta rodada, o endpoint shared atual apareceu como `96000 Hz`, `8 ch`, `float32`; o formato cliente 48 kHz shared não foi aceito exatamente. Para não mudar o contrato do DeepFilterNet3, o worker permaneceu em 48 kHz e o render mudo apenas duplicou amostras para seguir o relógio de 96 kHz. Os WAVs salvos de auditoria continuam em 48 kHz.

Gate B2 usado:

| camada | critério |
|---|---|
| DFN worker | p99 <= 4 ms |
| DFN worker | p999 <= 8 ms |
| DFN worker | max <= 10 ms |
| WASAPI callback | p99 <= 1 ms |
| buffer | underflow = 0 |
| ring buffer | mínimo antes do callback >= 480 amostras |

Resultados da suite local:

| input | worker p99 | worker p999 | worker max | callback p99 | underflow | status |
|---|---:|---:|---:|---:|---:|---|
| dfn3_default | 1,782 ms | 2,121 ms | 2,227 ms | 0,137 ms | 0 | PASS |
| clean_lufs16 | 1,648 ms | 1,933 ms | 1,946 ms | 0,165 ms | 0 | PASS |
| noisy_reference_lufs16 | 1,823 ms | 4,056 ms | 6,073 ms | 0,140 ms | 0 | PASS |

Conclusão: B2 aprovada na suite local. A separação worker/ring buffer resolveu a falha estrutural da B1, mantendo o callback WASAPI abaixo de `0,2 ms` p99 nos três inputs e underflow zero.

Próximo passo recomendado: antes de reabrir SYSVAD/ponte PCM v1, executar teste mais longo ou pior caso de conteúdo, ou seguir para a trilha host-paced PCM rumo à VM.

### Atualização 2026-06-29: Fase B3 pré-VM longa

A B3 foi executada sobre a arquitetura B2 com um input composto de `60 s`:

```text
tmp/dfn_native/wasapi_worker_bench/b3_inputs/mixed_60s_capi_input48.wav
```

O input mistura os três casos usados nos gates curtos: `dfn3_default`, `clean_lufs16` e `noisy_reference_lufs16`.

O `summary.json` bruto ficou `CHECK` porque o frame `0` do worker mediu `14,451 ms`. Esse frame está dentro do preroll descartado e não chega ao output alinhado. Mantendo o CSV completo para auditoria e aplicando gate estável que ignora apenas o frame `0`, o resultado foi:

| métrica | valor |
|---|---:|
| worker frames no gate | 5999 |
| worker p99 | 1,875 ms |
| worker p999 | 2,508 ms |
| worker max | 3,306 ms |
| worker > 4 ms | 0 |
| worker > 8 ms | 0 |
| worker > 10 ms | 0 |
| callback p99 | 0,039 ms |
| callback p999 | 0,076 ms |
| callback max | 0,158 ms |
| underflow | 0 |
| ring mínimo antes do callback | 480 samples |
| status estável | PASS |

Conclusão: B3 pré-VM aprovada no gate estável. A validação local do motor fica encerrada o suficiente para preparar a trilha de VM.

Handoff criado:

```text
tmp/dfn_native/VM_HANDOFF_NEXT_STEPS.md
```

Decisão operacional: a VM deve começar por transporte host-paced PCM com sequência, CRC/hash, timing e WAV reconstruído. SYSVAD/ponte PCM v1 só deve ser reaberto depois do transporte limpo.

### Fase DFN-4: host-cadenciado sem endpoint

Objetivo: substituir RNNoise no ensaio aceito de relogio externo.

Caminho:

```text
host captura/replay -> pacing absoluto 50 blocos/s -> VM recebe -> DeepFilterNet3 -> WAV/hash/metrica
```

Sem ponte PCM v1, sem endpoint SYSVAD e sem escuta ponta a ponta nesta etapa.

Gate:

- 1.000 blocos por perna;
- zero erro de sequencia, CRC ou framing;
- p99 de processamento abaixo do orcamento;
- hashes de entrada pareados em bypass e DeepFilterNet3;
- audio privado fora do repositorio.

### Fase DFN-5: ponte PCM v1 e endpoint

Objetivo: reabrir a parte funcional do microfone virtual apenas depois do motor
estar validado.

Caminho:

```text
host-paced PCM -> VM -> DeepFilterNet3 -> ponte PCM v1 -> SYSVAD MicIn -> cliente externo
```

Gate:

- bypass e DeepFilterNet3 precisam entregar 50 blocos/s ao endpoint;
- consumo do driver nao pode parar antes do fim;
- rejeicao do endpoint deve bloquear escuta e promocao;
- se o endpoint falhar tambem no bypass, a falha continua no transporte/driver,
  nao no DeepFilterNet3.

### Fase DFN-6: escuta controlada

Objetivo: validar o que importa: naturalidade percebida.

Regras:

- a avaliacao perceptual do usuario e soberana;
- RNNoise nao volta como solucao principal;
- comparar bruto, DeepFilterNet3 pre-ponte e DeepFilterNet3 endpoint;
- evitar `--atten-lim` no candidato principal;
- nao publicar audio privado.

## Decisao operacional atual

DeepFilterNet3 default merece sequencia. A investigacao nao deve tentar
"consertar" RNNoise como eixo principal. O proximo trabalho tecnico deve ser
runtime nativo offline e streaming nativo simulado, antes de qualquer rodada de
VM com endpoint.

O resultado esperado para o anteprojeto e forte: o projeto deixa de ser apenas
"testar RNNoise em tempo real" e passa a documentar uma decisao de engenharia
baseada em qualidade perceptual, custo computacional, risco de driver e
prototipacao incremental no Windows.

## VM-DFN3-TRANSPORT-48K

Em 2026-06-29 foi executada a primeira rodada de transporte VM para o DeepFilterNet3, ainda sem SYSVAD, sem ponte PCM v1 e sem processamento DFN dentro do convidado.

Contrato usado:

- PCM16 mono;
- `48 kHz`;
- `480 samples` por bloco;
- `10 ms` por bloco;
- `100 blocos/s`.

A anotacao anterior de `50 blocos/s` foi tratada como inconsistencia do handoff, pois `480 samples @ 48 kHz` corresponde fisicamente a `10 ms` e `100 blocos/s`.

Resultado:

- `6000/6000` blocos recebidos;
- perda zero;
- erros de sequencia, CRC e framing iguais a zero;
- WAV reconstruido com `60,0 s`;
- hash de payload recebido igual ao de origem: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
- gate final `check`.

A classificacao `check` veio do jitter de chegada: p99 `18,722 ms`, max `442,938 ms`, um stall acima de `100 ms` e rajadas compensatorias. Assim, a integridade do canal foi demonstrada, mas a cadencia ainda nao esta limpa o suficiente para acoplar o DeepFilterNet3 dentro da VM ou reabrir SYSVAD.

Artefatos:

```text
resultados/dfn3_vm_transport_48k/
docs/vm_dfn3_transport_plan.md
```

### Repeticao R2 de jitter

A repeticao `VM-DFN3-TRANSPORT-48K-R2-JITTER` manteve o gate em `check`. O transporte logico continuou perfeito (`6000/6000` blocos, perda/CRC/framing/sequencia iguais a zero), mas a cadencia voltou a exibir jitter: recepcao p99 `20,646 ms`, max `110,346 ms` e um stall acima de `100 ms`.

A sonda interna de scheduler no convidado registrou 37 gaps acima de `30 ms`, 2 acima de `100 ms` e max `569,455 ms`. Como apenas 1 dos 3 stalls de recepcao acima de `50 ms` coincidiu com gap de scheduler acima de `30 ms`, a causa ainda nao esta totalmente isolada. A decisao permanece: nao acoplar DFN dentro da VM nem reabrir SYSVAD antes de resolver a cadencia do transporte.

### R4 host-send

A rodada `VM-DFN3-TRANSPORT-48K-R4-HOSTSEND` executou o servidor host em prioridade `High` e limpou a contribuicao do host/send: p99 `10,015 ms`, max `10,532 ms` e zero stall acima de `20 ms`.

Mesmo assim, o gate permaneceu `check`: o convidado teve recepcao p99 `21,297 ms`, max `428,577 ms`, dois stalls acima de `50 ms` e um acima de `100 ms`. A instrumentacao mostrou que os stalls ficaram em `header_wait_ms`; payload read, CRC, hash e escrita WAV nao explicam a pausa. Como o envio host estava normal e nao houve correlacao com gaps de scheduler acima de `30 ms` na janela medida, a classificacao atual e `guest_receive_or_nat_jitter`.

A decisao continua conservadora: nao acoplar DeepFilterNet3 dentro da VM nem reabrir SYSVAD antes de isolar o caminho `recv`/NAT.

### R5 receive-only

A rodada `VM-DFN3-TRANSPORT-48K-R5-RECEIVE-ONLY` removeu a escrita WAV do loop do cliente (`sink=memory`). A integridade permaneceu perfeita e o envio host continuou limpo, mas o gate ficou em `check`: recepcao p99 `16,896 ms`, max `473,736 ms` e dois stalls acima de `100 ms`.

Como os stalls ficaram em `header_wait_ms`, com payload read e CRC baixos, a escrita WAV nao era a causa principal. A classificacao atual e `guest_recv_or_nat_header_wait_jitter`. A saude da trilha e boa: o bloqueio e especifico de cadencia de transporte, antes de DSP/driver, e nao ha perda ou corrupcao de payload.
