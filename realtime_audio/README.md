# Prototipo Windows em tempo real

Esta pasta contem a primeira CLI para demonstracao local captura-processa-reproduz/salva. A biblioteca `sounddevice` so e importada quando a captura real ou a listagem de dispositivos e solicitada; o autoteste sintetico roda sem microfone.

## Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

## Verificar sem microfone

```powershell
python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1
```

## Processar WAV sem dispositivo

O caminho de arquivo usa diretamente o mesmo `CausalSTFTProcessor` da captura
Windows e nao importa `sounddevice`:

```powershell
python -m realtime_audio.process_wav_blocks `
  --input entrada.wav `
  --output saida.wav `
  --method stft_subtraction `
  --noise-mode adaptive `
  --block-ms 20 `
  --metrics-json resultados/file_blocks/run.json `
  --blocks-csv resultados/file_blocks/run.csv
```

Metodos: `bypass`, `stft_subtraction` e `stft_wiener`. O modo `adaptive` e o
principal; `calibration` existe somente como baseline explicito. Os blocos
aceitos sao 10, 20 e 32 ms. A CLI:

- converte estereo para mono e reamostra para 16 kHz;
- nao normaliza automaticamente;
- preserva o comprimento processado e aceita ultimo bloco curto;
- limita a faixa apenas ao escrever PCM16 e registra a contagem de excessos;
- recusa sobrescrita sem `--overwrite`;
- grava hashes SHA-256, configuracao, ambiente, percentis, RTF e memoria;
- registra latencia algoritmica separada de driver ou dispositivo.

Exemplo versionado:

- `resultados/file_blocks/example/vector_causal_20ms.wav`;
- `resultados/file_blocks/example/vector_causal_20ms.csv`;
- `resultados/file_blocks/example/vector_causal_20ms.json`.

Os vetores sinteticos para futura portabilidade ficam em
`test_vectors/file_blocks/`. Detalhes de alinhamento e reproducao estao em
`docs/processamento_wav_blocos.md`.

## Listar dispositivos

```powershell
python -m realtime_audio.windows_realtime --list-devices
```

## Rodar captura local

Primeiro, teste apenas captura/processamento, sem reproduzir nos alto-falantes:

```powershell
python -m realtime_audio.windows_realtime --input-only --duration 5 --method bypass --block-ms 20 --no-save
python -m realtime_audio.windows_realtime --input-only --duration 5 --method stft_subtraction --noise-mode adaptive --block-ms 20 --no-save
```

## Alimentar o microfone virtual PTC

O Checkpoint 33 adiciona um produtor Python para a ponte PCM validada no
Checkpoint 32. Este modo deve ser executado somente no Windows convidado com o
SYSVAD modificado instalado:

```powershell
python -m realtime_audio.windows_realtime `
  --virtual-mic `
  --duration 30 `
  --method stft_subtraction `
  --noise-mode adaptive `
  --block-ms 20 `
  --input-device 1 `
  --output-dir resultados/sysvad_checkpoint33 `
  --no-save
