# Checkpoints do projeto

Este arquivo registra pontos de parada organizados para retomada do trabalho.

## Checkpoint 0 - Organizacao local e prompt de implementacao

- Data: 2026-06-06
- Estado: repositorio Git local inicializado e remoto configurado.
- Commit local inicial: `c4546ee` (`docs: organizar prompts e checkpoints do projeto`)
- Remoto: `https://github.com/gamathias14/reducao-de-ruido-algoritmica.git`
- Identidade local Git: `Kasajizoo <augustolima04@gmail.com>`
- Arquivos principais envolvidos:
  - `.gitignore`
  - `prompt_aprofundamento_implementacao.md`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
- Pendencia: autenticar `gh` com uma conta que tenha permissao de escrita no repositorio remoto.
- Proximo checkpoint sugerido: primeiro commit com organizacao documental e prompts.

## Checkpoint 1 - Pipeline Python de benchmark

- Data: 2026-06-06
- Estado: pacote `benchmark_audio` criado e verificado por sintaxe.
- Commit local: `f690988` (`code: adicionar pipeline de benchmark de audio`)
- Arquivos principais:
  - `.gitignore`
  - `README_benchmark.md`
  - `requirements.txt`
  - `dados/README.md`
  - `benchmark_audio/__init__.py`
  - `benchmark_audio/run_benchmark.py`
- Comandos de verificacao:
  - `python -c "import numpy, scipy, pandas, matplotlib, pywt; print('imports ok')"`
  - `python -m compileall benchmark_audio`
- Pendencias:
  - avaliar uso de base real de ruido, como DEMAND, no proximo ciclo;
  - testar variacoes de familias Wavelet e limiares.

## Checkpoint 2 - Resultados preliminares gerados

- Data: 2026-06-06
- Estado: benchmark demonstrativo executado de ponta a ponta.
- Commit local: `49ebff0` (`results: gerar benchmark preliminar de audio`)
- Comando principal:
  - `python -m benchmark_audio.run_benchmark --prepare-demo-data`
- Matriz experimental:
  - 5 trechos de fala humana do FSDD;
  - 4 ruidos sinteticos;
  - SNRs alvo de -5, 0, 5 e 10 dB;
  - metodos `noisy`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`;
  - 320 linhas de metricas.
- Arquivos gerados:
  - `resultados/tabelas/metricas_por_condicao.csv`
  - `resultados/tabelas/resumo_por_metodo_snr.csv`
  - `resultados/tabelas/resumo_resultados_latex.tex`
  - `resultados/tabelas/metadata_benchmark.json`
  - `resultados/tabelas/viabilidade_embarcada.csv`
  - `resultados/figuras/barras_melhoria_snr.png`
  - `resultados/figuras/barras_rtf.png`
  - `resultados/figuras/exemplo_formas_onda.png`
  - `resultados/figuras/exemplo_espectrogramas.png`
  - `resultados/audio/exemplo_clean.wav`
  - `resultados/audio/exemplo_noisy.wav`
  - `resultados/audio/exemplo_stft_subtraction.wav`
  - `resultados/audio/exemplo_stft_wiener.wav`
  - `resultados/audio/exemplo_wavelet_soft.wav`
- Resultados principais:
  - STFT subtracao: melhoria media de SNR entre 5,89 dB e 9,63 dB, conforme SNR alvo.
  - STFT Wiener: melhoria media de SNR entre 5,49 dB e 7,46 dB.
  - Wavelet soft: melhoria pequena e inconsistente, com piora de -0,92 dB no caso de SNR alvo 10 dB.
  - RTF medio maximo observado entre os metodos processados: aproximadamente `0.0021`, em PC.
- Pendencias:
  - atualizar `entrega3.tex` com resultados preliminares;
  - compilar e verificar PDF atualizado;
  - registrar commit especifico do relatorio atualizado.
