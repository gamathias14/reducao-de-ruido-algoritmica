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

## 2026-06-06 - Migracao dos graficos para LaTeX nativo

### Exportacao de dados para `pgfplots`

- Adicionada saida numerica leve em `resultados/pgfplots/`.
- O pipeline continua calculando metricas e sinais em Python, mas o PDF passou a montar os graficos principais com `pgfplots` e `tikzpicture`.
- Arquivos gerados:
  - `resultados/pgfplots/melhoria_snr.csv`;
  - `resultados/pgfplots/rtf_por_metodo.csv`;
  - `resultados/pgfplots/formas_onda_exemplo.csv`;
  - `resultados/pgfplots/espectrograma_clean.csv`;
  - `resultados/pgfplots/espectrograma_noisy.csv`;
  - `resultados/pgfplots/espectrograma_stft_subtraction.csv`;
  - `resultados/pgfplots/espectrograma_wavelet_soft.csv`;
  - `resultados/pgfplots/parametros_espectrograma.tex`;
  - `resultados/pgfplots/espectrogramas_manifesto.csv`;
  - `resultados/pgfplots/README.md`.
- Criado modo de exportacao leve:
  - `python -m benchmark_audio.run_benchmark --export-pgfplots-only`
- Verificacoes executadas:
  - `python -m compileall benchmark_audio`
  - `python -m benchmark_audio.run_benchmark --export-pgfplots-only`
- Commit criado:
  - `7b0d8c9` - `data: exportar series para pgfplots`

### Alteracoes em `entrega3.tex`

- Inserido indice de ilustracoes apos o sumario, contendo:
  - lista de figuras;
  - lista de tabelas;
  - lista de graficos;
  - lista de codigos.
- Declarado o ambiente `codigo` apenas se ele ainda nao existir.
- Observacao: foi usada a extensao auxiliar `.cod` para `codigo`, em vez de reutilizar `.grf`, para evitar mistura com a lista de `grafico`, ja declarada em `cab.tex`.
- Substituidos os `\includegraphics` dos graficos principais por ambientes `grafico` com dados tabulados:
  - melhoria media de SNR por metodo e SNR alvo;
  - RTF medio por metodo, em escala `1000 x RTF`;
  - formas de onda empilhadas e decimadas;
  - espectrogramas reduzidos em matriz 2 x 2.
- Inserida secao `Proximos passos tecnicos`, com foco em DEMAND/VoiceBank-DEMAND, ampliacao de amostras, validacao separada, refinamento de Wavelet, protocolo STFT sem silencio inicial, latencia por blocos, Raspberry Pi, ESP32/ESP32-S3 e Arduino Uno R3 como inviabilidade/trabalho simplificado.
- Incluido um trecho curto de codigo do exportador `pgfplots` para alimentar a lista de codigos sem inflar o PDF.
- Atualizado `.gitignore` para ignorar auxiliares de listas LaTeX: `.lof`, `.lot`, `.grf` e `.cod`.

### Compilacao e verificacao visual

- Comandos executados:
  - `pdflatex -interaction=nonstopmode entrega3.tex`
  - recompilacoes adicionais para estabilizar sumario, listas, referencias e floats;
  - `pdftoppm` para renderizar paginas de indice, graficos e codigo.
- Resultado:
  - `entrega3.pdf` gerado com 28 paginas;
  - sem erro fatal;
  - sem referencias indefinidas;
  - sem `Overfull \hbox` remanescente apos ajuste dos espectrogramas e do grafico de formas de onda;
  - avisos remanescentes esperados: `microtype` em `footnote` e alguns `Underfull \hbox`.
- Verificacao visual:
  - o indice de ilustracoes lista tabelas, graficos e codigo corretamente;
  - os quatro graficos principais sao nativos em LaTeX;
  - os espectrogramas usam matriz reduzida para manter a compilacao confortavel;
  - o trecho de codigo ficou legivel e curto.

### Commit criado

- `dbc4fe7` - `tex: migrar graficos e listas para pgfplots`

## 2026-06-06 - Fase 1 da trilha de tempo real: nucleo reutilizavel

### Objetivo

- Preparar o codigo para o futuro prototipo em tempo real no Windows, separando os algoritmos reutilizaveis do script offline sem alterar o protocolo experimental principal.
- Evitar refatoracao ampla: o `run_benchmark.py` continua sendo o ponto de entrada do benchmark, mas passa a importar o nucleo de processamento.

### Codigo alterado

- Criado `benchmark_audio/denoise.py` com:
  - `DenoiseConfig`;
  - `normalize_peak`, `read_wav_mono`, `write_wav`;
  - geracao de ruido sintetico usada pelo benchmark;
  - `mix_at_snr`, `snr_db`, `mse`, `si_sdr`;
  - STFT, ISTFT, subtracao espectral, ganho Wiener e Wavelet;
  - `process_method`.
- Atualizado `benchmark_audio/run_benchmark.py` para usar esse nucleo e manter a exportacao de resultados como antes.
- Corrigida fragilidade encontrada no teste temporario: a selecao do exemplo representativo assumia `config.snrs_db[1]` e quebrava quando um subconjunto tinha apenas uma SNR. Agora usa a segunda SNR quando existe, ou a primeira quando ha apenas uma.
- Criado `tests/test_denoise.py` com verificacoes de sanidade via `unittest`.
- Atualizado `README_benchmark.md` com a secao de nucleo reutilizavel e comandos de verificacao.

### Verificacoes executadas

- `python -m compileall benchmark_audio`
- `python -m unittest discover -s tests`
- `python -m benchmark_audio.run_benchmark --export-pgfplots-only`
- Smoke test completo em diretorio temporario, com uma amostra sintetica curta, uma SNR e um ruido branco:
  - validou geracao de metricas e resumo sem sobrescrever os resultados oficiais;
  - resultado final: `smoke benchmark ok`.

### Resultado

- Fase 1 da trilha concluida: existe um nucleo Python reutilizavel para o futuro processamento em blocos.
- Os resultados oficiais em `resultados/tabelas/` nao foram regenerados pelo benchmark completo; apenas os dados `pgfplots` existentes foram reexportados como teste de integracao.

### Commit criado

- `d69421f` - `code: separar nucleo reutilizavel de denoise`

## 2026-06-06 - Fase 2 da trilha: prototipo Windows em tempo real por CLI

### Objetivo

- Criar a primeira versao de um processador por blocos para Windows, ainda em CLI, com caminho para captura via microfone e reproducao local.
- Permitir validacao sem dispositivo fisico por meio de autoteste sintetico.

### Codigo criado

- Criado pacote `realtime_audio/`.
- Criado `realtime_audio/windows_realtime.py` com:
  - `RealtimeConfig`;
  - `RealtimeBlockProcessor`;
  - metodos `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`;
  - blocos configuraveis em ms;
  - calibracao inicial para metodos STFT;
  - modo `--self-test` sem microfone;
  - modo `--list-devices` via `sounddevice`;
  - captura/reproducao duplex via `sounddevice.Stream`;
  - exportacao de `*_metrics.json`, `*_blocks.csv` e WAVs curtos quando habilitado.
- Criado `realtime_audio/README.md` com comandos de uso.
- Criado `tests/test_realtime_audio.py`.
- Atualizado `requirements.txt` para incluir `sounddevice>=0.4.6`.
- Atualizado `.gitignore` para ignorar `resultados/realtime/`.

### Verificacoes executadas

- `python -m compileall benchmark_audio realtime_audio`
- `python -m unittest discover -s tests`
- `python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --duration 1 --block-ms 20 --no-save`
- `python -m realtime_audio.windows_realtime --help`
- `python -c "import importlib.util; print('sounddevice', 'available' if importlib.util.find_spec('sounddevice') else 'missing')"`

### Resultado do autoteste sintetico

- Configuracao:
  - taxa de amostragem: 16 kHz;
  - metodo: `stft_subtraction`;
  - bloco: 20 ms;
  - duracao: 1 s;
  - calibracao: 250 ms;
  - STFT: `n_fft=512`, `hop_length=160`.
- Resultado registrado em `resultados/realtime/`, pasta ignorada pelo Git:
  - blocos: 50;
  - tempo medio de processamento por bloco: aproximadamente 0,357 ms;
  - pior caso por bloco: aproximadamente 0,676 ms;
  - desvio padrao: aproximadamente 0,209 ms;
  - RTF medio por bloco: aproximadamente 0,0179;
  - RTF pior caso por bloco: aproximadamente 0,0338;
  - latencia algoritmica estimada: 32 ms;
  - eventos de status: nenhum no autoteste sintetico.

### Limitacoes

- `sounddevice` nao estava instalado no ambiente atual, portanto a captura real de microfone e a reproducao fisica ainda nao foram testadas.
- O autoteste sintetico valida o processamento por blocos e a exportacao de metricas, mas nao mede latencia de driver, dispositivo, microfone ou saida.
- A adaptacao STFT ainda e uma primeira aproximacao por janela historica e calibracao inicial; estimativa adaptativa de ruido fica como proximo refinamento.

### Commit criado

- `1610701` - `code: adicionar prototipo realtime windows`

## 2026-06-06 - Fase 2: captura real input-only no Windows

### Objetivo

- Validar o prototipo em audio real sem risco de realimentacao acustica e sem salvar voz.
- Gerar uma tabela pequena de comparacao interna inicial para Windows/notebook.

### Dependencias e dispositivos

- Executado:
  - `python -m pip install -r requirements.txt`
- Resultado:
  - `sounddevice 0.5.5` instalado com sucesso.
  - Houve um reset de conexao durante consulta ao indice do pip, mas a instalacao concluiu.
- Executado:
  - `python -m realtime_audio.windows_realtime --list-devices`
- Dispositivos padrao reportados:
  - entrada: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida: `SteelSeries Sonar - Gaming`, indice 6, MME.

### Codigo alterado

- Adicionado modo `--input-only` em `realtime_audio/windows_realtime.py`.
  - Captura e processa blocos reais sem enviar audio para a saida.
  - Mantem medicao de tempo por bloco, RTF, picos e latencia de entrada reportada pelo stream.
- Criado `realtime_audio/summarize_realtime.py` para consolidar JSONs de metricas em CSV.
- Atualizado `realtime_audio/README.md` com fluxo seguro de teste.
- Gerada tabela:
  - `resultados/tabelas/realtime_windows_input_only.csv`

### Comandos executados

- Verificacao:
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
  - `python -m realtime_audio.windows_realtime --help`
- Captura real sem playback e sem salvar WAV:
  - `python -m realtime_audio.windows_realtime --input-only --duration 3 --method bypass --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 3 --method stft_subtraction --block-ms 20 --no-save`
- Consolidacao:
  - `python -m realtime_audio.summarize_realtime --pattern "windows_input_only_*_20260606_220159_metrics.json" --output resultados/tabelas/realtime_windows_input_only.csv`

### Resultados

- `bypass`:
  - 148 blocos;
  - tempo medio por bloco: 0,034 ms;
  - pior caso por bloco: 0,160 ms;
  - desvio padrao: 0,027 ms;
  - RTF medio por bloco: 0,00170;
  - RTF pior caso: 0,00801;
  - latencia de entrada reportada: 40 ms;
  - `status_counts`: vazio.
- `stft_subtraction`:
  - 148 blocos;
  - tempo medio por bloco: 0,486 ms;
  - pior caso por bloco: 2,026 ms;
  - desvio padrao: 0,278 ms;
  - RTF medio por bloco: 0,0243;
  - RTF pior caso: 0,1013;
  - latencia de entrada reportada: 40 ms;
  - latencia algoritmica estimada: 32 ms;
  - latencia total estimada input-only: 72 ms;
  - `status_counts`: vazio.

### Limitacoes

- Testes duraram apenas 3 s, suficientes para validar caminho tecnico, mas ainda curtos para estabilidade final.
- Nao houve playback/duplex nesta etapa.
- Nenhum WAV foi salvo; a medicao preserva privacidade, mas nao permite escuta comparativa.
- Os valores de latencia total ainda sao estimativas, pois falta medir saida de audio e round-trip.

### Commit criado

- `c6ce99f` - `code: medir realtime input-only no windows`

## 2026-06-06 - Fase 2: estabilidade input-only por 30 s no Windows

### Objetivo

- Estender a validacao real input-only de 3 s para 30 s por metodo.
- Comparar `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft` com a mesma taxa, bloco e politica de nao salvar WAV.
- Manter o teste sem playback, pois ainda nao houve confirmacao de uso de fone ou saida acusticamente controlada.

### Verificacoes antes da rodada

- Estado do Git conferido com:
  - `git status --short`
- Verificacoes executadas antes de alterar arquivos:
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
- Resultado:
  - compilacao sem erro;
  - 4 testes unitarios aprovados.

### Dispositivos observados

- Comando executado:
  - `python -m realtime_audio.windows_realtime --list-devices`
- Padroes reportados pelo `sounddevice` nesta rodada:
  - entrada: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida: `SteelSeries Sonar - Gaming`, indice 7, MME.

### Comandos executados

- Captura real sem playback e sem salvar WAV:
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method bypass --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_subtraction --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_wiener --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method wavelet_soft --block-ms 20 --no-save`
- Consolidacao:
  - `python -m realtime_audio.summarize_realtime --pattern "windows_input_only_*_metrics.json" --output resultados/tabelas/realtime_windows_input_only.csv`

### Resultados da rodada de 30 s

- `bypass`:
  - 1498 blocos;
  - tempo medio por bloco: 0,031 ms;
  - pior caso por bloco: 0,134 ms;
  - desvio padrao: 0,024 ms;
  - RTF medio por bloco: 0,00157;
  - RTF pior caso: 0,00670;
  - latencia de entrada reportada: 40 ms;
  - latencia total estimada input-only: 40 ms;
  - `status_counts`: vazio.
- `stft_subtraction`:
  - 1498 blocos;
  - tempo medio por bloco: 0,471 ms;
  - pior caso por bloco: 1,929 ms;
  - desvio padrao: 0,175 ms;
  - RTF medio por bloco: 0,0236;
  - RTF pior caso: 0,0964;
  - latencia de entrada reportada: 40 ms;
  - latencia algoritmica estimada: 32 ms;
  - latencia total estimada input-only: 72 ms;
  - `status_counts`: vazio.
- `stft_wiener`:
  - 1498 blocos;
  - tempo medio por bloco: 0,412 ms;
  - pior caso por bloco: 1,423 ms;
  - desvio padrao: 0,175 ms;
  - RTF medio por bloco: 0,0206;
  - RTF pior caso: 0,0711;
  - latencia de entrada reportada: 40 ms;
  - latencia algoritmica estimada: 32 ms;
  - latencia total estimada input-only: 72 ms;
  - `status_counts`: vazio.
- `wavelet_soft`:
  - 1498 blocos;
  - tempo medio por bloco: 0,258 ms;
  - pior caso por bloco: 14,749 ms;
  - desvio padrao: 0,394 ms;
  - RTF medio por bloco: 0,0129;
  - RTF pior caso: 0,737;
  - latencia de entrada reportada: 40 ms;
  - latencia algoritmica estimada: 20 ms;
  - latencia total estimada input-only: 60 ms;
  - `status_counts`: vazio.

### Observacoes e limitacoes

- Nenhum WAV de voz foi salvo; foram gerados JSONs de metricas e CSVs por bloco em `resultados/realtime/`.
- A tabela `resultados/tabelas/realtime_windows_input_only.csv` agora agrega tambem as duas medicoes curtas anteriores de 3 s.
- O metodo `wavelet_soft` emitiu `RuntimeWarning: invalid value encountered in divide` dentro de `pywt.threshold`; a checagem do CSV de blocos nao encontrou `NaN` nem infinito, e o pior caso ainda ficou abaixo do orcamento de 20 ms por bloco.
- A rodada comprova captura real input-only com folga computacional no notebook, mas ainda nao comprova reproducao/monitoramento duplex.
- O modo duplex deve continuar pendente ate haver confirmacao explicita de fone ou saida controlada para evitar realimentacao acustica.

## 2026-06-06 - Fase 2: teste duplex curto com fone Bluetooth

### Objetivo

- Testar o caminho captura-processa-reproduz da CLI no Windows.
- Manter uma duracao curta e sem salvar WAV para reduzir risco acustico e preservar privacidade.

### Condicao de seguranca

- O usuario confirmou uso de fone Bluetooth `HUAWEI FreeBuds SE 2`.
- O usuario informou que os alto-falantes do notebook estao quebrados e nao funcionam.
- O dispositivo de saida selecionado no Windows era `Fones de ouvido (HUAWEI FreeBuds SE 2)`.

### Dispositivos e comandos

- Dispositivos listados antes do teste:
  - entrada padrao: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida padrao: `Fones de ouvido (HUAWEI FreeBuds SE 2)`, indice 7, MME.
- Comandos executados:
  - `python -m realtime_audio.windows_realtime --duration 5 --method bypass --block-ms 20 --input-device 1 --output-device 7 --no-save`
  - `python -m realtime_audio.windows_realtime --duration 5 --method stft_subtraction --block-ms 20 --input-device 1 --output-device 7 --no-save`
- Consolidacao:
  - `python -m realtime_audio.summarize_realtime --pattern "windows_*_20260606_2221*_metrics.json" --output resultados/tabelas/realtime_windows_duplex.csv`

### Resultados tecnicos

- `bypass`:
  - 248 blocos;
  - tempo medio por bloco: 0,032 ms;
  - pior caso por bloco: 0,107 ms;
  - desvio padrao: 0,024 ms;
  - RTF medio por bloco: 0,00162;
  - RTF pior caso: 0,00536;
  - latencia de entrada reportada: 40 ms;
  - latencia de saida reportada: 200 ms;
  - latencia total estimada: 240 ms;
  - `status_counts`: vazio.
- `stft_subtraction`:
  - 248 blocos;
  - tempo medio por bloco: 0,472 ms;
  - pior caso por bloco: 1,463 ms;
  - desvio padrao: 0,209 ms;
  - RTF medio por bloco: 0,0236;
  - RTF pior caso: 0,0731;
  - latencia de entrada reportada: 40 ms;
  - latencia de saida reportada: 200 ms;
  - latencia algoritmica estimada: 32 ms;
  - latencia total estimada: 272 ms;
  - `status_counts`: vazio.

### Observacoes e limitacoes

- Os testes duplex curtos concluiram sem erro de driver reportado e sem eventos em `status_counts`.
- O fone Bluetooth reportou 200 ms de latencia de saida, valor alto, mas esperado para monitoramento via Bluetooth.
- Nenhum WAV foi salvo.
- Apos repetir a captura localmente, o usuario informou que a captura correu muito bem.
- Nao foram relatados eco, feedback, volume desconfortavel ou comportamento estranho no fone.
- A etapa valida tecnicamente e operacionalmente a CLI captura-processa-reproduz por duracao curta, com a ressalva de que a saida Bluetooth nao representa uma condicao de baixa latencia.

## 2026-06-06 - Atualizacao cautelosa do relatorio com resultados realtime

### Objetivo

- Atualizar `entrega3.tex` com as evidencias da Fase 2 Windows, sem transformar testes curtos em conclusoes fortes.
- Separar claramente benchmark offline com referencia limpa, estabilidade input-only de 30 s por metodo e duplex curto como demonstracao funcional limitada pela latencia Bluetooth.

### Alteracoes em `entrega3.tex`

- Incluida a CLI `realtime_audio/windows_realtime.py` como etapa complementar ao benchmark offline.
- Atualizada a secao de tempo real, memoria e latencia.
- Inserida tabela de medicoes input-only de 30 s com `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`.
- Inserida tabela de teste duplex curto com `bypass` e `stft_subtraction`.
- Registrada a limitacao do aviso numerico do PyWavelets em `wavelet_soft`.
- Registrada a validacao subjetiva positiva do duplex curto pelo usuario.
- Atualizados atividades realizadas, avaliacao do andamento, proximos passos, cronograma, riscos e consideracoes finais.

### Compilacao e verificacao

- A compilacao direta com `pdflatex -interaction=nonstopmode entrega3.tex` encontrou auxiliares antigos `entrega3.*` inconsistentes.
- Para verificar o fonte sem depender desses auxiliares, foi usada compilacao limpa com `pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex`, repetida ate estabilizar referencias.
- O PDF final gerado por `entrega3_build.pdf` foi copiado para `entrega3.pdf`.
- Resultado:
  - `entrega3.pdf` com 30 paginas;
  - sem referencias indefinidas no log final;
  - sem `Overfull`;
  - avisos remanescentes esperados de `microtype` e alguns `Underfull`.
- Verificacao visual:
  - renderizadas paginas da secao realtime com `pdftoppm`;
  - as tabelas input-only e duplex ficaram legiveis e sem sobreposicao.

## 2026-06-07 - Preparacao para ruidos ambientais reais

### Objetivo

- Abrir a proxima etapa experimental com ruidos ambientais reais sem baixar bases grandes por padrao.
- Registrar origem, licenca, tamanho e integridade dos arquivos DEMAND antes de misturar esses ruidos com fala.
- Manter a rodada demonstrativa sintetica intacta para comparacao e reproducibilidade.

### Codigo criado ou alterado

- Criado `benchmark_audio/prepare_environmental_noise.py` com:
  - manifesto local dos arquivos DEMAND 16 kHz disponiveis no Zenodo;
  - selecao de subconjunto padrao: `DKITCHEN`, `OOFFICE`, `PCAFETER` e `STRAFFIC`;
  - download opcional e explicito para `dados/external/demand/`;
  - verificacao de MD5 dos ZIPs oficiais;
  - extracao de um canal por ambiente e preparacao de snippets WAV em `dados/demo/noise_demand/`;
  - geracao de `resultados/tabelas/demand_archives_manifest.csv` e `resultados/tabelas/demand_noise_prepared.csv`.
- Atualizado `benchmark_audio/run_benchmark.py` com `--noise-dir` e `--max-noises`, permitindo substituir os ruidos sinteticos por WAVs locais mantendo o mesmo pareamento fala/ruido/SNR/metodo.
- Criado `tests/test_environmental_noise.py` para validar selecao de canal, preparo local sem download e smoke test do benchmark com uma pasta temporaria de ruidos reais.
- Atualizados `README_benchmark.md` e `dados/README.md` com o novo fluxo.

### Fonte e licenca registradas

- Base escolhida para a proxima etapa: DEMAND, depositada no Zenodo em `https://zenodo.org/records/1227121`, DOI `10.5281/zenodo.1227121`.
- O texto descritivo do registro informa licenca `CC BY-SA 3.0` para obra, audio e documento.
- Observacao de cautela: o metadado atual de direitos no Zenodo tambem deve ser conferido antes de redistribuir derivados, pois pode aparecer diferente do texto descritivo.

### Comandos executados

- `python -m benchmark_audio.prepare_environmental_noise --manifest-only`
- `python -m benchmark_audio.prepare_environmental_noise`
- `python -m compileall benchmark_audio realtime_audio`
- `python -m unittest discover -s tests`

### Resultado

- O manifesto DEMAND foi gerado com metadados leves e URLs dos arquivos 16 kHz.
- A preparacao sem `--download` terminou sem erro e registrou quatro arquivos ausentes em `demand_noise_prepared.csv`, como esperado.
- Nao foi feito download dos ZIPs grandes nesta etapa.
- Nao houve nova rodada oficial de benchmark com ruidos reais; o trabalho atual e infraestrutura de preparo.

### Proximos passos

- Baixar um subconjunto pequeno do DEMAND quando houver decisao explicita de tempo/espaco em disco.
- Preparar snippets e rodar uma primeira matriz curta com `--noise-dir dados/demo/noise_demand --max-noises`.
- Comparar os resultados com a rodada sintetica sem afirmar conclusoes finais antes de ampliar ambientes e separar validacao de teste final.

## 2026-06-07 - Primeira rodada ambiental DEMAND

### Dados preparados

- Foram baixados e verificados por MD5 quatro arquivos DEMAND 16 kHz:
  - `DKITCHEN_16k.zip`: cozinha;
  - `OOFFICE_16k.zip`: escritorio;
  - `PCAFETER_16k.zip`: cafeteria;
  - `STRAFFIC_16k.zip`: trafego.
- Tamanho total aproximado dos ZIPs: 406 MB.
- Foram extraidos tres segmentos nao sobrepostos de 3 s do primeiro canal de cada ambiente.
- Total preparado: 12 WAVs mono a 16 kHz, aproximadamente 1,1 MB.
- A tabela `resultados/tabelas/demand_noise_prepared.csv` terminou com 12 linhas `prepared` e nenhuma ausencia.

### Isolamento de resultados

- Adicionado `--results-dir` ao benchmark.
- A rodada ambiental foi gravada em `resultados/demand/`, preservando os resultados sinteticos em `resultados/`.
- O teste automatizado passou a verificar que uma saida isolada nao altera um arquivo sentinela do diretorio padrao.

### Comando executado

- `python -m benchmark_audio.run_benchmark --noise-dir dados/demo/noise_demand --results-dir resultados/demand`

### Matriz experimental

