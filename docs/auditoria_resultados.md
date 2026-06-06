# Auditoria dos resultados

Este arquivo deve ser atualizado ao final de cada etapa tecnica.

## 2026-06-06 - Auditoria inicial

Ainda nao ha resultados experimentais de benchmark para auditar. A auditoria inicial identificou que:

- `entrega3.tex` esta bem estruturado como reformulacao de escopo, mas ainda e prospectivo.
- A secao de atividades realizadas afirma que ainda nao ha resultados experimentais de desempenho.
- O proximo trabalho precisa gerar evidencias concretas: scripts, tabelas, graficos, exemplos de audio e analise de viabilidade.
- O prompt de aprofundamento foi atualizado para exigir reproducibilidade, comparacao pareada e autocritica antes de alterar o relatorio.

## Checklist de auditoria para benchmarks futuros

- Os dados de entrada estao documentados?
- As comparacoes usam as mesmas amostras, ruidos e SNRs?
- Os parametros de STFT e Wavelet foram registrados?
- As formulas de SNR, melhoria de SNR, MSE e SI-SDR foram revisadas?
- Os graficos foram gerados automaticamente por scripts?
- As conclusoes do relatorio sao proporcionais ao tamanho do experimento?
- As limitacoes foram registradas explicitamente?

## 2026-06-06 - Auditoria do benchmark preliminar

### Reprodutibilidade

- Resultado observado: o pipeline roda de ponta a ponta com:
  - `python -m benchmark_audio.run_benchmark --prepare-demo-data`
- O script baixa amostras pequenas do FSDD e gera ruidos sinteticos por semente fixa.
- A matriz experimental resultante tem 5 amostras de fala, 4 ruidos, 4 SNRs e 4 metodos, totalizando 320 linhas.
- Risco: a etapa de download depende do GitHub e sofreu reset intermitente de conexao. O script agora tem retentativas, mas uma execucao totalmente offline exige que `dados/raw/fsdd/` ja esteja preenchido.

### Pareamento das comparacoes

- Resultado observado: os metodos `noisy`, `stft_subtraction`, `stft_wiener` e `wavelet_soft` recebem exatamente a mesma mistura para cada combinacao de amostra, ruido e SNR.
- Apos correcao da funcao de mistura, o baseline ruidoso apresenta melhoria de SNR igual a zero e SNR de saida igual as SNRs alvo.
- Conclusao de auditoria: a comparacao esta pareada para esta demonstracao.

### Parametros registrados

- Os parametros foram salvos em `resultados/tabelas/metadata_benchmark.json`.
- STFT: Hann, `n_fft=512`, salto de 160 amostras, estimativa de ruido em 0,25 s.
- Wavelet: `db4`, nivel 5, limiarizacao soft por MAD.
- Limitacao: os parametros nao foram otimizados em conjunto de validacao separado. Logo, a comparacao e de baselines iniciais, nao de metodos plenamente ajustados.

### Metricas

- SNR, melhoria de SNR, MSE, SI-SDR, tempo de processamento, RTF, latencia algoritmica e memoria aproximada foram salvos em CSV.
- Risco corrigido: a primeira versao escalava a mistura para evitar clipping e alterava a SNR observada contra a referencia. A escala foi removida das metricas; a normalizacao ficou restrita aos WAVs de demonstracao.
- Risco remanescente: SI-SDR pode penalizar fortemente distorcoes de escala e forma; deve ser interpretada junto de SNR, MSE, forma de onda e espectrograma.

### Resultados que merecem cautela

- STFT por subtracao espectral obteve melhoria media alta de SNR, de 5,89 a 9,63 dB. Isso e plausivel no arranjo demonstrativo porque ha silencio inicial para estimativa de ruido e ruidos sinteticos controlados.
- Essa melhoria nao deve ser extrapolada para ambientes reais sem DEMAND, VoiceBank-DEMAND ou base equivalente.
- Wavelet soft foi mais rapida, mas teve melhoria pequena e piorou SNR em 10 dB. Isso sugere que o limiar universal/MAD pode estar agressivo ou inadequado para fala ja relativamente limpa.
- A conclusao permitida e limitada: neste benchmark preliminar, os baselines STFT foram mais efetivos nas metricas objetivas; ainda nao se pode afirmar superioridade geral em fala real ruidosa.

### Justica STFT versus Wavelet

- Pontos justos:
  - mesmas entradas;
  - mesmas SNRs;
  - mesmas duracoes;
  - mesma taxa de amostragem;
  - metricas calculadas contra a mesma referencia limpa.
- Pontos frageis:
  - STFT usa uma vantagem explicita: silencio inicial para estimar ruido.
  - Wavelet nao usa modelo explicito de ruido nem ajuste por tipo de ruido.
  - A familia `db4`, nivel 5 e limiar soft nao foram comparados contra outras familias ou limiares.
- Recomendacao: no proximo ciclo, testar `sym4`, limiar hard, limiares por escala e um protocolo sem silencio inicial garantido.

### Viabilidade embarcada

- A tabela `resultados/tabelas/viabilidade_embarcada.csv` diferencia PC, Raspberry Pi, ESP32/ESP32-S3 e Arduino Uno R3.
- Resultado tecnico preliminar:
  - PC e adequado para validacao e geracao de referencia.
  - Raspberry Pi e a primeira plataforma embarcada plausivel.
  - ESP32/ESP32-S3 exige simplificacao, C/C++ e cuidado com buffers.
  - Arduino Uno R3 e impraticavel para STFT/Wavelet de voz em tempo real no escopo atual, especialmente por 2 KB de SRAM, 32 KB de flash e ausencia de FPU.

### Conclusoes permitidas

- Permitido afirmar:
  - foi implementado um pipeline inicial em PC;
  - foram geradas misturas pareadas com SNRs controladas;
  - STFT subtracao e STFT Wiener melhoraram SNR neste experimento preliminar;
  - Wavelet soft teve resultado inferior com os parametros atuais;
  - todos os metodos medidos rodaram abaixo de tempo real em PC.
- Nao permitido afirmar ainda:
  - que STFT e superior a Wavelet em geral;
  - que os resultados representam ruido ambiental real;
  - que o pipeline esta pronto para Raspberry Pi, ESP32 ou Arduino;
  - que as metricas objetivas substituem avaliacao perceptual.
