# Diario tecnico

Este arquivo registra como o trabalho esta sendo conduzido, nao apenas os resultados finais.

## 2026-06-06 - Organizacao inicial

- Verificado que `git` e `gh` estao instalados.
- Verificado que a pasta local ainda nao era um repositorio Git.
- Verificado que o `gh` esta autenticado, mas a conta ativa atual possui permissao apenas de leitura no repositorio remoto `gamathias14/reducao-de-ruido-algoritmica`.
- Inicializado repositorio Git local na pasta do projeto.
- Configurada identidade local do Git:
  - `user.name = Kasajizoo`
  - `user.email = augustolima04@gmail.com`
- Configurado remoto `origin` como `https://github.com/gamathias14/reducao-de-ruido-algoritmica.git`.
- Adicionado `.gitignore` para evitar versionamento de artefatos de LaTeX, caches Python, bases de audio grandes e resultados temporarios.
- Refinado `prompt_aprofundamento_implementacao.md` para exigir registro detalhado, auditoria critica, checkpoints e fluxo com Git.

## Proximo passo

- Autenticar no GitHub CLI com uma conta que tenha permissao de escrita no repositorio.
- Fazer o primeiro checkpoint versionado do material que deve ser preservado no Git.

## 2026-06-06 - Implementacao do benchmark preliminar em PC

### Ambiente e dependencias

- Confirmado `Python 3.11.4`.
- Confirmado `pip 25.3`.
- Confirmado `pdfTeX 3.141592653-2.6-1.40.25` / TeX Live 2023.
- O pacote PyWavelets instalado inicialmente estava incompativel com o NumPy:
  - erro observado: `ValueError: numpy.dtype size changed`.
  - comando executado: `python -m pip install --upgrade PyWavelets`.
  - versao resultante: `PyWavelets 1.9.0`.
- Verificacao de importacao executada:
  - `python -c "import numpy, scipy, pandas, matplotlib, pywt; print('imports ok')"`.

### Codigo criado

- Criado pacote `benchmark_audio/`.
- Criado script executavel por linha de comando:
  - `python -m benchmark_audio.run_benchmark --prepare-demo-data`
- Criado `requirements.txt`.
- Criado `README_benchmark.md`.
- Criado `dados/README.md`.
- Ajustado `.gitignore` para ignorar bases brutas em `dados/raw/`, mas permitir versionamento de resultados leves em `resultados/`.

### Dados e preparo

- Modo demonstrativo usa amostras pequenas de voz humana do Free Spoken Digit Dataset (FSDD):
  - origem: `https://github.com/Jakobovski/free-spoken-digit-dataset`
  - arquivos baixados para `dados/raw/fsdd/`, que fica fora do Git.
- Tentativa inicial de download via `urllib` falhou por reset de conexao:
  - erro observado: `WinError 10054`.
  - decisao: adicionar retentativas no downloader Python.
  - teste com `curl.exe` confirmou que a URL era valida e que a falha era intermitente.
- Os trechos demonstrativos sao formados por concatenacao de digitos de 5 locutores ate 3 s, com silencio inicial de 0,30 s para permitir estimativa simples de ruido nos metodos STFT.
- Ruidos do experimento demonstrativo foram gerados por script:
  - branco;
  - rosa;
  - hum de 60/120 Hz;
  - impulsivo.
- Limitacao registrada: os ruidos sinteticos validam pipeline e pareamento, mas ainda nao substituem DEMAND, VoiceBank-DEMAND ou outra base ambiental real.

### Parametros do benchmark

- Taxa de amostragem: 16 kHz.
- Duracao por trecho: 3 s.
- Semente aleatoria: 3527.
- Amostras de fala: 5.
- Tipos de ruido: 4.
- SNRs alvo: -5, 0, 5 e 10 dB.
- Total de linhas em `metricas_por_condicao.csv`: 320.
- STFT:
  - janela Hann;
  - `n_fft = 512`;
  - salto `hop_length = 160` amostras, equivalente a 10 ms;
  - estimativa de ruido pelos primeiros 0,25 s;
  - subtracao espectral com `alpha = 1.2` e piso `0.03`;
  - ganho Wiener simples com piso `0.05`.
- Wavelet:
  - familia `db4`;
  - nivel 5;
  - limiarizacao soft;
  - estimativa robusta de sigma por MAD.

### Execucao e verificacoes

- Comando executado:
  - `python -m benchmark_audio.run_benchmark --prepare-demo-data`
- Aviso observado:
  - `RuntimeWarning: divide by zero encountered in log10` durante geracao de espectrograma.
  - interpretacao: pontos com potencia zero no espectrograma; nao impediu geracao das figuras.
- Primeira execucao revelou inconsistencia na SNR observada:
  - causa: a funcao de mistura escalava internamente a mistura para evitar clipping, mas as metricas comparavam contra a fala limpa original.
  - correcao: remover escala interna da mistura para preservar a SNR matematicamente definida; normalizar apenas os audios de demonstracao no momento de salvar WAV.