- 5 trechos de fala FSDD;
- 12 segmentos DEMAND;
- SNRs de -5, 0, 5 e 10 dB;
- metodos `noisy`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`;
- total: 960 linhas de metricas.

### Resultados medios por SNR alvo

- `stft_subtraction`: melhoria de 7,69 dB em -5 dB, 7,31 dB em 0 dB, 6,82 dB em 5 dB e 6,21 dB em 10 dB.
- `stft_wiener`: melhoria de 4,62 dB, 4,50 dB, 4,33 dB e 4,07 dB, respectivamente.
- `wavelet_soft`: 0,28 dB, 0,14 dB, -0,05 dB e -0,38 dB, respectivamente.
- Nenhum `NaN` ou infinito foi encontrado nos CSVs.

### Variacao entre ambientes

- Melhoria media da subtracao espectral, agregada sobre SNRs:
  - cozinha: 10,00 dB;
  - escritorio: 8,45 dB;
  - cafeteria: 4,11 dB;
  - trafego: 5,47 dB.
- A diferenca confirma que o tipo de ruido altera substancialmente a magnitude do ganho.
- A Wavelet soft ficou proxima de zero no agregado, com pequenas perdas em cozinha/escritorio e pequenos ganhos em cafeteria/trafego.

### Limitacoes

- Os tres segmentos de cada ambiente sao contiguos e pertencem ao mesmo canal, portanto nao devem ser tratados como doze ambientes independentes.
- A fala FSDD ainda contem silencio inicial de 0,30 s, condicao favoravel a estimativa inicial de ruido dos metodos STFT.
- Nao houve separacao formal entre conjunto de validacao e teste final.
- O Matplotlib repetiu o aviso conhecido de `log10` em pontos de potencia zero durante a figura diagnostica; os CSVs permaneceram finitos.

### Atualizacao do relatorio

- `entrega3.tex` passou a separar benchmark sintetico, rodada ambiental DEMAND e validacao realtime.
- Foi adicionada uma tabela compacta com melhoria media de SNR da rodada DEMAND.
- Compilacao limpa executada tres vezes com:
  - `pdflatex -interaction=nonstopmode -jobname=entrega3_demand_build entrega3.tex`
- Resultado:
  - 31 paginas;
  - sem `Overfull`;
  - sem referencias indefinidas;
  - apenas avisos anteriores de `Underfull` e `microtype`.
- As paginas 8 a 13 foram renderizadas e verificadas visualmente.
- O PDF validado foi copiado para `entrega3.pdf`.

## 2026-06-07 - Refinamento separado e teste sem silencio inicial

### Objetivo de encerramento da fase

- Completar a fase algorítmica em PC com:
  - mais um falante FSDD;
  - separacao reproduzivel entre validacao e conjunto final operacional;
  - refinamento STFT e Wavelet;
  - teste sem silencio inicial garantido;
  - comparacao de qualidade e custo;
  - relatorio atualizado.

### Preservacao do benchmark historico

- O benchmark historico permanece com cinco falantes em `dados/demo/clean/`.
- O refinamento usa seis falantes em `dados/demo/clean_refinement/`.
- O sexto falante e `lucas`, tambem do FSDD.
- Uma primeira tentativa colocou `speech_lucas.wav` no diretorio historico; o arquivo derivado foi removido e a preparacao foi isolada para evitar mudar retrospectivamente a matriz antiga.

### Falha e recuperacao de download

- `urllib` sofreu `WinError 10054` ao baixar `1_lucas_0.wav`, mesmo apos retentativas.
- Os nove arquivos restantes foram baixados da mesma URL oficial por `fetch` no ambiente Node.
- O executor foi retomado sem perda dos arquivos ja concluidos.

### Divisao do protocolo

- Validacao:
  - falantes: `jackson`, `nicolas`, `theo`;
  - ambientes: `DKITCHEN`, `OOFFICE`;
  - 72 condicoes.
- Conjunto final operacional:
  - falantes: `george`, `lucas`, `yweweler`;
  - ambientes: `PCAFETER`, `STRAFFIC`;
  - 72 condicoes.
- O prefixo fixo de 0,30 s foi removido antes das misturas.
- O conjunto final nao foi usado pelo script para selecao, mas nao e historicamente cego porque os ambientes ja tinham sido vistos na rodada exploratoria.

### Busca de parametros

- Script: `benchmark_audio/run_refinement.py`.
- Comando:
  - `python -m benchmark_audio.run_refinement --prepare-speech --results-dir resultados/demand_refinement`
- Foram avaliadas 144 configuracoes apenas na validacao:
  - 48 de subtracao espectral;
  - 24 Wiener;
  - 72 Wavelet.
- STFT:
  - `n_fft` 256/512;
  - saltos 80/160;
  - estimativa inicial ou quadros de menor energia;
  - quantis 0,10/0,20/0,35;
  - variacoes de agressividade e piso.
- Wavelet:
  - `db4`, `sym4`, `coif1`;
  - niveis 3/5;
  - soft/hard;
  - limiar global/por escala;
  - fatores 0,50/0,75/1,00.

### Configuracoes escolhidas na validacao

- Subtracao espectral:
  - `n_fft=512`, `hop=160`;
  - estimador `low_energy`, quantil 0,35;
  - `alpha=1,5`, piso 0,02;
  - melhoria media de validacao: 4,75 dB;
  - melhoria media de SI-SDR: 3,96 dB;
  - nenhuma degradacao de SNR.
- Wiener:
  - `n_fft=512`, `hop=160`;
  - estimador `low_energy`, quantil 0,35;
  - piso 0,05;
  - melhoria media de validacao: 2,23 dB;
  - melhoria media de SI-SDR: 1,62 dB;
  - nenhuma degradacao de SNR.
- Wavelet:
  - `sym4`, nivel 3, hard, limiar global, fator 0,50;
  - melhoria media de validacao: 0,14 dB;
  - melhoria media de SI-SDR: 0,05 dB;
  - degradacao de SNR em 45,8% das condicoes.

### Resultado no conjunto final operacional

- Subtracao padrao com estimativa inicial:
  - melhoria de SNR: 1,82 dB;
  - melhoria de SI-SDR: -0,16 dB;
  - degradacao de SNR em 33,3% das condicoes.
- Subtracao refinada:
  - melhoria de SNR: 4,85 dB;
  - melhoria de SI-SDR: 3,72 dB;
  - nenhuma degradacao de SNR;
  - RTF medio de arquivo: aproximadamente 0,004.
- Wiener padrao:
  - melhoria de SNR: 1,30 dB;
  - melhoria de SI-SDR: -0,40 dB;
  - degradacao em 27,8%.
- Wiener refinado:
  - melhoria de SNR: 2,92 dB;
  - melhoria de SI-SDR: 2,25 dB;
  - nenhuma degradacao;
  - RTF medio de arquivo: aproximadamente 0,002.
- Wavelet padrao:
  - melhoria de SNR: 0,32 dB;
  - melhoria de SI-SDR: -0,46 dB;
  - degradacao em 19,4%.
- Wavelet refinada:
  - melhoria de SNR: 0,03 dB;
  - melhoria de SI-SDR: 0,01 dB;
  - degradacao em 11,1%;
  - RTF medio de arquivo: aproximadamente 0,0006.

### Interpretacao

- O silencio inicial favorecia fortemente a estimativa STFT antiga.
- Sem esse silencio, a estimativa inicial pode degradar fala, especialmente nas condicoes de 10 dB.
- A selecao offline de quadros de baixa energia recupera qualidade, mas ainda nao e causal.
- O refinamento Wavelet reduz dano e custo, mas nao produz supressao relevante com as familias e limiares testados.
- Candidata principal para continuidade: subtracao espectral com estimativa adaptada.
- Alternativa: Wiener, com menor melhoria e menor agressividade.
- Wavelet permanece como baseline leve, nao como candidata principal atual.

### Arquivos gerados

- `resultados/demand_refinement/tabelas/split_manifest.csv`
- `validation_candidates.csv`
- `selected_configs.csv` e `.json`
- `comparison_metrics.csv`
- `comparison_summary.csv`
- `comparison_by_noise.csv`
- `comparison_overall.csv`
- `metadata_refinement.json`
- exemplos WAV curtos em `resultados/demand_refinement/audio/`.

### Fechamento do checkpoint

- A suite terminou com 12 testes e 4 subtestes aprovados.
- A auditoria final confirmou:
  - 144 configuracoes na busca de validacao;
  - 1008 linhas na comparacao padrao/refinada;
  - ausencia de `NaN` e infinito nas colunas numericas.
- `entrega3.tex` foi recompilado em tres passagens.
- `entrega3.pdf` ficou com 32 paginas.
- O log final nao apresentou `Overfull`, referencias indefinidas ou citacoes indefinidas.
- Foram inspecionadas visualmente as paginas de metodologia, resultados DEMAND/refinamento, cronograma, riscos, conclusao e referencias.
- A tabela de riscos foi compactada para evitar titulo isolado, e a legenda do refinamento foi abreviada para melhorar a composicao tipografica.
- O codigo, os resultados e o relatorio foram registrados no commit `13d98c1`.

## 2026-06-07 - PC-1: estimador causal de ruido

### Auditoria de partida

- `main` estava 15 commits a frente de `origin/main`.
- Nao havia alteracao rastreada pendente.
- Havia artefatos antigos nao rastreados; nenhum foi removido ou incluido.
- A linha de base passou com 12 testes e 4 subtestes.
- O modo `rolling` da CLI nao mantinha estimador causal real: ele recaia no
  estimador offline aplicado a uma janela movel.

### Implementacao

- Criado `CausalNoiseEstimator` com:
  - estado explicito e `reset()`;
  - calibracao curta congelada;
  - historico causal de potencia espectral;
  - quantil rolante por bin;
  - piso de energia causal;
  - EMA rapida em baixa energia;
  - EMA lenta durante fala provavel;
  - protecao contra zero, `NaN` e infinito.
- Criado `CausalSTFTProcessor` com API `process_block()` independente de
  dispositivo.
- O bloco atual e processado com a estimativa existente; seus espectros
  atualizam apenas blocos seguintes.
- A captura Windows passou a delegar subtracao, Wiener e bypass ao novo nucleo.
- O alias `rolling` foi mantido e mapeia para `adaptive`.
- Logs passaram a incluir p95, p99, blocos acima do orcamento, memoria de
  estado, aquecimento e decisao de fala.

### Busca no conjunto de desenvolvimento

- Executor: `python -m benchmark_audio.run_causal_estimator`.
- Foram avaliadas 20 variantes adaptativas e uma calibracao de 250 ms.
- Grade:
  - historico 500/1000 ms;
  - quantil 0,10/0,20/0,22/0,25/0,35;
  - EMA de baixa energia 0,20/0,30;
  - limiar de fala fixo em 6 dB;
  - EMA durante fala em 0,005.
- Regra: minimizar degradacao de SNR, maximizar SNR, maximizar SI-SDR e
  minimizar RTF.
- Escolha:
  - historico 500 ms;
  - quantil 0,22;
  - EMA baixa energia 0,30;
  - aquecimento 250 ms;
  - demais parametros documentados em `docs/estimador_causal.md`.

### Resultados

- Validacao:
  - subtracao causal: +3,74 dB SNR, +3,15 dB SI-SDR, 0% degradacao;
  - pior melhoria individual: +0,05 dB.
- Conjunto final operacional:
  - subtracao causal: +3,76 dB SNR, +2,65 dB SI-SDR, 0% degradacao;
  - Wiener causal: +1,68 dB SNR, +1,35 dB SI-SDR, 0% degradacao;
  - calibracao causal: +0,96 dB SNR, -2,38 dB SI-SDR, 33,3% degradacao;
  - offline de baixa energia: +4,85 dB SNR e +3,72 dB SI-SDR.
- Estado maximo: 60.900 bytes.
- Subtracao causal final:
  - RTF medio 0,068;
  - p99 medio 3,08 ms;
  - pior bloco 13,31 ms.
- A rodada de validacao em lote teve um pico isolado de 104,12 ms; o fato foi
  preservado como limitacao de jitter.

### Correcao durante a auditoria

- A primeira rodada mostrou bypass diferente de zero porque o nucleo limitava
  amplitude em `[-1, 1]`.
- O clipping foi removido do nucleo de pesquisa e mantido apenas na borda da
  captura Windows.
- A selecao completa foi repetida.
- O bypass final ficou exatamente em 0,00 dB de melhoria, como controle.

### Verificacao e relatorio

- `python -m compileall benchmark_audio realtime_audio`.
- `python -m pytest -q`: 21 testes e 4 subtestes aprovados.
- CSVs: 21 candidatos, 1152 linhas de comparacao, sem `NaN` ou infinito.
- Autoteste causal de 1 s:
  - media 1,58 ms;
  - p99 4,01 ms;
  - pior bloco 4,62 ms;
  - zero blocos acima de 20 ms.
- `entrega3.tex` compilado tres vezes com `jobname=entrega3_causal_build`.
- PDF final: 33 paginas, sem `Overfull` e sem referencias/citacoes
  indefinidas.
- Paginas alteradas renderizadas e inspecionadas visualmente.
- Commit tecnico: `a03f05a`.

### Privacidade e intervencao

- Nenhuma gravacao autoral foi solicitada ou iniciada.
- Nenhum microfone, fone, playback ou escuta foi usado.
- Nenhum audio privado foi criado ou versionado.
- A etapa seguinte pode ser PC-2 sem intervencao humana.

## 2026-06-07 - Etapa PC-2: WAV reproduzivel em blocos

### Auditoria de partida

- Lidos os prompts de fechamento da plataforma, incorporacao autoral e
  continuidade apos o Checkpoint 20.
- Lidos nucleo causal, denoise, executor causal, captura Windows, agregador,
  READMEs, documentos de estimador, checkpoints, diario, auditoria e secoes
  relevantes de `entrega3.tex`.
- Estado inicial:
  - `main` 18 commits a frente de `origin/main`;
  - arquivos antigos nao rastreados mantidos intocados;
  - 21 testes e 4 subtestes aprovados;
  - `compileall` sem erro.

### Implementacao

- Criado `realtime_audio/process_wav_blocks.py`.
- A CLI usa diretamente `CausalProcessorConfig` e `CausalSTFTProcessor`.
- Extraido `realtime_audio/block_metrics.py` para compartilhar percentis e
  contagens com a captura Windows.
- Separadas conversao PCM/mono e reamostragem da normalizacao historica em
  `benchmark_audio/denoise.py`; chamadas antigas continuam normalizando por
  padrao, enquanto a CLI usa conversao sem normalizacao.
- Entrada:
  - WAV mono ou estereo;
  - taxa original arbitraria valida;
  - conversao para float32 mono a 16 kHz;
  - rejeicao de vazio, truncado, ausente e nao finito.
- Saida:
  - WAV PCM16;
  - CSV por bloco;
  - JSON por execucao;
  - hashes SHA-256;
  - recusa de sobrescrita sem flag explicita.
- O ultimo bloco curto e processado pelo tamanho real.
- O processador e criado novamente por arquivo, garantindo reset.
- Nao ha normalizacao automatica nem clipping dentro do processamento; a
  limitacao ocorre somente na escrita PCM e e registrada.

### Testes

- Criado `tests/test_process_wav_blocks.py`.
- Cobertura:
  - bypass exato antes da escrita;
  - comprimento multiplo e nao multiplo;
  - ultimo bloco curto;
  - determinismo;
  - igualdade com chamada direta;
  - blocos 10/20/32 ms;
  - estereo 8 kHz para mono 16 kHz;
  - ausente, vazio e truncado;
  - sobrescrita;
  - CSV/JSON completos e finitos;
  - reset entre arquivos;
  - hashes e configuracao estaveis;
  - retorno nao zero da CLI.
- Resultado final: 30 testes e 9 subtestes aprovados.

### Matriz PC-2

- Criado `benchmark_audio/run_file_blocks_experiment.py`.
- Dados:
  - `speech_george.wav`, fala publica FSDD preparada;
  - `pcafeter_ch01_seg01.wav`, DEMAND;
  - SNRs -5 e 5 dB.
- Metodos:
  - bypass;
  - subtracao causal adaptativa;
  - Wiener causal adaptativo;
  - subtracao e Wiener offline de baixa energia como referencias.
- Blocos: 10, 20 e 32 ms, sem alterar parametros internos.
- Resultados da subtracao causal:
  - 10 ms: +3,36 dB SNR, +1,22 dB SI-SDR, RTF 0,111;
  - 20 ms: +3,27 dB SNR, +1,27 dB SI-SDR, RTF 0,081;
  - 32 ms: +3,25 dB SNR, +1,35 dB SI-SDR, RTF 0,068.
- Resultados do Wiener causal:
  - 10 ms: +1,54 dB SNR, +0,74 dB SI-SDR;
  - 20 ms: +1,33 dB SNR, +0,67 dB SI-SDR;
  - 32 ms: +1,27 dB SNR, +0,68 dB SI-SDR.
- Referencias offline:
  - subtracao: +4,31 dB SNR e +2,14 dB SI-SDR;
  - Wiener: +2,85 dB SNR e +1,68 dB SI-SDR.
- Nenhum bloco acima do orcamento.
- Estado maximo: 60.900 bytes.
- Comprimento preservado e deslocamento de indice zero em todas as linhas.

### Vetores e execucao representativa

- Criado `realtime_audio/generate_test_vectors.py`.
- Vetores sinteticos de 0,75 s com semente 3527:
  - entrada ruidosa;
  - bypass esperado;
  - subtracao causal esperada;
  - configuracao;
  - manifesto e tolerancias.
- A execucao CLI representativa processou 12.000 amostras em 38 blocos,
  incluindo ultimo bloco de 160 amostras.
- Hash esperado e obtido:
  - `47f70c20306c7a602d2b1bb6a320ca6451f8c4f4229e8992ca8a856fb476a3ed`.
- Nenhuma amostra fora da faixa, nenhum nao finito e nenhum bloco acima do
  orcamento.

### Documentacao e relatorio

- Criado `docs/processamento_wav_blocos.md`.
- Atualizados `README_benchmark.md`, `realtime_audio/README.md` e
  `docs/estimador_causal.md`.
- `entrega3.tex` passou a distinguir:
  - arquivo em blocos;
  - referencia offline de arquivo completo;
  - captura Windows;
  - latencia algoritmica versus latencia fisica.
- O PDF foi compilado em tres passagens, ficou com 35 paginas e foi
  inspecionado nas paginas alteradas.
- Sem `Overfull`, referencias ou citacoes indefinidas.

### Commits

- `f781eeb` - `code: adicionar processamento wav em blocos`;
- `b526eb8` - `results: validar processamento wav por blocos`;
- `fc42d3f` - `docs: documentar processamento wav em blocos`.

### Limites e privacidade

- A matriz nao reotimiza parametros.
- Um unico falante, um unico ruido e duas SNRs limitam a generalizacao.
- Tempo de arquivo nao comprova latencia ou estabilidade de dispositivo.
- Nao houve gravacao, escuta, microfone, playback ou voz autoral.
- Nenhum dado privado entrou no Git.

## 2026-06-07 - Checkpoint 19 adiado: protocolo de voz autoral

### Decisao de sequenciamento

- O roteiro original previa o Checkpoint 19 antes do estimador causal.
- A equipe decidiu congelar primeiro PC-1 e PC-2.
- Depois do Checkpoint 21, o protocolo autoral foi retomado sem reabrir
  parametros.
- O objetivo desta rodada foi preparar tudo que pode ser automatizado antes de
  solicitar gravacoes.

### Protocolo e privacidade

- Criados:
  - guia de gravacao;
  - modelo de autorizacao;
  - roteiro para Sessoes A e B;
  - manifesto bruto;
  - folha de sessao;
  - registro codificado de autorizacao.
- Definidos codigos `spk01`, `spk02` e `spk03`.
- Definidos niveis:
  - `local_only`;
  - `advisor_board`;
  - `public_excerpt`.
- Termos assinados ficam em `dados/private/authored_voice/consent/`.
- Nomes, assinaturas, WAVs brutos e derivados ficam fora do Git.
- A publicacao de trecho exige autorizacao ampla e aprovacao explicita do
  arquivo.

### Estrutura local

- Criadas 21 pastas locais para:
  - tres falantes;
  - duas sessoes;
  - `quiet`, `noise` e `live_noisy`;
  - consentimentos, manifestos e derivados.
- Modelos foram copiados para a area privada como arquivos de trabalho.
- `git check-ignore` confirmou as regras de exclusao.

### CLI de ingestao

- Criado `benchmark_audio/prepare_authored_voice.py`.
- Manifesto exige:
  - codigo do falante;
  - sessao;
  - tipo de gravacao;
  - identificador do enunciado;
  - caminho bruto;
  - nivel de autorizacao;
  - identificador do consentimento;
  - metadados de captura.
- A CLI aceita somente WAV PCM inteiro.
- Profundidades aceitas: 8, 16, 24 e 32 bits.
- O bruto e lido, nunca alterado.
- Derivado:
  - media de canais;
  - remocao de DC;
  - reamostragem polifasica para 16 kHz;
  - mono PCM16;
  - sem normalizacao ou DSP de reducao de ruido.
- Relatorios:
  - manifesto preparado CSV;
  - qualidade JSON;
  - SHA-256 bruto e preparado;
  - pico, RMS, DC, clipping, silencio, duracao e divergencias.

### Testes e smoke test

- Nove testes novos cobrem:
  - estereo 48 kHz;
  - PCM24;
  - amplitude preservada;
  - remocao de DC;
  - clipping e silencio;
  - duracao fora do protocolo;
  - metadados divergentes;
  - consentimento ausente;
  - duplicidade;
  - arquivos invalidos e caminho externo;
  - sobrescrita;
  - determinismo;
  - esquema e retorno de erro.
- Suite completa: 39 testes e 9 subtestes aprovados.
- Smoke test:
  - WAV sintetico estereo 48 kHz;
  - preparado em mono 16 kHz;
  - zero erros e zero avisos.

### Commits

- `d13500b` - `docs: adicionar protocolo de voz autoral`;
- `61a067f` - `code: preparar ingestao de voz autoral`.

### Ponto de intervencao humana

- Nenhum consentimento foi inventado.
- Nenhum equipamento foi presumido.
- Nenhuma gravacao foi solicitada antes de scripts e modelos estarem prontos.
- Para iniciar a coleta, os tres participantes precisam:
  - escolher o nivel de autorizacao;
  - informar o equipamento;
  - gravar conforme o guia;
  - preencher manifestos sem nomes reais.
- O Checkpoint 22 so pode produzir resultados depois dessa etapa.

## 2026-06-07 - Preparacao da avaliacao autoral e escuta critica

### Auditoria de partida

- Lido o prompt de fechamento da plataforma PC e os documentos obrigatorios da
  retomada.
- `git status --short` mostrou muitos arquivos antigos nao rastreados,
  incluindo `revisao_wavelets_gabriel/`; eles foram mantidos intocados.
- `python -m compileall benchmark_audio realtime_audio` passou.
- `python -m pytest -q` falhou inicialmente na coleta, porque a copia nao
  rastreada `revisao_wavelets_gabriel/tests/` continha modulos com os mesmos
  nomes da suite oficial.
- `python -m pytest -q tests` confirmou que a suite oficial passava antes das
  novas alteracoes: 39 testes e 9 subtestes.

### Implementacao

- Adicionado `pytest.ini` com `testpaths = tests`, para que o comando canonico
  do roteiro ignore copias locais nao rastreadas e colete somente a suite do
  projeto.
- Criado `benchmark_audio/run_authored_evaluation.py`.
- A nova CLI consome o manifesto preparado por
  `benchmark_audio.prepare_authored_voice`.
- Para `raw_quiet + raw_noise`, monta misturas controladas em SNRs
  configuraveis e calcula SNR, melhoria de SNR, SI-SDR, MSE, RTF, percentis,
  blocos acima do orcamento e memoria.
- Para `raw_live_noisy`, registra apenas estatisticas operacionais, sem SNR ou
  SI-SDR pareadas.
- Os metodos incluidos sao:
  - bypass;
  - subtracao causal adaptativa;
  - Wiener causal adaptativo;
  - subtracao offline de baixa energia;
  - Wiener offline de baixa energia;
  - Wavelet refinada como baseline leve.
- A CLI nao salva audio por padrao; grava CSV/JSON com identificadores
  codificados.
- Por padrao, arquivos `prepared_with_warnings` sao recusados, exigindo revisao
  ou `--allow-warnings`.

### Documentacao

- Criado `docs/avaliacao_autoral.md` com:
  - comando de avaliacao para Sessao A e Sessao B;
  - politica de metricas pareadas;
  - matriz pequena recomendada;
  - protocolo de escuta critica;
  - checklist antes de atualizar `entrega3.tex`.
- Criado `dados/templates/authored_voice/perceptual_rating_template.csv`.
- Atualizados:
  - `README_benchmark.md`;
  - `dados/README.md`;
  - `dados/templates/authored_voice/README.md`;
  - `docs/protocolo_voz_autoral.md`.

### Verificacao

- `python -m compileall benchmark_audio realtime_audio`.
- `python -m pytest -q`: 41 testes e 9 subtestes aprovados.

### Limitacoes

- Nenhum WAV autoral real foi criado, ingerido ou avaliado.
- Nenhuma autorizacao real foi presumida.
- O Checkpoint 22 continua dependente de coleta humana, revisao de metadados e
  execucao da Sessao B com parametros congelados.
- `entrega3.tex` nao foi alterado porque ainda nao ha resultados auditados de
  voz autoral nem escuta critica.

## 2026-06-07 - Reabertura da trilha Wavelet adaptativa

### Discussao tecnica

- Gabriel questionou a interpretacao de que os resultados quase nulos
  encerrariam a linha Wavelet.
- A revisao separou duas afirmacoes:
  - os resultados existentes sao validos para DWT com MAD e limiarizacao
    hard/soft;
  - eles nao descartam formulacoes Wavelet com subbandas uniformes, rastreamento
    temporal de ruido e ganho suave.
- A sugestao aceita para continuidade foi WPT + rastreamento de ruido por
  subbanda, inspirado em MCRA/IMCRA, + ganho Wiener.

### Decisao

- `wavelet_soft` permanece como baseline historico leve.
- A proxima candidata Wavelet deve ser metodo novo, por exemplo
  `wavelet_packet_wiener`.
- A comparacao minima deve incluir:
  - DWT limiarizada antiga;
  - WPT + Wiener offline;
  - WPT + Wiener causal;
  - subtracao STFT causal;
  - limite offline de baixa energia.
- Criado `docs/plano_wavelet_packet_wiener.md`.
- Atualizados `README_benchmark.md`, `docs/auditoria_resultados.md`,
  `docs/checkpoints.md`, `docs/revisao_wavelets_gabriel.md` e
  `docs/onboarding_equipe.md`.

### Limitacao

- Nenhum resultado numerico novo foi produzido nesta decisao.
- A mudanca e de interpretacao e planejamento: os CSVs e checkpoints anteriores
  continuam representando corretamente a DWT com limiarizacao testada.

## 2026-06-07 - Implementacao inicial WPT + Wiener

### Objetivo

- Dar continuidade ao plano `docs/plano_wavelet_packet_wiener.md`.
- Criar um metodo novo para Wavelet Packet Transform com tracking temporal de
  ruido e ganho Wiener, sem substituir `wavelet_soft`.
- Produzir uma primeira rodada em pasta propria para auditoria.

### Implementacao

- Em `benchmark_audio/denoise.py`:
  - adicionado `wavelet_packet_wiener` em `DENOISE_METHODS`;
  - adicionados parametros `wpt_*` em `DenoiseConfig`;
  - criada `wavelet_packet_wiener_denoise`;
  - usado `pywt.WaveletPacket` no nivel configurado;
  - cada subbanda estima potencia de ruido por quantil rolante;
  - o ganho e `speech_power / (speech_power + noise_power + eps)`, com piso;
  - a saida preserva comprimento, `float32` e finitude numerica.
- Em `benchmark_audio/run_refinement.py`:
  - criada familia separada `wavelet_packet`;
  - candidatos WPT ficam atras de `--include-wpt`;
  - o refinamento historico continua sem WPT por padrao.
- Em testes:
  - bypass `noisy` permanece copia exata;
  - todos os metodos, incluindo WPT, retornam mesmo comprimento e valores
    finitos;
  - candidatos WPT usam familia e metodo proprios.

### Comandos executados

```powershell
python -m pytest -q tests\test_denoise.py tests\test_refinement.py
python -m compileall benchmark_audio realtime_audio
python -m benchmark_audio.run_refinement --include-wpt --results-dir resultados/wpt_refinement
python -m pytest -q
```

- Verificacao final completa: 44 testes e 10 subtestes aprovados.

### Resultado numerico inicial

- Rodada: 180 candidatos, 72 condicoes de validacao e 72 finais.
- Melhor WPT escolhido na validacao:
  `wpt_wiener_sym4_l3_rolling_q0.2_w31_f0.1`.
- Validacao:
  - +0,878 dB de SNR medio;
  - +0,200 dB de SI-SDR medio;
  - 25,0% de degradacoes de SNR.
- Final operacional:
  - +0,366 dB de SNR medio;
  - -0,248 dB de SI-SDR medio;
  - 25,0% de degradacoes de SNR.

### Interpretacao

- A primeira WPT + Wiener supera a DWT limiarizada em SNR medio, portanto a
  reabertura da trilha Wavelet faz sentido como investigacao.
- Ainda nao ha evidencia para promove-la a candidata principal:
  - a STFT de baixa energia offline continua muito superior;
  - a STFT causal adaptativa continua sendo a referencia realtime mais madura;
  - a queda de SI-SDR no final sugere distorcao ou perda estrutural de fala;
  - a selecao por SNR pode favorecer configuracoes agressivas demais.
- `entrega3.tex` nao foi alterado.

### Proximos experimentos sugeridos

- Testar WPT em blocos com overlap e janela para reduzir artefatos de fronteira.
- Adicionar suavizacao explicita do ganho e/ou decisao de fala por subbanda.
- Ajustar regra de selecao para penalizar SI-SDR negativo e degradacao.
- Comparar audivelmente os WAVs salvos em `resultados/wpt_refinement/audio/`.
- So depois desenhar uma versao causal com estado explicito.

## 2026-06-07 - Benchmark Wavelet pesado apos provocacao do Gabriel

### Motivacao

- Gabriel observou que a performance Wavelet parecia estranha e sugeriu
  benchmarkar mais pesado as ondaletas.
- A hipotese revisada foi que a WPT inicial por arquivo ainda nao representava
  uma formulacao suficientemente justa: ela rastreava ruido nos coeficientes,
  mas nao fazia uma analise por quadros com energia temporal explicita por
  subbanda.

### Implementacao

- Adicionado `wavelet_packet_wiener_frames` em `benchmark_audio/denoise.py`.
- O novo metodo:
  - segmenta o audio em quadros sobrepostos;
  - aplica WPT em cada quadro;
  - calcula potencia por subbanda/quadro;
  - estima ruido por quantil global ou rolante ao longo dos quadros;
  - aplica ganho Wiener por subbanda/quadro;
  - reconstrui por overlap-add.
- Criado `benchmark_audio/run_wavelet_heavy_refinement.py`.
- A busca pesada:
  - usa apenas subconjunto de validacao na triagem ampla;
  - reavalia os melhores na validacao completa;
  - so depois mede o final operacional;
  - usa escore robusto que penaliza SI-SDR ruim, pior caso negativo e fracao
    de degradacao.

### Rodadas

```powershell
python -m benchmark_audio.run_wavelet_heavy_refinement `
  --profile quick `
  --results-dir resultados/wavelet_heavy_smoke `
  --screening-speakers 1 `
  --screening-noises-per-group 1 `
  --full-per-family 2

python -m benchmark_audio.run_wavelet_heavy_refinement `
  --profile focused `
  --results-dir resultados/wavelet_heavy_refinement `
  --screening-speakers 1 `
  --screening-noises-per-group 1 `
  --full-per-family 16