```

O contrato e fixo em mono, PCM16, 16 kHz e blocos de 320 amostras. A captura
e o DSP usam `float32`; a conversao para PCM16 ocorre somente antes do IOCTL.
Uma thread separada consulta a profundidade da fila do driver e envia novos
blocos quando ela fica abaixo de `--bridge-target-depth`, cujo padrao passou a
ser dois blocos no Checkpoint 34. Isso substitui o pacing fixo do produtor
sintetico.

A fila de usuario aceita quatro blocos por padrao. Se ela lotar, o bloco mais
antigo e descartado para limitar o atraso acumulado. A sequencia do protocolo
e atribuida apenas no envio, portanto esse descarte local nao cria erro de
sequencia no driver. As metricas registram:

- blocos processados, enviados e descartados na fila de usuario;
- idade media, p95 e maxima dos blocos na fila de usuario;
- erros de escrita;
- profundidade media, p95, maxima e contadores finais da fila do driver;
- taxas efetivas de submissao e envio;
- underruns, overruns e rejeicoes;
- tempos por bloco e latencia de entrada reportada pelo `sounddevice`;
- latencia estimada incluindo algoritmo, stream e buffers da ponte.

A matriz controlada do Checkpoint 34 escolheu profundidade 2 e fila local 4.
A estimativa resultante foi `182,36 ms`, com 56 underruns e zero overruns. Ela
nao e uma medicao fisica ponta a ponta.

O modo falha antes da captura se a interface do driver nao estiver presente ou
se outro produtor ja possuir a ponte. O host fisico deve permanecer sem
SYSVAD, certificado de teste e `TESTSIGNING`.

Para uma rodada de estabilidade input-only mais defensavel:

```powershell
python -m realtime_audio.windows_realtime --input-only --duration 30 --method bypass --block-ms 20 --no-save
python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_subtraction --noise-mode adaptive --block-ms 20 --no-save
python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_wiener --noise-mode adaptive --block-ms 20 --no-save
python -m realtime_audio.windows_realtime --input-only --duration 30 --method wavelet_soft --block-ms 20 --no-save
python -m realtime_audio.summarize_realtime --pattern "windows_input_only_*_metrics.json" --output resultados/tabelas/realtime_windows_input_only.csv
```

## Interface de controle do microfone virtual

O Checkpoint 35 adiciona uma interface utilitária em `tkinter`:

```powershell
python -m realtime_audio.virtual_mic_ui
```

A janela lista entradas físicas, inicia e para o pipeline, permite escolher a
agressividade de forma explícita e mostra nível, estado, contadores da ponte e
latência estimada. O preset padrão mantém `spectral_alpha=1,5`, a profundidade
da ponte permanece em `2` e a fila local permanece em `4`.

A configuração do usuário é salva fora do repositório:

```text
%LOCALAPPDATA%\PTC3527\virtual_mic_ui.json
```

Uma configuração ausente ou corrompida não impede a abertura. No host sem o
driver, a UI informa que o endpoint está desconectado. Testes funcionais do
endpoint PTC continuam restritos à VM.

Depois, para demonstracao com monitoramento de saida:

```powershell
python -m realtime_audio.windows_realtime --duration 10 --method stft_subtraction --block-ms 20
```

Quando houver fone ou saida controlada, tambem e possivel fixar os dispositivos por indice. Exemplo usado na validacao curta com entrada SteelSeries no indice 1 e fone HUAWEI no indice 7:

```powershell
python -m realtime_audio.windows_realtime --duration 5 --method bypass --block-ms 20 --input-device 1 --output-device 7 --no-save
python -m realtime_audio.windows_realtime --duration 5 --method stft_subtraction --block-ms 20 --input-device 1 --output-device 7 --no-save
python -m realtime_audio.summarize_realtime --pattern "windows_*_20260606_2221*_metrics.json" --output resultados/tabelas/realtime_windows_duplex.csv
```

O padrao atual usa audio mono a 16 kHz e o estimador causal adaptativo congelado
na PC-1. Ele aquece por 250 ms, mantem 500 ms de historico espectral e nao
depende de silencio inicial. O modo `--noise-mode calibration` preserva a
calibracao curta como baseline; `rolling` e um alias de compatibilidade para
`adaptive`.

### Demonstracao PC com fone cabeado

No Checkpoint 26, a demonstracao full-duplex cabeada valida usou entrada
`Microfone (USB Audio Device), MME` no indice 2 e saida
`Alto-falantes (AB13X USB Audio), MME` no indice 8. Antes de rodar, deixe o
fone cabeado conectado e volume baixo, por exemplo 20/100.

Smoke seguro com bypass:

```powershell
python -m realtime_audio.windows_realtime `
  --duration 3 `
  --method bypass `
  --block-ms 20 `
  --input-device 2 `
  --output-device 8 `
  --output-dir resultados/windows_realtime_wired `
  --no-save
```

Demo curta da STFT causal:

```powershell
python -m realtime_audio.windows_realtime --pc-demo wired --duration 30
```

Rodada longa usada no checkpoint:

```powershell
python -m realtime_audio.windows_realtime --pc-demo wired --duration 600
```

O preset `--pc-demo wired` aplica automaticamente: `stft_subtraction`,
`noise-mode adaptive`, bloco de 20 ms, entrada indice 2, saida indice 8,
`resultados/windows_realtime_wired` e `--no-save`. Para uma rodada sem saida,
use:

```powershell
python -m realtime_audio.windows_realtime --pc-demo input-only --duration 600
```

A rodada longa registrou 29.998 blocos, pior bloco 7,301 ms, RTF medio 0,063,
zero blocos acima de 20 ms e `status_counts` vazio. A saida MME cabeada
reportou 200 ms de latencia de saida, entao a demonstracao comprova
funcionalidade full-duplex e estabilidade computacional por bloco, mas nao
prova baixa latencia fisica ponta a ponta.

Os logs ficam em `resultados/realtime/`. Os WAVs salvos sao artefatos locais
curtos de teste; nao devem ser tratados como base publica do projeto. Use
`--input-only` quando quiser medir estabilidade e custo computacional sem risco
de realimentacao acustica. O modo com saida deve ser usado apenas com fone ou
saida controlada para evitar feedback.

## Saidas

No processamento de arquivo:

- JSON por execucao: caminhos, hashes, formato original, configuracao causal,
  alinhamento, clipping, ambiente e resumo de tempos;