- Reexecucao confirmou baseline ruidoso com melhoria de SNR igual a zero e SNR de saida igual as SNRs alvo.

### Arquivos gerados

- Tabelas:
  - `resultados/tabelas/metricas_por_condicao.csv`
  - `resultados/tabelas/resumo_por_metodo_snr.csv`
  - `resultados/tabelas/resumo_resultados_latex.tex`
  - `resultados/tabelas/metadata_benchmark.json`
  - `resultados/tabelas/viabilidade_embarcada.csv`
- Figuras:
  - `resultados/figuras/barras_melhoria_snr.png`
  - `resultados/figuras/barras_rtf.png`
  - `resultados/figuras/exemplo_formas_onda.png`
  - `resultados/figuras/exemplo_espectrogramas.png`
- Audios curtos:
  - `resultados/audio/exemplo_clean.wav`
  - `resultados/audio/exemplo_noisy.wav`
  - `resultados/audio/exemplo_stft_subtraction.wav`
  - `resultados/audio/exemplo_stft_wiener.wav`
  - `resultados/audio/exemplo_wavelet_soft.wav`

### Resultados observados

- STFT por subtracao espectral apresentou maior melhoria media de SNR no experimento demonstrativo:
  - 9,63 dB para SNR alvo -5 dB;
  - 8,42 dB para 0 dB;
  - 7,15 dB para 5 dB;
  - 5,89 dB para 10 dB.
- STFT Wiener simples tambem melhorou SNR:
  - 7,46 dB para -5 dB;
  - 6,89 dB para 0 dB;
  - 6,22 dB para 5 dB;
  - 5,49 dB para 10 dB.
- Wavelet soft teve efeito menor e inconsistente:
  - melhorou 2,15 dB em -5 dB;
  - melhorou 1,16 dB em 0 dB;
  - melhorou 0,15 dB em 5 dB;
  - piorou -0,92 dB em 10 dB.
- Tempos medios em PC ficaram muito abaixo do tempo real:
  - STFT subtracao: RTF medio aproximado `0.0021`;
  - STFT Wiener: RTF medio aproximado `0.0012`;
  - Wavelet soft: RTF medio aproximado `0.00032`.

### Commits criados

- `f690988` - `code: adicionar pipeline de benchmark de audio`
- `49ebff0` - `results: gerar benchmark preliminar de audio`

## 2026-06-06 - Atualizacao e verificacao do relatorio

### Secoes atualizadas em `entrega3.tex`

- Metodologia experimental:
  - pipeline em PC alterado de plano futuro para implementacao realizada;
  - descritos comando de reproducao, dados FSDD, ruidos sinteticos, SNRs e metodos.
- Amostras, ruidos e controle de variaveis:
  - documentado uso de fala publica pequena;
  - explicitada limitacao de ruidos sinteticos;
  - registrado pareamento por amostra, ruido, SNR e metodo.
- Metricas e custo computacional:
  - verbos ajustados para metricas ja calculadas;
  - adicionada tabela de resultados medios;
  - descritos RTF, latencia e memoria aproximada.
- Referencias:
  - adicionados FSDD, NumPy, SciPy, PyWavelets e Matplotlib.
- Atividades realizadas e resultados:
  - adicionadas atividades de implementacao;
  - inseridas figuras de melhoria de SNR, RTF, forma de onda e espectrograma.
- Cronograma:
  - ajustado para refletir tarefas antecipadas e proximo foco em ruidos reais.
- Riscos:
  - adicionados riscos de ruidos sinteticos, silencio inicial e Wavelet subajustada.
- Consideracoes finais:
  - incluida conclusao preliminar proporcional aos dados e caminho para Raspberry Pi/ESP32/Arduino Uno R3.

### Compilacao e verificacao

- Comando executado:
  - `pdflatex -interaction=nonstopmode entrega3.tex`
- Executado duas vezes para resolver referencias cruzadas.
- Resultado:
  - `entrega3.pdf`, 26 paginas, gerado sem erro fatal.
- Avisos remanescentes:
  - `microtype` nao conseguiu aplicar patch de footnote;
  - alguns `Underfull \hbox`, principalmente em tabelas;
  - sem referencias indefinidas apos a segunda compilacao.
- Verificacao visual:
  - renderizadas paginas representativas com `pdftoppm`;
  - verificadas visualmente tabela de parametros, tabela de resultados, figuras, cronograma e tabela de referencias/viabilidade;
  - figuras e tabelas principais ficaram legiveis.

### Commit criado

- `1df8e9c` - `tex: atualizar relatorio com resultados preliminares`

### GitHub

- Comando executado:
  - `git push origin main`
- Resultado:
  - push realizado com sucesso para `https://github.com/gamathias14/reducao-de-ruido-algoritmica.git`.
  - intervalo enviado: `cb4f070..43fe261`.