```

- Smoke `quick`: concluiu em 34 s.
- Rodada `focused`:
  - 2556 candidatos na triagem;
  - 86 candidatos na validacao completa;
  - 11 candidatos na comparacao final;
  - elapsed registrado: 525,95 s.
- O perfil `max` tambem foi iniciado em `resultados/wavelet_heavy_max_refinement`,
  mas foi interrompido ainda na triagem inicial por custo excessivo antes de
  gerar CSVs. A pasta foi marcada com `RUN_INCOMPLETE.txt`.

### Resultados

- DWT pesada:
  - melhor final: +0,055 dB SNR e +0,008 dB SI-SDR;
  - confirma que DWT limiarizada continua fraca.
- WPT por coeficiente:
  - melhor robusta: +0,393 dB SNR, +0,132 dB SI-SDR, 9,7% degradacoes;
  - melhor por SNR teve SI-SDR negativo e 25,0% degradacoes;
  - continua insuficiente.
- WPT em quadros:
  - robusta: `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
    final +3,210 dB SNR, +1,753 dB SI-SDR, 0,0% degradacoes;
  - maior SNR: `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
    final +3,524 dB SNR, +1,785 dB SI-SDR, 4,2% degradacoes.
- Comparacao:
  - STFT subtracao baixa energia offline: +4,848 dB SNR, +3,716 dB SI-SDR;
  - STFT subtracao causal adaptativa: +3,763 dB SNR, +2,648 dB SI-SDR;
  - STFT Wiener offline: +2,920 dB SNR, +2,253 dB SI-SDR.

### Verificacao

- `python -m compileall benchmark_audio realtime_audio`.
- `python -m pytest -q`: 48 testes e 11 subtestes aprovados.

### Interpretacao

- A provocacao do Gabriel foi pertinente: a primeira WPT era subexplorada.
- A trilha Wavelet nao deve ser encerrada com base na DWT ou na WPT por
  coeficientes.
- A WPT em quadros tem desempenho objetivo decente e pode ser descrita como
  candidata exploratoria forte.
- Ainda nao ha motivo para trocar a candidata PC principal:
  - a melhor STFT offline continua superior;
  - a STFT causal adaptativa ainda tem SI-SDR maior e ja tem estado causal;
  - a WPT em quadros usa quantil global na melhor configuracao e portanto nao e
    causal.
- Proximo passo cientifico possivel: tentar uma WPT em quadros causal/rolante,
  mas isso deve ser tratado como nova frente, nao como requisito para fechar a
  implementacao PC atual.

## 2026-06-08 - Perfil max completo da busca Wavelet pesada

### Auditoria de partida

- Conferido `git status --short` antes das edicoes.
- O workspace ja continha muitas alteracoes e arquivos nao rastreados; elas
  foram tratadas como material pre-existente e mantidas.
- A rodada analisada foi a pasta nova
  `resultados/wavelet_heavy_max_refinement_full/`.
- A tentativa anterior em `resultados/wavelet_heavy_max_refinement/` permanece
  historica e incompleta; ela nao foi sobrescrita.
- Nenhuma captura de voz autoral foi criada, lida ou alterada.

### Rodada

```powershell
python -m benchmark_audio.run_wavelet_heavy_refinement `
  --profile max `
  --results-dir resultados/wavelet_heavy_max_refinement_full `
  --screening-speakers 1 `
  --screening-noises-per-group 1 `
  --full-per-family 20
```

- `metadata_wavelet_heavy.json` registra perfil `max` e `elapsed_s` de
  8929,75 s.
- Foram triados 8784 candidatos:
  - 864 DWT;
  - 2160 WPT por coeficiente;
  - 5760 WPT em quadros.
- A validacao completa reavaliou 113 candidatos.
- A comparacao final avaliou 12 candidatos em 72 condicoes finais.

### Resultados

- A DWT pesada continuou fraca:
  - melhor final: +0,055 dB SNR, +0,008 dB SI-SDR, 4,2% degradacoes.
- A WPT por coeficiente continuou limitada:
  - melhor robusta final: +0,393 dB SNR, +0,132 dB SI-SDR, 9,7% degradacoes;
  - melhor por SNR final: +0,672 dB SNR, -0,568 dB SI-SDR, 25,0%
    degradacoes.
- A WPT em quadros robusta do `max` foi
  `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`:
  - validacao: +2,288 dB SNR, +1,127 dB SI-SDR, 0,0% degradacoes;
  - final: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes.
- A melhor WPT em quadros por SNR foi
  `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`:
  - validacao: +2,685 dB SNR, +1,050 dB SI-SDR, 4,2% degradacoes;
  - final: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes.
- A STFT subtracao offline continuou superior:
  - +4,848 dB SNR, +3,716 dB SI-SDR, 0,0% degradacoes.
- A STFT subtracao causal adaptativa continuou candidata PC principal:
  - +3,763 dB SNR, +2,648 dB SI-SDR, 0,0% degradacoes.

### Interpretacao

- O perfil `max` encontrou configuracoes WPT em quadros melhores que o
  `focused`; nao foi apenas confirmacao.
- A melhoria e real, mas proporcional:
  - a robusta `max` melhora sobretudo SI-SDR final em relacao a robusta
    `focused`, mantendo 0,0% degradacoes;
  - a `db6` aumenta o teto de SNR WPT final, mas teve 4,2% degradacoes na
    validacao e por isso nao deve ser vendida como escolha sem ressalva.
- A conclusao sobre Wavelets fica refinada:
  - DWT limiarizada continua fraca;
  - WPT por coeficiente continua insuficiente;
  - WPT em quadros com overlap e estimativa por subbanda e uma frente offline
    forte.
- A WPT em quadros nao deve ser chamada de causal. A melhor configuracao usa
  quantil global por subbanda e olha a estrutura temporal do arquivo.

### Fechamento PC sugerido

- Checkpoint 23: escuta critica controlada com exemplos publicos e, se houver
  autorizacao futura, material autoral conforme protocolo.
- Checkpoint 24: validacao Windows prolongada com o estimador causal STFT
  congelado, medindo estabilidade, status de stream, CPU e memoria.
- Checkpoint 25: consolidar a decisao PC para entrega, mantendo STFT causal
  como implementacao principal e WPT em quadros como resultado cientifico
  offline/futura frente causal.

## 2026-06-08 - Checkpoint 23: fechamento da decisao tecnica PC

### Decisao

- A trilha PC fica tecnicamente fechada em torno da subtracao STFT causal
  adaptativa.
- O criterio nao e apenas melhor SNR: a STFT causal ja tem estado explicito,
  semantica causal, processamento por blocos, parametros congelados e resultado
  final operacional consistente.
- Resultado preservado da STFT causal adaptativa:
  - +3,763 dB SNR;
  - +2,648 dB SI-SDR;
  - 0,0% degradacoes.

### Papel da WPT

- A WPT em quadros com overlap virou o melhor resultado Wavelet e deve aparecer
  como achado importante.
- O perfil `max` melhorou o teto WPT final:
  - robusta `haar`: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes;
  - maior SNR `db6`: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes no
    final, com ressalva de 4,2% degradacoes na validacao.
- A leitura correta e: WPT em quadros e forte como resultado offline, mas ainda
  nao e implementacao PC. Ela usa informacao temporal do arquivo e precisaria
  de uma versao causal/rolante antes de competir como caminho realtime.

### Papel da voz autoral

- O protocolo autoral, a ingestao, a avaliacao objetiva e o formulario
  perceptual continuam preparados.
- Nenhum resultado autoral foi usado para decidir a implementacao PC.
- A voz autoral passa a ser validacao complementar posterior, com parametros
  congelados, e nao bloqueio para fechar a decisao tecnica.

### Narrativa consolidada

- DWT limiarizada historica: baseline fraco/neutro, nao conclusao contra toda a
  familia Wavelet.
- WPT por coeficiente: insuficiente no protocolo atual.
- WPT em quadros: achado Wavelet offline relevante.
- STFT causal adaptativa: caminho PC.
- Voz autoral: validacao privada e perceptual depois, sem ajuste oportunista.

### Proxima continuidade

- Preparar Checkpoint 24 com validacao Windows prolongada da STFT causal
  congelada.
- Medir estabilidade de stream, CPU, memoria, jitter, picos por bloco e
  eventos de underflow/overflow.
- Nao reabrir a busca WPT nem a avaliacao autoral como bloqueios da validacao
  Windows.

## 2026-06-08 - Checkpoint 24: validacao Windows prolongada

### Auditoria de partida

- Retomado o projeto a partir de
  `prompt_continuidade_pos_checkpoint23_decisao_pc.md`.
- `git status --short` mostrou alteracoes rastreadas e muitos arquivos nao
  rastreados ja existentes; todos foram tratados como material pre-existente.
- Lidos os registros obrigatorios:
  - `docs/checkpoints.md`, do Checkpoint 20 em diante;
  - secoes PC-1, PC-2, WPT pesada e Checkpoint 23 deste diario;
  - auditorias do estimador causal, PC-2, WPT e fechamento PC;
  - `docs/estimador_causal.md`;
  - `docs/processamento_wav_blocos.md`;
  - `README_benchmark.md`.
- Confirmado que o caminho PC permanece:
  - `benchmark_audio.causal.CausalSTFTProcessor`;
  - `realtime_audio.windows_realtime.RealtimeBlockProcessor`;
  - subtracao STFT causal adaptativa;
  - bloco externo de 20 ms;
  - parametros congelados da PC-1.

### CLIs verificadas

- `python -m realtime_audio.windows_realtime --help` exibiu:
  - `--list-devices`;
  - `--self-test`;
  - `--duration`;
  - `--block-ms`;
  - `--method`;
  - `--noise-mode`;
  - `--input-device` e `--output-device`;
  - `--input-only`;
  - `--output-dir`;
  - `--no-save`;
  - parametros STFT e Wavelet.
- `python -m realtime_audio.process_wav_blocks --help` confirmou a CLI de
  arquivo em blocos com `--input`, `--output`, `--metrics-json`,
  `--blocks-csv`, `--method`, `--noise-mode`, `--block-ms` e `--overwrite`.
- `benchmark_audio/causal.py` foi tratado como modulo/API, nao como CLI de
  usuario.

### Rodada sem dispositivo fisico

Comando curto:

```powershell
python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --noise-mode adaptive --duration 60 --block-ms 20 --output-dir resultados/windows_realtime_longrun --no-save
```

- Artefato:
  `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_100642_metrics.json`.
- Resultado:
  - 3.000 blocos;
  - media 0,977 ms;
  - p95 1,260 ms;
  - p99 1,573 ms;
  - pior bloco 3,669 ms;
  - zero blocos acima de 20 ms.

Comando prolongado:

```powershell
python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --noise-mode adaptive --duration 600 --block-ms 20 --output-dir resultados/windows_realtime_longrun --no-save
```

- Artefato:
  `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_100737_metrics.json`.
- Resultado:
  - 30.000 blocos;
  - media 0,987 ms;
  - p95 1,271 ms;
  - p99 1,594 ms;
  - pior bloco 4,127 ms;
  - RTF medio 0,049;
  - pior RTF 0,206;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio.

### Rodada com dispositivo fisico input-only

- `python -m realtime_audio.windows_realtime --list-devices` encontrou
  multiplas entradas e saidas.
- A tentativa inicial com `Microfone (USB Audio Device), Windows WASAPI`,
  indice 49, falhou com `sounddevice.PortAudioError: Invalid sample rate` em
  16 kHz.
- A validacao passou a usar `Microfone (USB Audio Device), MME`, indice 2.
- A captura foi feita com `--input-only` e `--no-save`, portanto nenhum WAV de
  microfone foi salvo.

Smoke fisico:

```powershell
python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-dir resultados/windows_realtime_longrun --no-save
```

- Artefato:
  `resultados/windows_realtime_longrun/windows_input_only_stft_subtraction_20ms_20260608_100911_metrics.json`.
- Resultado:
  - 1.498 blocos;
  - media 1,215 ms;
  - p95 2,019 ms;
  - p99 3,354 ms;
  - pior bloco 6,013 ms;
  - zero blocos acima de 20 ms;
  - `status_counts` vazio.

Rodada longa:

```powershell
python -m realtime_audio.windows_realtime --input-only --duration 600 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-dir resultados/windows_realtime_longrun --no-save
```

- Artefato:
  `resultados/windows_realtime_longrun/windows_input_only_stft_subtraction_20ms_20260608_101937_metrics.json`.
- Resultado:
  - 29.998 blocos;
  - media 1,280 ms;
  - p95 2,205 ms;
  - p99 3,904 ms;
  - pior bloco 6,799 ms;
  - RTF medio 0,064;
  - pior RTF 0,340;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio;
  - latencia de entrada reportada pelo driver: 40 ms;
  - total estimado registrado no JSON: 72 ms.

### Interpretacao

- O nucleo STFT causal congelado sustentou 10 min sinteticos e 10 min de
  captura fisica de entrada sem excesso de tempo por bloco.
- O pior bloco fisico ficou abaixo de 7 ms, ainda com margem em relacao ao
  orcamento de 20 ms.
- A ausencia de `status_counts` indica que a CLI nao recebeu underflow/overflow
  reportado pelo stream durante as rodadas.
- A latencia de 72 ms registrada no JSON nao e round-trip fisico: ela soma
  32 ms algoritmicos e 40 ms de entrada reportada pelo driver no modo
  `input-only`.
- Bluetooth nao foi usado como evidencia de baixa latencia.
- WPT em quadros permanece resultado offline e nao foi reaberta.
- Voz autoral permanece validacao complementar futura; nenhum audio autoral foi
  criado, processado ou salvo nesta etapa.

## 2026-06-08 - Pos-Checkpoint 24: consolidacao no relatorio e defesa

### Decisao de continuidade

- Como a STFT causal adaptativa ja estava validada por 600 s em self-test e
  600 s em captura fisica `input-only`, a continuidade escolhida foi
  consolidar a narrativa no relatorio/defesa.
- Nao foi solicitada intervencao do usuario com fone cabeado ou microfone.
- Nenhuma nova captura, reproducao, voz autoral ou WPT foi executada nesta
  etapa.

### Alteracoes feitas

- `entrega3.tex` recebeu uma tabela de validacao Windows prolongada da STFT
  causal adaptativa, com linhas para:
  - self-test sintetico de 600 s;
  - captura fisica `input-only` de 600 s.
- As conclusoes do relatorio foram atualizadas para remover a pendencia antiga
  de nova validacao Windows prolongada.
- `docs/onboarding_equipe.md` foi sincronizado com o estado pos-Checkpoint 24.
- `docs/plano_wavelet_packet_wiener.md` passou de status apos Checkpoint 23
  para status apos Checkpoint 24.
- Criado `docs/roteiro_defesa_checkpoint24.md` com:
  - mensagem central;
  - sequencia sugerida para apresentacao;
  - numeros citaveis;
  - afirmacoes a evitar.

### Verificacao

- Uma tentativa direta com `lualatex entrega3.tex` falhou porque o arquivo usa
  o formato/preambulo local indicado por `%&cab`, portanto nao e compilavel como
  documento LaTeX puro.
- A verificacao correta seguiu o padrao dos checkpoints anteriores:

```powershell
pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex
pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex
```

- A segunda passagem nao registrou referencias indefinidas.
- `entrega3_build.pdf` foi gerado com 35 paginas e copiado para `entrega3.pdf`.
- A busca textual nao encontrou mais as frases antigas que diziam que a
  validacao Windows prolongada ainda estava pendente.

### Interpretacao

- O relatorio agora sustenta que a pendencia operacional do pico isolado de
  104,12 ms foi tratada por uma rodada longa separada.
- A defesa deve afirmar estabilidade operacional por blocos no Windows, nao
  latencia fisica ponta a ponta.
- O valor de 72 ms continua sendo uma estimativa `input-only` registrada no
  JSON: 32 ms algoritmicos + 40 ms de entrada reportada.
- Uma rodada full-duplex cabeada permanece experimento opcional e separado.

## 2026-06-08 - Checkpoint 26: full-duplex cabeado

### Preparacao guiada

- O usuario conectou fone cabeado e manteve volume do Windows em 20/100.
- A listagem de dispositivos passou a mostrar `Alto-falantes (AB13X USB Audio),
  MME` como saida padrao, indice 8.
- O microfone usado continuou sendo `Microfone (USB Audio Device), MME`,
  indice 2.
- O usuario confirmou, apos as rodadas curtas, que ouviu retorno pelo fone
  cabeado, sem eco, desconforto ou volume inseguro.
- Apos a rodada longa de 10 min, o usuario confirmou que nao houve desconforto,
  que o volume permaneceu seguro, que o retorno ficou claro e que era possivel
  ouvir basicamente todo o som capturado pelo microfone.

### Tentativas de driver

- Primeiro teste valido MME:

```powershell
python -m realtime_audio.windows_realtime --duration 3 --method bypass --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save
```

- Resultado: 148 blocos, pior bloco 0,158 ms, zero blocos acima de 20 ms,
  `status_counts` vazio.
- Tentativa WASAPI com entrada indice 49 e saida indice 38 falhou com
  `Invalid sample rate` em 16 kHz.
- Tentativa WDM-KS com entrada indice 80 e saida indice 68 falhou com
  `Invalid device`.
- Tentativa hibrida MME/WASAPI com entrada indice 2 e saida indice 38 falhou
  com `Illegal combination of I/O devices`.
- Leitura: o pareamento de baixa latencia declarado pelo driver nao abriu na
  CLI atual a 16 kHz; a demonstracao valida foi feita via MME.

### Rodadas STFT cabeadas

Smoke STFT:

```powershell
python -m realtime_audio.windows_realtime --duration 5 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save
```

- 248 blocos;
- media 1,265 ms;
- p99 3,284 ms;
- pior bloco 3,941 ms;
- zero blocos acima de 20 ms;
- `status_counts` vazio.

Rodada curta defensavel:

```powershell
python -m realtime_audio.windows_realtime --duration 30 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save
```

- 1.498 blocos;
- media 1,239 ms;
- p95 1,761 ms;
- p99 2,688 ms;
- pior bloco 4,811 ms;
- RTF medio 0,062;
- zero blocos acima de 20 ms;
- `status_counts` vazio.

Rodada longa:

```powershell
python -m realtime_audio.windows_realtime --duration 600 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save
```

- 29.998 blocos;
- media 1,259 ms;
- p95 1,965 ms;
- p99 3,283 ms;
- pior bloco 7,301 ms;
- RTF medio 0,063;
- pior RTF 0,365;
- zero blocos acima de 20 ms;
- estado maximo 60.900 bytes;
- `status_counts` vazio.

### Artefatos

- Pasta: `resultados/windows_realtime_wired/`.
- Resumo:

```powershell
python -m realtime_audio.summarize_realtime --input-dir resultados/windows_realtime_wired --pattern "windows_*_metrics.json" --output resultados/tabelas/realtime_windows_wired.csv
```

- CSV consolidado: `resultados/tabelas/realtime_windows_wired.csv`.

### Interpretacao

- A plataforma PC demonstrou caminho captura-processa-reproduz cabeado por
  10 min com a STFT causal adaptativa congelada.
- A estabilidade computacional por bloco continua folgada: nenhum bloco passou
  de 20 ms e o pior bloco da rodada longa ficou em 7,301 ms.
- A saida cabeada MME reportou 200 ms de latencia de saida; por isso, a rodada
  nao deve ser vendida como prova de baixa latencia ponta a ponta.
- O resultado substitui a demonstracao Bluetooth como evidencia funcional
  cabeada, mas nao substitui uma medicao fisica de loopback.
- A observacao subjetiva do usuario entra apenas como conforto operacional da
  demonstracao local, nao como avaliacao perceptual formal.

## 2026-06-08 - Checkpoint 27: presets da demo PC

### Motivacao

- A plataforma PC ja tinha comandos longos e validados, mas eles exigiam lembrar
  metodo, modo de ruido, indices de dispositivo, pasta de saida e `--no-save`.
- Para reduzir erro operacional na defesa, a CLI recebeu presets oficiais.

### Implementacao

- `realtime_audio/windows_realtime.py` recebeu `--pc-demo` com tres valores:
  - `self-test`;
  - `input-only`;
  - `wired`.
- O preset aplica:
  - `stft_subtraction`;
  - `noise-mode adaptive`;
  - bloco de 20 ms;
  - `--no-save`;
  - pastas de saida usadas nos checkpoints.
- O preset `wired` tambem fixa:
  - entrada indice 2;
  - saida indice 8.

### Comandos curtos

```powershell
python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1
python -m realtime_audio.windows_realtime --pc-demo input-only --duration 600
python -m realtime_audio.windows_realtime --pc-demo wired --duration 600
```

### Testes

- `python -m pytest tests\test_realtime_audio.py`
  - 5 testes passaram.
- `python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1`
  - concluiu e gerou JSON em `resultados/windows_realtime_longrun`.

### Interpretacao

- O preset nao muda o algoritmo nem os parametros congelados; ele apenas
  empacota comandos ja validados.
- Como os indices de dispositivo sao especificos deste PC, qualquer troca de
  hardware deve comecar por `--list-devices`.

## 2026-06-08 - Planejamento da trilha Virtual Microphone proprio

### Contexto

- O usuario perguntou se a plataforma poderia evoluir para um microfone virtual
  proprio, semelhante em funcao ao SteelSeries Sonar, mas sem depender de outro
  programa auxiliar.
- A resposta tecnica foi: sim, e possivel, mas a trilha deixa de ser apenas
  aplicacao Python/PC e passa a envolver driver virtual de audio no Windows.

