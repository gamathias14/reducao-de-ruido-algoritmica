# Dados de audio

Este repositorio nao versiona bases grandes de audio. O benchmark usa dois caminhos:

1. `dados/raw/`: entrada local ou baixada automaticamente, ignorada pelo Git.
2. `dados/demo/`: amostras preparadas pelo script a partir de arquivos publicos pequenos, tambem regeneraveis.

## Demonstracao reprodutivel

O comando abaixo baixa pequenas gravacoes de voz humana do Free Spoken Digit Dataset (FSDD), concatena trechos curtos ate 3 s, gera ruidos sinteticos controlados e executa o benchmark:

```powershell
python -m benchmark_audio.run_benchmark --prepare-demo-data
```

Origem das amostras de fala usadas no modo demonstrativo:

- Free Spoken Digit Dataset: https://github.com/Jakobovski/free-spoken-digit-dataset

Os ruidos do modo demonstrativo sao gerados por script para manter o experimento leve e reprodutivel: branco, rosa, hum de baixa frequencia e impulsivo. Essa escolha e uma limitacao metodologica; para resultados finais, recomenda-se substituir ou complementar esses ruidos por bases como DEMAND ou VoiceBank-DEMAND.

## Como usar dados locais

Para usar bases externas sem versiona-las, coloque arquivos WAV de fala limpa em `dados/raw/clean/` e ruidos em `dados/raw/noise/`. O pipeline atual prioriza o modo demonstrativo automatizado, mas as funcoes de leitura padronizam WAV para mono, 16 kHz e amplitude normalizada.

## DEMAND como proxima base ambiental

Foi criado um preparador opcional para a base DEMAND:

```powershell
python -m benchmark_audio.prepare_environmental_noise --manifest-only
python -m benchmark_audio.prepare_environmental_noise --download --environments DKITCHEN OOFFICE PCAFETER STRAFFIC
```

O primeiro comando gera apenas o manifesto leve `resultados/tabelas/demand_archives_manifest.csv`. O segundo baixa os ZIPs selecionados para `dados/external/demand/` e prepara trechos WAV em `dados/demo/noise_demand/`.

As pastas `dados/external/` e `dados/demo/` ficam fora do Git. Assim, os metadados e scripts permanecem reprodutiveis, mas as bases grandes e os trechos derivados nao incham o repositorio.

Para executar a rodada ambiental sem sobrescrever o benchmark sintetico:

```powershell
python -m benchmark_audio.run_benchmark --noise-dir dados/demo/noise_demand --results-dir resultados/demand
```

O refinamento usa `dados/demo/clean_refinement/`, com seis falantes FSDD, para nao alterar o conjunto historico de cinco falantes em `dados/demo/clean/`. Ambas as pastas sao regeneraveis e ignoradas pelo Git.

Fonte registrada para DEMAND:

- Zenodo: https://zenodo.org/records/1227121
- DOI: `10.5281/zenodo.1227121`
- Licenca a conferir antes de redistribuir derivados: o texto do registro informa `CC BY-SA 3.0`; o metadado atual do Zenodo tambem deve ser verificado no momento de uso final.

## Voz autoral privada

O protocolo de coleta fica em:

- `docs/protocolo_voz_autoral.md`;
- `docs/autorizacao_voz_autoral.md`;
- `docs/roteiro_voz_autoral.md`.

Modelos de manifesto e folha de sessao ficam em
`dados/templates/authored_voice/`. Os arquivos preenchidos devem ser copiados
para `dados/private/authored_voice/`, pasta ignorada pelo Git.

Estrutura dos WAVs:

```text
dados/raw/authored_voice/
  spk01/session_a/quiet/
  spk01/session_a/noise/
  spk01/session_a/live_noisy/
  spk01/session_b/...
  spk02/...
  spk03/...
```

Ingestao:

```powershell
python -m benchmark_audio.prepare_authored_voice `
  --manifest dados/private/authored_voice/manifests/session_a_raw_manifest.csv
```

Os derivados mono a 16 kHz ficam em `dados/prepared/authored_voice/`. O script
remove apenas DC e faz conversao de canais/taxa/formato; nao aplica
normalizacao, denoising, gate, equalizacao ou compressao. WAVs brutos,
derivados e termos assinados permanecem fora do Git.

Depois da ingestao, a avaliacao objetiva autoral deve consumir somente o
manifesto preparado:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --session session_b `
  --results-dir resultados/authored_voice/evaluation/session_b_final
```

Essa etapa gera CSV/JSON em `resultados/authored_voice/evaluation/`, sem salvar
audio processado por padrao. SNR, SI-SDR e MSE sao calculados apenas em
misturas controladas com `raw_quiet`; `raw_live_noisy` recebe somente
estatisticas operacionais e avaliacao perceptual separada.
