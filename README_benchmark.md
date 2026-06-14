# Benchmark preliminar de reducao de ruido em voz

> Para o contexto completo do projeto, estado atual e responsabilidades da
> equipe, consulte [`docs/onboarding_equipe.md`](docs/onboarding_equipe.md).

Este diretório implementa um pipeline pequeno e reprodutivel em PC para comparar baselines de reducao de ruido em voz humana:

- baseline ruidoso sem processamento;
- STFT com subtracao espectral;
- STFT com ganho espectral simples inspirado em Wiener;
- Wavelet DWT com limiarizacao soft;
- Wavelet Packet Transform com ganho Wiener, em trilha experimental separada.

## Decisao tecnica atual

A implementacao principal para a plataforma PC e a subtracao STFT causal
adaptativa. Ela ja opera com estado causal, blocos de 20 ms e parametros
congelados, e obteve no final operacional +3,76 dB de SNR, +2,65 dB de SI-SDR
e 0,0% de degradacoes.

A WPT em quadros e o resultado Wavelet mais forte ate agora, especialmente no
perfil `max`, mas permanece offline: usa estimativa global/por arquivo de
energia por subbanda e nao deve ser descrita como causal nem como substituta da
STFT PC. A voz autoral entra depois como validacao complementar de parametros
ja congelados; ela nao e bloqueio para a decisao tecnica PC.

O plano e o historico da trilha Wavelet estao em
`docs/plano_wavelet_packet_wiener.md`.

## Nucleo reutilizavel

As funcoes de processamento e metricas ficam em `benchmark_audio/denoise.py`. Esse modulo nao depende de pandas nem Matplotlib e pode ser importado pelo futuro prototipo em tempo real:

- `DenoiseConfig`: parametros padrao de audio e algoritmos;
- `process_method`: aplica `noisy`, `stft_subtraction`, `stft_wiener`,
  `wavelet_soft` ou `wavelet_packet_wiener`;
- `spectral_subtraction`, `wiener_gain`, `wavelet_denoise` e
  `wavelet_packet_wiener_denoise`: metodos individuais;
- `mix_at_snr`, `snr_db`, `mse`, `si_sdr`: mistura controlada e metricas;
- `read_wav_mono` e `write_wav`: E/S WAV mono normalizada.

Parametros padrao do nucleo: 16 kHz, STFT com `n_fft=512`,
`hop_length=160`, estimativa de ruido nos primeiros 0,25 s, subtracao
espectral com `alpha=1.2` e piso `0.03`, Wiener com piso `0.05`, DWT Wavelet
`db4` nivel 5 com limiarizacao soft e WPT `db4` nivel 3 com quantil rolante
0,20 e piso de ganho 0,05.

## Ambiente

```powershell
python -m pip install -r requirements.txt
```

## Execucao principal

```powershell
python -m benchmark_audio.run_benchmark --prepare-demo-data
```

O comando baixa amostras publicas pequenas de fala humana, gera ruidos sinteticos controlados, cria misturas pareadas em SNRs de -5, 0, 5 e 10 dB, processa todos os metodos e salva resultados em:

- `resultados/tabelas/metricas_por_condicao.csv`
- `resultados/tabelas/resumo_por_metodo_snr.csv`
- `resultados/tabelas/viabilidade_embarcada.csv`
- `resultados/pgfplots/`
- `resultados/figuras/`
- `resultados/audio/`

Os arquivos em `resultados/pgfplots/` sao dados numericos leves para montagem nativa dos graficos no LaTeX com `pgfplots`. Eles incluem series de melhoria de SNR, RTF medio, formas de onda decimadas e espectrogramas reduzidos.

Para regenerar apenas esses dados a partir dos CSVs e WAVs ja existentes:

```powershell
python -m benchmark_audio.run_benchmark --export-pgfplots-only
```

## Ruidos ambientais reais

Para a proxima etapa experimental, foi adicionado um caminho opcional para usar ruidos ambientais reais do DEMAND, sem baixar bases grandes automaticamente durante o benchmark.

Primeiro, gere ou atualize o manifesto leve dos arquivos 16 kHz:

```powershell
python -m benchmark_audio.prepare_environmental_noise --manifest-only
```

O manifesto fica em `resultados/tabelas/demand_archives_manifest.csv` e registra codigo do ambiente, categoria, URL do deposito Zenodo, DOI, tamanho, MD5 e observacao de licenca.

Para preparar snippets locais, copie os ZIPs oficiais para `dados/external/demand/` ou rode o preparador com download explicito. O subconjunto padrao cobre um ambiente domestico, um de escritorio, um publico e um de transporte:

```powershell
python -m benchmark_audio.prepare_environmental_noise --download
```

Tambem e possivel selecionar ambientes:

```powershell
python -m benchmark_audio.prepare_environmental_noise --download --environments DKITCHEN OOFFICE PCAFETER STRAFFIC
```

Os WAVs preparados ficam em `dados/demo/noise_demand/`, pasta ignorada pelo Git. A tabela `resultados/tabelas/demand_noise_prepared.csv` registra quais snippets foram gerados ou quais arquivos ainda estao ausentes.

Depois de preparar os WAVs, rode o benchmark usando a pasta de ruido real:

```powershell
python -m benchmark_audio.run_benchmark --noise-dir dados/demo/noise_demand --results-dir resultados/demand
```

Quando `--noise-dir` e usado, os ruidos sinteticos sao substituidos pelos WAVs da pasta, mas o pareamento por fala, ruido, SNR e metodo continua o mesmo. `--results-dir` mantem a rodada ambiental separada dos resultados sinteticos oficiais. Use `--max-noises` para limitar uma rodada de validacao curta.

## Refinamento com validacao e conjunto final

O refinamento de parametros usa uma pasta de fala separada para preservar o benchmark historico de cinco falantes. O comando abaixo prepara seis falantes FSDD, remove o silencio inicial garantido apenas durante a montagem das condicoes, testa 144 configuracoes na validacao e avalia as tres configuracoes escolhidas em falantes e ambientes separados:

```powershell
python -m benchmark_audio.run_refinement --prepare-speech
```

Divisao usada:

- validacao: falantes `jackson`, `nicolas` e `theo`; ruidos `DKITCHEN` e `OOFFICE`;
- conjunto final operacional: falantes `george`, `lucas` e `yweweler`; ruidos `PCAFETER` e `STRAFFIC`;
- quatro SNRs por combinacao: -5, 0, 5 e 10 dB.

A busca compara:

- STFT com estimativa inicial ou selecao offline dos quadros de menor energia;
- `n_fft` 256/512, saltos 80/160, diferentes pisos e agressividades;
- DWT Wavelets `db4`, `sym4` e `coif1`;
- niveis 3/5, limiares soft/hard, globais/por escala e fatores 0,50/0,75/1,00.

Resultados ficam em `resultados/demand_refinement/`. Os principais arquivos sao:

- `validation_candidates.csv`: 144 configuracoes avaliadas apenas na validacao;
- `selected_configs.csv`: melhor configuracao de cada familia;
- `comparison_metrics.csv`: comparacao padrao versus refinada;
- `comparison_overall.csv`: resumo agregado com melhoria, degradacao e custo;
- `split_manifest.csv` e `metadata_refinement.json`: divisao e regras do protocolo.

A estimativa por quadros de baixa energia e offline, pois examina o trecho completo. Ela testa a robustez sem silencio inicial, mas ainda precisa ser convertida em estimador causal/rolante antes de uso realtime.

O resultado neutro da DWT limiarizada nao encerra a linha Wavelet. A proxima
comparacao Wavelet deve usar WPT para tratar baixas e altas frequencias como
subbandas, estimar ruido ao longo do tempo e aplicar ganho Wiener suave, em vez
de threshold hard/soft global.

### Refinamento WPT + Wiener

A primeira versao offline da trilha WPT fica atras de uma flag explicita para
preservar a rodada historica. Use sempre um diretorio novo:

```powershell
python -m benchmark_audio.run_refinement `
  --include-wpt `
  --results-dir resultados/wpt_refinement
```