### Decisao de planejamento

- A trilha nao deve substituir o Checkpoint 28.
- Primeiro deve ser fechada a auditoria final de release da plataforma PC atual.
- Depois, a trilha Virtual Microphone proprio deve ser aberta como frente
  propria, com checkpoints separados.

### Roadmap definido

- Checkpoint 29: especificacao do Virtual Microphone proprio.
- Checkpoint 30: ambiente WDK e build do SYSVAD baseline.
- Checkpoint 31: instalacao local em modo de teste.
- Checkpoint 32: ponte usuario/driver para audio processado.
- Checkpoint 33: integracao STFT causal ao pipeline virtual.
- Checkpoint 34 no roteiro da epoca: interface minima. A numeracao foi
  supersedida depois do fechamento do Checkpoint 33.
- Etapa posterior no roteiro da epoca: auditoria de distribuicao, assinatura
  e custos. A numeracao `Checkpoint 35` foi supersedida.

### Ressalvas

- Para prototipo academico, modo de teste do Windows pode ser suficiente.
- Para distribuicao real, driver kernel-mode exige assinatura e provavelmente
  envolve certificado EV, Partner Center, attestation/HLK e instalador.
- VB-Cable pode ser usado como controle temporario, mas nao deve ser tratado
  como solucao final se o objetivo e um microfone proprio.

### Artefato criado

- `prompt_continuidade_pos_checkpoint27_release_pc_virtual_mic.md`, com:
  - instrucoes para abrir novo chat;
  - tarefas do Checkpoint 28;
  - roadmap Virtual Microphone proprio;
  - regras de narrativa e limites.

## 2026-06-08 - Checkpoint 28: auditoria final de release PC

### Auditoria de partida

- Retomado o projeto a partir de
  `prompt_continuidade_pos_checkpoint27_release_pc_virtual_mic.md`.
- `git status --short --branch` mostrou `main...origin/main [ahead 26]`,
  varias alteracoes rastreadas e muitos arquivos nao rastreados pre-existentes.
- Nada foi revertido.
- Foram revisados:
  - `docs/checkpoints.md`, do Checkpoint 24 em diante;
  - `docs/diario_tecnico.md`, do Checkpoint 24 em diante;
  - `README_benchmark.md`;
  - `realtime_audio/README.md`;
  - `docs/roteiro_defesa_checkpoint24.md`;
  - `realtime_audio/windows_realtime.py`;
  - `tests/test_realtime_audio.py`.

### Verificacoes

Suite automatizada:

```powershell
python -m pytest
```

- Resultado: 50 testes passaram.

Smoke oficial sem dispositivo fisico:

```powershell
python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1
```

- Artefato:
  `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_114451_metrics.json`.
- Resultado:
  - 50 blocos;
  - media 0,977 ms;
  - p95 1,391 ms;
  - p99 1,556 ms;
  - pior bloco 1,612 ms;
  - RTF medio 0,049;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio.

O smoke `wired` de 30 s nao foi executado nesta sessao porque abriria saida
fisica. Ele continua sendo comando opcional dependente de fone cabeado, volume
baixo e autorizacao explicita.

### Documentacao criada

- Criado `docs/release_pc_checklist.md`.
- O checklist registra:
  - escopo congelado do release PC;
  - comandos oficiais;
  - artefatos esperados;
  - metricas dos Checkpoints 24, 26, 27 e da auditoria atual;
  - procedimento de demonstracao segura;
  - limitacoes obrigatorias;
  - itens fora do release PC.

### Interpretacao

- A auditoria confirma que a plataforma PC esta em estado defensavel de release
  academico: STFT causal adaptativa, presets oficiais e estabilidade por
  blocos.
- O termo correto para a defesa continua sendo "estavel por blocos no Windows",
  nao "baixa latencia ponta a ponta".
- A latencia de 72 ms no input-only e a de 272 ms no duplex cabeado continuam
  estimativas registradas pela CLI, nao medicoes fisicas de loopback.
- WPT em quadros permanece achado offline e voz autoral permanece validacao
  futura.

## 2026-06-08 - Checkpoint 29: especificacao do Virtual Microphone proprio

### Fontes oficiais consultadas

- SYSVAD Virtual Audio Device Driver Sample:
  `https://learn.microsoft.com/en-us/samples/microsoft/windows-driver-samples/sysvad-virtual-audio-device-driver-sample/`
- Sample Audio Drivers:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/sample-audio-drivers`
- Driver signing:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/install/driver-signing`
- Introduction to Test-Signing:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/install/introduction-to-test-signing`
- Partner Center for Windows Hardware:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/`

### Especificacao

- Criado `docs/virtual_mic_architecture.md`.
- Arquitetura-alvo:
  - app/servico de usuario captura microfone fisico;
  - `CausalSTFTProcessor` processa blocos de 20 ms em mono 16 kHz;
  - audio processado e publicado em buffer local;
  - driver virtual baseado em SYSVAD expoe endpoint de captura para apps
    externos, por exemplo `PTC Noise Reduction Microphone`.
- Regra de engenharia:
  - primeiro compilar e instalar SYSVAD sem modificacoes;
  - depois validar ponte usuario/driver com tom sintetico;
  - so entao integrar microfone real e STFT causal.

### Alternativas e limites

- SYSVAD e caminho principal para endpoint proprio.
- APO e alternativa complementar quando o objetivo for processar endpoint
  existente, mas nao substitui sozinho o microfone virtual proprio.
- VB-Cable pode ser usado como controle temporario, nao como solucao final.
- Test-signing serve para desenvolvimento e teste; nao e distribuicao.
- Driver kernel-mode distribuivel exige assinatura e fluxo Microsoft, com EV,
  Partner Center e possivel attestation/HLK.

### Proxima continuidade

- Checkpoint 30: verificar Visual Studio, Windows SDK e WDK; obter
  `Windows-driver-samples`; inicializar submodulos; abrir/compilar SYSVAD
  baseline sem integrar DSP.

## 2026-06-11 - Checkpoint 30: ambiente WDK e tentativa de build SYSVAD

### Retomada e preservacao do repositorio

- A sessao foi retomada a partir de
  `prompt_continuidade_pos_checkpoint29_virtual_mic.md`.
- `git status --short --branch` confirmou
  `main...origin/main [ahead 26]`, com varias alteracoes pre-existentes.
- Nenhum arquivo pre-existente foi revertido.
- Foram relidos `docs/release_pc_checklist.md`,
  `docs/virtual_mic_architecture.md`, os Checkpoints 28 e 29 e os pontos de
  integracao em `realtime_audio/windows_realtime.py` e
  `benchmark_audio/causal.py`.

### Auditoria do ambiente Windows

- Sistema: Windows 11 Home Single Language `10.0.26200`, x64.
- Visual Studio Community 2026 `18.1.1`, instalado em
  `C:\Program Files\Microsoft Visual Studio\18\Community`.
- MSBuild: `18.0.5.56406`.
- MSVC: `14.50.35717`.
- A carga C++ desktop, ferramentas x64/x86 e ATL atual estao instaladas.
- Windows SDK:
  - headers/libs em `10.0.26100.0`;
  - produto instalado `10.1.26100.7175`.
- WDK ausente:
  - nenhum produto Windows Driver Kit no registro;
  - nenhum componente Driver Kit selecionado no estado do Visual Studio;
  - nenhum diretorio `Windows Kits\10\build`;
  - nenhum header `km`;
  - nenhum `WindowsDriver.Common.props`;
  - nenhum `inf2cat.exe` ou `stampinf.exe`.
- A comparacao do estado instalado com
  `_wdk_utils/winget/configs/wdk-desktop.vsconfig` tambem apontou, para x64:
  - `Microsoft.VisualStudio.Component.VC.ATL.Spectre`;
  - `Microsoft.VisualStudio.Component.VC.ATLMFC.Spectre`;
  - `Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre`.
- Componentes ARM64/ARM64EC do `.vsconfig` tambem estao ausentes, mas nao
  bloqueiam a primeira tentativa `Debug|x64`.

### Clone e preparacao do sample

Comandos:

```powershell
git clone https://github.com/microsoft/Windows-driver-samples.git `
  %USERPROFILE%\source\repos\Windows-driver-samples
cd %USERPROFILE%\source\repos\Windows-driver-samples
git submodule update --init
```

Resultado:

- sample em
  `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad`;
- branch `main`;
- commit do repositorio:
  `e99ae832b48b245404f9bd750af4864247b061e8`;
- WIL:
  `3c00e7f1d8cf9930bbb8e5be3ef0df65c84e8928`;
- repositorio de samples limpo apos a inicializacao.

### Tentativa de build baseline

Comando:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe' `
  audio\sysvad\sysvad.sln `
  /t:Build /m `
  /p:Configuration=Debug `
  /p:Platform=x64 `
  /v:minimal
```

Resultado:

- codigo de saida `1`;
- seis erros `MSB8020`;
- toolset ausente `WindowsApplicationForDrivers10.0` em:
  - `SwapAPO.vcxproj`;
  - `DelayAPO.vcxproj`;
  - `AecAPO.vcxproj`;
  - `KeywordDetectorContosoAdapter.vcxproj`;
  - `KwsAPO.vcxproj`;
- toolset ausente `WindowsKernelModeDriver10.0` em:
  - `EndpointsCommon.vcxproj`.

Mensagem central do MSBuild:

```text
error MSB8020: The build tools for WindowsApplicationForDrivers10.0
cannot be found.

error MSB8020: The build tools for WindowsKernelModeDriver10.0
cannot be found.
```

O log diagnostico completo foi preservado em:

`resultados/sysvad_checkpoint30/sysvad_debug_x64_build.log`

Nenhum `.sys`, `.cat`, `package.cer` ou diretorio de saida `package` foi
gerado.

### Plano de correcao

As paginas oficiais atuais da Microsoft recomendam WDK 28000 com Visual Studio
2026. O plano e:

1. Adicionar pelo Visual Studio Installer o componente individual
   `Windows Driver Kit` e os componentes Spectre x64 indicados pelo
   `_wdk_utils/winget/configs/wdk-desktop.vsconfig` oficial.
2. Instalar o Windows SDK 28000:

```powershell
winget install Microsoft.WindowsSDK.10.0.28000
```

3. Instalar o WDK 28000:

```powershell
winget install Microsoft.WindowsWDK.10.0.28000
```

4. Reabrir o terminal e confirmar headers `km`, targets de driver,
   `inf2cat.exe` e `stampinf.exe`.
5. Repetir o build `Debug|x64` sem modificar nem retargetar o SYSVAD.
6. Somente depois de obter a pasta `package`, planejar a instalacao local do
   Checkpoint 31.

Versoes oferecidas pelo WinGet nesta auditoria:

- SDK: `10.0.28000.1721`;
- WDK: `10.1.28000.1839`.

### Limites

- O Checkpoint 30 ainda nao estava aprovado como build concluido nesta
  primeira tentativa.
- O resultado desta etapa foi uma caracterizacao reproduzivel da pendencia.
- Nenhum driver foi instalado.
- Test-signing nao foi habilitado.
- Nenhuma configuracao de boot foi alterada.
- Nao existe endpoint virtual proprio instalado.

## 2026-06-11 - Conclusao do Checkpoint 30

### Instalacao e reparo do toolchain

- Foram instalados:
  - Windows SDK `10.0.28000.1721`;
  - WDK `10.1.28000.1839`;
  - componente WDK do Visual Studio;
  - ATL, ATL/MFC e runtimes Spectre para x86/x64.
- O Visual Studio Community 2026 foi atualizado de `18.1.1` para `18.7.0`;
  o MSBuild passou a `18.7.1.23011`.
- A atualizacao encontrou um registro MSI orfao do
  `Microsoft Visual C++ 2022 X86 Additional Runtime - 14.34.31938`.
- O solucionador oficial Microsoft removeu o product code corrompido
  `{080D8397-60F4-44B3-BB95-FBB950CB0B4E}` do banco do Windows Installer.
- O runtime x86 `14.51.36247` foi reparado; os pacotes Minimum e Additional
  terminaram com codigo `0`.
- O reparo do Visual Studio terminou com codigo `3010`. A reinicializacao
  continua pendente e nao foi executada automaticamente.

### Verificacao do WDK

- Confirmados:
  - `Include\10.0.28000.0\km`;
  - `build\10.0.28000.0`;
  - `WindowsDriver.Common.props`;
  - `stampinf.exe`;
  - `Inf2Cat.exe`;
  - `WindowsApplicationForDrivers10.0`;
  - `WindowsKernelModeDriver10.0`.
- Os toolsets passaram a existir tambem em `MSBuild\Microsoft\VC\v180`.
- O SDK foi reinstalado com `winget --force` para completar `midl.exe` e
  `rc.exe`, ausentes depois da primeira tentativa interrompida.

### Builds finais

- O comando original com MSBuild x86 reconheceu os toolsets e gerou os
  binarios principais, mas falhou na validacao:
  - `x86\InfVerif.dll` nao existe no WDK 28000 instalado;
  - `ApiValidator.exe` x86 encerrou com codigo `193`.
- Log:
  `resultados/sysvad_checkpoint30/sysvad_debug_x64_build_vs187_wdk28000_sdk_repaired.log`.
- O mesmo build com MSBuild amd64 terminou com codigo `0`:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\amd64\MSBuild.exe' `
  audio\sysvad\sysvad.sln `
  /t:Build /m `
  /p:Configuration=Debug `
  /p:Platform=x64 `
  /v:minimal
