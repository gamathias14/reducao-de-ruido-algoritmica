# Dados leves para graficos nativos em LaTeX

Esta pasta e gerada por `python -m benchmark_audio.run_benchmark` ou pelo modo
`python -m benchmark_audio.run_benchmark --export-pgfplots-only`.

O Python calcula metricas, sinais decimados e matrizes reduzidas; o PDF final monta os graficos com `pgfplots` e `tikzpicture`.

Arquivos principais:

- `melhoria_snr.csv`: barras agrupadas de melhoria media de SNR por SNR alvo e metodo.
- `rtf_por_metodo.csv`: RTF medio por metodo, tambem em escala `rtf_medio_x1000` para leitura no eixo vertical.
- `formas_onda_exemplo.csv`: exemplo temporal decimado, com sinais originais e versoes empilhadas para plotagem.
- `espectrograma_*.csv`: matrizes reduzidas de espectrograma, em dB relativo ao pico global do exemplo.
- `parametros_espectrograma.tex`: macros com dimensoes da malha usada por `matrix plot*`.
- `espectrogramas_manifesto.csv`: metadados dos espectrogramas exportados.

Parametros do benchmark associado:

- taxa de amostragem: 16000 Hz;
- duracao: 3.00 s;
- semente: 3527;
- STFT: `n_fft=512`, `hop_length=160`;
- Wavelet: `db4`, nivel 5, limiarizacao `soft`.

Os espectrogramas sao reduzidos de proposito para manter a compilacao LaTeX confortavel.
Eles servem como visualizacao preliminar, nao como substituto dos CSVs completos de metricas.