Com `--include-wpt`, a grade adiciona 36 candidatos `wavelet_packet`:
`db4`/`sym4`, niveis 3/4, quantis rolantes 0,10/0,20/0,35 e pisos de ganho
0,02/0,05/0,10. A primeira rodada local selecionou
`wpt_wiener_sym4_l3_rolling_q0.2_w31_f0.1`. Na divisao operacional existente,
essa configuracao obteve +0,37 dB de SNR medio, -0,25 dB de SI-SDR medio e
25,0% de degradacoes de SNR. Portanto, a WPT inicial supera a DWT limiarizada
em SNR, mas ainda nao supera as STFTs e deve permanecer como exploratoria ate
haver nova formulacao, escuta critica e validacao adicional.

### Busca Wavelet pesada

Para responder a revisao tecnica de que a WPT inicial poderia estar
subexplorada, foi criado um executor separado:

```powershell
python -m benchmark_audio.run_wavelet_heavy_refinement `
  --profile focused `
  --results-dir resultados/wavelet_heavy_refinement
```

Esse comando faz uma triagem ampla somente dentro da validacao, depois reavalia
os melhores na validacao completa e so entao mede o final operacional. O perfil
`focused` avaliou 2556 candidatos na triagem: 720 DWT, 972 WPT por coeficiente
e 864 WPT em quadros com overlap. O melhor resultado Wavelet veio da formulacao
em quadros:

- robusta: `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  final com +3,21 dB SNR, +1,75 dB SI-SDR e 0,0% degradacoes;
- maior SNR: `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  final com +3,52 dB SNR, +1,78 dB SI-SDR e 4,2% degradacoes.

Leitura atual: a DWT limiarizada continua fraca, a WPT por coeficiente continua
limitada, mas WPT em quadros demonstrou desempenho objetivo decente. Ainda assim
ela e offline, usa estimativa global de quantil e permanece abaixo da subtracao
STFT offline de baixa energia (+4,85 dB SNR e +3,72 dB SI-SDR). O perfil `max`
existe para auditoria longa; uma tentativa inicial em
`resultados/wavelet_heavy_max_refinement/` foi interrompida antes de gerar
resultados completos.

Uma rodada `max` completa posterior foi salva em pasta separada:

```powershell
python -m benchmark_audio.run_wavelet_heavy_refinement `
  --profile max `
  --results-dir resultados/wavelet_heavy_max_refinement_full `
  --screening-speakers 1 `
  --screening-noises-per-group 1 `
  --full-per-family 20
```

Ela triou 8784 candidatos, reavaliou 113 na validacao completa e comparou 12 no
final operacional. O `max` encontrou configuracoes WPT em quadros melhores que
o `focused`:

- robusta: `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  final com +3,21 dB SNR, +1,92 dB SI-SDR e 0,0% degradacoes;
- maior SNR: `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  final com +3,61 dB SNR, +2,10 dB SI-SDR e 0,0% degradacoes.

A leitura proporcional e que o `max` reforca a WPT em quadros como frente
Wavelet offline forte. Ele nao troca a candidata PC principal: a subtracao STFT
causal adaptativa segue com +3,76 dB SNR, +2,65 dB SI-SDR e 0,0% degradacoes, e
ja opera com estado causal. A configuracao `db6` tambem deve ser narrada com
cautela porque teve 4,2% degradacoes na validacao, apesar de nao degradar no
final.

## Estimador causal de ruido

A etapa PC-1 adiciona `benchmark_audio/causal.py`, com estado explicito,
reinicializavel e deterministico. O modo adaptativo usa somente espectros
passados, quantil rolante por bin, decisao causal de baixa energia e duas taxas
de atualizacao exponencial: rapida fora de fala provavel e lenta durante fala.

Para reproduzir a selecao no conjunto de desenvolvimento e a comparacao com
bypass, calibracao curta, estimativa inicial antiga e limite offline de baixa
energia:

```powershell
python -m benchmark_audio.run_causal_estimator
```

Os resultados ficam em `resultados/causal_estimator/tabelas/`. A configuracao
selecionada usa STFT 512/160, blocos de 20 ms, aquecimento de 250 ms, historico
de 500 ms, quantil espectral 0,22, limiar de fala de 6 dB, EMA 0,30 em baixa
energia e 0,005 durante fala provavel. Na divisao operacional existente, a
subtracao causal obteve +3,76 dB de SNR e +2,65 dB de SI-SDR, sem degradacoes;
o estimador offline de baixa energia permaneceu como limite superior em
+4,85 dB e +3,72 dB.

O contrato completo, estado e limitacoes estao em
`docs/estimador_causal.md`.

## Validacao Windows prolongada

O Checkpoint 24 executou a implementacao PC congelada no Windows usando a
subtracao STFT causal adaptativa, bloco de 20 ms e `noise-mode adaptive`.
Os artefatos foram gravados em pasta nova:

```text
resultados/windows_realtime_longrun/
```

Rodada sintetica prolongada, sem dispositivo fisico:

```powershell
python -m realtime_audio.windows_realtime `
  --self-test `
  --method stft_subtraction `
  --noise-mode adaptive `
  --duration 600 `
  --block-ms 20 `
  --output-dir resultados/windows_realtime_longrun `
  --no-save
```