```

- Log diagnostico aprovado:
  `resultados/sysvad_checkpoint30/sysvad_debug_x64_build_vs187_wdk28000_amd64.log`.
- Tamanho: 10.771.324 bytes.
- SHA-256:
  `EE101121F354D8F192422815B2D3390E967466660CF4719D5933591F1FE08BFD`.

### Pacote auditado

- Pasta:
  `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad\x64\Debug\package`.
- Arquivos principais:
  - `TabletAudioSample.sys`;
  - `AecApo.dll`;
  - `DelayAPO.dll`;
  - `KeywordDetectorContosoAdapter.dll`;
  - `KWSApo.dll`;
  - `SwapAPO.dll`;
  - `ComponentizedApoSample.inf`;
  - `ComponentizedAudioSample.inf`;
  - `ComponentizedAudioSampleExtension.inf`;
  - `sysvad.cat`.
- Certificado:
  `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad\x64\Debug\package.cer`.
- Hashes SHA-256:
  - `TabletAudioSample.sys`:
    `413794EC01534AAFD0B45073144A34E86048CFE444F7B2B66881996F817AD5F3`;
  - `sysvad.cat`:
    `891EF974D39FB22784612D4D4DCD56A270504788E1985B635BB2B34DB39DC62C`;
  - `package.cer`:
    `ACCDB75C1395C53786C3AF6DB44012D773D665B8FBA214B7375C029C9B3D1215`.
- A assinatura de teste foi criada, mas a cadeia ainda nao e confiavel
  localmente porque o certificado nao foi instalado.
- O clone oficial permaneceu limpo no commit
  `e99ae832b48b245404f9bd750af4864247b061e8`.

### Fechamento

- Checkpoint 30 concluido.
- Nenhum driver foi instalado.
- Test-signing nao foi habilitado.
- Nenhuma configuracao de boot foi alterada.
- O Checkpoint 31 permanece fechado ate existir plano explicito de reversao,
  Secure Boot, BitLocker e test-signing.

## 2026-06-11 - Verificacao final do ambiente apos reinicializacao

### Estado do Visual Studio e WDK

- A maquina foi reiniciada pelo usuario.
- O Visual Studio Community 2026 `18.7.0` passou a informar:
  - `isComplete=true`;
  - `isLaunchable=true`;
  - `isRebootRequired=false`.
- MSBuild amd64 confirmado em `18.7.1.23011`.
- SDK `10.0.28000.1721` e WDK `10.1.28000.1839` continuam instalados.
- Foram reconfirmados:
  - headers `Include\10.0.28000.0\km`;
  - `WindowsDriver.Common.props`;
  - `Inf2Cat.exe` e `stampinf.exe`;
  - toolsets `WindowsApplicationForDrivers10.0` e
    `WindowsKernelModeDriver10.0`;
  - componentes WDK, ATL Spectre, ATL/MFC Spectre e runtimes Spectre.
- `devcon.exe` x64 foi localizado em
  `C:\Program Files (x86)\Windows Kits\10\Tools\10.0.28000.0\x64\devcon.exe`.

### Build de confirmacao

- O build `Debug|x64` pelo MSBuild amd64 terminou com codigo `0`.
- A saida registrou `Errors: None` e `Warnings: None`.
- Teste de assinabilidade, geracao de catalogo e assinatura de teste foram
  concluidos.
- Log:
  `resultados/sysvad_checkpoint30/sysvad_debug_x64_build_post_reboot.log`.
- Tamanho: 5.886 bytes.
- SHA-256:
  `9C8D3478887F97F1E9E6A3D1713CC6ABC79DA85632172EBCCDBC905B44D738D8`.
- Hashes atuais:
  - `TabletAudioSample.sys`:
    `413794EC01534AAFD0B45073144A34E86048CFE444F7B2B66881996F817AD5F3`;
  - `sysvad.cat` regenerado:
    `DBFEFC712F9F9EBB0862EF48829428E2ABA3E62DF53680166B6FF83F21BDCB4A`;
  - `package.cer`:
    `ACCDB75C1395C53786C3AF6DB44012D773D665B8FBA214B7375C029C9B3D1215`.
- O clone oficial permaneceu limpo no commit
  `e99ae832b48b245404f9bd750af4864247b061e8`, com WIL em
  `3c00e7f1d8cf9930bbb8e5be3ef0df65c84e8928`.

### Pre-auditoria de seguranca para o Checkpoint 31

- Secure Boot esta habilitado (`UEFISecureBootEnabled=1`).
- A consulta completa ao BitLocker foi negada no terminal nao elevado; seu
  estado continua desconhecido e deve ser obtido como administrador antes de
  qualquer mudanca de firmware ou boot.
- Nenhum `bcdedit` foi executado.
- Nenhum certificado ou driver foi instalado.
- O certificado esperado tem thumbprint SHA-1
  `7ABED3D56ECAFD8B95C7B98451237673A53F899B` e nao foi encontrado em
  `LocalMachine\Root` nem em `LocalMachine\TrustedPublisher`.
- `pnputil /enum-devices /deviceid Root\Sysvad_ComponentizedAudioSample`
  nao encontrou dispositivo correspondente.
- Test-signing continua desabilitado e nenhuma configuracao de boot foi
  alterada.
- Foi criado um prompt separado para iniciar o Checkpoint 31 com auditoria,
  consentimento explicito e plano de reversao.

## 2026-06-11 - Checkpoint 31: auditoria administrativa somente leitura

- A Fase 1 foi executada em PowerShell elevado por um script dedicado que nao
  consulta nem registra material de senha de recuperacao.
- Secure Boot confirmado como habilitado.
- BitLocker em `C:` confirmado como desligado, com volume totalmente
  descriptografado, nenhum metodo de criptografia e zero protetores.
- VBS e Integridade de memoria/HVCI estao ativos.
- A entrada BCD atual nao possui `TESTSIGNING`.
- Nao foram encontrados ponto de restauracao, copia de sombra ou versao do
  Windows Backup.
- O Windows Recovery Environment esta habilitado na particao de recuperacao.
- A unidade `C:` tinha `11,37 GiB` livres de `931,25 GiB`.
- O pacote SYSVAD manteve os hashes aprovados e nao existe dispositivo ou
  certificado residual.
- A Fase 2 foi preparada documentalmente com remocao restrita aos IDs,
  `oem*.inf` e thumbprint que forem registrados durante a instalacao.
- Nenhum certificado ou driver foi instalado, nenhum comando `bcdedit /set`
  foi executado e nenhuma configuracao de firmware foi alterada.
- A continuidade foi interrompida no ponto de consentimento porque esta e a
  maquina principal, sem backup/restauracao detectavel e com pouco espaco
  livre.

### Preparacao de recuperacao autorizada

- A Protecao do Sistema foi habilitada em `C:`.
- Foi criado e enumerado o ponto de restauracao
  `PTC3527 Checkpoint 31 pre-SYSVAD`, sequencia `281`.
- O ponto usou inicialmente `58,3 MB`; o VSS alocou `320 MB`, com limite de
  `1,13 GB`.
- Permaneceram aproximadamente `11,06 GiB` livres.
- O BCD foi exportado para
  `resultados/sysvad_checkpoint31/bcd_pre_sysvad.bak`, SHA-256
  `98F09CF7BBCE86C67D5D7B0B187996D70691F64D6ECDFB4FB2F1BA06A4B60A26`.
- A listagem completa anterior foi preservada e nao continha `TESTSIGNING`.
- Os logs de build confirmam `signtool sign /ph /fd sha256` no driver e no
  catalogo, permitindo manter HVCI habilitada na primeira tentativa.
- Nenhum reinicio foi solicitado e Secure Boot continuou habilitado.

### Retorno apos alteracao manual do Secure Boot

- O usuario reiniciou e desabilitou somente Secure Boot no firmware UEFI.
- A auditoria elevada confirmou Secure Boot desabilitado.
- BitLocker permaneceu desligado e o volume `C:` totalmente descriptografado.
- VBS e Integridade de memoria/HVCI permaneceram ativos.
- O ponto de restauracao `281` continuou enumeravel.
- `TESTSIGNING` ainda estava ausente do BCD.
- Certificado e dispositivo SYSVAD continuaram ausentes.
- O espaco livre observado apos o boot foi `9,83 GiB`.
- O script para habilitar `TESTSIGNING` foi preparado com validacoes de
  Secure Boot, BitLocker, ponto de restauracao e backup BCD, mas nao executado
  sem consentimento especifico.

### TESTSIGNING habilitado no BCD

- Depois de consentimento explicito, foi executado
  `bcdedit.exe /set TESTSIGNING ON`.
- O comando terminou com codigo `0` e a entrada atual passou a mostrar
  `testsigning Yes`.
- O script validou antes da alteracao:
  - Secure Boot desabilitado;
  - BitLocker desligado;
  - ponto de restauracao `281` presente;
  - backup BCD existente.
- Nenhum reinicio foi executado automaticamente.
- Certificado e driver SYSVAD ainda nao foram instalados.
- A proxima acao e uma reinicializacao normal pelo usuario, seguida de nova
  auditoria antes da instalacao.

### Modo de teste ativo e certificado confiavel

- Depois da reinicializacao, o usuario confirmou visualmente a marca d'agua
  `Modo de Teste`.
- A auditoria elevada confirmou:
  - Secure Boot desabilitado;
  - `testsigning Yes`;
  - BitLocker desligado;
  - VBS/HVCI ativos;
  - ponto de restauracao `281` presente;
  - nenhum dispositivo SYSVAD instalado.
- O certificado de thumbprint
  `7ABED3D56ECAFD8B95C7B98451237673A53F899B` foi instalado em
  `LocalMachine\Root` e `LocalMachine\TrustedPublisher`.
- O certificado foi confirmado exatamente uma vez em cada store.
- As assinaturas de `TabletAudioSample.sys` e `sysvad.cat` passaram a ser
  verificadas como validas.
- O README oficial foi relido: a ordem obrigatoria e INF base primeiro; APO e
  extensao podem ser instalados depois em qualquer ordem.
- A instalacao isolada do INF base foi preparada para registrar `oem*.inf`,
  ID de instancia, codigo de problema e log SetupAPI.

## 2026-06-11 - Incidente SYSVAD e reversao de emergencia

- O DevCon iniciou a instalacao do INF base aproximadamente as `02:11`.
- Foram criados `ROOT\MEDIA\0004`, `oem50.inf` e o servico
  `sysvad_componentizedaudiosample`.
- O script nao chegou a gravar seu JSON final porque o kernel falhou durante
  a inicializacao do dispositivo.
- Ocorreram duas telas azuis `0x7E`, ambas atribuídas a
  `TabletAudioSample.sys`.
- A tentativa de Restauracao do Sistema feita no WinRE falhou por falta de
  espaco durante a restauracao de `%ProgramFiles%\WindowsApps`.
- O Windows voltou a iniciar e o dispositivo apareceu parado.
- Foram preservados dois minidumps e o log SetupAPI.
- O WinDbg, usando o PDB local, localizou a falha em
  `BthHfpDevice::Init`, `BthhfpDevice.cpp:264`.
- `WdfIoTargetOpen`, chamado com `STANDARD_RIGHTS_ALL` para uma interface
  Bluetooth HFP/SCO, retornou `STATUS_ACCESS_DENIED`.
- No binario Debug, o caminho de erro atingiu uma instrucao `INT 3`, que nao
  foi tratada e produziu `SYSTEM_THREAD_EXCEPTION_NOT_HANDLED`.
- A reversao removeu, sem `/force`, o dispositivo `ROOT\MEDIA\0004`, o pacote
  `oem50.inf`, o servico, os dois certificados e habilitou
  `TESTSIGNING OFF`.
- Nenhum novo teste de driver sera feito nesta maquina principal.
- Secure Boot ainda deve ser reabilitado manualmente depois da limpeza.

### Fechamento seguro do incidente

- O usuario reabilitou Secure Boot no firmware.
- A marca d'agua do modo de teste desapareceu.
- A auditoria elevada final confirmou:
  - Secure Boot ativo;
  - `TESTSIGNING` desligado;
  - VBS/HVCI ativos;
  - zero dispositivo, pacote, servico ou certificado SYSVAD;
  - nenhum novo bugcheck ou desligamento inesperado desde o boot das `02:37`;
  - `10,8 GiB` livres em `C:`.
- O host possui `31,57 GiB` de RAM, 20 processadores logicos e hypervisor
  presente, portanto suporta uma VM de teste.
- A proxima tentativa exige liberar espaco para um disco virtual e criar um
  snapshot antes de instalar qualquer driver.

## 2026-06-11 - Checkpoint 31 concluido em VM

- Foi criada a VM `PTC3527-SYSVAD-LAB` no VirtualBox `7.2.8`, com Windows 11
  Pro 25H2, 8 GiB, 4 vCPUs, PIIX3, EFI e TPM 2.0.
- O host permaneceu protegido; modo de teste e Secure Boot desativado foram
  usados somente no convidado.
- O pacote aprovado foi copiado para `C:\PTC3527\sysvad-package`; os hashes
  de `TabletAudioSample.sys`, `sysvad.cat` e `package.cer` coincidiram com o
  Checkpoint 30.
- Foram criados os snapshots `base-limpa`, `pre-sysvad`,
  `testsigning-pronto`, `sysvad-instalado` e `checkpoint31-revertido`.
- A instalacao gerou `ROOT\MEDIA\0000`, `oem5.inf`, `oem6.inf` e `oem7.inf`.
- O dispositivo apareceu como `SYSVAD (with APO Extensions)`, iniciado, com
  endpoints virtuais de reproducao e captura.
- A instalacao persistiu apos novo boot e nao provocou tela azul.
- A reversao removeu dispositivo, tres pacotes e certificado, desligou
  `TESTSIGNING` e foi validada depois de novo boot.
- Duas desconexoes acidentais do HD externo pausaram a VM. Os estados
  afetados foram descartados por snapshot; o volume `E:` permaneceu integro.
- Regra operacional: nao desconectar o HD enquanto a VM estiver ligada,
  pausada, salvando snapshot ou desligando.
- O Checkpoint 31 foi concluido sem integrar `CausalSTFTProcessor` e sem
  afirmar a existencia de um endpoint PTC.

## 2026-06-11 - Checkpoint 32: implementacao host-side

- A VM permaneceu desligada em `checkpoint31-revertido`; `E:` foi confirmado
  saudavel e nao dirty.
- O clone SYSVAD estava limpo no baseline
  `e99ae832b48b245404f9bd750af4864247b061e8`.
- Foi criada a branch
  `codex/checkpoint32-user-driver-bridge`.
- O caminho de captura foi mapeado:
  `UpdatePosition` chama `WriteBytes`, que chamava `GenerateSine`.
- O callback do timer pode consumir em `DISPATCH_LEVEL`; por isso a fila usa
  memoria nao paginada e spin lock.
- O endpoint `MicIn` foi escolhido por anunciar nativamente PCM mono, 16 bits,
  16 kHz.
- Foi implementado contrato versao `1` com interface de dispositivo, IOCTLs
  `METHOD_BUFFERED`, blocos de 20 ms e fila de 1 segundo.
- Underrun gera zeros e overrun descarta o bloco novo.
- Foi criado produtor CLI de tom/silencio e capturador WASAPI exclusivo.
- O teste host-side da fila passou.
- O build final `Debug|x64` terminou com codigo `0`, sem erros nem avisos.
- Artefatos e hashes foram congelados em
  `resultados/sysvad_checkpoint32`.
- O host permaneceu sem driver, certificado ou `TESTSIGNING`.
- A implantacao aguarda somente execucao protegida na VM a partir do snapshot
  `testsigning-pronto`.

## 2026-06-11 - Checkpoint 32 concluido na VM

- Foi criado `checkpoint32-pre-bridge` a partir de `testsigning-pronto`, com
  zero driver, pacote e certificado SYSVAD.
- A primeira iteracao registrou a interface, mas o PortCls recusava a abertura
  sem nome. O snapshot `checkpoint32-bridge-installed` foi preservado como
  evidencia dessa etapa.
- A correcao final adicionou a referencia `\ptcpcm` e handlers isolados de
  `CREATE`, `CLOSE`, `CLEANUP` e `DEVICE_CONTROL`.
- O pacote v2 passou no boot com `ROOT\MEDIA\0000`, `oem5.inf`, `oem6.inf`,
  `oem7.inf`, servico `Running` e oito endpoints `OK`.
- O capturador foi ligado com runtime C++ estatico e alterado de evento WASAPI
  para polling, pois o evento nao era sinalizado na VM.
- O WAV `functional/normal_440hz.wav` confirmou 12 s, 16 kHz, mono, 16 bits,
  pico `0,25` e frequencia dominante `440,0 Hz`.
- Testes negativos:
  - versao de configuracao invalida: erro `87`;
  - versao de bloco e tamanho de escrita invalidos: `rejected=1`;
  - salto de sequencia: `sequence_errors=2`;
  - overrun acelerado: 50 aceitos e 50 descartados;
  - segundo produtor conectado: `ERROR_BUSY (170)` e `rejected` incrementado;
  - cleanup liberou o dono e permitiu reconexao.
- O boot repetido manteve a ponte funcional. O snapshot
  `checkpoint32-functional-validated-v2` preserva esse estado.
- O VirtualBox Guest Additions apresentou atrasos e travamentos do Guest
  Control apos alguns reboots; ciclos de energia foram usados somente depois
  de aguardar o Windows e confirmar o estado visual.
- Reversao:
  - removidos dispositivo e `oem7/oem6/oem5`;
  - removido o certificado dos dois stores pelo thumbprint exato;
  - `TESTSIGNING OFF`;
  - auditoria apos boot confirmou zero residuos.
- Estado final:
  - VM desligada;
  - snapshot atual `checkpoint32-revertido`;
  - volume `E:` saudavel e nao dirty;
  - host sem alteracoes de driver, certificado ou boot.

## 2026-06-12 - Checkpoint 33 aberto

- O protocolo v1 e o driver do Checkpoint 32 foram mantidos sem alteracao.
- Foi implementado um cliente Python para descobrir a interface PTC PCM,
  configurar a ponte, enviar blocos e consultar estatisticas.
- Os layouts binarios foram conferidos contra `PtcPcmBridge.h`: 24 bytes para
  configuracao, 664 bytes para bloco e 112 bytes para estatisticas.
- A captura continua usando `sounddevice` e o DSP continua usando o
  `CausalSTFTProcessor` compartilhado com os testes por arquivo.
- O callback de audio nao executa IOCTL diretamente. Ele entrega a saida a uma
  fila limitada, consumida por uma thread de escrita.
- O pacing passou a consultar a profundidade da fila do driver. O alvo padrao
  e quatro blocos.
- Em lotacao da fila local, o bloco mais antigo e descartado para evitar
  crescimento indefinido da latencia. A sequencia e criada somente no envio.
- A suite completa passou: `53 passed` e `11 subtests passed`.
- A abertura da ponte no host falhou como esperado porque a interface nao esta
  instalada. Nenhuma configuracao do host foi alterada.
- A VM foi confirmada desligada em `checkpoint32-revertido`; `E:` esta
  saudavel.
- A entrada de audio do VirtualBox, antes desativada, foi habilitada com a VM
  desligada. Nenhum snapshot foi restaurado nesta etapa.
- Depois da preparacao host-side, foi restaurado
  `checkpoint32-functional-validated-v2`.
- O snapshot `checkpoint33-pre-dsp-user` foi criado, mas a restauracao havia
  reposto `audio_in=off`.
- A entrada foi reabilitada e o estado atual foi preservado em
  `checkpoint33-pre-dsp-user-audio-in`.
- Foi gerado `checkpoint33_python_bundle.zip`, SHA-256
  `2670007743FF0E87383CF02F1A7A0A215AC156FE4760F6E9FD0213B8AED14E9E`.
- A VM permanece desligada; nenhum comando foi executado no convidado.

### Incidente de E/S na abertura do Checkpoint 33

- O HD externo foi desconectado e reconectado acidentalmente enquanto a VM
  estava ligada durante o bootstrap.
- As sessoes de Guest Control e consultas do VirtualBox ficaram bloqueadas.
- Os processos de automacao foram encerrados sem continuar a copia ou os
  testes.
- O Windows confirmou `E:` como saudavel, operacional e nao dirty.
- Foi tentado desligamento ACPI e aguardado mais de 60 segundos, sem
  encerramento da VM.
- Depois da falha do desligamento normal, os processos da instancia foram
  encerrados; o VirtualBox reportou `VMState="aborted"`.
- `checkpoint33-pre-dsp-user-audio-in` foi restaurado para descartar o delta
  potencialmente afetado.
- Estado final confirmado:
  - VM em `poweroff`;
  - snapshot atual `checkpoint33-pre-dsp-user-audio-in`;
  - entrada de audio habilitada;
  - `E:` saudavel e nao dirty;
  - sem arquivo temporario de credencial.

## 2026-06-12 - Checkpoint 33 concluido na VM

- Python 3.12 e as dependencias do bundle foram instalados no convidado.
- O Windows Update do primeiro boot foi aguardado ate a area de trabalho e o
  Guest Additions ficarem estaveis.
- O endpoint padrao do host foi trocado temporariamente para o conjunto
  interno Intel Smart Sound antes de iniciar a VM.
- Uma sonda direta confirmou amostras nao nulas no dispositivo fisico da VM.
- O controle sintetico produziu 440,08 Hz, pico 0,25, 500 blocos aceitos, 471
  consumidos e zero overruns.
- O bypass aquecido processou 478 blocos com media de 0,464 ms e sem blocos
  acima do orcamento de 20 ms.
- O STFT principal processou 484 blocos com media de 9,772 ms e p95 de
  18,656 ms; 125 blocos foram consumidos pelo endpoint virtual.
- A latencia total do STFT foi registrada como estimativa de 72 ms, nao como
  medicao fisica ponta a ponta.
- Tres ciclos estabilizados consumiram 244, 223 e 187 blocos.
- Todos terminaram com `write_errors=0`, zero overruns e zero erros de
  sequencia.
- Os WAVs finais possuem amostras nao nulas, mas o nivel do microfone estava
  muito baixo; a etapa valida conectividade, nao qualidade perceptual.
- O polling WASAPI consumiu abaixo da producao em alguns trechos. A fila
  local descartou blocos antigos para limitar latencia, sem overrun no
  driver.
- Evidencias:
  `resultados/sysvad_checkpoint33/host_mic_rerun_20260612/`.
- Snapshot final: `checkpoint33-functional-validated`.
- Estado final:
  - VM em `poweroff`;
  - snapshot UUID `575f66ee-78fd-4fe3-a6db-c698e88d8c0e`;
  - volume `E:` saudavel, `OK` e nao dirty;
  - SteelSeries Sonar restaurado como captura padrao do host;
  - arquivo temporario de credencial removido.

## 2026-06-12 - Checkpoint 34 concluido

- A estimativa de latencia do modo virtual foi corrigida para incluir a fila
  local e a profundidade observada no driver.
- `BridgePacedWriter` passou a registrar taxas, residencia, profundidades,
  idade dos descartes e descarte no timeout de encerramento.
- O encerramento ganhou limite de drenagem para nao manter thread e fila
  indefinidamente quando o consumidor para.
- Foi criado um sinal deterministico no VB-Audio Virtual Cable, com pico
  `0,10` e RMS `0,026197`.
- A matriz valida comparou profundidades 1, 2 e 4, sempre com fila local 4:
  - profundidade 1: 326 underruns e `181,50 ms`;
  - profundidade 2: 56 underruns e `182,36 ms`;
  - profundidade 4: 24 underruns e `201,57 ms`.
- Profundidade 2 foi escolhida como compromisso entre continuidade e atraso.
- Os defaults passaram a `target_driver_depth=2` e
  `user_queue_blocks=4`.
- Uma segunda matriz de fila local foi invalidada por uma pausa de varios
  minutos no Guest Control, que fez o capturador terminar antes do produtor.
  O JSON com zero consumo e `input overflow` nao foi usado.
- Suite final: `55 passed`, `11 subtests passed`.
- O delta experimental foi descartado e o snapshot final limpo
  `checkpoint34-latency-validated` foi criado com UUID
  `a4354c01-6d82-4ed5-ae68-e613acdd75b3`.
- Estado final: VM desligada, `E:` saudavel e nao sujo, endpoint SteelSeries
  Sonar restaurado.
- Foram preparados:
  - `prompt_continuidade_checkpoint35_interface_controle.md`;
  - `mensagem_novo_chat_checkpoint35.md`;
  - o proximo chat deve implementar a UI minima sem alterar driver, protocolo
    ou parametros DSP congelados.

## 2026-06-12 - Checkpoint 35 concluído

- Antes do boot, `E:` foi confirmado como `TOSHIBA EXT`, NTFS, `Healthy`,
  `OK` e não sujo.
- A VM estava em `poweroff`, com `audio_in=on` e snapshot atual
  `checkpoint34-latency-validated`.
- Foi criado o snapshot `checkpoint35-pre-control-ui`, UUID
  `a2242464-5d2e-4071-b65a-430e8e42ebe1`, antes da cópia do bundle.
- A interface foi implementada em `tkinter`, com controlador separado,
  snapshots imutáveis, persistência fora do repositório e encerramento
  limitado.
- O host abriu a UI sem driver e informou endpoint desconectado sem crash.
- A suíte final passou com `62 passed` e `11 subtests passed`.
- A resolução 800×600 da VM revelou compressão do quadro de métricas. Os
  espaçamentos foram reduzidos e todos os contadores ficaram visíveis.
- A automação por `MainWindowHandle` falhou porque o processo do Guest Control
  não enxergava o handle da janela interativa. A validação visual foi movida
  para atalhos enviados pelo console do VirtualBox.
- Na VM:
  - três ciclos iniciar/parar foram concluídos;
  - o medidor respondeu em torno de `-96 dBFS`;
  - o primeiro ciclo mostrou 329 blocos processados, 311 enviados, 15
    descartes locais, 76 underruns, zero overruns e zero erros de escrita;
  - a estimativa mostrada foi `184,6 ms`;
  - o cliente externo recebeu 352.000 frames e 11.150 amostras não nulas;
  - o WAV privado foi removido após gerar o resumo numérico;
  - fechar durante processamento encerrou a janela e o processo;
  - a reabertura preservou entrada `1` e agressividade `1,8`;
  - outro produtor causou `[WinError 170] Recurso solicitado em uso`, exibido
    como estado de erro controlado.
- O desligamento do Windows foi solicitado normalmente, mas o VirtualBox
  marcou a instância como `aborted` após a criação do snapshot final.
- O snapshot `checkpoint35-control-ui-validated`, UUID
  `17eae767-97b4-4b16-89ba-6e4af54310f0`, foi restaurado imediatamente.
- Estado final confirmado: VM em `poweroff`, snapshot funcional atual,
  `audio_in=on`, `E:` saudável e não sujo.

## 2026-06-12 - Checkpoint 36 concluído

- A auditoria inicial confirmou `E:` como `TOSHIBA EXT`, NTFS, saudável,
  operacional e não sujo.
- A VM estava desligada no snapshot
  `checkpoint35-control-ui-validated`, com `audio_in=on`.
- O endpoint `Microfone (USB Audio Device)` foi correlacionado ao descritor
  USB `HyperX Quadcast`, `VID_098C&PID_16DF`.
- A captura padrão do host foi trocada temporariamente pelo ID do HyperX.
- Foi criado o snapshot `checkpoint36-pre-hyperx-acoustic`, UUID
  `c2c8b093-0b58-4053-8df1-a66d7abcb4c8`.
- A VM mapeou o HyperX para a entrada MME observada no índice 1. O índice foi
  apenas registrado, não usado como identidade permanente.
- A sonda física válida obteve pico de fala `-12,52 dBFS`, RMS de fala
  `-32,55 dBFS`, RMS de silêncio `-73,99 dBFS` e zero clipping.
- O cenário limpo preservou um par simultâneo bruto/processado, com picos
  `-7,14/-7,20 dBFS` e zero clipping.
- O cenário com ruído marrom usou telefone a 35 cm, volume `100/150`, e boca
  a 20 cm. A redução no trecho de ruído sem fala foi `2,75 dB RMS`.
- Os gravadores começaram em instantes diferentes. Os pares privados foram
  alinhados pelo envelope apenas para comparação; o deslocamento não foi
  interpretado como latência física.
- Uma tomada com o mute físico do HyperX acionado foi explicitamente
  invalidada para medição de piso acústico.
- A estabilidade durou 630 s e terminou com 27.638 blocos processados,
  23.143 enviados, 4.491 descartes locais, 10.626 underruns, zero overruns,
  zero erros de escrita e zero processos residuais.
- Na escuta A/B privada, o bruto foi claramente preferido nos dois cenários.
  A voz foi considerada natural e inteligível, mas houve pipocos nos dois
  caminhos, muito mais severos no processado.
- As notas foram:
  - limpo: `4, 4, 5, 2, 1`;
  - ruidoso: `4, 3, 5, 2, 1`;
  - ordem: inteligibilidade, redução, naturalidade, ausência de artefatos e
    preferência, com `1=A` e `5=B`.
- Os WAVs foram autorizados e preservados fora do repositório. Somente hashes,
  formatos, durações e métricas foram registrados no projeto.
- Todo áudio e temporário do Checkpoint 36 foi removido da VM antes do
  desligamento.
- A suíte passou com `62 passed`, `11 subtests passed`; `compileall` também
  passou.
- O Windows convidado desligou normalmente em `poweroff`.
- Snapshot final:
  `checkpoint36-hyperx-acoustic-validated`, UUID
  `95b7a812-c34c-4967-9c7c-15415a31b980`.
- SteelSeries Sonar foi restaurado como captura padrão do host.
- Estado final: VM desligada, `audio_in=on`, `E:` saudável e não sujo, host
  sem dispositivo, serviço ou certificado SYSVAD/PTC.
- Classificação adotada:
  **Protótipo funcional, com validação perceptual pendente**.

## 2026-06-12 - Checkpoint 37 interrompido pela automação da VM

- A auditoria inicial confirmou `E:` saudável, operacional e não sujo, VM
  desligada, `audio_in=on`, HyperX presente e ausência de credenciais
  temporárias.
- Foi criado o snapshot `checkpoint37-pre-pop-diagnostics`, UUID
  `e47138eb-df0d-4d27-9948-e17503b7cc25`.
- O padrão final solicitado para o host passou a ser o HyperX direto:
  `Microfone (USB Audio Device)`, sem SteelSeries Sonar.
- Foram implementados detector de continuidade, telemetria de callbacks,
  rastreamento da ponte, polling configurável, progresso atômico e fonte
  determinística contínua.
- A instrumentação sintética passou nos testes focados.
- A VM enumerou a entrada virtualizada como
  `Microfone (High Definition Audio Device)`, WASAPI, índice observado 33.
  O índice foi apenas registrado.
- A captura bruta não produziu WAV nem métricas. As tentativas seguintes
  mostraram sessões do Guest Control presas em `starting` e erros
  `VERR_TIMEOUT`.
- Uma pasta compartilhada temporária preservou evidências parciais e
  screenshots, mas não resolveu a execução.
- A injeção de teclado do VirtualBox não dispensou a tela de bloqueio da VM,
  inclusive após Enter, Espaço e `Ctrl+Alt+Del`.
- Nenhuma voz foi solicitada ou gravada. A STFT, o protocolo PCM v1 e o driver
  não foram modificados para mascarar a falha.
- Como não houve captura válida, não foi testada mitigação nem criada
  conclusão sobre a fronteira dominante dos pipocos.
- Estado final: VM restaurada e desligada no snapshot pré-diagnóstico, pasta
  compartilhada removida, HyperX direto como padrão, `E:` não sujo.

## 2026-06-12 - Checkpoint 37 retomado interativamente

- Foi criado o clone consolidado `PTC3527-SYSVAD-LAB-FAST` no SSD interno,
  preservando integralmente a VM histórica e sua árvore de snapshots em `E:`.
- O segundo boot do clone atingiu Guest Additions em 73,9 s.
- A matriz foi executada manualmente na sessão gráfica, sem Guest Control.
- A entrada WASAPI observada no índice 33 rejeitou 16 kHz com
  `Invalid sample rate`. A entrada MME observada no índice 1 foi usada nas
  rodadas válidas, coerente com os checkpoints anteriores.
- Captura bruta, bypass pré-ponte e STFT pré-ponte ficaram livres de falhas
  objetivas de continuidade.
- A STFT pré-ponte teve p95 de `5,594 ms` e pior bloco de `13,825 ms`.
- A matriz do endpoint confirmou correlação entre silêncio inserido,
  descartes locais e underruns.
- No bypass, polling de 2 ms reduziu descartes locais de 97 para 26, underruns
  de 17 para 5 e zeros excedentes de 90 para 22.
- Na STFT, polling de 2 ms reduziu underruns, mas não melhorou descartes e
  zeros excedentes de forma consistente nesta repetição.
- Nenhuma voz foi gravada. Driver, protocolo PCM v1 e STFT permaneceram
  inalterados.
- O HyperX foi restaurado como captura padrão; sinais controlados foram
  encerrados; clipboard e pasta compartilhada transitória foram desabilitados.
- As duas VMs terminaram em `poweroff`; `E:` terminou saudável e não sujo.
- O clone rápido foi selado no snapshot
  `checkpoint37-pop-diagnostics-validated`, UUID
  `f3f72efa-0aed-41db-b444-4fa06f1afd62`.

## 2026-06-13 - Checkpoint 38 concluído

- Três pares STFT de 60 s alternaram polling de 10 ms e 2 ms.
- Em 10 ms, o agregado foi 8.899 enviados, 95 descartes locais, 72 underruns
  e 97 zeros excedentes.
- Em 2 ms, o agregado foi 8.972 enviados, 20 descartes locais, 54 underruns e
  25 zeros excedentes.
- A melhoria de underruns com 2 ms ocorreu nos três pares.
- Uma tomada privada de 20 s com HyperX foi autorizada e executada.
- A tomada terminou com 998 blocos, 960 enviados, 34 descartes locais, 4 no
  fechamento, 21 underruns e zero overruns, erros de escrita ou sequência.
- O p95 do DSP foi `6,017 ms`; o pior bloco foi `18,636 ms`.
- Na escuta A/B, o bruto foi preferido. Os pipocos desapareceram nos dois
  caminhos, mas houve travamentos de início/fim, e o processado apresentou
  mais ruído de fundo e chiado.
- Notas do processado: inteligibilidade `4/5`, naturalidade `4/5` e ausência
  de artefatos `2/5`.
- Os WAVs ficaram somente na área privada do host e foram removidos da VM.
- Guest Control foi novamente validado no clone SSD, com resposta em cerca de
  7 s, e deve substituir a operação manual por comandos fragmentados.
- Snapshot final:
  `checkpoint38-poll2-hyperx-validated`, UUID
  `e74ea911-08a6-4778-a7a2-a5a4ab191480`.
- Estado final seguro confirmado; classificação mantida como
  **Protótipo funcional, com validação perceptual pendente**.

## 2026-06-13 - Checkpoint 39 concluído

- Foi criado um orquestrador host/guest completo com bundle validado por hash,
  watchdog, progresso e coleta automática.
- A fonte determinística segmentada usou silêncio, ruído de semente fixa e
  multiton modulado, sem voz.
- O modo `headless` desacelerou a captura MME. Uma sonda em frontend GUI
  produziu 498 callbacks em 10 s; a matriz passou a usar GUI, ainda totalmente
  operada por Guest Control.
- Foram concluídos três pares `bypass`/STFT de 30 s.
- A saída STFT pré-bridge não introduziu o chiado: reduziu a energia de
  4–8 kHz em `4,12 dB` e o piso total em `1,72 dB`.
- O endpoint STFT elevou 4–8 kHz em `4,00 dB` e o piso total em `15,66 dB`
  contra o pré-bridge.
- A análise exploratória mostrou elevação agregada depois do pré-bridge, mas
  uma revisão causal posterior concluiu que o alinhamento e as janelas usadas
  não permitem localizar o chiado percebido durante fala.
- O par privado do Checkpoint 38 foi reutilizado sem nova gravação. O B
  processado apresentou início ativo aproximadamente 1,82 s depois de A e
  final ativo aproximadamente 1,30 s depois.
- Foram preparados pares privados de corte comum e fade de 80 ms em
  `C:\PTC3527-Private\checkpoint39_edge_ab`.
- Na escuta privada, o corte comum removeu o travamento de início/fim. O fade
  não trouxe melhora adicional. O chiado de B continuou durante a fala e A
  permaneceu preferido.
- A matriz publicou `RESULT=OK`, mas o shutdown imediato rompeu a sessão
  Guest Control e gerou erro vazio. Uma nova sessão retornou
  `VERR_DUPLICATE`.
- Uma revisão pelo Claude CLI, via assinatura Pro e esforço `high`, confirmou
  que o desligamento deve ser validado por `VMState`, não pelo exit code da
  sessão que ele encerra.
- ACPI não respondeu no estado órfão; o desligamento normal foi disparado por
  teclado virtual do VirtualBox, sem intervenção manual.
- Snapshot final:
  `checkpoint39-quality-boundary-validated`, UUID
  `21ad4f02-4dfa-48d1-b683-7a6e7b502160`.
- `30 passed`; HyperX padrão; VM original intocada; `E:` saudável e não sujo.
- Após o retorno perceptual, uma segunda revisão pelo Claude CLI questionou a
  atribuição causal ao pós-bridge. A métrica anterior usava janelas de ruído
  para explicar chiado durante fala, com alinhamento global apesar de perdas
  não uniformes.
- A conclusão foi corrigida: `musical noise` pré-bridge, drops, underruns,
  endpoint e captura externa permanecem hipóteses abertas.
- O Checkpoint 40 deve começar por escuta raw/pré-bridge/endpoint e
  correspondência exata por ID de bloco, antes de qualquer mitigação.

## 2026-06-13 - Checkpoint 40, parte objetiva concluida

- A tomada privada do Checkpoint 38 foi reutilizada sem nova gravacao.
- O trio `raw`, pre-bridge e endpoint recebeu o mesmo corte de 16,86 s, sem
  fade, em `C:\PTC3527-Private\checkpoint40_threeway`.
- A fonte interna identificavel por bloco preservou a cadencia MME e eliminou
  a dependencia de um lag global.
- A ponte publicou listas exatas de blocos enviados, descartados e abandonados
  no fechamento, alem da sequencia PCM de cada envio.
- Blocos recuperados no endpoint apresentaram correlacao mediana praticamente
  unitaria e erro abaixo de `-95 dBFS`.
- A STFT aumentou a densidade de picos tonais durante atividade antes da
  ponte, enquanto o transporte concentrou defeitos em perdas e lacunas.
- `drop-newest` reduziu underruns, mas duplicou descartes e piorou a
  preservacao recuperada. A politica foi rejeitada.
- Todo audio deterministico foi removido apos a publicacao de hashes e
  metricas.
- Snapshot final:
  `checkpoint40-transport-separated-validated`,
  UUID `693e8851-f905-4e98-b526-671c904965e9`.
- `81 passed`, `11 subtests passed`.
- Na escuta humana do trio:
  - A bruto foi considerado perfeito e sem chiado;
  - B pre-bridge apresentou chiado metalizado leve exatamente durante a voz;
  - C endpoint apresentou chiado metalizado consideravelmente mais forte,
    tambem durante a voz.
- O ambiente da gravacao bruta era silencioso, tornando ruido original da
  tomada uma explicacao implausivel.
- A fronteira perceptual foi fechada como:
  `origem no DSP com agravamento no caminho posterior`.
- O proximo passo deve primeiro reduzir o `musical noise` pre-bridge com a
  tomada privada existente e, depois, verificar se a mesma reducao permanece
  no endpoint diante de perdas e lacunas. Nenhuma nova voz deve ser solicitada
  antes de existir uma variante objetiva pareada.

## 2026-06-13 - Checkpoint 41 concluido

- Foi escolhida uma unica familia conservadora: suavizacao temporal causal do
  ganho espectral.
- O processador offline usou o mesmo `CausalSTFTProcessor`, em blocos de
  20 ms, sobre a tomada privada integral do Checkpoint 38.
- O corte de 16,86 s foi aplicado somente depois do processamento, preservando
  aquecimento e estado causal.
- A reproducao do baseline contra o B pre-bridge congelado atingiu correlacao
  `0.99999199` e erro RMS `-76.98 dBFS`.
- Coeficientes de `0.50`, `0.70`, `0.85` e `0.93` reduziram picos tonais em
  apenas `0.36%`, `1.28%`, `1.82%` e `2.91%`.
- A suavizacao forte causou perdas crescentes de envelope, energia e banda
  alta; nenhuma variante passou o gate objetivo.
- Nenhum WAV A/B foi criado e nenhuma escuta foi solicitada.
- A opcao `gain_smoothing` foi integrada ao caminho realtime com default zero,
  sem alterar o baseline.
- A VM validou compilacao e comportamento deterministico sem captura de audio.
- Suite: `84 passed`, `11 subtests passed`.
- Snapshot final:
  `checkpoint41-musical-noise-limit-validated`,
  UUID `12ea0826-47f6-48c1-a1b1-2701f000e19a`.
- Proximo passo: avaliar o Wiener causal existente como mudanca de metodo
  pre-bridge, ainda offline e com a mesma tomada privada.

## 2026-06-13 - Checkpoint 42 concluido

- O baseline congelado foi comparado offline ao `stft_wiener` causal.
- Foram variados somente os pisos `0.02`, `0.05`, `0.08` e `0.10`.
- O processamento preservou o aquecimento causal e aplicou o corte somente
  depois da tomada integral.
- O Wiener aumentou a flatness mediana em cerca de 15%, preservou envelope
  acima de `0.9965` e ficou mais proximo da energia do bruto.
- A reducao de densidade tonal ficou limitada a `1.90%` ate `2.13%`.
- Nenhuma variante passou o gate de 10%; nenhum WAV de escuta foi criado.
- Nao houve escuta humana nem ensaio ponta a ponta.
- A VM executou os quatro pisos deterministicamente com fonte sintetica sem
  voz e teve seus temporarios removidos.
- O app persistente da VM ainda usa a assinatura anterior, sem
  `gain_smoothing`; a divergencia foi registrada sem alterar o app.
- Suite: `84 passed`, `11 subtests passed`.
- Snapshot final:
  `checkpoint42-wiener-limit-validated`,
  UUID `b9909e84-c1d7-4948-9c5f-21870ff57f69`.
- Proximo passo: comparar offline o `wavelet_soft` causal existente, ainda
  antes da ponte e com a mesma tomada privada.

## 2026-06-13 - Checkpoint 43 concluido

- O `wavelet_soft` foi executado pelo mesmo `RealtimeBlockProcessor` usado na
  captura Windows.
- A janela causal usou 512 amostras de historico mais o bloco corrente de 320
  amostras.
- Foram comparados niveis 3, 4 e 5 com `db4`, soft, estrategia global e escala
  1.0.
- A reducao tonal variou de `6.74%` a `8.34%`, abaixo do gate.
- Todos os niveis removeram cerca de `10.5 dB` adicionais em 4-8 kHz e foram
  rejeitados por abafamento.
- Nenhum WAV de escuta foi criado; nao houve escuta nem ensaio ponta a ponta.
- Host e VM emitiram aviso interno do PyWavelets para coeficientes nulos; o
  saneamento realtime manteve as saidas finitas.
- A VM validou determinismo e teve os temporarios removidos.
- O desligamento normal terminou marcado como `aborted` pelo VirtualBox; a
  restauracao do snapshot terminal descartou o delta e normalizou `poweroff`.
- Suite: `84 passed`, `11 subtests passed`.
- Snapshot final:
  `checkpoint43-wavelet-limit-validated`,
  UUID `2a530e40-1981-4321-839f-88060d78cc2c`.
- Proximo passo: reduzir somente a escala do limiar Wavelet, inicialmente
  offline, antes de expor qualquer parametro novo no app.

## 2026-06-13 - Checkpoint 44 concluido

- A avaliacao manteve `db4`, nivel 3, soft, estrategia global e a mesma janela
  causal.
- Escalas `0.10`, `0.25`, `0.50` e `0.75` foram testadas apenas offline.
- `0.10` preservou melhor a banda media, mas reduziu picos em apenas `4.07%` e
  ainda perdeu `1.93 dB` em 4-8 kHz.
- `0.50` foi a unica escala acima do gate tonal, com `10.13%`, mas perdeu
  `2.42 dB` em 2-4 kHz e `7.64 dB` em 4-8 kHz.
- Nenhuma escala passou todos os gates; nenhum WAV de escuta foi criado.
- O parametro nao foi exposto no `RealtimeConfig` nem implantado no app.
- A VM validou o nucleo offline com fonte sintetica e removeu temporarios.
- Suite: `84 passed`, `11 subtests passed`.
- Snapshot final:
  `checkpoint44-wavelet-threshold-limit-validated`,
  UUID `3024cc30-6a67-436b-9154-36d3b57529c8`.
- A auditoria confirmou que `wavelet_packet_wiener_frames` continua offline e
  nao causal, pois calcula ganhos depois de observar todos os quadros.
- Proximo passo: implementar e provar uma WPT causal/rolante somente com
  vetores sinteticos antes de reutilizar voz privada.

## 2026-06-13 - Checkpoint 45 concluido

- Criado `benchmark_audio/causal_wpt.py` com estado causal explicito.
- O ganho atual usa apenas potencias de quadros anteriores; a potencia atual
  entra no historico depois da saida.
- Foram adicionados sete testes focados, todos aprovados.
- Em fonte sintetica, a WPT ficou proxima da STFT em SNR e produziu menos
  picos tonais, com custo e memoria muito menores.
- Como todos os gates sinteticos passaram, a configuracao foi congelada antes
  de uma unica avaliacao objetiva privada.
- Na tomada autorizada, a WPT reduziu picos em `11.72%`, preservando bandas,
  envelope e energia.
- Nenhum WAV de escuta foi criado e nenhuma integracao ocorreu.
- Suite total: `91 passed`, `11 subtests passed`.
- VM: `2.74 ms` medios por bloco, 2.144 bytes de estado, sem voz.
- Snapshot:
  `checkpoint45-causal-wpt-validated`,
  UUID `2255a9ed-2bb7-43c5-8b2c-5d10a70c140d`.
- Proximo passo: um unico par privado A/B pre-bridge no Checkpoint 46.

## 2026-06-13 - Checkpoint 46 preparado para escuta

- A tomada integral autorizada foi processada novamente com o baseline STFT
  causal e a WPT causal congelada.
- O processamento ocorreu antes do corte para preservar todo o estado causal.
- Foi preparado fora do repositorio um unico par pre-bridge de 16,86 s,
  mono PCM16 a 16 kHz, sem fade e sem normalizacao.
- Os dois arquivos possuem 269.760 amostras e 539.564 bytes cada.
- Hashes:
  - baseline:
    `8e959dcc22566872464b2ac5a7f7baa2060cd6156f37eeabbd35a0ed50217422`;
  - WPT:
    `1143240aa5bcfa8ab0eb06045f289ce20c5ee263e5ae171f32c9f063c007d325`.
- Testes focados do preparador e da WPT: `9 passed`.
- Nenhuma VM, ponte, aplicacao ou captura de endpoint foi iniciada.
- Estado: aguardando escuta privada para decidir entre integracao no
  Checkpoint 47 e encerramento tecnico da trilha DSP.

## 2026-06-13 - Checkpoint 46 concluido

- Resultado da escuta privada:
  - inteligibilidade: baseline `A`;
  - naturalidade: baseline `A`;
  - menor chiado metalizado: baseline `A`;
  - preferencia geral: baseline `A`.
- Decisao explicita: rejeitar a WPT causal `B`.
- A reducao objetiva de picos tonais nao produziu beneficio auditivo nesta
  tomada; o baseline continuou mais inteligivel, natural e menos metalizado.
- Nenhuma integracao foi autorizada e nenhum ensaio ponta a ponta foi
  executado.
- O Checkpoint 47 foi cancelado e a trilha DSP foi encerrada.
- O par privado foi removido depois da decisao; hashes e metadados foram
  preservados.
- Fechamento tecnico:
  **prototipo funcional integrado, sem melhoria perceptual aprovada do DSP**.

## 2026-06-13 - Checkpoint 46-R reaberto

- O usuario autorizou reabrir a investigacao cientifica depois da rejeicao do
  primeiro `B`.
- A evidencia anterior foi preservada: WPT causal continua rejeitada.
- Claude Code 2.1.177 foi invocado em modo de planejamento somente leitura.
- Foram realizadas tres rodadas de analise e contraditorio tecnico.
- O parecer externo priorizou estimador e ganho STFT, mas a primeira proposta
  continha erros sobre piso espectral, flatness e desenho fatorial.
- As objecoes foram devolvidas e aceitas pelo Claude.
- Plano consolidado:
  - `E0`: quantil 0.22 e atualizacao 0.30;
  - `E1`: quantil 0.35 e atualizacao 0.40;
  - `S02`: subtracao alpha 1.5, piso 0.02;
  - `S05`: subtracao alpha 1.5, piso 0.05;
  - `W05`: Wiener, piso 0.05;
  - total de seis configuracoes.
- A selecao usara gates de nao regressao e fronteira de Pareto, sem colapsar a
  decisao em SNR.
- Novos cortes privados somente serao gerados depois de configuracoes
  congeladas.
- Clone e VM original permaneceram desligados; nenhum codigo DSP foi alterado.

## 2026-06-13 - Ensaio publico 46-R concluido

- Criado `benchmark_audio/run_checkpoint46r_stft.py`.
- A matriz causal executou seis bracos em 72 condicoes de validacao.
- Uma primeira execucao revelou referencia incorreta dos gates de envelope e
  banda contra a fala limpa; o protocolo foi corrigido para medir preservacao
  contra a entrada ruidosa, mantendo SNR, SI-SDR e distancia espectral contra
  a fala limpa.
- O gate absoluto de envelope passou a ser aplicavel somente quando o proprio
  baseline publico atinge 0.975; o gate relativo permaneceu obrigatorio.
- Resultado final:
  - nenhum desafiante elegivel;
  - `E1-S02` e `E1-S05` melhoraram medias, mas degradaram 8,33% das condicoes;
  - Wiener reduziu tonalidade, mas perdeu SI-SDR de forma substancial;
  - `E1-W05` permaneceu apenas como hipotese limítrofe.
- Claude Code revisou as tabelas e recomendou honrar a parada, evitando
  relaxamento post-hoc dos gates.
- Suite final: `99 passed`, `11 subtests passed`.
- Nenhuma VM foi iniciada, nenhum WAV foi produzido e nenhuma voz privada foi
  reutilizada.

## 2026-06-13 - Inicio do benchmark de literatura do Checkpoint 46-R

- O novo protocolo foi separado da varredura STFT encerrada.
- Criados:
  - `benchmark_audio/literature_harness.py`;
  - `benchmark_audio/run_literature_benchmark.py`;
  - `tests/test_literature_harness.py`;
  - `docs/plano_benchmark_literatura_checkpoint46r.md`.
- O contrato comum registra taxa nativa, framing, causalidade, licenca,
  revisao, latencia e backend.
- As misturas canonicas de 16 kHz recebem SHA-256 dos bytes `float32`
  little-endian.
- A ordem congelada ficou:
  baseline, OM-LSA/IMCRA, RNNoise, WebRTC APM e DeepFilterNet.
- SpeexDSP permanece reserva.
- GTCRN foi verificado como MIT, com checkpoints e implementacao streaming,
  mas nao entrou na primeira bateria.
- A maquina possui MSVC/CMake, PyTorch e ONNX Runtime; nao possui Rust nem
  `pystoi`.
- A revisao independente com Claude Code e Chrome foi tentada em modo de
  planejamento, mas a conta atingiu o limite de sessao ate 17h.
- Testes focados iniciais: `20 passed`.
- O baseline foi executado nas 72 condicoes de validacao sem gerar audio.
- O novo resumo reproduziu exatamente oito metricas do `E0-S02` anterior,
  incluindo SNR, SI-SDR, tonalidade, flatness, distancia espectral e envelope.
- Estado de memoria causal: `60.900 bytes`; latencia algoritmica registrada:
  `32 ms`.
- Nenhuma selecao foi realizada e o split final permaneceu bloqueado.
- Suite completa depois do primeiro incremento: `104 passed`,
  `11 subtests passed`.
- `pystoi 0.4.1` foi instalado e fixado em `requirements.txt`.
- No baseline, STOI medio caiu de `0,94269` para `0,92450`, variacao de
  `-0,01819`.
- O resultado foi registrado como evidencia complementar: ele nao desfaz os
  ganhos de SNR/SI-SDR nem autoriza decisao isolada por STOI.

## 2026-06-13 - OM-LSA + IMCRA integrado ao harness

- As equacoes e tabelas dos artigos originais de 2001 e 2003 foram verificadas
  antes da implementacao.
- Criado `benchmark_audio/omlsa_imcra.py` com:
  - nucleo espectral sequencial;
  - estimador IMCRA em duas iteracoes;
  - rastreamento de minimos em subjanela;
  - ganho OM-LSA geometrico;
  - camada WOLA Hamming 512/128.
- Criado `tests/test_omlsa_imcra.py`.
- O smoke em `DKITCHEN`, `-5 dB`, produziu:
  - SNR `+0,7088 dB`;
  - SI-SDR `+0,6461 dB`;
  - STOI `-0,00440`;
  - RTF `0,0354`.
- A matriz de 72 condicoes foi executada para baseline e OM-LSA/IMCRA.
- Resultado OM-LSA/IMCRA:
  - SNR medio `+0,8985 dB`;
  - SI-SDR medio `+0,8506 dB`;
  - STOI medio `-0,00499`;
  - densidade tonal media `11,5774`;
  - envelope medio `0,96008`;
  - RTF medio `0,0716`;
  - estado `57.568 bytes`;
  - zero degradacoes de SNR.
- Contra o baseline, houve menos supressao, melhor preservacao de STOI e
  envelope e menor tonalidade agregada.
- Em `OOFFICE`, a tonalidade media do OM-LSA/IMCRA ficou acima do baseline.
- Nenhum finalista foi congelado; a comparacao continua aberta.
- Claude Code com Chrome foi tentado novamente, mas o limite de sessao
  permaneceu ativo ate 17h.
- Suite depois da integracao: `112 passed`, `11 subtests passed`.

## 2026-06-13 - RNNoise 0.2 integrado ao harness

- Fontes clonadas em cache externo ao repositorio.
- A tag anotada `v0.2` resolve para o commit
  `904a876dce1f9ab8860c0a5000ed151f9f6eef58`.
- O modelo oficial `0b50c45` foi baixado da Xiph.
- Criados:
  - `scripts/native/rnnoise_adapter.c`;
  - `scripts/native/Build-RNNoiseAdapter.ps1`;
  - `benchmark_audio.literature_harness.RNNoiseAdapter`.
- O primeiro teste revelou corrupcao binaria porque stdin/stdout estavam em
  modo texto no Windows.
- O wrapper foi corrigido com `O_BINARY`; finitude e determinismo passaram.
- A medicao por impulso encontrou atraso total de `960` amostras a 48 kHz,
  equivalente a `20 ms`.
- A saida e deslocada somente para metricas pareadas; a latencia permanece
  registrada.
- Build final:
  - modelo SHA-256
    `4AC81C5C0884EC4BD5907026AAAE16209B7B76CD9D7F71AF582094A2F98F4B43`;
  - executavel SHA-256
    `6D35F2465B5A8C1E1E87F0F54418BFDF3F84D0105067E6204748987989ECF7CB`.
- Resultado nas 72 condicoes:
  - SNR `+9,3893 dB`;
  - SI-SDR `+9,3925 dB`;
  - STOI `-0,00769`;
  - densidade tonal `18,2612`;
  - envelope `0,79418`;
  - banda 4-8 kHz `-14,0928 dB`;
  - RTF wall `0,0247`;
  - pico de working set `9.388.032 bytes`.
- RNNoise nao degradou SNR, mas degradou STOI em `63,89%` das condicoes e
  preservou envelope >= 0,9 em apenas `48,61%`.
- Nenhum finalista foi selecionado.
- Suite apos RNNoise: `114 passed`, `11 subtests passed`.
- Depois das 17h, Claude Code foi tentado novamente:
  - com Chrome, expirou apos 10 min sem parecer;
  - sem Chrome, expirou apos 4 min sem parecer.
- Os processos filhos criados por essas duas chamadas foram encerrados; as
  sessoes Claude antigas do usuario foram preservadas.
- Nenhuma aprovacao externa foi inferida. A revisao independente permanece
  pendente antes do fechamento da bateria.

## 2026-06-13 - Correcao de fidelidade OM-LSA/IMCRA

- A auditoria direta das Eqs. 15 e 16 do artigo OM-LSA encontrou que `Gmin`
  representa o ganho hipotetico sob `H0`, nao um clipping do ganho condicional
  ou do ganho final.
- A auditoria do rastreamento `D=UV` encontrou uma subjanela excedente.
- Foram corrigidos:
  - clipping indevido de `GH1`;
  - clipping indevido do ganho geometrico final;
  - memoria de minimos para subjanela corrente mais `U-1` anteriores.
- A matriz dos tres sistemas foi repetida integralmente.
- Os novos valores OM-LSA/IMCRA substituem os anteriores:
  - SNR `+0,8985 dB`;
  - SI-SDR `+0,8506 dB`;
  - STOI `-0,00499`;
  - tonalidade `11,5774`;
  - envelope `0,96008`;
  - RTF `0,0716`.
- Baseline e RNNoise permaneceram numericamente inalterados nas metricas de
  qualidade.
- Suite: `115 passed`, `11 subtests passed`.

## 2026-06-13 - WebRTC APM Noise Suppression integrado ao harness

- O checkout oficial foi fixado no commit
  `eb79ac6e330baa0a6d26c53d522f9ed57495edb7`.
- `depot_tools` foi fixado em
  `30e761311cf7529a8b6b16233da46af5d26fba02`.
- O build Windows usou Visual Studio Community 2026 e Windows SDK local,
  sem baixar o toolchain privado do Google.
- Criados:
  - `scripts/native/webrtc_apm_ns_adapter.cc`;
  - `scripts/native/webrtc_apm_ns_BUILD.gn`;
  - `scripts/native/Build-WebRTCAPMAdapter.ps1`;
  - `benchmark_audio.literature_harness.WebRTCAPMNSAdapter`.
- Somente Noise Suppression foi habilitado. AEC, AGC, HPF e os demais
  modulos permaneceram desligados.
- O nivel oficial usado foi o padrao recomendado `moderate`. Uma execucao
  preliminar em `high` foi descartada antes do congelamento por nao seguir
  esse criterio.
- A API processa `float32` mono a 16 kHz em blocos de 160 amostras.
- O codigo oficial usa FFT 256/160; impulso em quatro posicoes confirmou
  atraso constante de 96 amostras, ou `6 ms`.
- Build final SHA-256:
  `D2FCB649518676BC0BD5951F1392F6BEB27023CEE97F5648D79AB5A572EB889C`.
- Resultado oficial nas mesmas 72 condicoes:
  - SNR `-3,5039 dB`;
  - SI-SDR `-14,6908 dB`;
  - STOI `-0,03274`;
  - densidade tonal `11,0088`;
  - envelope `0,75281`;
  - banda 4-8 kHz `-8,1681 dB`;
  - RTF wall `0,0060`;
  - pico de working set `8.237.056 bytes`;
  - degradacao de SNR em `73,61%` das condicoes.
- WebRTC APM foi rejeitado como finalista nesta configuracao oficial.
- Os quatro sistemas usaram os mesmos hashes nas 72 misturas.
- Suite completa: `117 passed`, `11 subtests passed`.
- Claude nao foi usado: a API, o build e a divergencia foram resolvidos por
  auditoria direta das fontes oficiais e testes locais.
- Split final, audio privado, endpoint e VM permaneceram bloqueados.

## 2026-06-13 - DeepFilterNet3 e congelamento dos finalistas

- DeepFilterNet foi fixado na tag `v0.5.6`, commit
  `978576aa8400552a4ce9730838c635aa30db5e61`.
- A wheel oficial `DeepFilterLib 0.5.6` para CPython 3.11/Windows foi usada em
  ambiente virtual isolado.
- O modelo DeepFilterNet3 da mesma tag foi congelado:
  - ZIP SHA-256
    `49C52EDC8947AE1F9BF50D81530BEAF3A2C3245AEAF34B6F31FF535CD22284D2`;
  - checkpoint SHA-256
    `23B92884F63CCF54BB026014604625AB231657B6480DF65DB4095C4C171E6003`;
  - `libdf` SHA-256
    `67D03591503315F7F5D5FA43B44CBBE504DB3D2FC557B0AF8C4D41F40ABD271C`.
- A configuracao oficial usa 48 kHz, FFT 960/480 e dois hops de lookahead.
- O wrapper materializa o atraso causal completo de 1.440 amostras, `30 ms`,
  confirmado por impulso.
- Resultado nas 72 condicoes:
  - SNR `+9,1978 dB`;
  - SI-SDR `+10,5105 dB`;
  - STOI `-0,06588`;
  - densidade tonal `17,1685`;
  - envelope `0,75312`;
  - banda 4-8 kHz `-23,2995 dB`;
  - RTF de inferencia `0,1087`;
  - RTF wall com carregamento por arquivo `1,0323`;
  - pico de memoria da arvore de processos `255.102.976 bytes`;
  - degradacao de SNR em 6 de 72 condicoes.
- DeepFilterNet foi rejeitado: RNNoise o supera em SNR, STOI, envelope,
  preservacao de bandas, latencia, RTF e memoria.
- Congelados no maximo permitido de dois finalistas:
  - RNNoise, extremo de supressao;
  - OM-LSA/IMCRA, extremo de preservacao.
- O baseline permanece referencia, nao finalista novo.
- Decisao gravada em
  `resultados/sysvad_checkpoint46_reopened/literature_benchmark/candidate_decision.json`.
- Suite: `119 passed`, `11 subtests passed`.
- Proximo gate liberado: split publico final operacional somente para
  baseline e os dois finalistas. Audio privado e VM ainda nao foram usados.

## 2026-06-13 - Confirmacao no split publico final operacional

- Foram executados somente:
  - baseline STFT;
  - RNNoise;
  - OM-LSA/IMCRA.
- As 72 condicoes finais usaram hashes identicos entre os tres sistemas.
- Nenhum WAV foi gerado e nenhum audio privado foi acessado.
- Resultado:
  - baseline: SNR `+3,7631`, SI-SDR `+2,6476`, STOI `+0,00005`,
    envelope `0,94220`;
  - RNNoise: SNR `+6,5684`, SI-SDR `+5,5728`, STOI `+0,01817`,
    envelope `0,83602`;
  - OM-LSA/IMCRA: SNR `+0,9349`, SI-SDR `+0,6896`, STOI `-0,00130`,
    envelope `0,94767`.
- RNNoise confirmou o extremo de supressao; OM-LSA/IMCRA confirmou o extremo
  de preservacao.
- Os dois finalistas permanecem congelados.
- Proximo gate: escuta privada cega pre-ponte com baseline como referencia.
- A VM continua proibida ate aprovacao perceptual.

## 2026-06-13 - Trio privado cego preparado

- A tomada privada autorizada do Checkpoint 38 foi reutilizada; nenhuma nova
  gravacao foi feita.
- O processamento ocorreu integralmente antes do corte comum para preservar o
  aquecimento causal.
- Sistemas no conjunto:
  - baseline STFT;
  - RNNoise;
  - OM-LSA/IMCRA.
- Foram gerados tres WAVs cegos `A`, `B` e `C`, mono PCM16 a 16 kHz, com
  `16,86 s` cada.
- Corte comum: amostras `28.160:297.920`.
- Nao houve normalizacao, fade, endpoint ou VM.
- A chave foi gravada apenas na area privada e nao foi aberta durante a
  verificacao.
- Resumo publico:
  `resultados/sysvad_checkpoint46_reopened/literature_benchmark/private_listening_summary.json`.
- Suite final: `121 passed`, `11 subtests passed`.
- Estado: `private_listening_pending`.

## 2026-06-13 - Resultado da escuta privada do benchmark de literatura

- O formulario foi validado antes da abertura da chave:
  - tres rotulos unicos;
  - ranks `1, 2, 3`;
  - escalas dentro de `1..5`;
  - nenhum clipping ou dropout reportado.
- Chave revelada:
  - `A = baseline_stft`;
  - `B = rnnoise`;
  - `C = omlsa_imcra`.
- Ranking:
  1. RNNoise;
  2. OM-LSA/IMCRA;
  3. baseline STFT.
- RNNoise recebeu inteligibilidade `5`, naturalidade `5`, artefatos `5` e
  foi o preferido. Foi percebido apenas ruido inicial leve.
- OM-LSA/IMCRA ficou muito proximo, com inteligibilidade e naturalidade `5`.
- O baseline apresentou som metalizado e chiado durante a fala, confirmando
  perceptualmente o problema que motivou a reabertura do Checkpoint 46-R.
- Decisao:
  **RNNoise aprovado como candidato de integracao**.
- OM-LSA/IMCRA permanece como reserva perceptual.
- A VM nao foi iniciada. O proximo passo e integrar e validar RNNoise no host
  pre-bridge antes de qualquer ensaio no endpoint.

## 2026-06-14 - RNNoise persistente validado no host pre-ponte

- A auditoria confirmou o contrato de 320 amostras mono a 16 kHz entre
  `RealtimeBlockProcessor` e a ponte PCM v1.
- Cada bloco vira exatamente 960 amostras a 48 kHz e dois frames RNNoise de
  480 amostras, sem fila fracionaria.
- Foi criada uma DLL em processo com estado RNNoise continuo, FIR causal de
  63 coeficientes em cada direcao, buffers fixos e operacoes `create`,
  `reset`, `process` e `destroy`.
- O primeiro prototipo Python com `scipy.signal.lfilter` foi substituido antes
  do gate porque ainda alocava arrays temporarios no callback.
- O build foi protegido para nao sobrescrever o executavel offline aprovado:
  `6D35F2465B5A8C1E1E87F0F54418BFDF3F84D0105067E6204748987989ECF7CB`.
- DLL usada no gate:
  `593D387801A7D0464D2F11449E43E466811DEAEB66C39E367085E28DAAB0F84C`.
- O atraso por impulso foi 341 amostras a 16 kHz, `21,3125 ms`, coerente com
  20 ms do RNNoise e `1,2917 ms` dos FIRs.
- O ensaio de 30.000 blocos, equivalente a 10 minutos, mediu media
  `0,8184 ms`, p95 `1,4240 ms`, p99 `1,9510 ms`, pior caso `18,2485 ms`,
  zero estouros de 20 ms e crescimento de RSS de `225.280 bytes`.
- Determinismo, causalidade, reset, encerramento e continuidade passaram.
- O smoke pela CLI corrigida mediu media `0,6206 ms`, p99 `0,9547 ms`, sem
  blocos repetidos ou descontinuidades de borda.
- Suite completa: `128 passed`, `11 subtests passed`.
- `VBoxManage list runningvms` retornou vazio; a VM permaneceu desligada.
- RNNoise esta disponivel por `--method rnnoise`, mas a UI e o padrao
  operacional permanecem em STFT ate o ensaio VM controlado.
- Claude nao foi usado: a API oficial, o codigo local e os testes resolveram
  as duvidas tecnicas deste incremento.

## 2026-06-14 - RNNoise integrado e medido na VM

- Foi criado um orquestrador reversivel em
  `scripts/vm/Invoke-RNNoiseIntegrationVm.ps1` e um executor convidado em
  `scripts/vm/guest/Invoke-RNNoiseIntegrationGates.ps1`.
- Cada sessao verificou snapshot, hashes, clipboard, VM original, volume
  `E:` e captura padrao; ao final limpou o convidado, desligou e restaurou o
  snapshot 45.
- Falhas intermediarias de automacao foram resolvidas sem mudar o produto:
  - espera de logon/Guest Additions;
  - separador de argumentos do `VBoxManage`;
  - `ExitCode` nulo no PowerShell 5.1;
  - nome MME truncado;
  - esquema real do JSON de metricas;
  - lock tardio do `VBoxSVC`;
  - sessao Guest Control orfa com `VERR_DUPLICATE`.
- O gate isolado final passou com controle bypass na mesma sessao.
- Duas matrizes deterministicas foram executadas na ordem pareada
  `bypass, RNNoise, RNNoise, bypass`.
- O RNNoise permaneceu abaixo de 20 ms no p99 de todos os cenarios.
- O transporte apresentou alta variancia entre repeticoes, mas nenhum erro de
  protocolo ou regressao pareada consistente.
- A captura fisica pareada mostrou o limite atual do laboratorio:
  a VM nao preserva tempo na entrada MME, entregando 13,36 s e 24,72 s em
  duas janelas nominais de 20 s.
- Nenhum arquivo privado foi versionado e nenhum WAV clipou.
- Claude nao foi usado; os sintomas foram resolvidos pelo historico local,
  pelas ferramentas do VirtualBox e pelos testes medidos.
- Proximo passo:
  estabilizar a cadencia de entrada fisica antes de gravar fala controlada ou
  realizar nova escuta cega ponta a ponta.

## 2026-06-14 - Auditoria MME, DirectSound e WASAPI na VM

- A investigacao foi iniciada sem alterar
  `realtime_audio/windows_realtime.py`.
- Foi criado um probe independente que registra:
  - tempo monotonic de entrada do callback;
  - `inputBufferAdcTime` e `currentTime`;
  - frames, status, pico e RMS;
  - tempo de processamento quando habilitado;
  - nenhum audio.
- A primeira matriz usou apenas captura, com 320 amostras a 16 kHz e ordem
  espelhada entre MME, DirectSound e WASAPI.
- WASAPI recusou 16 kHz no modo padrao do PortAudio. A opcao compartilhada
  `auto_convert=True` foi medida explicitamente, sem ser confundida com
  suporte nativo.
- Resultado da captura pura:
  - MME manteve o total proximo de 20 s, mas entregou pares de callbacks em
    rajadas separados por pausas;
  - DirectSound manteve o total, mas teve timestamps regressivos e uma pausa
    de `373,9 ms`;
  - WASAPI perdeu tempo nas duas pernas e teve pausa de `2,371 s`.
- Os relogios reportados pelo PortAudio nao sao utilizaveis:
  - MME alternou ADC entre `0` e `0,02 s` e repetiu `currentTime`;
  - DirectSound e WASAPI tiveram deltas negativos ou repetidos.
- Foi executada uma segunda matriz input-only em MME e DirectSound, na ordem
  pareada `bypass, RNNoise, RNNoise, bypass`.
- Em MME, a primeira perna RNNoise entregou `26,52 s` em 20 s, mas a segunda
  entregou `19,96 s`. Os p99 de processamento foram `2,015 ms` e
  `1,334 ms`, sem estouro sustentado.
- Em DirectSound, uma perna bypass passou `22,75 s` dentro do stream e
  entregou `19,82 s`, com callback parado por `3,092 s`.
- A variacao apareceu em bypass e RNNoise e nao acompanha custo de DSP.
- Fila local, fila do driver, capturador e endpoint ficaram ausentes; a causa
  foi localizada a montante dessas camadas.
- Duas tentativas de automacao falharam antes das matrizes:
  - separador de argumentos do `VBoxManage`;
  - array de um elemento no PowerShell 5.1 sob `StrictMode`.
  Ambas foram revertidas e nao integram a evidencia.
- Rodadas aceitas:
  - `20260614-000536-backend-cadence`;
  - `20260614-001439-workload-cadence`.
- A VM foi restaurada ao snapshot 45 depois de cada sessao.
- Decisao: nao abrir ponte, nao capturar fala e nao promover RNNoise.
- Proxima hipotese incremental:
  usar captura e pacing no host para fornecer ao convidado blocos PCM de
  320 amostras a 50 Hz por um canal de ensaio, provando antes comprimento,
  causalidade, ausencia de duplicacao e ausencia de perda.

## 2026-06-14 - Canal PCM cadenciado pelo host aceito

- Foi implementado `scripts/audio/host_guest_pcm_stream.py`, com framing
  explicito, sequencia, CRC e pacing absoluto de 20 ms.
- O convidado inicia a conexao para `10.0.2.2` pela NIC NAT existente.
- Foi criado um analisador independente para comprimento, integridade,
  pareamento, cadencia e causalidade por prefixo.
- Falhas iniciais ficaram restritas a automacao:
  - janela transitoria `The object is not ready` do VirtualBox;
  - separador `--` perdido na chamada Guest Control;
  - continuadores de linha removidos do comando remoto;
  - `ExitCode` vazio de `Start-Process`.
- Nenhuma dessas tentativas completou uma matriz e elas nao foram usadas como
  evidencia.
- O smoke de 5 s e a matriz nominal de 20 s foram aceitos.
- Na matriz nominal, cada uma das quatro pernas entregou 1.000 blocos.
- Os pares bypass/RNNoise tiveram hashes de entrada identicos e zero erro de
  sequencia, CRC ou framing.
- A causalidade foi confirmada por duas entradas com prefixo comum de 500
  blocos e futuro divergente.
- A maior pausa de recepcao foi `53,5155 ms`, seguida de compensacao; nenhum
  bloco foi perdido e a duracao final permaneceu 20 s.
- RNNoise ficou abaixo de 20 ms em todos os 2.000 blocos processados.
- A fila local, a fila do driver e o endpoint nao participaram.
- A VM foi limpa, desligada e restaurada ao snapshot 45 depois de cada
  sessao; a VM original e a captura padrao permaneceram inalteradas.
- Foi adicionado um modo de replay que le PCM somente no host e envia os
  mesmos blocos as duas pernas.
- O smoke desse modo usou 1 s de silencio sintetico privado, passou com hash
  pareado e teve o arquivo temporario removido.
- `capture_host_pcm.py` foi preparado para selecionar exatamente o microfone
  USB no WASAPI e salvar somente PCM privado com comprimento multiplo de 320.
- O formato PCM16/16 kHz foi aceito pelo host com conversao WASAPI explicita;
  nenhuma gravacao de microfone foi iniciada.
- Suite completa: `145 passed`, `11 subtests passed`.
- Proximo passo: gravar uma unica fala controlada pelo microfone USB no host,
  manter o PCM somente na area privada e reproduzir a mesma fonte nas pernas
  bypass e RNNoise antes de abrir a ponte.

## 2026-06-14 - Runbook de automacao consolidado

- Os incidentes recorrentes de operacao da VM foram consolidados em
  `docs/runbook_automacao_vm.md`.
- O runbook cobre:
  - separador literal `--` do Guest Control;
  - `EncodedCommand` e comandos remotos sem continuadores;
  - stderr de programas nativos sob `$ErrorActionPreference=Stop`;
  - `The object is not ready`;
  - espera de Guest Additions e logon;
  - sessoes orfas, `VERR_DUPLICATE` e `VERR_TIMEOUT`;
  - lock tardio do `VBoxSVC`;
  - colecoes de um elemento sob `StrictMode`;
  - variaveis PowerShell reservadas, incluindo `$Host`;
  - `ExitCode` nulo no PowerShell 5.1;
  - selecao de dispositivos, schema JSON, copia, shutdown e restauracao.
- A mensagem de continuidade do proximo gate foi criada em
  `mensagem_novo_chat_checkpoint46r_physical_endpoint.md`.

## 2026-06-14 - Auditoria historica de incidentes e economia de boots

- Os registros locais dos Checkpoints 31 a 46-R, scripts preservados,
  READMEs, diario, checkpoints, auditoria e mensagens de continuidade foram
  cruzados em `docs/historico_incidentes_vm.md`.
- As threads historicas disponiveis no Codex tambem foram lidas diretamente,
  incluindo Checkpoints 35, 38, 39, 40 e integracao RNNoise.
- A leitura dos chats acrescentou ao catalogo:
  - `shutdown.exe` com argumentos incorretos exibindo ajuda;
  - cliente `showvminfo` preso e lock do VirtualBox;
  - warm-up PowerShell de 53 s causando falso timeout;
  - processos graficos retendo handles da pasta implantada;
  - preservacao de matriz valida quando apenas o teardown falha;
  - geracao pesada no host competindo com a cadencia da VM;
  - ambiente virtual e line endings incorretos no fechamento.
- O catalogo separa:
  - infraestrutura e armazenamento;
  - Guest Control;
  - PowerShell 5.1 e programas nativos;
  - processos, timeouts e shutdown;
  - audio e interpretacao;
  - resultados, credenciais e privacidade.
- Foi criada uma matriz que distingue erros recuperaveis na mesma sessao dos
  casos que exigem shutdown e restauracao.
- O runbook passou a exigir preflight host-only, uma unica sessao GUI para
  cenarios pareados e recuperacao em sessao antes de considerar reboot.
- Foi criado `scripts/vm/Test-VmAutomationPreflight.ps1`, somente-leitura.
- O preflight foi executado contra `Invoke-HostPacedPcmVm.ps1` e passou com
  zero erros e zero avisos sem iniciar a VM.
- A auditoria de `%TEMP%` encontrou tres arquivos antigos de credencial, todos
  com 16 bytes, dos Checkpoints 39/RNNoise. O conteudo nao foi exibido; os
  tres arquivos foram removidos e a ausencia foi confirmada.
- O preflight passou a bloquear novos runs quando detectar arquivos
  temporarios de credencial conhecidos.
- Estado confirmado:
  - clone e VM original em `poweroff`;
  - snapshot `checkpoint45-causal-wpt-validated`;
  - `audio_in=on`;
  - clipboard e drag-and-drop desabilitados;
  - NIC NAT;
  - `E:` saudavel, operacional e nao sujo;
  - captura padrao `Microfone (USB Audio Device)`;
  - orquestrador parseavel, com separador literal e frontend GUI.

## 2026-06-14 - Fala controlada, replay e gate de endpoint

- A primeira tomada foi rejeitada porque a contagem regressiva nao estava
  visivel ao participante. O PCM privado teve RMS `-62,32 dBFS` e nao foi
  usado.
- Foi criada uma janela sempre no topo com `3, 2, 1`, aviso sonoro,
  `FALE AGORA`, cronometro e resultado final.
- A repeticao valida produziu:
  - 20 s, 320.000 amostras e 1.000 blocos;
  - pico `-14,16 dBFS` e RMS `-33,60 dBFS`;
  - zero clipping;
  - SHA-256
    `4938B14BFA3311CFF715A569AF6A5C51C5D6930FE05DDDD472F4F7D4E237A308`.
- Duas tentativas de replay falharam por automacao:
  - timeout de aceite do servidor host antes do inicio tardio do cliente;
  - Guest Control preso no estado `starting`.
- O orquestrador passou a usar timeout de 180 s, preservar tentativas,
  registrar sessoes/processos, executar `closesession --all` e retomar uma
  vez dentro do cenario.
- O replay fisico final passou com 1.000 blocos por perna, hashes de entrada
  identicos e zero erro de sequencia, CRC ou framing.
- A ponte PCM v1 foi aberta incrementalmente, mantendo profundidade 2 e fila
  local 4.
- O gate de endpoint foi rejeitado:
  - bypass: 569 enviados, 427 descartados na fila e 4 no fechamento;
  - RNNoise: 794 enviados, 202 descartados na fila e 4 no fechamento;
  - ambos sem erro de escrita, overrun, rejeicao ou sequencia;
  - WAVs privados de 24 s, mono PCM16/16 kHz e sem clipping.
- O consumidor do endpoint deixou de drenar a fila antes do fim em ambas as
  pernas. Como o bypass foi pior, o efeito nao foi atribuido ao RNNoise.
- Nenhuma chave cega foi criada e nenhuma escuta foi aberta.
- A VM foi desligada e restaurada ao snapshot 45 depois de cada sessao.

## 2026-06-14 - Migracao do runtime de automacao para o SSD

- A auditoria de armazenamento confirmou cerca de 130,5 GiB livres em `C:`.
- O clone rapido ja estava no SSD e a VM original ocupava cerca de 51,0 GiB
  no `E:`. A copia integral foi descartada por consumir espaco sem acelerar o
  caminho ativo.
- `scripts/vm/Initialize-VmSsdRuntime.ps1` criou
  `C:\PTC3527-Private\vm_runtime` com heranca de ACL removida.
- A pasta permite acesso somente ao usuario atual, `SYSTEM` e administradores.
- Foram copiados e conferidos por SHA-256 o XML de credencial e uma referencia
  `.vbox`, totalizando 137.525 bytes. O manifesto nao contem a senha.
- `VmSsdRuntime.ps1` passou a validar hashes, extrair a credencial e auditar a
  fonte externa apenas quando ela estiver disponivel.
- `Invoke-HostPacedPcmVm.ps1`, `Invoke-RNNoiseIntegrationVm.ps1`,
  `Invoke-InputCadenceBackendAuditVm.ps1` e o preflight deixaram de exigir
  `E:` para o fluxo ativo.
- A ausencia da fonte externa foi simulada sem desconectar o disco e retornou
  `external_source_unavailable`, mantendo o runtime local valido.
- Os tres preflights passaram com zero erros e zero avisos. A suite terminou
  com `150 passed`, `11 subtests passed`.
- Nenhuma VM foi iniciada e nenhum arquivo do `E:` foi alterado.

## 2026-06-14 - Diagnostico sincronizado do endpoint SYSVAD

- `PtcPcmCapture` passou a registrar por pacote hash, nivel e estatisticas da
  ponte PCM v1.
- A rodada `20260614-030118-host-paced-endpointdiagnostic` confirmou que a
  captura terminava cedo:
  - primeira atividade da ponte em `15.079 ms`;
  - fim da captura em `24.063 ms`;
  - somente `8.984 ms` de sobreposicao para uma fonte de 20 s.
- A aparente parada do consumidor era consequencia do fechamento antecipado
  do stream WaveRT, nao evidencia de stall persistente do driver.
- Foi implementada uma barreira cliente pronto -> captura pronta -> envio.
- A repeticao `20260614-031100-host-paced-endpointdiagnostic` obteve:
  - janela observada de `23.750 ms`;
  - 1.000 blocos submetidos;
  - 944 aceitos, 943 consumidos e profundidade final zero;
  - zero erro de escrita;
  - 56 descartes locais.
- Os descartes coincidiram com pausas transitorias:
  - lacuna maxima da captura de `329 ms`;
  - quatro lacunas acima de `100 ms`;
  - intervalo maximo de recepcao de `125,441 ms`.
- Classificacao:
  `transient_scheduling_pauses_with_queue_overflow`.
- Driver, protocolo PCM v1, profundidade alvo 2 e fila local 4 permaneceram
  inalterados.
- O clone foi restaurado ao snapshot 45; clone e VM original terminaram
  desligados.
- Uma consulta complementar ao Claude CLI foi tentada, mas expirou sem
  resposta e nao foi usada como evidencia.

## 2026-06-14 - Timer do convidado mitigado, cadencia WaveRT ainda limitada

- O preflight host-only passou antes de cada sessao com zero erros e zero
  avisos.
- Foi criada uma base QPC comum entre:
  - envio do host;
  - recepcao do cliente;
  - loop da `BridgePacedWriter`;
  - polls e pacotes do `PtcPcmCapture`;
  - heartbeat independente no convidado.
- Duas tentativas operacionais foram rejeitadas antes do primeiro cenario:
  - tres processos `VirtualBoxVM` impediram selecao por nome;
  - o host negou alteracao de `PriorityClass` sem elevacao.
- As duas tentativas terminaram com clone desligado e restaurado ao snapshot
  45; nao produziram evidencia experimental.
- Matriz MMCSS aceita:
  `20260614-034605-host-paced-endpointscheduling`.
- Resultado MMCSS:
  - controle normal: 59 descartes em 2.000 blocos;
  - MMCSS: 269 descartes em 2.000 blocos;
  - MMCSS rejeitado como mitigacao.
- A pausa maxima do escritor, `2,261 s`, ocorreu enquanto 113 pacotes TCP
  eram recebidos pelo thread principal.
- Os IOCTLs `GET_STATS` e `WRITE` permaneceram normalmente submilissegundo.
- Interpretacao refinada:
  - nao houve pausa global da VM;
  - threads e processos apoiados em timers de 2 ms sofreram wakeups tardios;
  - a recepcao orientada a evento continuou ativa.
- Matriz de timer aceita:
  `20260614-035359-host-paced-endpointtimer`.
- Trocar `Sleep(2 ms)` por yield ate o mesmo prazo de 2 ms reduziu:
  - descartes de 142 para 36;
  - lacunas do escritor acima de 30 ms de 56 para 1.
- As pernas yield ainda descartaram 17 e 19 blocos.
- Matriz de prefill aceita:
  `20260614-040101-host-paced-endpointprefill`.
- Um burst inicial de dois blocos, igual a profundidade alvo existente,
  reduziu 74 descartes de controle para 38, mas nao chegou a zero.
- Com yield, a thread escritora ficou regular, mas o driver consumiu blocos
  frescos a somente `48,55..49,20 Hz`, mantendo profundidade 2 em cerca de
  90% da janela.
- Classificacao final:
  `writer_wakeup_mitigated_consumer_cadence_deficit_remains`.
- O VirtualBox registrou fallback de VT-x direto para NEM/Windows Hypervisor
  Platform. A relacao causal com a cadencia restante ainda nao foi provada.
- Defaults preservados:
  - protocolo PCM v1;
  - profundidade 2;
  - fila local 4;
  - blocos de 320 amostras;
  - RNNoise nao promovido;
  - MMCSS, yield e prefill somente opt-in.
- Nenhum replay privado foi executado e nenhuma escuta foi aberta.
- Suite final: `158 passed`, `11 subtests passed`.
- Estado final confirmado:
  - clone desligado e restaurado ao snapshot 45;
  - VM original desligada;
  - audio input ligado;
  - clipboard e drag-and-drop desabilitados;
  - NIC NAT;
  - captura padrao do host inalterada.

## 2026-06-14 - Topologia de vCPU sob NEM/WHP

- A revisao de `minwavertstream.cpp` e `PtcPcmBridgeRing.h` mostrou que o
  timer WaveRT calcula deslocamento por QPC e consome bytes do ring.
- Quando faltam bytes, `PopBytes` preenche zeros e incrementa `Underruns`.
- O analisador foi corrigido para medir underruns apenas entre o primeiro e
  o ultimo bloco recebidos, evitando confundir a espera de prontidao com a
  janela experimental.
- Hipotese: reduzir vCPUs diminuiria pausas de escalonamento sob NEM/WHP.
- Tentativa de 2 vCPUs:
  - run `20260614-041534-host-paced-endpointprefill`;
  - boot nao alcancou Guest Additions ou rede em 723 s;
  - estatisticas do VirtualBox registraram zero byte de rede;
  - nenhuma perna foi iniciada;
  - configuracao rejeitada operacionalmente.
- Matriz de 3 vCPUs:
  - run `20260614-042924-host-paced-endpointprefill`;
  - boot, quatro cenarios, coleta e restauracao concluidos;
  - classificacao
    `three_vcpu_reduced_pauses_but_zero_drop_not_reached`.
- Grupo com prefill, 4 versus 3 vCPUs:
  - enviados: `1962 -> 1989`;
  - descartados: `38 -> 11`;
  - gaps de scheduler: `54 -> 11`;
  - gaps de captura: `67 -> 28`;
  - underruns uteis: `77 -> 30`;
  - gaps do escritor: `3 -> 3`.
- As pernas de 3 vCPUs enviaram 993 e 996 blocos, com 7 e 4 descartes.
- Portanto, a topologia reduziu pausas de processo e endpoint, mas nao
  satisfez o gate de 1.000 blocos sem perdas.
- `Invoke-HostPacedPcmVm.ps1` passou a registrar `vm_cpu_count` no manifesto.
- Validacao:
  - `159 passed`, `11 subtests passed`;
  - 24 scripts PowerShell parseaveis;
  - JSONs dos gates validos;
  - preflight final com zero erros e zero avisos.
- Defaults e restricoes preservados:
  - PCM v1, driver, profundidade 2 e fila local 4 inalterados;
  - PCM16 mono, 16 kHz e blocos de 320 amostras;
  - yield e prefill continuam opt-in;
  - RNNoise nao promovido;
  - nenhum replay privado e nenhuma escuta.
- Estado final:
  - clone desligado, snapshot 45 e 4 vCPUs;
  - VM original desligada;
  - audio input ligado;
  - clipboard e drag-and-drop desabilitados;
  - NIC NAT;
  - captura padrao do host preservada;
  - preflight final com zero erros e zero avisos.

## 2026-06-14 - Repeticao da topologia de 3 vCPUs

- Metrica fixada antes do boot:
  - quatro cenarios com evidencia completa;
  - `vm_cpu_count=3` no manifesto;
  - nas duas pernas com prefill, descartes abaixo de 38, gaps de scheduler
    abaixo de 54 e gaps de polling da captura abaixo de 67;
  - somente duas pernas de 1.000 blocos sem descarte liberariam replay
    privado.
- Preflight host-only:
  - zero erros e zero avisos;
  - clone e VM original desligados;
  - snapshot 45, NAT, audio input, clipboard e drag-and-drop corretos;
  - captura padrao preservada;
  - VBS ativo e hipervisor presente;
  - consulta direta de Secure Boot sem elevacao retornou acesso negado;
    nenhuma configuracao protegida foi alterada.
- Validacao local antes do boot:
  - 11 testes direcionados passaram;
  - analisadores Python compilaram;
  - scripts PowerShell usados no gate passaram no parser;
  - hashes congelados do capturador e da DLL RNNoise conferiram.
- Repeticao:
  - run `20260614-094007-host-paced-endpointprefill`;
  - sessao GUI unica, sintetica e com 3 vCPUs;
  - manifesto confirmou `vm_cpu_count=3`;
  - quatro cenarios terminaram com evidencia completa.
- Grupo com prefill, controle de 4 vCPUs versus repeticao de 3 vCPUs:
  - enviados: `1962 -> 1946`;
  - descartados: `38 -> 54`;
  - gaps de scheduler: `54 -> 21`;
  - gaps de captura: `67 -> 27`;
  - underruns uteis: `77 -> 52`;
  - gaps do escritor: `3 -> 3`.
- As pernas com prefill enviaram 952 e 994 blocos, com 48 e 6 descartes.
- A perna `02-primed-a` teve uma pausa conjunta de scheduler e captura de
  aproximadamente 886 ms.
- Classificacao:
  `three_vcpu_not_confirmed_as_mitigation`.
- A reducao de pausas de scheduler e captura se repetiu, mas nao a reducao
  de perdas. Tres vCPUs permanecem variaveis entre boots e nao constituem
  mitigacao confirmada.
- O gate A/B de afinidade em CPUs de desempenho nao foi aberto, pois a
  precondicao de repeticao falhou.
- Teardown:
  - `host_result.json` registrou clone desligado e snapshot 45;
  - a consulta externa imediatamente posterior observou `VMState=aborted`;
  - o snapshot 45 foi restaurado novamente sem boot;
  - estado final confirmado: `poweroff`, snapshot 45 e 4 vCPUs;
  - recuperacao registrada em `teardown_recovery.json`.
- Preflight final passou com zero erros e zero avisos.
- Nenhum replay privado, escuta, mudanca de prioridade ou afinidade foi
  executado.

## 2026-06-14 - Yield no polling do capturador

- A pausa de 886 ms atingiu os componentes apoiados em `Sleep(2 ms)`:
  - probe de scheduler;
  - loop de polling do `PtcPcmCapture`.
- O escritor da ponte, ja em yield, permaneceu abaixo de 30 ms nessa perna.
- Hipotese testada: substituir somente a espera do capturador por yield
  cadenciado por QPC reduziria as pausas do endpoint.
- Implementacao:
  - `PtcPcmCapture` recebeu `--poll-wait-strategy sleep|yield`;
  - yield preserva o periodo de 2 ms por deadline QPC e `SwitchToThread`;
  - default permaneceu `sleep`;
  - script convidado passou a encaminhar e registrar a estrategia;
  - criado modo ABBA `EndpointCaptureTimer`;
  - analisador passou a classificar esse gate sem atribui-lo ao writer;
  - contabilidade de perna completa passou a usar os 1.000 blocos aceitos
    pelo driver, sem exigir que a profundidade final 2 ja tivesse sido
    consumida.
- Build:
  - MSBuild Release x64;
  - zero erros e zero avisos;
  - SHA-256 do capturador:
    `9E4C44EE6A277AC43E726D3866270E45B57312CD1A2F415682B3396656E70D65`.
- Validacao host-only:
  - 12 testes direcionados passaram;
  - scripts PowerShell parseaveis;
  - preflight com zero erros e zero avisos.
- Matriz:
  - run `20260614-095256-host-paced-endpointcapturetimer`;
  - 4 vCPUs, uma sessao GUI, quatro pernas sinteticas ABBA;
  - writer yield e prefill 2 em todas as pernas;
  - unica variavel: polling de captura sleep versus yield.
- Resultado agregado:
  - sleep: 1.968 enviados, 32 descartes;
  - yield: 2.000 enviados, zero descarte;
  - gaps de polling: `43 -> 1`;
  - underruns uteis: `56 -> 23`;
  - gaps do escritor: `0 -> 1`;
  - gaps do scheduler: `20 -> 31`.
- As duas pernas yield:
  - enviaram e tiveram 1.000 blocos aceitos;
  - zero descarte e zero erro de escrita;
  - terminaram com 998 consumidos e profundidade final 2.
- Classificacao:
  `capture_poll_yield_completed_without_drops`.
- O requisito de duas pernas de 1.000 blocos sem descartes foi atingido.
- A escuta continua bloqueada:
  - houve 23 underruns na janela util;
  - 13 ocorreram nos primeiros 2,5 ms, antes da estabilizacao do prefill;
  - os 10 restantes foram eventos esparsos durante a fonte.
- Proximo gate formulado:
  - manter captura yield, writer yield, prefill 2, profundidade 2 e fila 4;
  - preencher o driver e confirmar profundidade 2 antes de iniciar o
    `IAudioClient`;
  - comparar partida atual versus barreira em duas fases;
  - exigir zero descarte e reducao dos underruns, sem replay ou escuta.
- Estado final:
  - clone desligado, snapshot 45 e 4 vCPUs;
  - VM original desligada;
  - captura padrao e configuracoes protegidas preservadas;
  - preflight final com zero erros e zero avisos.

## 2026-06-14 - Barreira de partida do endpoint

- Foi adicionada uma inicializacao em duas fases ao capturador:
  - inicializar WASAPI e publicar prontidao;
  - esperar a ponte atingir profundidade 2;
  - chamar `IAudioClient::Start` e publicar o marcador de inicio.
- O default da ferramenta nao mudou.
- Matriz:
  `20260614-100628-host-paced-endpointstartbarrier`.
- Resultado:
  - imediato: 2.000/2.000, zero descarte, 34 underruns;
  - barreira: 2.000/2.000, zero descarte, 7 underruns;
  - pernas com barreira: 0 e 7 underruns.
- Classificacao:
  `capture_start_barrier_reduced_but_did_not_zero_underruns`.
- A corrida inicial foi mitigada, mas eventos esparsos durante a fonte
  mantiveram a escuta bloqueada.

## 2026-06-14 - Lead de envio de 10 ms

- Hipotese: antecipar fisicamente os blocos em 10 ms absorveria jitter curto
  sem alterar a cadencia logica do PCM v1.
- Matriz:
  `20260614-101531-host-paced-endpointsendlead`.
- Controle:
  - 1.942 enviados;
  - 58 descartes;
  - 49 underruns.
- Lead:
  - 1.978 enviados;
  - 22 descartes;
  - 15 underruns.
- Uma perna lead completou 1.000/1.000; a segunda teve uma pausa de captura
  de aproximadamente 447 ms e descartou 22 blocos.
- Classificacao: `ten_ms_send_lead_not_confirmed`.
- O lead foi mantido apenas como opcao experimental e rejeitado como
  mitigacao.

## 2026-06-14 - Afinidade do VirtualBoxVM em CPUs de desempenho

- Feasibility host-only:
  - afinidade de processo gravavel sem elevacao;
  - processadores logicos 0..11 identificados como grupo de desempenho;
  - mascara proposta `0xFFF`;
  - nenhuma mudanca de prioridade.
- O orquestrador recebeu modo `EndpointHostAffinity` em ordem ABBA.
- Manifesto registra mascara, contagem logica, ausencia de elevacao e
  `vm_cpu_count=4`.
- Uma primeira tentativa,
  `20260614-102615-host-paced-endpointhostaffinity`, abortou antes dos
  cenarios porque o VirtualBox apresentou um processo primario e dois
  filhos de hardening com o mesmo UUID.
- O seletor foi corrigido para exigir que o primeiro token da linha de
  comando seja `VirtualBoxVM.exe`.
- Estado protegido foi confirmado e o preflight repetido com zero erros e
  zero avisos.
- Matriz aceita:
  `20260614-102925-host-paced-endpointhostaffinity`.
- Afinidade e prioridade efetivas:
  - controle `0xFFFFF`, `Normal`;
  - P-cores `0xFFF`, `Normal`.
- Resultado agregado:
  - controle: 1.902 enviados, 98 descartes, 44 underruns;
  - P-cores: 1.999 enviados, 1 descarte, 54 underruns;
  - uma perna completa em cada grupo.
- A perna `04-all-cpus-b` sofreu uma pausa de polling de captura de
  aproximadamente 1,328 s. O probe geral do convidado ficou abaixo de
  37,5 ms e o escritor abaixo de 48 ms nessa perna.
- A diferenca de descartes ficou dominada por esse outlier e o grupo P-core
  ainda falhou com 1 descarte e mais underruns agregados.
- Classificacao: `performance_core_affinity_not_confirmed`.
- A afinidade original foi restaurada antes do desligamento.
- Proximo passo objetivo:
  - nao testar outra sintonia de CPU;
  - instrumentar tempos de `GetNextPacketSize`, `GetBuffer`, escrita do PCM
    e `ReleaseBuffer`;
  - distinguir bloqueio WASAPI, I/O e desagendamento especifico do processo;
  - manter replay privado e escuta bloqueados ate evidencia reprodutivel sem
    descartes e sem underruns.
- Estado final:
  - clone desligado, snapshot 45, 4 vCPUs;
  - VM original desligada;
  - audio input ligado;
  - clipboard e drag-and-drop desabilitados;
  - NIC NAT;
  - captura padrao do host inalterada;
  - VBS/HVCI/Secure Boot nao alterados.

## 2026-06-14 - Instrumentacao QPC interna do PtcPcmCapture

- O checkpoint de afinidade foi reaberto somente no host; nenhuma VM foi
  iniciada.
- O trace anterior media polls e pacotes, mas nao separava o tempo gasto
  dentro das chamadas WASAPI, no trabalho local ou nas escritas de trace.
- Foi adicionado `--timing-trace` ao `PtcPcmCapture`.
- Os eventos ficam em memoria durante a captura e sao serializados depois de
  `IAudioClient::Stop`, evitando uma nova escrita no caminho critico.
- Schema v1:
  - identificacao: `schema_version`, `event_index`, `poll_index`,
    `packet_index`, `phase`;
  - relogio: `qpc_frequency_hz`, `qpc_start_ns`, `qpc_end_ns`,
    `duration_ms`;
  - contexto: `hresult`, `packet_frames`, `bytes`, `flags`.
- Fases medidas:
  - intervalo externo entre iteracoes;
  - `GetNextPacketSize`, `GetBuffer` e `ReleaseBuffer`;
  - copia do PCM em memoria;
  - analise do pacote e consulta da ponte;
  - escritas dos traces de pacote e polling;
  - consulta de estatisticas por poll;
  - iteracao agregada;
  - escrita final do WAV e do proprio timing trace.
- Foi criado `scripts/audio/analyze_capture_timing.py`.
- O analisador:
  - valida schema, indices, frequencia QPC, spans e duracoes;
  - usa 30 ms como limiar de stall;
  - prioriza fases internas sobre o intervalo agregado da iteracao;
  - exclui I/O posterior a captura da atribuicao causal de gaps do loop;
  - cruza stalls entre iteracoes com scheduler e writer para distinguir
    atraso compartilhado de desagendamento especifico do capturador.
- Foi criado o modo `EndpointCaptureTiming`:
  - duas pernas sinteticas identicas de bypass;
  - writer yield, captura yield e barreira em profundidade 2;
  - prefill exatamente 2, fila local 4, PCM16 mono 16 kHz e 320 amostras;
  - 4 vCPUs, prioridade Normal e afinidade inalterada.
- Criterio do proximo gate:
  - dois traces completos no schema v1;
  - fases obrigatorias presentes e QPC coerente;
  - classificacao objetiva de qualquer evento acima de 30 ms;
  - `no_capture_stall_observed` e aceito apenas como evidencia de uma rodada
    limpa, nao como prova de mitigacao.
- Replay privado e escuta permanecem bloqueados em todas as classificacoes.
- A tentativa de revisao auxiliar via Claude expirou sem resposta; nenhuma
  conclusao externa foi usada.
- Build final:
  - MSBuild Release x64;
  - zero erros e zero avisos;
  - SHA-256:
    `1D6025481F4546BFE9FB266CD093D7032E872E0F37B56C98D8FA8E0CDD4F3217`.
- Validacao final:
  - 19 testes direcionados passaram;
  - analisadores Python passaram em `compileall`;
  - scripts PowerShell usados no gate passaram no parser;
  - preflight somente leitura com zero falhas e zero avisos.
- Estado protegido confirmado:
  - clone desligado, snapshot 45 e 4 vCPUs;
  - afinidade original, sem processo `VirtualBoxVM` ativo;
  - VM original desligada;
  - audio input ligado;
  - clipboard e drag-and-drop desabilitados;
  - NIC NAT;
  - captura padrao `Microfone (USB Audio Device)` inalterada;
  - VBS ativo e HVCI em execucao;
  - Secure Boot nao foi alterado; consulta sem elevacao permaneceu negada;
  - nenhuma credencial temporaria residual.
- Manifesto host-only:
  `resultados/sysvad_checkpoint46_reopened/host_paced_pcm/`
  `capture_timing_instrumentation_manifest.json`.

## 2026-06-14 - Gate de timing interno e refinamento da espera

- Run:
  `20260614-121252-host-paced-endpointcapturetiming`.
- Duas pernas sinteticas identicas terminaram com:
  - 2.000 blocos submetidos, enviados e aceitos;
  - zero descarte;
  - zero erro de escrita;
  - profundidade final 2 em ambas.
- Primeira perna:
  - zero underrun util;
  - nenhum evento do loop acima de 30 ms.
- Segunda perna:
  - 13 underruns uteis em 6 incrementos;
  - dois gaps de polling, `31,339 ms` e `34,714 ms`;
  - os dois gaps ocorreram em `inter_iteration`;
  - scheduler geral e writer permaneceram ativos nas janelas;
  - o capturador drenou dois pacotes acumulados ao retornar.
- Maximos internos da segunda perna:
  - `GetNextPacketSize`: `3,333 ms`;
  - `GetBuffer`: `3,297 ms`;
  - copia PCM: `1,361 ms`;
  - analise/estatisticas: `1,085 ms`;
  - escrita do trace: `3,196 ms`;
  - `ReleaseBuffer`: `0,408 ms`.
- Conclusao:
  - nao houve bloqueio sustentado em WASAPI;
  - nao houve bloqueio sustentado de I/O;
  - o atraso ficou no caminho de espera entre iteracoes;
  - sem medir cada `SwitchToThread`, chamar o evento de desagendamento de
    todo o processo seria mais forte que a evidencia.
- Refinamento host-only:
  - medir `poll_wait`;
  - medir a maior chamada individual de `SwitchToThread` por poll;
  - reservar antecipadamente o vetor de eventos para evitar realocacoes.
- Build Release x64 refinado:
  `BBFC9622470913B9E969150809B6AB2A5261393B79CF20909B919026E697F574`.
- Validacao:
  - 19 testes direcionados;
  - zero erro ou aviso no build;
  - scripts PowerShell parseaveis.
- Criterio fixado antes da repeticao:
  **se houver novo gap acima de 30 ms, atribui-lo a
  `poll_wait_switch_to_thread` ou ao restante do intervalo; se nao houver,
  registrar nao reproducao sem inferir correcao**.

## 2026-06-14 - SwitchToThread confirmado como origem de stalls

- Repeticao refinada:
  `20260614-122013-host-paced-endpointcapturetiming`.
- Binario implantado:
  `BBFC9622470913B9E969150809B6AB2A5261393B79CF20909B919026E697F574`.
- Transporte:
  - 2.000/2.000 blocos enviados e aceitos;
  - zero descarte;
  - zero erro de escrita;
  - profundidade final 2 nas duas pernas.
- Underruns uteis:
  - primeira perna: 15 em 5 eventos;
  - segunda perna: 8 em 3 eventos.
- Primeira perna, stalls reproduzidos:
  - poll 1526: espera `33,211 ms`, uma chamada de `SwitchToThread`
    `32,739 ms`;
  - poll 1543: espera `34,373 ms`, uma chamada de `SwitchToThread`
    `33,944 ms`;
  - poll 9518: espera `33,705 ms`, uma chamada de `SwitchToThread`
    `32,089 ms`.
- Os tres stalls nao coincidiram com gap acima de 30 ms no scheduler geral
  nem no writer.
- Segunda perna:
  - nenhum stall do loop acima de 30 ms;
  - maior `SwitchToThread`: `16,427 ms`;
  - ainda assim, 8 underruns uteis.
- Classificacao final:
  `capture_thread_delayed_inside_switch_to_thread`.
- Conclusao:
  - o retorno tardio de `SwitchToThread` causa diretamente alguns gaps;
  - WASAPI e I/O continuam excluidos para esses eventos;
  - retirar o yield pode tratar esses stalls;
  - underruns menores permanecem uma causa adicional a controlar.
- Proximo gate formulado, sem novo boot neste checkpoint:
  - adicionar estrategia opt-in `spin`, por deadline QPC;
  - manter default atual;
  - ABBA `yield`, `spin`, `spin`, `yield`;
  - prioridade Normal, 4 vCPUs, afinidade original;
  - writer yield, barreira de profundidade 2, prefill 2 e fila 4;
  - medir impacto em captura, writer, scheduler, transporte e underruns.
- Criterio:
  - duas pernas spin com 1.000/1.000 e zero descarte;
  - nenhum wait spin acima de 30 ms;
  - reducao reprodutivel de gaps e underruns;
  - escuta somente com zero underrun nas duas pernas.

## 2026-06-14 - Gate ABBA de spin rejeitado

- Implementacao host-only:
  - estrategia opt-in `spin` no `PtcPcmCapture`;
  - mesmo deadline QPC do yield, sem `SwitchToThread`;
  - fase nova `poll_wait_spin`;
  - default preservado em `sleep`.
- Build Release x64:
  - zero erros e zero avisos;
  - SHA-256:
    `12D137DAA8E4F5016C2DB3673AA8E03CB3C77CD35F5FAD70135F207FEA059661`.
- Validacao anterior ao boot:
  - 24 testes direcionados sem warnings;
  - `compileall` e parser PowerShell aprovados;
  - preflight com zero falhas e zero avisos.
- Run unico:
  `20260614-123752-host-paced-endpointcapturespin`.
- Controles yield:
  - 2.000/2.000 enviados;
  - zero descarte e zero erro de escrita;
  - zero gap de polling da captura acima de 30 ms;
  - 32 underruns uteis.
- Spin:
  - 1.991/2.000 enviados;
  - 9 descartes e zero erro de escrita;
  - 5 gaps de polling e 9 gaps entre pacotes acima de 30 ms;
  - 74 underruns uteis.
- Impacto compartilhado, controle versus spin:
  - gaps do writer: `2 -> 8`;
  - gaps do scheduler na fonte: `16 -> 42`;
  - gaps de recepcao: `7 -> 13`.
- Esperas `poll_wait_spin` longas:
  - perna A: `89,040` e `43,989 ms`;
  - perna B: `44,684` e `48,310 ms`.
- As quatro esperas longas coincidiram com gaps do scheduler e do writer.
- Interpretacao:
  - remover `SwitchToThread` nao impediu o desagendamento do capturador;
  - ocupar continuamente um vCPU aumentou contencao e piorou writer,
    scheduler, transporte e consumo WaveRT.
- Classificacao:
  `capture_spin_not_confirmed`.
- Decisao:
  **rejeitar spin, manter o default inalterado e manter replay privado e
  escuta bloqueados**.
- Estado final:
  - clone desligado, snapshot 45, 4 vCPUs e afinidade original;
  - VM original desligada;
  - audio input ligado, clipboard e drag-and-drop desabilitados, NIC NAT;
  - captura padrao inalterada;
  - VBS/HVCI preservados, sem processo `VirtualBoxVM`;
  - preflight final com zero falhas e zero avisos;
  - nenhuma credencial residual.

## 2026-06-14 - Rejeicao do spin confirmada sem I/O diagnostico sincrono

- Motivacao:
  - uma repeticao diagnostica mostrou chamadas `packet_trace_write` longas;
  - os CSVs de captura e polling passaram a usar buffers `stdio` de 4 MiB;
  - o flush ficou depois de `IAudioClient::Stop`, sem mudar o audio.
- Build Release x64:
  - zero erros e zero avisos;
  - SHA-256:
    `0F44BEC1B9F6242D3ADC6C328D4C94824352CB88CE10351CB146BA26C9E219F6`.
- Validacao anterior ao boot:
  - 30 testes direcionados;
  - `compileall` e parser PowerShell aprovados;
  - preflight com zero falhas e zero avisos.
- Run unico:
  `20260614-130602-host-paced-endpointcapturespin`.
- O fator de confusao foi removido:
  - maior `packet_trace_write`: `8,284 ms`;
  - maior `poll_trace_write`: `6,407 ms`;
  - nenhum I/O de trace acima de `30 ms` durante a captura.
- Controles yield:
  - 1.998/2.000 blocos;
  - 2 descartes;
  - 41 underruns uteis.
- Spin:
  - 1.996/2.000 blocos;
  - 4 descartes;
  - 58 underruns uteis.
- Regressao agregada do spin:
  - gaps de polling da captura: `1 -> 2`;
  - writer: `5 -> 6`;
  - scheduler: `45 -> 84`;
  - recepcao: `8 -> 12`.
- A perna spin A mediu `poll_wait_spin` de `82,093` e `32,737 ms`.
- O controle yield B mediu `SwitchToThread` de `40,340 ms`.
- Classificacao:
  `capture_spin_not_confirmed`.
- Conclusao:
  - I/O diagnostico nao explica a falha;
  - spin e yield continuam sujeitos a desagendamento;
  - spin aumenta contencao e nao deve ser repetido;
  - sintonias de CPU, afinidade, prioridade e espera estao encerradas.
- Proximo gate proposto, ainda sem implementacao ou boot:
  - modo opt-in WASAPI exclusivo com `AUDCLNT_STREAMFLAGS_EVENTCALLBACK`;
  - `SetEventHandle` e espera no evento do endpoint;
  - manter `yield` como controle e default atual inalterado;
  - instrumentar separadamente a espera no evento e o processamento;
  - ABBA somente depois de build, testes, manifesto e preflight host-only.
- Estado final protegido confirmado, com preflight de zero falhas e zero
  avisos.

## 2026-06-14 - Captura WASAPI orientada a evento rejeitada

- Implementacao host-only:
  - modo exclusivo opt-in `event`;
  - `AUDCLNT_STREAMFLAGS_EVENTCALLBACK`, evento auto-reset e
    `SetEventHandle`;
  - timeout defensivo de 1.000 ms;
  - fase QPC `poll_wait_endpoint_event`;
  - default preservado.
- Build Release x64:
  - zero erros e zero avisos;
  - SHA-256:
    `046681AB92B7E4D20F1AA408E3B2E373900CD4E4B01450EABD244BA1E629EB4F`.
- Validacao host-only:
  - 36 testes direcionados;
  - parser PowerShell e `compileall` aprovados;
  - revisao auxiliar pelo Claude;
  - preflight com zero falhas e zero avisos.
- Gate:
  `20260614-132705-host-paced-endpointcaptureevent`.
- Controles yield:
  - 1.998/2.000 blocos, 2 descartes e 22 underruns uteis.
- Evento:
  - 1.918/2.000 blocos, 82 descartes e 137 underruns uteis.
- A API teve zero timeout, zero falha e zero erro de escrita.
- Maiores esperas sinalizadas: `220,532 ms` e `158,404 ms`.
- Das 59 esperas acima de 30 ms:
  - scheduler e writer: 3;
  - apenas scheduler: 33;
  - apenas writer: 0;
  - sem sobreposicao: 23.
- A perna evento B teve zero gap do writer acima de 30 ms, mas perdeu 17
  blocos e registrou 48 underruns.
- Classificacao:
  `capture_event_not_confirmed`.
- Conclusao:
  - a sinalizacao orientada a evento e instavel neste endpoint virtual;
  - remover polling, rede ou writer nao resolve o consumidor WaveRT;
  - o resultado confirma quantitativamente a observacao do Checkpoint 32;
  - novas sintonias de espera, CPU e produtor nesta VM nao se justificam.
- Estado final:
  - clone desligado, snapshot 45, 4 vCPUs e afinidade original;
  - VM original desligada;
  - audio input ligado, clipboard e drag-and-drop desabilitados, NIC NAT;
  - captura padrao inalterada;
  - preflight final com zero falhas e zero avisos;
  - nenhuma credencial residual.
- Proxima fase:
  **fechamento do prototipo academico e protocolo de validacao futura em
  Windows nativo com driver devidamente assinado**.

## 2026-06-14 - Preparacao do contrafactual de eventos

- Foi formulado um contrafactual na mesma VM entre o endpoint SYSVAD
  `External Microphone Headphone` e o endpoint HDA emulado pelo VirtualBox.
- A ferramenta nova e separada do driver e do `PtcPcmCapture`.
- Ela enumera todos os endpoints ativos e executa cada perna por ID exato.
- O HDA e identificado somente depois da enumeracao, por nome de interface
  exato normalizado em ingles ou portugues; ambiguidades encerram o ensaio.
- O modo compartilhado e o formato de mix evitam confundir suporte a PCM16
  exclusivo com regularidade de notificacao.
- Nenhum produtor, DSP, ponte PCM, replay privado ou persistencia de audio
  participa.
- Foram implementados resumo JSON, trace CSV, scheduler probe e analisador
  com normalizacao pelo periodo de dispositivo.
- A automacao preserva ordem ABBA, quatro vCPUs, prioridade Normal, afinidade
  inalterada, GUI, snapshot 45 e configuracoes protegidas.
- O orquestrador executa preflight somente leitura antes e depois da sessao.
- Build final do probe:
  `Release|x64`, zero erros, zero avisos e SHA-256
  `A3967D5979BF7AE04598198753E351E0618057EAB002AC7E432F6BDBF4ED4674`.
- Validacao:
  23 testes direcionados, parser PowerShell, `compileall`, enumeracao
  host-only sem stream e preflight de zero falhas e zero avisos.
- A segunda revisao via Claude expirou na primeira tentativa e concluiu na
  segunda para Python e PowerShell. O C++ foi revisado localmente, incluindo
  ordem de vida COM por RAII e ausencia de copia ou arquivo de audio.
- Nenhum boot foi realizado.

## 2026-06-14 - Resultado do contrafactual de eventos

- Run aceito:
  `20260614-144937-endpoint-event-contrafactual`.
- As quatro pernas ABBA terminaram com evidencia completa.
- O HDA nao foi um controle limpo:
  - perna A: 22 sinais tardios e maximo de `7.554,401 ms`;
  - perna B: 23 sinais tardios e maximo de `834,825 ms`.
- O SYSVAD tambem reproduziu:
  - perna A: 21 sinais tardios e maximo de `2.302,083 ms`;
  - perna B: 48 sinais tardios e maximo de `437,176 ms`.
- Em periodos de dispositivo, os maximos foram `230,21`, `743,64`, `82,18`
  e `43,72`, respectivamente.
- A correlacao com scheduler cobriu 54/69 atrasos SYSVAD e 37/45 atrasos HDA.
- Classificacao predefinida:
  `virtualbox_event_timing_supported`.
- Conclusao conservadora:
  a evidencia reforca uma limitacao do VirtualBox/NEM ou do agendamento do
  convidado que afeta endpoints modificados e nao modificados. Ela nao
  demonstra correcao do driver SYSVAD e nao libera escuta.
- O gate nao salvou audio.
- Teardown:
  `guest_shutdown`, snapshot 45 restaurado, clone e VM original desligados,
  configuracoes protegidas preservadas, nenhuma credencial residual e
  preflight final com zero falhas e zero avisos.