- CSV por bloco: indices de amostra, tamanho, tempo, RTF, picos, aquecimento,
  estado do estimador e memoria;
- WAV de saida: mono, 16 kHz e PCM16.

Na captura Windows:

- `*_metrics.json`: configuracao, media, p95, p99, pior caso, blocos acima do
  orcamento, RTF, memoria de estado e latencia estimada.
- `*_blocks.csv`: uma linha por bloco com tempo, RTF, picos, aquecimento,
  decisao de fala e estado do estimador.
- `*_input.wav` e `*_output.wav`: entrada e saida curtas, salvo quando `--no-save` nao for usado.

Para consolidar os JSONs em uma tabela CSV pequena:

```powershell
python -m realtime_audio.summarize_realtime --pattern "windows_input_only_*_metrics.json" --output resultados/tabelas/realtime_windows_input_only.csv
```

## Validação acústica com HyperX

O Checkpoint 36 validou o caminho físico com um HyperX Quadcast, identificado
no Windows como `Microfone (USB Audio Device)`. O índice não é estável e não
deve ser fixado sem nova enumeração.

Parâmetros preservados:

- `stft_subtraction`;
- estimador `adaptive`;
- 16 kHz;
- blocos de 20 ms;
- `spectral_alpha=1,5`;
- ponte com profundidade 2 e fila local 4.

O endpoint virtual foi capturado por cliente externo com áudio não nulo. Em
630 s de estabilidade, a UI registrou 27.638 blocos processados, 23.143
enviados, 4.491 descartes locais, 10.626 underruns, zero overruns e zero erros
de escrita.

A escuta A/B revelou pipocos, muito mais severos no áudio processado. Antes de
alterar o DSP, uma continuidade deve investigar o consumo do endpoint, polling,
cadência e buffers. A redução de ruído marrom observada foi moderada,
aproximadamente `2,75 dB RMS`.

Os WAVs de voz são privados. Não devem ser gravados em `resultados/` nem
versionados; preserve apenas hashes e métricas no repositório.

## Diagnóstico de continuidade

`realtime_audio.audio_continuity` analisa blocos ou WAV PCM16 e registra
saltos entre amostras, blocos zerados, sequências longas de zeros, repetições,
ausências, descontinuidades de fronteira, RMS, pico e cadência.

Na captura Windows, `--progress-file caminho.json` preserva atomicamente o
último estágio do stream e a contagem de callbacks. Em modo de ponte,
`--diagnostic-trace` registra a relação entre o índice do bloco de origem,
descartes locais e envios. O polling explícito usa:

```powershell
python -m realtime_audio.windows_realtime `
  --virtual-mic `
  --bridge-poll-interval-ms 2 `
  --diagnostic-trace `
  --progress-file resultados\progresso.json
```

Esses recursos não corrigem nem mascaram descontinuidades. Eles servem para
localizar a primeira fronteira em que o artefato aparece.

Na matriz interativa do Checkpoint 37, captura bruta, bypass pré-ponte e STFT
pré-ponte não apresentaram falhas objetivas. Os blocos silenciosos adicionais
apareceram no endpoint e acompanharam descartes locais e underruns.

Polling de 2 ms reduziu fortemente esses eventos no bypass, mas a STFT ainda
precisa de repetição pareada antes de qualquer mudança de default. Portanto,
`--poll-ms 2` no capturador de diagnóstico permanece uma mitigação
experimental; profundidade 2, fila local 4, DSP e protocolo PCM v1 continuam
congelados.

O Checkpoint 38 repetiu a comparação STFT em três pares de 60 s. No agregado,
2 ms reduziu descartes locais de 95 para 20, underruns de 72 para 54 e zeros
excedentes de 97 para 25. Portanto, 2 ms passa a ser o valor preferido para o
capturador de diagnóstico.

No retorno privado ao HyperX, os pipocos desapareceram, mas o áudio processado
continuou não preferido por chiado, maior ruído de fundo e artefatos nas
bordas. Essa decisão não altera o DSP, a profundidade 2, a fila local 4 nem o
protocolo PCM v1.

## RNNoise persistente

O RNNoise aprovado na escuta cega pode ser testado no host sem ponte:

```powershell
.\scripts\native\Build-RNNoiseAdapter.ps1
python -m realtime_audio.windows_realtime `
  --self-test `
  --method rnnoise `
  --duration 5 `
  --block-ms 20 `
  --no-save
```

O caminho usa uma DLL persistente, dois frames nativos de 480 amostras por
bloco e resampling FIR causal `16 -> 48 -> 16 kHz`. A latencia algoritmica
medida e `21,3125 ms`. O metodo esta disponivel na CLI, mas ainda nao e o
padrao da UI nem do ensaio com endpoint.
