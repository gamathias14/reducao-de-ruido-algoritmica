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