Resultado principal: 30.000 blocos, media 0,987 ms, p95 1,271 ms,
p99 1,594 ms, pior bloco 4,127 ms, RTF medio 0,049 e zero blocos acima de
20 ms.

Rodada fisica de entrada, sem salvar audio:

```powershell
python -m realtime_audio.windows_realtime `
  --input-only `
  --duration 600 `
  --method stft_subtraction `
  --noise-mode adaptive `
  --block-ms 20 `
  --input-device 2 `
  --output-dir resultados/windows_realtime_longrun `
  --no-save
```

No PC testado, o dispositivo valido foi `Microfone (USB Audio Device), MME`
com indice 2. A rodada registrou 29.998 blocos, media 1,280 ms, p95 2,205 ms,
p99 3,904 ms, pior bloco 6,799 ms, RTF medio 0,064, zero blocos acima de
20 ms e `status_counts` vazio. A latencia de entrada reportada pelo driver foi
40 ms e o JSON estimou 72 ms ao somar 32 ms algoritmicos; esse valor nao e
round-trip fisico, pois a validacao foi `input-only`.

Esses resultados sustentam estabilidade operacional prolongada da STFT causal
no Windows. Eles nao medem playback, escuta perceptual, Bluetooth ou voz
autoral.

## Full-duplex cabeado no Windows

O Checkpoint 26 executou uma demonstracao captura-processa-reproduz usando
entrada fisica e saida cabeada/controlada, sem Bluetooth como saida. Os
artefatos foram gravados em:

```text
resultados/windows_realtime_wired/
```

No PC testado, os dispositivos validos via MME foram:

- entrada: `Microfone (USB Audio Device), MME`, indice 2;
- saida: `Alto-falantes (AB13X USB Audio), MME`, indice 8.

Comando principal da rodada longa:

```powershell
python -m realtime_audio.windows_realtime --pc-demo wired --duration 600
```

Esse preset aplica automaticamente a configuracao validada do Checkpoint 26:
`stft_subtraction`, `noise-mode adaptive`, bloco de 20 ms, entrada indice 2,
saida indice 8, `resultados/windows_realtime_wired` e `--no-save`.

Comando equivalente expandido:

```powershell
python -m realtime_audio.windows_realtime `
  --duration 600 `
  --method stft_subtraction `
  --noise-mode adaptive `
  --block-ms 20 `
  --input-device 2 `
  --output-device 8 `
  --output-dir resultados/windows_realtime_wired `
  --no-save
```

Resultado principal: 29.998 blocos, media 1,259 ms, p95 1,965 ms, p99
3,283 ms, pior bloco 7,301 ms, RTF medio 0,063, zero blocos acima de 20 ms,
estado maximo 60.900 bytes e `status_counts` vazio. Um resumo CSV foi gerado
em `resultados/tabelas/realtime_windows_wired.csv`.

Essa rodada demonstra funcionamento full-duplex cabeado da plataforma PC por
10 min, com folga computacional por bloco. A saida MME cabeada, porem,
reportou 200 ms de latencia de saida; portanto o total estimado de 272 ms no
JSON nao deve ser interpretado como prova de baixa latencia ponta a ponta.
Tentativas com WASAPI/WDM-KS de menor latencia declarada falharam por
`Invalid sample rate`, `Invalid device` ou combinacao ilegal de dispositivos a
16 kHz neste PC.

