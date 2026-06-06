# Benchmark preliminar de reducao de ruido em voz

Este diretório implementa um pipeline pequeno e reprodutivel em PC para comparar baselines de reducao de ruido em voz humana:

- baseline ruidoso sem processamento;
- STFT com subtracao espectral;
- STFT com ganho espectral simples inspirado em Wiener;
- Wavelet DWT com limiarizacao soft.

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
- `resultados/figuras/`
- `resultados/audio/`

## Parametros padrao

- Taxa de amostragem: 16 kHz.
- Duracao por trecho: 3 s.
- Semente aleatoria: 3527.
- STFT: janela Hann, `n_fft=512`, salto de 160 amostras (10 ms), estimativa de ruido pelos primeiros 0,25 s da mistura.
- Wavelet: `db4`, nivel 5, limiarizacao soft com estimativa robusta por MAD.

## Observacao metodologica

As amostras de fala sao humanas e publicas, mas os ruidos do modo demonstrativo sao sinteticos. Portanto, os resultados devem ser tratados como preliminares: eles validam o pipeline, a comparacao pareada e a instrumentacao de metricas, mas ainda nao substituem uma avaliacao com bases ambientais reais como DEMAND.