## Preparacao de voz autoral

O protocolo de privacidade, gravacao e divisao entre Sessoes A/B esta em
`docs/protocolo_voz_autoral.md`. Antes da coleta, use tambem:

- `docs/autorizacao_voz_autoral.md`;
- `docs/roteiro_voz_autoral.md`;
- modelos em `dados/templates/authored_voice/`.

Depois de preencher um manifesto privado:

```powershell
python -m benchmark_audio.prepare_authored_voice `
  --manifest dados/private/authored_voice/manifests/session_a_raw_manifest.csv
```

A ingestao valida WAV PCM, metadados, clipping, silencio e duracao; preserva o
bruto; remove somente DC; converte para mono a 16 kHz; e gera manifesto
preparado, relatorio de qualidade e SHA-256. Nenhuma normalizacao ou reducao de
ruido e aplicada aos derivados de referencia. A CLI exige nivel de autorizacao
e `consent_record_id`.

Depois de ingerir a Sessao A ou B, a avaliacao objetiva autoral usa os
parametros congelados do estimador causal e nao faz nova busca:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --session session_b `
  --results-dir resultados/authored_voice/evaluation/session_b_final
```

A CLI monta misturas controladas apenas com `raw_quiet + raw_noise`, calcula
SNR, SI-SDR, MSE, RTF, percentis e memoria, e processa `raw_live_noisy` somente
com estatisticas operacionais. Ela grava CSV/JSON, mas nao salva audio por
padrao. O protocolo de escuta e o modelo de formulario estao em
`docs/avaliacao_autoral.md` e
`dados/templates/authored_voice/perceptual_rating_template.csv`.

## Processamento reproduzivel de WAV em blocos

A etapa PC-2 adiciona uma CLI sem dispositivo de audio que converte o WAV para
mono a 16 kHz, processa blocos de 10, 20 ou 32 ms com o mesmo
`CausalSTFTProcessor` da captura Windows e grava WAV PCM16, CSV por bloco e JSON
por execucao:

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

Nao ha normalizacao automatica. O comprimento depois da conversao para 16 kHz
e preservado, inclusive no ultimo bloco curto. A saida permanece alinhada por
indice de amostra; a latencia algoritmica estimada da STFT e registrada
separadamente e nao e inserida como silencio no arquivo. Use `--overwrite` para
autorizar explicitamente a substituicao das tres saidas.

A matriz pequena da PC-2 usa uma fala publica FSDD preparada, um trecho
`PCAFETER` do DEMAND, SNRs de -5 e 5 dB, blocos de 10/20/32 ms, bypass,
subtracao causal, Wiener causal e as referencias offline de baixa energia:

```powershell
python -m benchmark_audio.run_file_blocks_experiment
python -m realtime_audio.generate_test_vectors
```

Resultados ficam em `resultados/file_blocks/`; vetores sinteticos curtos,
configuracao e hashes ficam em `test_vectors/file_blocks/`. O contrato completo
esta em `docs/processamento_wav_blocos.md`.

## Verificacao

```powershell
python -m compileall benchmark_audio realtime_audio
python -m pytest -q
python -m benchmark_audio.run_benchmark --export-pgfplots-only
```

## Parametros padrao

- Taxa de amostragem: 16 kHz.
- Duracao por trecho: 3 s.
- Semente aleatoria: 3527.
- STFT: janela Hann, `n_fft=512`, salto de 160 amostras (10 ms), estimativa de ruido pelos primeiros 0,25 s da mistura.
- Wavelet: `db4`, nivel 5, limiarizacao soft com estimativa robusta por MAD.

## Observacao metodologica

As amostras de fala sao humanas e publicas, mas os ruidos do modo demonstrativo sao sinteticos. Portanto, os resultados devem ser tratados como preliminares: eles validam o pipeline, a comparacao pareada e a instrumentacao de metricas, mas ainda nao substituem uma avaliacao com bases ambientais reais como DEMAND.
