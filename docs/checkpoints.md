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

## Checkpoint 3 - Relatorio atualizado e compilado

- Data: 2026-06-06
- Estado: `entrega3.tex` atualizado com resultados preliminares e `entrega3.pdf` recompilado.
- Commit local: `1df8e9c` (`tex: atualizar relatorio com resultados preliminares`)
- Comandos de verificacao:
  - `pdflatex -interaction=nonstopmode entrega3.tex`
  - `pdflatex -interaction=nonstopmode entrega3.tex`
  - `pdftoppm -f 7 -l 15 -png -r 120 entrega3.pdf previews\entrega3_verificacao`
  - `pdftoppm -f 19 -l 22 -png -r 120 entrega3.pdf previews\entrega3_finalcheck`
- Resultado da compilacao:
  - PDF gerado com 26 paginas;
  - sem erro fatal;
  - sem referencias indefinidas apos recompilacao;
  - avisos remanescentes de `Underfull \hbox` e `microtype`.
- Secoes atualizadas:
  - metodologia experimental;
  - amostras, ruidos e controle de variaveis;
  - metricas e custo computacional;
  - referencias bibliograficas;
  - atividades realizadas e resultados obtidos;
  - avaliacao do andamento;
  - cronograma;
  - riscos;
  - consideracoes finais.
- Pendencias para o proximo ciclo:
  - substituir/complementar ruidos sinteticos por DEMAND ou base ambiental real;
  - refinar parametros Wavelet;
  - medir latencia por blocos;
  - preparar reproducao em outro computador;
  - avaliar Raspberry Pi como primeira plataforma embarcada plausivel.

## Checkpoint 4 - Sincronizacao com GitHub

- Data: 2026-06-06
- Estado: commits locais enviados para o remoto.
- Comando:
  - `git push origin main`
- Remoto:
  - `https://github.com/gamathias14/reducao-de-ruido-algoritmica.git`
- Resultado:
  - push concluido com sucesso;
  - `main` remoto atualizado de `cb4f070` para `43fe261`.

## Checkpoint 5 - Graficos nativos e Entrega 3 consolidada

- Data: 2026-06-06
- Estado: `entrega3.tex` migrado para graficos principais nativos em LaTeX, com dados exportados pelo pipeline Python para `resultados/pgfplots/`.
- Commits locais:
  - `7b0d8c9` (`data: exportar series para pgfplots`)
  - `dbc4fe7` (`tex: migrar graficos e listas para pgfplots`)
- Arquivos principais:
  - `benchmark_audio/run_benchmark.py`
  - `README_benchmark.md`
  - `resultados/pgfplots/README.md`
  - `resultados/pgfplots/melhoria_snr.csv`
  - `resultados/pgfplots/rtf_por_metodo.csv`
  - `resultados/pgfplots/formas_onda_exemplo.csv`
  - `resultados/pgfplots/espectrograma_clean.csv`
  - `resultados/pgfplots/espectrograma_noisy.csv`
  - `resultados/pgfplots/espectrograma_stft_subtraction.csv`
  - `resultados/pgfplots/espectrograma_wavelet_soft.csv`
  - `resultados/pgfplots/parametros_espectrograma.tex`
  - `entrega3.tex`
  - `entrega3.pdf`
  - `.gitignore`
- Comandos de verificacao:
  - `python -m compileall benchmark_audio`
  - `python -m benchmark_audio.run_benchmark --export-pgfplots-only`
  - `pdflatex -interaction=nonstopmode entrega3.tex`
  - recompilacoes adicionais de `pdflatex` para estabilizar sumario, listas e referencias;
  - `pdftoppm -f 4 -l 4 -png -r 130 entrega3.pdf previews\entrega3_indices`
  - `pdftoppm -f 16 -l 17 -png -r 130 entrega3.pdf previews\entrega3_graficos_fix`
  - `pdftoppm -f 18 -l 18 -png -r 130 entrega3.pdf previews\entrega3_codigo`
- Resultado da compilacao:
  - PDF gerado com 28 paginas;
  - sem erro fatal;
  - sem referencias indefinidas;
  - sem `Overfull \hbox` remanescente apos ajustes;
  - avisos remanescentes: `microtype` em `footnote` e alguns `Underfull \hbox`.
- Verificacao visual:
  - indice de ilustracoes presente apos o sumario;
  - lista de figuras, tabelas, graficos e codigos presente;
  - graficos principais montados por `pgfplots`, sem `\includegraphics` para PNGs principais;
  - formas de onda e espectrogramas legiveis;
  - codigo curto de exportacao presente e listado.
- Pendencias para o proximo ciclo:
  - usar DEMAND, VoiceBank-DEMAND ou base ambiental real;
  - ampliar amostras e falantes;
  - separar validacao e comparacao final;
  - refinar Wavelet;
  - testar STFT sem silencio inicial garantido;
  - medir latencia por blocos;
  - preparar teste em Raspberry Pi;
  - estimar memoria e complexidade em C/C++ para ESP32/ESP32-S3;
  - manter Arduino Uno R3 como inviabilidade ou trabalho altamente simplificado.

## Checkpoint 11 - Nucleo de algoritmos reutilizavel

- Data: 2026-06-06
- Estado: Fase 1 da trilha de app em tempo real concluida.
- Objetivo: separar os algoritmos e utilitarios do benchmark offline para permitir reuso pelo futuro prototipo Windows em tempo real.
- Commit local:
  - `d69421f` (`code: separar nucleo reutilizavel de denoise`)
- Arquivos criados ou alterados:
  - `benchmark_audio/denoise.py`
  - `benchmark_audio/run_benchmark.py`
  - `tests/test_denoise.py`
  - `README_benchmark.md`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
- Comandos de verificacao:
  - `python -m compileall benchmark_audio`
  - `python -m unittest discover -s tests`
  - `python -m benchmark_audio.run_benchmark --export-pgfplots-only`
  - smoke test completo em diretorio temporario, com `run_benchmark` executando sobre uma amostra sintetica curta.
- Parametros do smoke test:
  - taxa de amostragem: 16 kHz;
  - duracao: 0,25 s;
  - SNR: 0 dB;
  - ruido: branco;
  - STFT: `n_fft=256`, `hop_length=80`;
  - Wavelet: nivel 3.
- Resultados numericos:
  - 2 testes de sanidade executados com sucesso;
  - smoke test gerou `metricas_por_condicao.csv` e `resumo_por_metodo_snr.csv` temporarios;
  - resultados oficiais do benchmark nao foram recalculados nesta etapa.
- Limitacoes:
  - a separacao ainda nao implementa streaming real;
  - os algoritmos continuam assumindo processamento vetorizado de arrays completos;
  - a estimativa de ruido dos metodos STFT ainda usa trecho inicial, o que devera ser revisto na Fase 2.
- Proximos passos:
  - criar prototipo CLI em `realtime_audio/windows_realtime.py`;
  - implementar processamento por blocos com bypass e medicao de tempo por bloco;
  - salvar logs curtos de latencia e estabilidade.

## Checkpoint 12 - Prototipo Windows em tempo real por CLI

- Data: 2026-06-06
- Estado: prototipo CLI criado e validado em autoteste sintetico; captura fisica pendente.
- Objetivo: iniciar a Fase 2 com processamento mono por blocos, metricas por bloco e caminho para captura/reproducao local no Windows.
- Commit local:
  - `1610701` (`code: adicionar prototipo realtime windows`)
- Arquivos criados ou alterados:
  - `.gitignore`
  - `requirements.txt`
  - `realtime_audio/__init__.py`
  - `realtime_audio/windows_realtime.py`
  - `realtime_audio/README.md`
  - `tests/test_realtime_audio.py`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
- Comandos de verificacao:
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
  - `python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --duration 1 --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --help`
- Parametros:
  - taxa de amostragem: 16 kHz;
  - audio mono;
  - bloco: 20 ms;
  - metodo testado: `stft_subtraction`;
  - calibracao inicial: 250 ms;
  - STFT: `n_fft=512`, `hop_length=160`;
  - duracao do autoteste: 1 s.
- Resultados numericos:
  - testes automatizados: 4 testes, todos aprovados;
  - blocos processados no autoteste: 50;
  - tempo medio por bloco: aproximadamente 0,357 ms;
  - pior caso por bloco: aproximadamente 0,676 ms;
  - desvio padrao: aproximadamente 0,209 ms;
  - RTF medio por bloco: aproximadamente 0,0179;
  - RTF pior caso por bloco: aproximadamente 0,0338;
  - latencia algoritmica estimada: 32 ms.
- Limitacoes:
  - `sounddevice` nao estava instalado no ambiente atual;
  - nao houve teste com microfone, alto-falante ou fone;
  - os resultados sao de autoteste sintetico, nao de audio real capturado;
  - a latencia total de dispositivo/driver ainda nao foi medida.
- Proximos passos:
  - instalar dependencias com `python -m pip install -r requirements.txt`;
  - listar dispositivos com `python -m realtime_audio.windows_realtime --list-devices`;
  - rodar primeiro `bypass` por alguns segundos;
  - rodar `stft_subtraction` com salvamento de logs;
  - comparar estabilidade, underruns/overruns e latencia aproximada entre bypass e processamento.

## Checkpoint 13 - Medicao de latencia e estabilidade Windows input-only

- Data: 2026-06-06
- Estado: captura real input-only validada por 30 s para `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`.
- Objetivo: medir o custo por bloco em audio real, sem playback e sem salvar voz.
- Commit local inicial:
  - `c6ce99f` (`code: medir realtime input-only no windows`)
- Atualizacao posterior:
  - rodada estendida de 30 s registrada em documentos e tabela consolidada; commit ainda nao criado nesta retomada.
- Arquivos criados ou alterados:
  - `realtime_audio/windows_realtime.py`
  - `realtime_audio/summarize_realtime.py`
  - `realtime_audio/README.md`
  - `resultados/tabelas/realtime_windows_input_only.csv`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
  - `prompt_continuacao_fase2_realtime_windows.md`
- Comandos principais ja executados nesta fase:
  - `python -m pip install -r requirements.txt`
  - `python -m realtime_audio.windows_realtime --list-devices`
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
  - `python -m realtime_audio.windows_realtime --input-only --duration 3 --method bypass --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 3 --method stft_subtraction --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method bypass --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_subtraction --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_wiener --block-ms 20 --no-save`
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method wavelet_soft --block-ms 20 --no-save`
  - `python -m realtime_audio.summarize_realtime --pattern "windows_input_only_*_metrics.json" --output resultados/tabelas/realtime_windows_input_only.csv`
- Dispositivos padrao observados na rodada de 30 s:
  - entrada: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida: `SteelSeries Sonar - Gaming`, indice 7, MME.
- Parametros da rodada de 30 s:
  - taxa de amostragem: 16 kHz;
  - audio mono;
  - bloco: 20 ms;
  - duracao configurada: 30 s por metodo;
  - STFT: `n_fft=512`, `hop_length=160`;
  - calibracao STFT: 250 ms;
  - WAV salvo: nao.
- Resultados numericos da rodada de 30 s:
  - `bypass`: 1498 blocos, media 0,031 ms/bloco, pior caso 0,134 ms, desvio 0,024 ms, RTF medio 0,00157, RTF pior caso 0,00670, latencia total input-only estimada 40 ms, sem status de erro.
  - `stft_subtraction`: 1498 blocos, media 0,471 ms/bloco, pior caso 1,929 ms, desvio 0,175 ms, RTF medio 0,0236, RTF pior caso 0,0964, latencia total input-only estimada 72 ms, sem status de erro.
  - `stft_wiener`: 1498 blocos, media 0,412 ms/bloco, pior caso 1,423 ms, desvio 0,175 ms, RTF medio 0,0206, RTF pior caso 0,0711, latencia total input-only estimada 72 ms, sem status de erro.
  - `wavelet_soft`: 1498 blocos, media 0,258 ms/bloco, pior caso 14,749 ms, desvio 0,394 ms, RTF medio 0,0129, RTF pior caso 0,737, latencia total input-only estimada 60 ms, sem status de erro.
- Limitacoes:
  - sem reproducao/duplex;
  - sem avaliacao perceptual;
  - sem salvamento de WAV de voz;
  - `wavelet_soft` emitiu warning numerico do PyWavelets, embora os CSVs de blocos nao tenham `NaN` ou infinito;
  - latencia total ainda e estimada por entrada reportada mais latencia algoritmica, sem medir saida/round-trip.
- Proximos passos:
  - investigar ou mitigar o warning do Wavelet se ele reaparecer em novas rodadas;
  - consultar o Checkpoint 14 para o teste duplex curto com fone Bluetooth;
  - depois de consolidar duplex ou decidir manter input-only, avaliar atualizacao do `entrega3.tex`.

## Checkpoint 14 - CLI demonstravel com captura e reproducao

- Data: 2026-06-06
- Estado: teste duplex curto concluido tecnicamente com fone Bluetooth, sem erro de stream.
- Objetivo: validar o caminho captura-processa-reproduz da CLI Windows por duracao curta e segura.
- Commit local:
  - ainda nao criado nesta retomada.
- Arquivos criados ou alterados:
  - `resultados/tabelas/realtime_windows_duplex.csv`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
  - `realtime_audio/README.md`
- Condicao de seguranca:
  - usuario confirmou uso de `HUAWEI FreeBuds SE 2`;
  - usuario informou que os alto-falantes do notebook estao quebrados;
  - nenhum WAV foi salvo.
- Dispositivos:
  - entrada: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida: `Fones de ouvido (HUAWEI FreeBuds SE 2)`, indice 7, MME.
- Comandos principais:
  - `python -m realtime_audio.windows_realtime --list-devices`
  - `python -m realtime_audio.windows_realtime --duration 5 --method bypass --block-ms 20 --input-device 1 --output-device 7 --no-save`
  - `python -m realtime_audio.windows_realtime --duration 5 --method stft_subtraction --block-ms 20 --input-device 1 --output-device 7 --no-save`
  - `python -m realtime_audio.summarize_realtime --pattern "windows_*_20260606_2221*_metrics.json" --output resultados/tabelas/realtime_windows_duplex.csv`
- Parametros:
  - taxa de amostragem: 16 kHz;
  - audio mono;
  - bloco: 20 ms;
  - duracao configurada: 5 s por metodo;
  - STFT: `n_fft=512`, `hop_length=160`;
  - calibracao STFT: 250 ms;
  - WAV salvo: nao.
- Resultados numericos:
  - `bypass`: 248 blocos, media 0,032 ms/bloco, pior caso 0,107 ms, desvio 0,024 ms, RTF medio 0,00162, RTF pior caso 0,00536, latencia total estimada 240 ms, sem status de erro.
  - `stft_subtraction`: 248 blocos, media 0,472 ms/bloco, pior caso 1,463 ms, desvio 0,209 ms, RTF medio 0,0236, RTF pior caso 0,0731, latencia total estimada 272 ms, sem status de erro.
- Limitacoes:
  - teste duplex curto;
  - apenas `bypass` e `stft_subtraction`;
  - saida Bluetooth com latencia de saida reportada de 200 ms;
  - latencia total estimada, sem round-trip fisico;
  - avaliacao subjetiva positiva registrada a partir do relato do usuario, mas ainda sem protocolo perceptual formal.
- Proximos passos:
  - decidir se vale repetir com fone cabeado ou outro dispositivo de menor latencia;
  - consultar o Checkpoint 15 para a atualizacao cautelosa do `entrega3.tex`.

## Checkpoint 15 - Relatorio atualizado com validacao realtime cautelosa

- Data: 2026-06-06
- Estado: `entrega3.tex` e `entrega3.pdf` atualizados com resultados realtime Windows.
- Objetivo: incorporar as evidencias da Fase 2 sem extrapolar os testes curtos.
- Commit local:
  - ainda nao criado nesta retomada.
- Arquivos principais:
  - `entrega3.tex`
  - `entrega3.pdf`
  - `resultados/tabelas/realtime_windows_input_only.csv`
  - `resultados/tabelas/realtime_windows_duplex.csv`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
  - `realtime_audio/README.md`
- Conteudo incorporado:
  - tabela input-only de 30 s para `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`;
  - tabela duplex curta para `bypass` e `stft_subtraction`;
  - observacao de `status_counts` vazio nos testes;
  - ressalva sobre warning numerico do PyWavelets;
  - ressalva sobre latencia Bluetooth;
  - relato subjetivo positivo do usuario no teste duplex.
- Verificacao:
  - `pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex`, repetido ate estabilizar referencias;
  - PDF final copiado de `entrega3_build.pdf` para `entrega3.pdf`;
  - log final sem referencias indefinidas e sem `Overfull`;
  - paginas da secao realtime renderizadas com `pdftoppm` e verificadas visualmente.
- Limitacoes:
  - a compilacao direta com `jobname=entrega3` encontrou auxiliares antigos inconsistentes; a verificacao limpa usou `jobname=entrega3_build`;
  - duplex ainda curto e com saida Bluetooth;
  - relatorio ainda depende de validacao futura com ruidos ambientais reais e plataforma menos potente.

## Checkpoint 16 - Preparacao DEMAND para ruidos ambientais reais

- Data: 2026-06-07
- Estado: caminho de preparo para DEMAND criado e validado sem baixar bases grandes.
- Objetivo: permitir uma proxima rodada experimental com ruidos ambientais reais mantendo reproducibilidade, controle de licenca e bases brutas fora do Git.
- Commit local:
  - ainda nao criado nesta retomada.
- Arquivos principais:
  - `benchmark_audio/prepare_environmental_noise.py`
  - `benchmark_audio/run_benchmark.py`
  - `tests/test_environmental_noise.py`
  - `README_benchmark.md`
  - `dados/README.md`
  - `resultados/tabelas/demand_archives_manifest.csv`
  - `resultados/tabelas/demand_noise_prepared.csv`
  - `docs/diario_tecnico.md`
  - `docs/auditoria_resultados.md`
  - `docs/checkpoints.md`
- Fonte registrada:
  - DEMAND no Zenodo: `https://zenodo.org/records/1227121`;
  - DOI: `10.5281/zenodo.1227121`;
  - observacao de licenca: texto descritivo informa `CC BY-SA 3.0`; conferir metadado atual de direitos antes de redistribuir derivados.
- Funcionalidades:
  - manifesto local dos ZIPs DEMAND 16 kHz;
  - subconjunto padrao: `DKITCHEN`, `OOFFICE`, `PCAFETER`, `STRAFFIC`;
  - download opcional com `--download`;
  - verificacao de MD5 dos arquivos oficiais;
  - extracao de canal e segmentacao em WAVs curtos para `dados/demo/noise_demand/`;
  - benchmark offline aceita `--noise-dir` para substituir ruidos sinteticos por WAVs locais.
- Comandos executados:
  - `python -m benchmark_audio.prepare_environmental_noise --manifest-only`
  - `python -m benchmark_audio.prepare_environmental_noise`
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
- Resultado:
  - manifesto DEMAND gerado;
  - preparacao sem download registrou 4 arquivos ausentes, como esperado;
  - 8 testes automatizados aprovados;
  - nenhuma nova medicao oficial de qualidade com DEMAND ainda.
- Proximos passos:
  - baixar um subconjunto pequeno com `python -m benchmark_audio.prepare_environmental_noise --download --environments DKITCHEN OOFFICE PCAFETER STRAFFIC`;
  - rodar uma matriz curta com `python -m benchmark_audio.run_benchmark --noise-dir dados/demo/noise_demand --max-noises 4`;
  - comparar resultados contra a rodada sintetica, mantendo conclusoes proporcionais.

## Checkpoint 17 - Primeira matriz DEMAND executada

- Data: 2026-06-07
- Estado: quatro ambientes DEMAND preparados e benchmark ambiental executado em diretorio isolado.
- Arquivos brutos locais, fora do Git:
  - `dados/external/demand/DKITCHEN_16k.zip`
  - `dados/external/demand/OOFFICE_16k.zip`
  - `dados/external/demand/PCAFETER_16k.zip`
  - `dados/external/demand/STRAFFIC_16k.zip`
- Dados derivados locais:
  - 12 WAVs em `dados/demo/noise_demand/`;
  - tres segmentos de 3 s por ambiente;
  - mono, 16 kHz, primeiro canal.
- Comando principal:
  - `python -m benchmark_audio.run_benchmark --noise-dir dados/demo/noise_demand --results-dir resultados/demand`
- Matriz:
  - 5 falas;
  - 12 ruidos;
  - 4 SNRs;
  - 4 metodos;
  - 960 linhas.
- Resultados principais:
  - `stft_subtraction`: melhoria media de 7,69 a 6,21 dB conforme a SNR alvo;
  - `stft_wiener`: 4,62 a 4,07 dB;
  - `wavelet_soft`: 0,28 a -0,38 dB;
  - nenhum `NaN` ou infinito.
- Variacao ambiental da subtracao espectral:
  - cozinha: 10,00 dB;
  - escritorio: 8,45 dB;
  - cafeteria: 4,11 dB;
  - trafego: 5,47 dB.
- Codigo:
  - `run_benchmark.py` aceita `--results-dir`;
  - gera `resumo_por_grupo_ruido.csv`;
  - metadata registra os ruidos efetivamente usados.
- Relatorio:
  - `entrega3.tex` atualizado cautelosamente com metodologia, tabela DEMAND, limitacoes, cronograma e conclusao.
  - `entrega3.pdf` recompilado com 31 paginas;
  - log final sem `Overfull` e sem referencias indefinidas;
  - paginas 8 a 13 verificadas visualmente.
- Limitacoes:
  - segmentos contiguos de um canal por ambiente;
  - silencio inicial ainda favorece a estimativa STFT;
  - sem separacao validacao/teste;
  - sem avaliacao perceptual formal.
- Proximos passos:
  - separar ambientes ou segmentos para validacao e teste final;
  - testar STFT sem silencio inicial garantido;
  - refinar Wavelet antes de conclusao comparativa final.

## Checkpoint 18 - Fase algoritmica em PC consolidada

- Data: 2026-06-07
- Estado: refinamento com validacao/final, teste sem silencio inicial e selecao tecnica concluidos.
- Objetivo: completar a fase atual antes da continuidade causal/perceptual/Raspberry Pi.
- Commit tecnico: `13d98c1` (`results: consolidar benchmark demand e refinamento`).
- Codigo:
  - `benchmark_audio/denoise.py`
  - `benchmark_audio/run_refinement.py`
  - `tests/test_denoise.py`
  - `tests/test_refinement.py`
- Dados:
  - benchmark historico preservado com 5 falantes;
  - refinamento com 6 falantes FSDD;
  - validacao: `jackson`, `nicolas`, `theo` + `DKITCHEN`, `OOFFICE`;
  - final: `george`, `lucas`, `yweweler` + `PCAFETER`, `STRAFFIC`;
  - 72 condicoes por divisao;
  - silencio inicial fixo removido.
- Busca:
  - 144 configuracoes;
  - 48 subtracao espectral;
  - 24 Wiener;
  - 72 Wavelet.
- Selecionados:
  - subtracao: 512/160, baixa energia q=0,35, alpha=1,5, piso 0,02;
  - Wiener: 512/160, baixa energia q=0,35, piso 0,05;
  - Wavelet: `sym4`, nivel 3, hard global, fator 0,50.
- Resultado final:
  - subtracao refinada: +4,85 dB SNR, +3,72 dB SI-SDR, 0% degradacao;
  - Wiener refinado: +2,92 dB SNR, +2,25 dB SI-SDR, 0% degradacao;
  - Wavelet refinada: +0,03 dB SNR, +0,01 dB SI-SDR, 11,1% degradacao.
- Comparacao com padrao:
  - subtracao inicial: +1,82 dB SNR, -0,16 dB SI-SDR, 33,3% degradacao;
  - Wiener inicial: +1,30 dB SNR, -0,40 dB SI-SDR, 27,8% degradacao;
  - Wavelet padrao: +0,32 dB SNR, -0,46 dB SI-SDR, 19,4% degradacao.
- Interpretacao:
  - o silencio inicial favorecia a STFT;
  - a estimativa por baixa energia recupera robustez sem silencio;
  - DWT Wavelet refinada reduz dano, mas permanece neutra;
  - candidata principal: subtracao espectral adaptada;
  - alternativa: Wiener;
  - DWT limiarizada: baseline leve.
- Arquivos:
  - `resultados/demand_refinement/tabelas/`
  - `resultados/demand_refinement/audio/`
  - `README_benchmark.md`
  - `dados/README.md`
  - `entrega3.tex`
  - `entrega3.pdf`
  - documentos em `docs/`.
- Verificacao final:
  - 12 testes e 4 subtestes aprovados;
  - 144 configuracoes de validacao e 1008 linhas na comparacao;
  - nenhum `NaN` ou infinito;
  - `entrega3.pdf` estabilizado em 32 paginas apos tres compilacoes;
  - log sem `Overfull` e sem referencias indefinidas;
  - metodologia, tabelas de resultado, cronograma, riscos e conclusao inspecionados visualmente.
- Limitacoes:
  - conjunto final nao historicamente cego;
  - estimador de baixa energia offline e nao causal;
  - sem avaliacao perceptual;
  - segmentos de um canal por ambiente.
- Proxima fase:
  - estimador causal/rolante;
  - reabertura controlada da trilha Wavelet com WPT, rastreamento temporal de
    ruido por subbanda e ganho Wiener;
  - escuta critica;
  - confirmacao em dados ainda nao vistos;
  - preparacao Raspberry Pi.

### Revisao posterior da trilha Wavelet

- Discussao com Gabriel: os resultados quase nulos nao devem ser lidos como
  falha geral de Wavelets, mas como limite da implementacao testada ate aqui:
  DWT com MAD e limiar universal escalado.
- Nova hipotese: implementar `Wavelet Packet Transform` com estimacao temporal
  de ruido por subbanda, inspirada em MCRA/IMCRA, e ganho Wiener suave.
- Consequencia para os proximos checkpoints: `wavelet_soft` permanece como
  baseline historico; a proxima candidata Wavelet deve ser um metodo novo, por
  exemplo `wavelet_packet_wiener`, comparado contra STFT causal e contra o
  limite offline de baixa energia.
- Plano tecnico: `docs/plano_wavelet_packet_wiener.md`.

## Checkpoint 20 - Estimador causal de ruido e testes

- Data: 2026-06-07
- Numeracao: segue o roteiro da plataforma PC; o Checkpoint 19 de voz autoral
  permanece pendente por decisao explicita de preparar primeiro o nucleo causal.
- Estado: etapa PC-1 concluida; gravacoes autorais e testes fisicos nao iniciados.
- Objetivo: substituir a dependencia de silencio inicial por estimativa causal,
  explicita e reutilizavel por arquivo em blocos e captura Windows.
- Commit tecnico:
  - `a03f05a` (`code: implementar estimador causal de ruido`).
- Codigo:
  - `benchmark_audio/causal.py`;
  - `benchmark_audio/run_causal_estimator.py`;
  - integracao em `realtime_audio/windows_realtime.py`;
  - percentis, memoria e blocos acima do orcamento nos logs realtime.
- Testes:
  - silencio e protecao numerica;
  - calibracao congelada;
  - fala continua com atualizacao lenta;
  - mudanca persistente de ruido;
  - blocos curtos;
  - reset deterministico;
  - prefixo causal independente de blocos futuros;
  - bypass exato.
- Selecao:
  - 20 configuracoes adaptativas e uma calibracao curta;
  - escolha somente nas 72 condicoes de `validation`;
  - nenhuma gravacao autoral ou Sessao B usada;
  - divisao operacional aberta somente depois da escolha.
- Parametros congelados:
  - 16 kHz, FFT 512, hop 160 e bloco 320 amostras;
  - aquecimento 250 ms;
  - historico 500 ms;
  - quantil espectral 0,22 e quantil de energia 0,20;
  - limiar de fala 6 dB;
  - EMA 0,30 em baixa energia e 0,005 durante fala provavel;
  - subtracao com alpha 1,5 e piso 0,02;
  - Wiener com piso 0,05.
- Resultado no conjunto final operacional:
  - subtracao causal: +3,76 dB SNR, +2,65 dB SI-SDR, 0% degradacao;
  - Wiener causal: +1,68 dB SNR, +1,35 dB SI-SDR, 0% degradacao;
  - calibracao causal: +0,96 dB SNR, -2,38 dB SI-SDR, 33,3% degradacao;
  - limite offline de baixa energia: +4,85 dB SNR e +3,72 dB SI-SDR.
- Custo:
  - estado maximo medido: 60.900 bytes, aproximadamente 59,5 KiB;
  - subtracao causal final: RTF medio 0,068, p99 medio 3,08 ms e pior
    bloco 13,31 ms;
  - pico isolado de 104,12 ms na execucao em lote da validacao, registrado
    como jitter e nao como validacao realtime prolongada;
  - autoteste posterior de 1 s: media 1,58 ms, p99 4,01 ms, pior 4,62 ms e
    zero blocos acima de 20 ms.
- Artefatos:
  - `resultados/causal_estimator/tabelas/`;
  - `docs/estimador_causal.md`;
  - `entrega3.tex` e `entrega3.pdf`.
- Verificacao:
  - 21 testes e 4 subtestes aprovados;
  - 21 linhas de candidatos e 1152 linhas de comparacao;
  - nenhum `NaN` ou infinito;
  - relatorio compilado tres vezes, 33 paginas;
  - sem `Overfull`, referencias ou citacoes indefinidas;
  - paginas de metodologia, resultados, riscos e conclusao inspecionadas.
- Intervencao humana:
  - nenhuma exigida nesta etapa;
  - nao houve gravacao, escuta, playback ou captura fisica.
- Dados privados:
  - nenhum audio autoral criado ou versionado;
  - artefatos antigos nao rastreados permaneceram intocados.
- Limitacoes:
  - conjunto final operacional nao e historicamente cego;
  - quantil exato em NumPy ainda tem custo e jitter de Python;
  - validacao Windows prolongada com o estimador novo pertence a PC-6;
  - avaliacao perceptual ainda pendente.
- Proximo checkpoint tecnico:
  - PC-2, processamento de WAV em blocos com o mesmo
    `CausalSTFTProcessor`, sem dispositivo de audio.

## Checkpoint 21 - Processamento reproduzivel de WAV em blocos

- Data: 2026-06-07.
- Estado: etapa PC-2 concluida; voz autoral, escuta e validacao fisica
  prolongada nao iniciadas.
- Objetivo: processar WAVs por blocos com exatamente o mesmo nucleo causal da
  captura Windows, preservando comprimento, alinhamento e rastreabilidade.
- Commits:
  - `f781eeb` (`code: adicionar processamento wav em blocos`);
  - `b526eb8` (`results: validar processamento wav por blocos`);
  - `fc42d3f` (`docs: documentar processamento wav em blocos`).
- Codigo:
  - `realtime_audio/process_wav_blocks.py`;
  - `realtime_audio/block_metrics.py`;
  - `realtime_audio/generate_test_vectors.py`;
  - `benchmark_audio/run_file_blocks_experiment.py`;
  - conversao WAV sem normalizacao automatica em `benchmark_audio/denoise.py`;
  - agregacao de tempos compartilhada com `windows_realtime.py`.
- Contrato da CLI:
  - entrada WAV mono ou estereo;
  - conversao para mono a 16 kHz;
  - metodos `bypass`, `stft_subtraction` e `stft_wiener`;
  - `adaptive` como modo principal e `calibration` como baseline;
  - blocos de 10, 20 e 32 ms;
  - WAV PCM16, CSV por bloco e JSON por execucao;
  - sobrescrita somente com `--overwrite`;
  - retorno 2 para entrada, caminho ou sobrescrita invalidos;
  - nenhuma dependencia de dispositivo ou `sounddevice`.
- Politica de alinhamento:
  - nenhum padding ou silencio e inserido;
  - o ultimo bloco usa somente amostras existentes;
  - entrada convertida e saida possuem o mesmo numero de amostras;
  - deslocamento por indice igual a zero;
  - 32 ms de latencia algoritmica STFT registrados separadamente;
  - clipping ocorre somente na escrita PCM16 e e contabilizado.
- Parametros congelados:
  - 16 kHz, FFT 512, hop 160;
  - aquecimento 250 ms e historico 500 ms;
  - quantis 0,22 espectral e 0,20 de energia;
  - limiar de fala 6 dB;
  - EMA 0,30/0,005;
  - subtracao alpha 1,5 e piso 0,02;
  - Wiener piso 0,05.
- Matriz:
  - uma fala publica FSDD preparada (`george`);
  - um ruido DEMAND `PCAFETER`;
  - SNRs -5 e 5 dB;
  - blocos 10, 20 e 32 ms;
  - bypass, subtracao causal, Wiener causal;
  - baixa energia offline como referencia nao causal.
- Resultados medios:
  - subtracao causal: 3,36/3,27/3,25 dB de melhoria de SNR para
    10/20/32 ms e 1,22/1,27/1,35 dB de SI-SDR;
  - Wiener causal: 1,54/1,33/1,27 dB de SNR e
    0,74/0,67/0,68 dB de SI-SDR;
  - offline: 4,31 dB de SNR e 2,14 dB de SI-SDR na subtracao;
  - offline: 2,85 dB de SNR e 1,68 dB de SI-SDR no Wiener;
  - nenhum bloco acima do orcamento;
  - estado causal maximo de 60.900 bytes;
  - todos os comprimentos preservados e deslocamento zero.
- Vetores:
  - entrada ruidosa sintetica de 0,75 s;
  - bypass esperado;
  - subtracao causal esperada;
  - configuracao e manifesto SHA-256;
  - a execucao CLI reproduziu exatamente o hash causal esperado
    `47f70c20306c7a602d2b1bb6a320ca6451f8c4f4229e8992ca8a856fb476a3ed`.
- Testes:
  - 30 testes e 9 subtestes aprovados;
  - bypass, comprimentos, ultimo bloco, determinismo, equivalencia direta,
    10/20/32 ms, estereo/8 kHz, entradas invalidas, sobrescrita, finitude,
    reset, hashes e metadados.
- Relatorio:
  - `entrega3.pdf` recompilado em tres passagens e estabilizado em 35 paginas;
  - sem `Overfull`, referencias ou citacoes indefinidas;
  - metodologia e tabela PC-2 inspecionadas visualmente.
- Limitacoes:
  - matriz pequena com uma fala, um ruido e duas SNRs;
  - tempos de arquivo nao representam driver ou dispositivo;
  - referencia offline examina o arquivo completo;
  - sem escuta perceptual;
  - sem validacao Windows prolongada nesta etapa.
- Intervencao humana:
  - nenhuma.
- Dados privados:
  - nenhuma gravacao autoral usada ou versionada;
  - vetores exclusivamente sinteticos;
  - arquivos antigos nao rastreados permaneceram intocados.
- Proximo checkpoint:
  - incorporar voz autoral conforme protocolo, sem reabrir os parametros
    congelados.

## Checkpoint 19 - Protocolo e ingestao de voz autoral (executado apos o 21)

- Data: 2026-06-07.
- Numeracao: checkpoint previsto antes da PC-1, executado agora porque o nucleo
  causal e o processamento de arquivo ja estao congelados.
- Estado:
  - protocolo, modelos, estrutura privada e CLI de ingestao concluidos;
  - nenhuma autorizacao real presumida;
  - nenhuma gravacao autoral realizada ou ingerida.
- Objetivo:
  - preparar a coleta dos tres autores com privacidade, rastreabilidade,
    Sessao A de desenvolvimento e Sessao B de confirmacao.
- Commits:
  - `d13500b` (`docs: adicionar protocolo de voz autoral`);
  - `61a067f` (`code: preparar ingestao de voz autoral`).
- Documentos:
  - `docs/protocolo_voz_autoral.md`;
  - `docs/autorizacao_voz_autoral.md`;
  - `docs/roteiro_voz_autoral.md`;
  - modelos em `dados/templates/authored_voice/`.
- Estrutura local criada e ignorada:
  - `dados/raw/authored_voice/spk01..spk03/session_a..session_b/`;
  - pastas `quiet`, `noise` e `live_noisy`;
  - `dados/private/authored_voice/consent/`;
  - `dados/private/authored_voice/manifests/`;
  - `dados/prepared/authored_voice/`.
- Niveis de autorizacao:
  - `local_only`;
  - `advisor_board`;
  - `public_excerpt`.
- Contrato da ingestao:
  - entrada por manifesto CSV;
  - identificacao apenas por `spk01`, `spk02`, `spk03`;
  - `consent_record_id` obrigatorio;
  - WAV PCM de 8, 16, 24 ou 32 bits;
  - deteccao de vazio, truncamento, silencio e clipping;
  - validacao de taxa, canais e profundidade esperados;
  - bruto somente leitura;
  - media de canais, remocao de DC e reamostragem para mono 16 kHz;
  - escrita PCM16;
  - sem normalizacao, denoising, gate, EQ ou compressao;
  - hashes SHA-256 e relatorio deterministico;
  - recusa de sobrescrita sem `--overwrite`.
- Testes adicionados:
  - estereo 48 kHz;
  - PCM 24 bits;
  - remocao de DC sem normalizacao;
  - clipping, silencio e duracao;
  - divergencia de metadados;
  - consentimento ausente;
  - identidade duplicada;
  - ausente, truncado e caminho fora da raiz;
  - sobrescrita e regeneracao deterministica;
  - esquema do manifesto e retorno da CLI.
- Verificacao:
  - 39 testes e 9 subtestes aprovados;
  - `compileall` aprovado;
  - smoke test sintetico com estereo 48 kHz preparado para mono 16 kHz;
  - nenhum dado privado versionado.
- Intervencao humana necessaria para continuar:
  - cada participante escolher e assinar o nivel de autorizacao;
  - informar equipamento, driver, taxa, canais e profundidade;
  - realizar as Sessoes A e B conforme o guia;
  - colocar os WAVs nas pastas locais;
  - preencher o manifesto privado sem nomes reais.
- Limitacoes:
  - a CLI esta validada apenas com arquivos sinteticos temporarios;
  - nenhum resultado de voz autoral existe ainda;
  - `entrega3.tex` nao foi alterado porque nao ha resultados auditados;
  - Checkpoint 22 depende da coleta humana.
- Proximo checkpoint:
  - Checkpoint 22, avaliacao objetiva autoral congelada, depois da ingestao da
    Sessao B.

### Nota de continuidade - Preparacao para o Checkpoint 22

- Data: 2026-06-07.
- Estado:
  - ferramental de avaliacao objetiva autoral e formulario perceptual
    preparados;
  - nenhuma gravacao autoral real avaliada;
  - Checkpoint 22 ainda nao concluido.
- Codigo:
  - `benchmark_audio/run_authored_evaluation.py`;
  - `tests/test_authored_evaluation.py`;
  - `pytest.ini`.
- Documentacao e modelos:
  - `docs/avaliacao_autoral.md`;
  - `dados/templates/authored_voice/perceptual_rating_template.csv`;
  - atualizacoes em `README_benchmark.md`, `dados/README.md`,
    `dados/templates/authored_voice/README.md`,
    `docs/protocolo_voz_autoral.md`, `docs/diario_tecnico.md` e
    `docs/auditoria_resultados.md`.
- Funcionalidade:
  - consome manifesto preparado;
  - mistura `raw_quiet + raw_noise` em SNRs controladas;
  - compara bypass, subtracao causal, Wiener causal, referencias offline de
    baixa energia e Wavelet refinada;
  - calcula SNR, SI-SDR, MSE, RTF, p95, p99, pior caso e memoria quando ha
    referencia;
  - processa `raw_live_noisy` apenas com estatisticas operacionais;
  - nao salva audio por padrao;
  - recusa arquivos com avisos sem `--allow-warnings`.
- Verificacao:
  - `python -m compileall benchmark_audio realtime_audio`;
  - `python -m pytest -q`: 41 testes e 9 subtestes aprovados.
- Limitacoes:
  - depende de autorizacao, gravacoes, ingestao e revisao humana;
  - nao produz resultados de Sessao B;
  - nao autoriza atualizar `entrega3.tex` com valores autorais ainda
    inexistentes.

## Checkpoint WPT-1/WPT-2 - WPT + Wiener offline inicial

- Data: 2026-06-07.
- Estado: primeira implementacao offline auditavel e primeira rodada DEMAND em
  pasta nova concluidas.
- Preservacao historica:
  - `wavelet_soft` permanece como baseline DWT com MAD e limiarizacao;
  - nenhum CSV historico em `resultados/demand_refinement/tabelas/` foi
    sobrescrito;
  - o novo metodo usa nome proprio: `wavelet_packet_wiener`.
- Codigo:
  - `benchmark_audio/denoise.py`;
  - `benchmark_audio/run_refinement.py`;
  - `tests/test_denoise.py`;
  - `tests/test_refinement.py`.
- Metodo implementado:
  - Wavelet Packet Transform por arquivo;
  - decomposicao configuravel por wavelet e nivel;
  - estimativa de potencia de ruido por quantil rolante em cada subbanda;
  - ganho Wiener suave por coeficiente com piso configuravel;
  - reconstrucao com comprimento preservado e saida `float32` finita.
- Integracao:
  - candidatos WPT ficam atras de `--include-wpt`;
  - familia separada: `wavelet_packet`;
  - comando executado:
    `python -m benchmark_audio.run_refinement --include-wpt --results-dir resultados/wpt_refinement`.
- Rodada:
  - 180 candidatos na validacao, sendo 36 WPT;
  - 72 condicoes de validacao e 72 condicoes finais;
  - resultados em `resultados/wpt_refinement/tabelas/`.
- Melhor WPT por validacao:
  - `wpt_wiener_sym4_l3_rolling_q0.2_w31_f0.1`;
  - validacao: +0,878 dB SNR, +0,200 dB SI-SDR, 25,0% degradacoes;
  - final operacional: +0,366 dB SNR, -0,248 dB SI-SDR, 25,0% degradacoes.
- Comparacao final:
  - DWT refinada historica: +0,026 dB SNR, +0,008 dB SI-SDR, 11,1%
    degradacoes;
  - STFT subtracao baixa energia offline: +4,848 dB SNR, +3,716 dB SI-SDR,
    sem degradacoes;
  - STFT Wiener baixa energia offline: +2,920 dB SNR, +2,253 dB SI-SDR, sem
    degradacoes.
- Interpretacao:
  - a WPT inicial melhora SNR em relacao a DWT limiarizada, mas nao compete com
    STFT no protocolo atual;
  - a queda de SI-SDR no final e a fracao de degradacao impedem conclusao forte;
  - a trilha deve permanecer exploratoria ate nova formulacao e escuta critica.
- Verificacao inicial:
  - `python -m compileall benchmark_audio realtime_audio`;
  - `python -m pytest -q tests\test_denoise.py tests\test_refinement.py`.
- Verificacao final:
  - `python -m compileall benchmark_audio realtime_audio`;
  - `python -m pytest -q`: 44 testes e 10 subtestes aprovados.
- Proximo passo tecnico:
  - investigar versoes WPT com janelamento/blocos, suavizacao de ganho,
    selecao menos orientada so por SNR e, depois, desenho causal com estado
    explicito.

## Checkpoint WPT-3 - Benchmark Wavelet pesado

- Data: 2026-06-07.
- Motivacao: Gabriel apontou que a performance Wavelet parecia estranha e que
  seria necessario insistir mais nas ondaletas antes de fechar a conclusao.
- Estado: rodada pesada `focused` concluida; perfil `max` iniciado e
  interrompido antes de gerar CSVs por custo excessivo de triagem.
- Preservacao:
  - `wavelet_soft` continua baseline historico DWT;
  - resultados historicos em `resultados/demand_refinement/tabelas/` nao foram
    alterados;
  - rodada nova em `resultados/wavelet_heavy_refinement/`;
  - tentativa incompleta `max` marcada em
    `resultados/wavelet_heavy_max_refinement/RUN_INCOMPLETE.txt`.
- Codigo:
  - `benchmark_audio/denoise.py`;
  - `benchmark_audio/run_wavelet_heavy_refinement.py`;
  - `tests/test_wavelet_heavy_refinement.py`.
- Novidade tecnica:
  - adicionado metodo `wavelet_packet_wiener_frames`;
  - WPT aplicada em quadros com overlap;
  - potencia por subbanda estimada ao longo dos quadros;
  - ganho Wiener escalar por subbanda/quadro;
  - reconstrucao por overlap-add;
  - continua sendo metodo offline, nao causal.
- Grade `focused`:
  - 2556 candidatos na triagem de validacao;
  - 720 DWT;
  - 972 WPT por coeficiente;
  - 864 WPT em quadros;
  - 86 candidatos reavaliados na validacao completa;
  - 11 candidatos comparados no final operacional.
- Melhor DWT pesada:
  - `dwt_coif3_l2_soft_global_s0.25`;
  - final: +0,055 dB SNR, +0,008 dB SI-SDR, 4,2% degradacoes.
- Melhor WPT por coeficiente robusta:
  - `wpt_coeff_bior4p4_l2_rolling_quantile_q0.1_w31_f0.05_sm0`;
  - final: +0,393 dB SNR, +0,132 dB SI-SDR, 9,7% degradacoes.
- Melhor WPT em quadros robusta:
  - `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - validacao: +2,236 dB SNR, +0,796 dB SI-SDR, 0,0% degradacoes;
  - final: +3,210 dB SNR, +1,753 dB SI-SDR, 0,0% degradacoes;
  - RTF medio final: 0,00765.
- Melhor WPT em quadros por SNR:
  - `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - validacao: +2,550 dB SNR, +0,573 dB SI-SDR, 6,9% degradacoes;
  - final: +3,524 dB SNR, +1,785 dB SI-SDR, 4,2% degradacoes;
  - RTF medio final: 0,00773.
- Referencias finais:
  - STFT subtracao baixa energia offline: +4,848 dB SNR, +3,716 dB SI-SDR,
    0,0% degradacoes;
  - STFT Wiener baixa energia offline: +2,920 dB SNR, +2,253 dB SI-SDR, 0,0%
    degradacoes;
  - STFT subtracao causal adaptativa: +3,763 dB SNR, +2,648 dB SI-SDR, 0,0%
    degradacoes.
- Interpretacao:
  - a conclusao antiga sobre DWT nao vale para toda a familia Wavelet;
  - WPT em quadros tem desempenho objetivo decente e deve ser tratada como
    candidata exploratoria forte;
  - ainda nao supera a subtracao STFT offline nem a STFT causal em SI-SDR;
  - como usa quantil global por subbanda, nao pode ser chamada de causal;
  - qualquer promocao a candidata principal depende de versao causal ou de
    escuta critica muito favoravel.
- Verificacao:
  - `python -m compileall benchmark_audio realtime_audio`;
  - `python -m pytest -q`: 48 testes e 11 subtestes aprovados.

## Checkpoint WPT-4 - Perfil max Wavelet pesado completo

- Data: 2026-06-08.
- Estado: rodada `max` completa concluida em pasta nova, sem sobrescrever
  resultados historicos.
- Diretorio:
  - `resultados/wavelet_heavy_max_refinement_full/`.
- Comando executado:
  - `python -m benchmark_audio.run_wavelet_heavy_refinement --profile max --results-dir resultados/wavelet_heavy_max_refinement_full --screening-speakers 1 --screening-noises-per-group 1 --full-per-family 20`.
- Metadata:
  - perfil `max`;
  - 8784 candidatos na triagem;
  - 864 DWT;
  - 2160 WPT por coeficiente;
  - 5760 WPT em quadros;
  - 113 candidatos reavaliados na validacao completa;
  - 12 candidatos comparados no final operacional;
  - 72 condicoes de validacao e 72 finais;
  - tempo total registrado: 8929,75 s.
- Selecionadas por familia:
  - DWT: `dwt_coif3_l2_soft_global_s0.15` e
    `dwt_coif3_l2_soft_global_s0.25`;
  - WPT por coeficiente:
    `wpt_coeff_bior4p4_l2_rolling_quantile_q0.1_w31_f0.05_sm0` e
    `wpt_coeff_haar_l2_rolling_quantile_q0.35_w31_f0.2_sm0`;
  - WPT em quadros:
    `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0` e
    `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`.
- Melhor WPT em quadros robusta no `max`:
  - `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - validacao: +2,288 dB SNR, +1,127 dB SI-SDR, 0,0% degradacoes;
  - final: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes;
  - RTF medio final: 0,0325.
- Melhor WPT em quadros por SNR no `max`:
  - `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - validacao: +2,685 dB SNR, +1,050 dB SI-SDR, 4,2% degradacoes;
  - final: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes;
  - RTF medio final: 0,0342.
- Comparacao com `focused`:
  - a robusta `focused`
    `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`
    tinha final +3,210 dB SNR, +1,753 dB SI-SDR e 0,0% degradacoes;
  - a robusta `max` manteve 0,0% degradacoes e melhorou sobretudo SI-SDR
    final, de +1,753 para +1,922 dB;
  - a melhor por SNR `max` superou a melhor por SNR `focused` no final
    (+3,613 contra +3,524 dB SNR) e nao degradou no final, embora tenha
    4,2% degradacoes na validacao.
- Referencias finais preservadas:
  - STFT subtracao baixa energia offline: +4,848 dB SNR, +3,716 dB SI-SDR,
    0,0% degradacoes;
  - STFT Wiener baixa energia offline: +2,920 dB SNR, +2,253 dB SI-SDR,
    0,0% degradacoes;
  - STFT subtracao causal adaptativa: +3,763 dB SNR, +2,648 dB SI-SDR,
    0,0% degradacoes.
- Interpretacao:
  - o `max` encontrou configuracoes WPT em quadros melhores que o `focused`;
  - nao e apenas confirmacao numerica, pois a configuracao `db6` elevou o
    teto WPT final e a `haar` elevou a candidata robusta;
  - tambem nao selecionou algo claramente instavel, mas a configuracao `db6`
    deve ser descrita com cautela porque degradou 4,2% na validacao;
  - a candidata PC principal continua sendo a subtracao STFT causal
    adaptativa, pois ja e causal e ainda tem SI-SDR final maior.
- Restricao metodologica:
  - WPT em quadros continua offline e nao deve ser chamada de causal.
- Proximo fechamento PC:
  - Checkpoint 23: fechar protocolo de escuta critica com audios publicos e
    exemplos selecionados;
  - Checkpoint 24: executar validacao Windows prolongada com parametros PC
    congelados;
  - Checkpoint 25: consolidar decisao de implementacao PC e preparar a
    transferencia para relatorio/defesa, mantendo WPT em quadros como frente
    offline ou futura versao causal/rolante.

## Checkpoint 23 - Fechamento da decisao tecnica PC

- Data: 2026-06-08.
- Estado: decisao tecnica consolidada sem nova rodada numerica.
- Objetivo:
  - limpar a narrativa depois das rodadas causal, PC-2, voz autoral preparada e
    Wavelet pesada;
  - separar implementacao PC, achado cientifico offline e validacao autoral;
  - preparar a proxima continuidade sem reabrir parametros ja congelados.
- Decisao principal:
  - a implementacao PC segue sendo a subtracao STFT causal adaptativa;
  - ela ja tem estado causal, processamento por blocos, parametros congelados e
    contrato reproduzivel em WAV;
  - resultado final operacional preservado: +3,763 dB SNR, +2,648 dB SI-SDR,
    0,0% degradacoes.
- Papel da WPT em quadros:
  - WPT em quadros com overlap e estimativa por subbanda e um achado importante;
  - o perfil `max` elevou a melhor WPT final para +3,613 dB SNR e +2,099 dB
    SI-SDR, com ressalva de 4,2% degradacoes na validacao da configuracao
    `db6`;
  - a candidata robusta `haar` manteve 0,0% degradacoes e +1,922 dB SI-SDR
    final;
  - mesmo assim, a WPT em quadros permanece offline e nao deve ser chamada de
    causal, pois usa informacao temporal do arquivo.
- Papel da voz autoral:
  - protocolo, ingestao, avaliacao objetiva e formulario perceptual estao
    preparados;
  - nenhuma gravacao autoral real foi usada nesta decisao;
  - a voz autoral entra depois como validacao complementar de parametros
    congelados, nao como bloqueio para fechar a decisao PC.
- Narrativa autorizada:
  - STFT causal e o caminho de implementacao PC;
  - WPT em quadros e uma contribuicao experimental offline relevante e uma
    frente futura para versao causal/rolante;
  - voz autoral servira para validar robustez e percepcao em material privado,
    sem ajuste oportunista dos metodos.
- Narrativa proibida:
  - nao afirmar que WPT em quadros e causal;
  - nao afirmar que WPT substituiu a STFT PC;
  - nao usar voz autoral inexistente para reforcar a conclusao;
  - nao tratar a avaliacao autoral como requisito pendente para decidir a
    implementacao PC.
- Documentos sincronizados:
  - `README_benchmark.md`;
  - `docs/checkpoints.md`;
  - `docs/diario_tecnico.md`;
  - `docs/auditoria_resultados.md`;
  - `docs/onboarding_equipe.md`;
  - `docs/plano_wavelet_packet_wiener.md`.
- Proximo checkpoint:
  - Checkpoint 24, validacao Windows prolongada com a STFT causal congelada,
    medindo estabilidade, underflows/overflows, CPU, memoria, jitter e logs por
    tempo suficiente para sustentar a demonstracao PC.

## Checkpoint 24 - Validacao Windows prolongada da STFT causal

- Data: 2026-06-08.
- Estado: validacao operacional concluida no PC atual, sem reabrir parametros.
- Objetivo:
  - exercitar a subtracao STFT causal adaptativa com bloco de 20 ms e
    parametros congelados;
  - medir estabilidade por bloco em self-test sintetico e em captura fisica
    `input-only`;
  - preservar a decisao tecnica do Checkpoint 23.
- Auditoria de partida:
  - `git status --short` mostrou muitas alteracoes e arquivos nao rastreados
    pre-existentes; nada foi revertido;
  - confirmadas as CLIs `realtime_audio/windows_realtime.py`,
    `realtime_audio/process_wav_blocks.py` e o nucleo
    `benchmark_audio/causal.py`;
  - `python -m benchmark_audio.causal --help` nao e uma CLI documentada; o
    contrato do modulo continua sendo a API `CausalSTFTProcessor`;
  - `python -m realtime_audio.windows_realtime --list-devices` listou entradas
    e saidas MME, DirectSound, WASAPI e WDM-KS.
- Dispositivos:
  - a tentativa com `Microfone (USB Audio Device), Windows WASAPI`, indice 49,
    falhou com `Invalid sample rate` para 16 kHz;
  - a validacao fisica usou explicitamente `Microfone (USB Audio Device), MME`,
    indice 2, em modo `--input-only`;
  - nenhum playback, fone Bluetooth ou round-trip fisico foi usado como prova
    de baixa latencia.
- Comandos principais:
  - `python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --noise-mode adaptive --duration 60 --block-ms 20 --output-dir resultados/windows_realtime_longrun --no-save`;
  - `python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --noise-mode adaptive --duration 600 --block-ms 20 --output-dir resultados/windows_realtime_longrun --no-save`;
  - `python -m realtime_audio.windows_realtime --input-only --duration 30 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-dir resultados/windows_realtime_longrun --no-save`;
  - `python -m realtime_audio.windows_realtime --input-only --duration 600 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-dir resultados/windows_realtime_longrun --no-save`.
- Artefatos novos:
  - `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_100642_metrics.json`;
  - `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_100737_metrics.json`;
  - `resultados/windows_realtime_longrun/windows_input_only_stft_subtraction_20ms_20260608_100911_metrics.json`;
  - `resultados/windows_realtime_longrun/windows_input_only_stft_subtraction_20ms_20260608_101937_metrics.json`;
  - CSVs por bloco correspondentes na mesma pasta.
- Self-test sintetico de 600 s:
  - 30.000 blocos processados;
  - media 0,987 ms, p95 1,271 ms, p99 1,594 ms e pior bloco 4,127 ms;
  - RTF medio 0,049 e pior RTF 0,206;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio;
  - latencia algoritmica estimada de 32 ms, sem latencia de stream fisico.
- Captura fisica `input-only` de 600 s:
  - 29.998 blocos registrados;
  - media 1,280 ms, p95 2,205 ms, p99 3,904 ms e pior bloco 6,799 ms;
  - RTF medio 0,064 e pior RTF 0,340;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio, sem underflow/overflow reportado pela CLI;
  - latencia de entrada reportada pelo driver: 40 ms;
  - total estimado registrado no JSON: 72 ms, sendo 32 ms algoritmicos +
    40 ms de entrada.
- Captura fisica curta de 30 s:
  - 1.498 blocos;
  - media 1,215 ms, p99 3,354 ms, pior bloco 6,013 ms;
  - zero blocos acima de 20 ms e `status_counts` vazio.
- Interpretacao:
  - a implementacao PC mostrou estabilidade operacional prolongada no Windows
    para o nucleo STFT causal congelado;
  - a validacao fisica foi `input-only`, portanto comprova captura e
    processamento por blocos, mas nao round-trip de saida;
  - nenhum WAV foi salvo nas rodadas fisicas por uso de `--no-save`;
  - WPT em quadros permanece achado offline e voz autoral permanece validacao
    complementar posterior.
- Proximo checkpoint:
  - consolidar esses resultados no relatorio/defesa ou, se a equipe quiser,
    executar uma rodada full-duplex explicita com entrada/saida cabeadas, sem
    tratar Bluetooth como evidencia de baixa latencia.

## Checkpoint 25 - Consolidacao relatorio/defesa pos-validacao Windows

- Data: 2026-06-08.
- Estado: consolidacao de narrativa concluida, sem nova rodada de audio.
- Objetivo:
  - transferir os resultados do Checkpoint 24 para o relatorio principal;
  - preparar uma fala curta de defesa com os numeros que podem ser citados;
  - manter Bluetooth, WPT e voz autoral nas posicoes corretas da narrativa.
- Alteracoes principais:
  - `entrega3.tex` passou a incluir tabela da validacao Windows prolongada da
    STFT causal adaptativa;
  - as consideracoes finais deixaram de apontar a validacao prolongada como
    pendencia e passaram a registra-la como concluida;
  - `docs/onboarding_equipe.md` foi atualizado para o estado pos-Checkpoint 24;
  - `docs/plano_wavelet_packet_wiener.md` passou a registrar que a WPT continua
    achado offline apos a validacao PC;
  - criado `docs/roteiro_defesa_checkpoint24.md` com mensagem central, numeros
    citaveis e afirmacoes a evitar.
- Numeros consolidados no relatorio/defesa:
  - self-test Windows de 600 s: 30.000 blocos, media 0,987 ms, p95 1,271 ms,
    p99 1,594 ms, pior bloco 4,127 ms, RTF medio 0,049, zero blocos acima de
    20 ms;
  - captura fisica `input-only` de 600 s: 29.998 blocos, media 1,280 ms,
    p95 2,205 ms, p99 3,904 ms, pior bloco 6,799 ms, RTF medio 0,064, zero
    blocos acima de 20 ms;
  - `status_counts` vazio nas duas rodadas longas;
  - latencia de 72 ms no JSON fisico mantida como estimativa input-only
    (32 ms algoritmicos + 40 ms de entrada), nao como `round-trip`.
- Verificacao:
  - compilacao limpa com
    `pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex`,
    executada em duas passagens;
  - `entrega3_build.pdf` gerou 35 paginas e foi copiado para `entrega3.pdf`;
  - busca textual nao encontrou as frases antigas de pendencia de validacao
    prolongada nos arquivos consolidados.
- Limites preservados:
  - nenhuma prova de baixa latencia por Bluetooth;
  - nenhuma medida de playback, loopback ou `round-trip` fisico;
  - nenhum resultado de voz autoral;
  - WPT em quadros continua offline e nao substitui a STFT PC.
- Proximo passo:
  - opcao A: preparar/ensaiar a defesa com o roteiro curto;
  - opcao B: planejar rodada full-duplex cabeada separada, se a equipe quiser
    medir caminho de saida e latencia fisica.

## Checkpoint 26 - Full-duplex cabeado no Windows

- Data: 2026-06-08.
- Estado: demonstracao full-duplex cabeada concluida com estabilidade por
  blocos, mas sem prova de baixa latencia fisica.
- Objetivo:
  - substituir a demonstracao Bluetooth por uma rodada explicita com saida
    cabeada/controlada;
  - manter a subtracao STFT causal adaptativa congelada;
  - verificar captura-processamento-reproducao por 30 s e 600 s.
- Intervencao do usuario:
  - usuario conectou fone cabeado;
  - volume do Windows ajustado para 20/100;
  - usuario confirmou retorno audivel no fone cabeado, sem eco, desconforto ou
    volume inseguro nas rodadas curtas.
  - apos a rodada longa de 10 min, usuario confirmou ausencia de desconforto,
    volume seguro, retorno claro e repasse satisfatorio do som capturado pelo
    microfone para o fone cabeado.
- Dispositivos:
  - entrada usada: `Microfone (USB Audio Device), MME`, indice 2;
  - saida usada: `Alto-falantes (AB13X USB Audio), MME`, indice 8;
  - saida Bluetooth nao foi usada nas rodadas validas.
- Tentativas de baixa latencia via driver:
  - `Microfone (USB Audio Device), WASAPI`, indice 49, com
    `Alto-falantes (AB13X USB Audio), WASAPI`, indice 38, falhou com
    `Invalid sample rate` em 16 kHz;
  - `Microfone (USB Audio Device), MME`, indice 2, com saida WASAPI indice 38,
    falhou com `Illegal combination of I/O devices`;
  - WDM-KS com microfone USB indice 80 e saida AB13X indice 68 falhou com
    `Invalid device`;
  - conclusao: a CLI conseguiu duplex fisico estavel via MME, mas nao abriu
    pareamentos de menor latencia para 16 kHz neste PC.
- Comandos validos:
  - `python -m realtime_audio.windows_realtime --duration 3 --method bypass --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save`;
  - `python -m realtime_audio.windows_realtime --duration 5 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save`;
  - `python -m realtime_audio.windows_realtime --duration 30 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save`;
  - `python -m realtime_audio.windows_realtime --duration 600 --method stft_subtraction --noise-mode adaptive --block-ms 20 --input-device 2 --output-device 8 --output-dir resultados/windows_realtime_wired --no-save`.
- Artefatos:
  - `resultados/windows_realtime_wired/windows_bypass_20ms_20260608_105114_metrics.json`;
  - `resultados/windows_realtime_wired/windows_stft_subtraction_20ms_20260608_105301_metrics.json`;
  - `resultados/windows_realtime_wired/windows_stft_subtraction_20ms_20260608_110542_metrics.json`;
  - `resultados/windows_realtime_wired/windows_stft_subtraction_20ms_20260608_111612_metrics.json`;
  - CSVs por bloco correspondentes;
  - resumo consolidado em `resultados/tabelas/realtime_windows_wired.csv`.
- Rodada STFT cabeada de 30 s:
  - 1.498 blocos;
  - media 1,239 ms, p95 1,761 ms, p99 2,688 ms e pior bloco 4,811 ms;
  - RTF medio 0,062 e pior RTF 0,241;
  - zero blocos acima de 20 ms;
  - `status_counts` vazio.
- Rodada STFT cabeada de 600 s:
  - 29.998 blocos;
  - media 1,259 ms, p95 1,965 ms, p99 3,283 ms e pior bloco 7,301 ms;
  - RTF medio 0,063 e pior RTF 0,365;
  - zero blocos acima de 20 ms;
  - estado maximo 60.900 bytes;
  - `status_counts` vazio.
- Latencia reportada:
  - entrada MME: 40 ms;
  - saida MME cabeada: 200 ms;
  - total estimado no JSON para STFT: 272 ms, sendo 32 ms algoritmicos +
    240 ms de I/O reportado;
  - esse valor e estimativa de driver/stream, nao medida fisica por loopback.
- Interpretacao:
  - a plataforma PC demonstrou captura-processamento-reproducao cabeada por
    10 min sem estouro de orcamento por bloco;
  - o resultado e mais forte que a demonstracao Bluetooth para funcionalidade,
    pois a saida foi cabeada/controlada;
  - a observacao do usuario sustenta conforto operacional local na condicao
    testada, mas nao substitui avaliacao perceptual formal;
  - a latencia reportada pelo MME ainda e alta, portanto nao usar esta rodada
    como prova de baixa latencia ponta a ponta;
  - para medir baixa latencia fisica, seria necessaria medicao de loopback ou
    abrir driver de menor latencia a 16 kHz.
- Proximo passo:
  - polir a CLI/demo final e documentar comandos oficiais da plataforma PC;
  - opcionalmente investigar configuracao de driver/taxa para WASAPI antes de
    qualquer nova afirmacao de baixa latencia.

## Checkpoint 27 - Presets oficiais da demo PC

- Data: 2026-06-08.
- Estado: CLI de demonstracao PC simplificada e testada.
- Objetivo:
  - reduzir risco de erro operacional na defesa;
  - encapsular os comandos oficiais dos Checkpoints 24 e 26;
  - manter os parametros tecnicos congelados.
- Implementacao:
  - `realtime_audio/windows_realtime.py` recebeu `--pc-demo` com presets:
    - `self-test`;
    - `input-only`;
    - `wired`;
  - todos os presets usam `stft_subtraction`, `noise-mode adaptive`, bloco de
    20 ms e `--no-save`;
  - `self-test` grava em `resultados/windows_realtime_longrun`;
  - `input-only` usa entrada indice 2 e grava em
    `resultados/windows_realtime_longrun`;
  - `wired` usa entrada indice 2, saida indice 8 e grava em
    `resultados/windows_realtime_wired`.
- Comandos oficiais:
  - `python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1`;
  - `python -m realtime_audio.windows_realtime --pc-demo input-only --duration 600`;
  - `python -m realtime_audio.windows_realtime --pc-demo wired --duration 600`.
- Documentacao:
  - `realtime_audio/README.md` passou a usar os presets na secao de demo PC;
  - `README_benchmark.md` passou a registrar o comando curto e o equivalente
    expandido da rodada cabeada.
- Verificacao:
  - `python -m pytest tests\test_realtime_audio.py`;
  - resultado: 5 testes passaram;
  - `python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1`
    concluiu e gerou JSON em `resultados/windows_realtime_longrun`.
- Limite:
  - o preset `wired` assume os indices do PC atual; se o Windows reorganizar os
    dispositivos, deve-se rodar `--list-devices` antes e, se necessario, usar o
    comando expandido com indices atualizados.
- Proximo passo:
  - fazer uma auditoria final de release PC: testes automatizados mais amplos,
    comandos oficiais de smoke e checklist de arquivos/artefatos.

## Planejamento pos-Checkpoint 28 - Trilha Virtual Microphone proprio

- Data: 2026-06-08.
- Estado: trilha planejada, nao iniciada tecnicamente.
- Motivacao:
  - usuario manifestou interesse em uma solucao propria, sem depender de
    VB-Cable, SteelSeries Sonar ou outro programa auxiliar como peca final;
  - objetivo desejado: apps externos enxergarem um endpoint proprio, por
    exemplo `PTC Noise Reduction Microphone`.
- Avaliacao tecnica resumida:
  - e tecnicamente possivel criar microfone virtual proprio no Windows;
  - o caminho mais direto para prototipo academico e partir do SYSVAD,
    sample oficial da Microsoft para driver virtual de audio;
  - para desenvolvimento local, pode ser usado modo de teste do Windows;
  - para distribuicao real, driver kernel-mode exige assinatura e processo de
    release pelo ecossistema Microsoft, com possivel certificado EV, Partner
    Center, attestation/HLK e instalador.
- Roadmap planejado:
  - Checkpoint 28: auditoria final de release PC atual;
  - Checkpoint 29: especificacao do Virtual Microphone proprio;
  - Checkpoint 30: ambiente WDK e build do SYSVAD baseline;
  - Checkpoint 31: instalacao local em modo de teste;
  - Checkpoint 32: ponte usuario/driver para audio processado;
  - Checkpoint 33: integracao STFT causal ao pipeline virtual;
  - Checkpoint 34 no roteiro da epoca: interface minima; a numeracao foi
    supersedida depois do fechamento do Checkpoint 33;
  - etapa posterior no roteiro da epoca: auditoria de distribuicao,
    assinatura e custos; a numeracao `Checkpoint 35` foi supersedida.
- Prompt de continuidade criado:
  - `prompt_continuidade_pos_checkpoint27_release_pc_virtual_mic.md`.
- Regra de continuidade:
  - nao pular direto para driver antes de fechar o Checkpoint 28;
  - nao prometer driver distribuivel sem discutir assinatura e requisitos;
  - tratar VB-Cable apenas como possivel controle/MVP temporario, nao como
    solucao final desejada.

## Checkpoint 28 - Auditoria final de release PC

- Data: 2026-06-08.
- Estado: auditoria documental e verificacao automatizada concluidas.
- Objetivo:
  - fechar a superficie de release da plataforma PC atual;
  - confirmar que os presets oficiais continuam executaveis;
  - registrar comandos, artefatos, metricas e limitacoes em checklist proprio;
  - nao reabrir parametros nem iniciar driver antes de concluir a auditoria.
- Auditoria de partida:
  - `git status --short --branch` mostrou `main...origin/main [ahead 26]`,
    varias alteracoes rastreadas e muitos arquivos nao rastreados ja
    existentes;
  - nenhuma alteracao pre-existente foi revertida;
  - foram lidos `README_benchmark.md`, `realtime_audio/README.md`,
    `docs/roteiro_defesa_checkpoint24.md`, `realtime_audio/windows_realtime.py`
    e `tests/test_realtime_audio.py`;
  - foram revisados os registros dos Checkpoints 24 a 27 em
    `docs/checkpoints.md` e `docs/diario_tecnico.md`.
- Verificacoes executadas:
  - `python -m pytest`;
  - resultado: 50 testes passaram;
  - `python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1`;
  - resultado: concluiu e gerou
    `resultados/windows_realtime_longrun/synthetic_stft_subtraction_20ms_20260608_114451_metrics.json`;
  - o smoke teve 50 blocos, media 0,977 ms, p95 1,391 ms, p99 1,556 ms,
    pior bloco 1,612 ms, RTF medio 0,049, zero blocos acima de 20 ms,
    estado maximo 60.900 bytes e `status_counts` vazio.
- Verificacao nao executada:
  - `python -m realtime_audio.windows_realtime --pc-demo wired --duration 30`
    nao foi rodado nesta retomada porque abre saida fisica e depende de fone
    cabeado/volume seguro e autorizacao explicita.
- Artefato criado:
  - `docs/release_pc_checklist.md`.
- Conteudo do checklist:
  - comandos oficiais;
  - artefatos esperados;
  - metricas que sustentam estabilidade;
  - passos de demonstracao segura;
  - limitacoes obrigatorias;
  - itens fora do release PC.
- Interpretacao:
  - a plataforma PC pode ser apresentada como estavel por blocos no Windows;
  - a evidencia full-duplex cabeada de 10 min continua valida como
    funcionalidade captura-processa-reproduz;
  - a auditoria nao transforma os valores de latencia estimada em medicao
    fisica ponta a ponta;
  - WPT em quadros e voz autoral permanecem fora do release PC atual.
- Proximo passo:
  - abrir a trilha Virtual Microphone proprio pelo Checkpoint 29, com
    especificacao, requisitos e limites de assinatura.

## Checkpoint 29 - Especificacao do Virtual Microphone proprio

- Data: 2026-06-08.
- Estado: especificacao inicial concluida; nenhuma compilacao WDK executada.
- Objetivo:
  - definir uma arquitetura propria para expor um endpoint de captura do tipo
    `PTC Noise Reduction Microphone`;
  - separar o DSP validado em usuario do driver virtual de audio;
  - registrar alternativas, requisitos e riscos antes de iniciar SYSVAD.
- Fontes oficiais consultadas:
  - SYSVAD Virtual Audio Device Driver Sample;
  - Sample Audio Drivers;
  - Driver signing;
  - Introduction to Test-Signing;
  - Partner Center for Windows Hardware.
- Arquitetura proposta:
  - app/servico de usuario captura microfone fisico, processa blocos com
    `CausalSTFTProcessor` e publica audio processado em buffer local;
  - driver virtual baseado em SYSVAD expoe endpoint de captura para apps
    externos e consome esse buffer;
  - a primeira ponte deve ser validada com sinal sintetico antes de usar
    microfone real.
- Alternativas registradas:
  - SYSVAD como caminho principal para microfone proprio;
  - APO como rota complementar quando o foco for processar endpoint existente;
  - VB-Cable apenas como controle temporario, nao solucao final.
- Requisitos levantados:
  - Visual Studio com C++;
  - Windows SDK;
  - WDK;
  - repositorio `Windows-driver-samples` com submodulos;
  - permissao administrativa e maquina de teste;
  - test-signing para desenvolvimento local;
  - certificado EV, Partner Center e possivel attestation/HLK para distribuicao
    real.
- Artefato criado:
  - `docs/virtual_mic_architecture.md`.
- Limites:
  - nao ha driver proprio pronto;
  - nao ha endpoint `PTC Noise Reduction Microphone` instalado;
  - nao ha integracao DSP-driver;
  - test signatures sao apenas para desenvolvimento e teste;
  - distribuicao real nao deve ser prometida sem assinatura e fluxo Microsoft.
- Proximo passo:
  - Checkpoint 30: verificar ambiente WDK, obter `Windows-driver-samples`,
    inicializar submodulos e compilar SYSVAD baseline sem modificacoes.

## Checkpoint 30 - Ambiente WDK e SYSVAD baseline

- Data: 2026-06-11.
- Estado: concluido; toolchain instalado, SYSVAD baseline compilado sem
  alteracoes e pacote `Debug|x64` auditado.
- Auditoria de partida:
  - `git status --short --branch` no repositorio PTC mostrou
    `main...origin/main [ahead 26]`, com alteracoes rastreadas e arquivos nao
    rastreados pre-existentes;
  - nenhuma alteracao pre-existente foi revertida.
- Ambiente encontrado:
  - sistema: Windows 11 Home Single Language, versao `10.0.26200`, x64;
  - Visual Studio Community 2026 `18.1.1`;
  - MSBuild `18.0.5.56406`;
  - MSVC `14.50.35717`;
  - carga `Desktop development with C++` instalada;
  - componente `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` instalado;
  - ATL atual instalado;
  - Windows SDK instalado: `10.0.26100.0`, produto
    `10.1.26100.7175`;
  - WDK nao localizado no registro, no Visual Studio Installer ou em
    `C:\Program Files (x86)\Windows Kits\10`;
  - ausentes headers `Include\10.0.26100.0\km`, targets
    `Windows Kits\10\build`, `WindowsDriver.Common.props`, `inf2cat.exe` e
    `stampinf.exe`.
- Repositorio oficial:
  - clone em
    `%USERPROFILE%\source\repos\Windows-driver-samples`;
  - remoto:
    `https://github.com/microsoft/Windows-driver-samples.git`;
  - branch `main`, commit
    `e99ae832b48b245404f9bd750af4864247b061e8`;
  - submodulo WIL inicializado no commit
    `3c00e7f1d8cf9930bbb8e5be3ef0df65c84e8928`;
  - arvore do repositorio de samples permaneceu limpa.
- Sample:
  - caminho:
    `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad`;
  - solucao: `audio\sysvad\sysvad.sln`;
  - configuracoes atuais: `Debug|x64`, `Release|x64`, `Debug|ARM64` e
    `Release|ARM64`;
  - projetos usam os toolsets `WindowsApplicationForDrivers10.0` e
    `WindowsKernelModeDriver10.0`.
- Comandos executados:

```powershell
git clone https://github.com/microsoft/Windows-driver-samples.git `
  %USERPROFILE%\source\repos\Windows-driver-samples
cd %USERPROFILE%\source\repos\Windows-driver-samples
git submodule update --init

& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe' `
  audio\sysvad\sysvad.sln `
  /t:Build /m /p:Configuration=Debug /p:Platform=x64 /v:minimal
```

- Resultado do build:
  - codigo de saida `1`;
  - seis erros `MSB8020`;
  - `SwapAPO`, `DelayAPO`, `AecAPO`, `KeywordDetectorContosoAdapter` e
    `KwsAPO` nao encontraram `WindowsApplicationForDrivers10.0`;
  - `EndpointsCommon` nao encontrou `WindowsKernelModeDriver10.0`;
  - `TabletAudioSample` e o projeto de pacote nao chegaram a produzir
    artefatos porque dependem dos projetos anteriores;
  - nenhum `.sys`, `.cat`, `package.cer` ou pasta de saida `package` foi
    gerado.
- Log completo:
  - `resultados/sysvad_checkpoint30/sysvad_debug_x64_build.log`;
  - log diagnostico do MSBuild com 3.447.158 bytes.
- Dependencias faltantes confirmadas:
  - componente individual `Windows Driver Kit`/WDK VSIX no Visual Studio;
  - Windows Driver Kit instalado no sistema;
  - par SDK/WDK compativel.
- Comparacao com
  `_wdk_utils/winget/configs/wdk-desktop.vsconfig`:
  - para `Debug|x64`, tambem faltam
    `Microsoft.VisualStudio.Component.VC.ATL.Spectre`,
    `Microsoft.VisualStudio.Component.VC.ATLMFC.Spectre` e
    `Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre`;
  - ferramentas e bibliotecas Spectre ARM64/ARM64EC tambem nao estao
    instaladas, mas so sao necessarias se o build ARM64 for executado.
- Plano de correcao confirmado em documentacao oficial atual:
  - instalar o componente `Windows Driver Kit` e os componentes Spectre x64
    faltantes pelo Visual Studio Installer, usando o `.vsconfig` oficial como
    referencia;
  - instalar Windows SDK 28000 e WDK 28000, recomendados para Visual Studio
    2026;
  - pacotes WinGet localizados em 2026-06-11:
    `Microsoft.WindowsSDK.10.0.28000` versao `10.0.28000.1721` e
    `Microsoft.WindowsWDK.10.0.28000` versao `10.1.28000.1839`;
  - reiniciar o Visual Studio/terminal apos a instalacao;
  - confirmar headers `km`, targets de driver, `inf2cat.exe` e
    `stampinf.exe`;
  - repetir primeiro o build `Debug|x64` sem retarget manual e sem alterar o
    sample.
- Conclusao do ambiente:
  - Visual Studio Community 2026 atualizado de `18.1.1` para `18.7.0`;
  - MSBuild atualizado para `18.7.1.23011`;
  - Windows SDK `10.0.28000.1721` instalado;
  - WDK `10.1.28000.1839`, assembly `10.0.28000.1839`, instalado;
  - componentes `Component.Microsoft.Windows.DriverKit`,
    `Microsoft.VisualStudio.Component.VC.ATL.Spectre`,
    `Microsoft.VisualStudio.Component.VC.ATLMFC.Spectre` e
    `Microsoft.VisualStudio.Component.VC.Runtimes.x86.x64.Spectre`
    instalados;
  - headers `Include\10.0.28000.0\km`, arvore `build\10.0.28000.0`,
    `WindowsDriver.Common.props`, `stampinf.exe`, `Inf2Cat.exe` e os
    toolsets de driver foram localizados;
  - a primeira instalacao do SDK ficou incompleta por concorrencia MSI e foi
    reparada com reinstalacao forcada pelo WinGet;
  - um registro MSI orfao do runtime VC++ x86 `14.34.31938` bloqueou a
    atualizacao do Visual Studio; o registro foi corrigido com o solucionador
    oficial Microsoft e o runtime x86 `14.51.36247` foi reparado;
  - o reparo do Visual Studio terminou com codigo `3010`; a reinicializacao
    foi executada pelo usuario e o estado do instalador foi validado depois
    do boot.
- Compatibilidade do host de build:
  - o comando original com
    `MSBuild\Current\Bin\MSBuild.exe` passou a reconhecer os toolsets, mas
    falhou porque o WDK 28000 nao fornece `build\...\bin\x86\InfVerif.dll` e
    o `ApiValidator` x86 encerrou com codigo `193`;
  - o mesmo build com
    `MSBuild\Current\Bin\amd64\MSBuild.exe` terminou com codigo `0`;
  - o sample nao foi retargetado nem editado.
- Comando aprovado:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\amd64\MSBuild.exe' `
  audio\sysvad\sysvad.sln `
  /t:Build /m `
  /p:Configuration=Debug `
  /p:Platform=x64 `
  /v:minimal
```

- Pacote gerado:
  - caminho:
    `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad\x64\Debug\package`;
  - certificado:
    `%USERPROFILE%\source\repos\Windows-driver-samples\audio\sysvad\x64\Debug\package.cer`;
  - 10 arquivos no pacote: `TabletAudioSample.sys`, `AecApo.dll`,
    `DelayAPO.dll`, `KeywordDetectorContosoAdapter.dll`, `KWSApo.dll`,
    `SwapAPO.dll`, tres INFs componentizados e `sysvad.cat`;
  - `TabletAudioSample.sys` SHA-256:
    `413794EC01534AAFD0B45073144A34E86048CFE444F7B2B66881996F817AD5F3`;
  - `sysvad.cat` SHA-256:
    `891EF974D39FB22784612D4D4DCD56A270504788E1985B635BB2B34DB39DC62C`;
  - `package.cer` SHA-256:
    `ACCDB75C1395C53786C3AF6DB44012D773D665B8FBA214B7375C029C9B3D1215`;
  - assinatura de teste criada com
    `CN="WDKTestCert augus,134256250901790469"`;
  - `Get-AuthenticodeSignature` encontra a assinatura, mas a cadeia termina
    em raiz ainda nao confiavel porque o certificado de teste nao foi
    instalado, como exigido pelas restricoes deste checkpoint.
- Log aprovado:
  - `resultados/sysvad_checkpoint30/sysvad_debug_x64_build_vs187_wdk28000_amd64.log`;
  - 10.771.324 bytes;
  - SHA-256:
    `EE101121F354D8F192422815B2D3390E967466660CF4719D5933591F1FE08BFD`.
- Estado final do clone:
  - branch `main`, commit
    `e99ae832b48b245404f9bd750af4864247b061e8`;
  - WIL em `3c00e7f1d8cf9930bbb8e5be3ef0df65c84e8928`;
  - `git status --short --branch` permaneceu limpo.
- Verificacao final apos reinicializacao:
  - Visual Studio `18.7.0`, estado `isComplete=true`,
    `isLaunchable=true` e `isRebootRequired=false`;
  - MSBuild amd64 `18.7.1.23011`;
  - componentes WDK, ATL Spectre, ATL/MFC Spectre e runtimes Spectre
    confirmados como selecionados;
  - novo build `Debug|x64` concluido com codigo `0`, sem erros nem avisos;
  - log:
    `resultados/sysvad_checkpoint30/sysvad_debug_x64_build_post_reboot.log`;
  - log com 5.886 bytes e SHA-256
    `9C8D3478887F97F1E9E6A3D1713CC6ABC79DA85632172EBCCDBC905B44D738D8`;
  - o `TabletAudioSample.sys` manteve o SHA-256 registrado;
  - o catalogo regenerado passou a ter SHA-256
    `DBFEFC712F9F9EBB0862EF48829428E2ABA3E62DF53680166B6FF83F21BDCB4A`;
  - o clone oficial permaneceu limpo.
- Limites preservados:
  - nenhum driver foi instalado;
  - test-signing nao foi habilitado;
  - nenhuma configuracao de boot foi alterada;
  - o SYSVAD nao foi modificado;
  - nao existe endpoint `PTC Noise Reduction Microphone`.
- Proximo passo:
  - abrir o Checkpoint 31 somente com auditoria administrativa de BitLocker,
    Secure Boot e integridade de memoria;
  - preparar e registrar plano explicito de reversao antes de instalar
    certificado, driver ou alterar test-signing;
  - preferir maquina de teste separada da maquina principal.

## Checkpoint 31 - Instalacao controlada do SYSVAD

- Data de abertura: 2026-06-11.
- Estado: Fase 1 concluida; instalacao nao iniciada e aguardando preparacao de
  recuperacao e consentimento explicito.
- Auditoria administrativa somente leitura:
  - firmware UEFI com Secure Boot habilitado;
  - BitLocker em `C:` totalmente desligado: volume descriptografado,
    protecao `Off`, metodo `None` e zero protetores;
  - nao existe senha de recuperacao BitLocker porque o volume nao esta
    protegido;
  - VBS em execucao e Integridade de memoria/HVCI habilitada;
  - `TESTSIGNING` ausente da entrada BCD atual;
  - nenhum dispositivo `Root\Sysvad_ComponentizedAudioSample`;
  - certificado de teste ausente de `LocalMachine\Root` e
    `LocalMachine\TrustedPublisher`;
  - nenhum ponto de restauracao, copia de sombra ou Windows Backup encontrado;
  - Windows Recovery Environment habilitado na particao de recuperacao;
  - unidade `C:` saudavel, mas com apenas `11,37 GiB` livres.
- Integridade do pacote reconfirmada:
  - `TabletAudioSample.sys`:
    `413794EC01534AAFD0B45073144A34E86048CFE444F7B2B66881996F817AD5F3`;
  - `sysvad.cat`:
    `DBFEFC712F9F9EBB0862EF48829428E2ABA3E62DF53680166B6FF83F21BDCB4A`;
  - `package.cer`:
    `ACCDB75C1395C53786C3AF6DB44012D773D665B8FBA214B7375C029C9B3D1215`.
- Evidencias:
  - `resultados/sysvad_checkpoint31/audit_readonly.ps1`;
  - `resultados/sysvad_checkpoint31/audit_readonly_admin.json`;
  - `resultados/sysvad_checkpoint31/README.md`.
- Plano de reversao preparado:
  - registrar o ID de instancia criado para o dispositivo raiz;
  - registrar os `oem*.inf` associados aos tres INFs antes de remover qualquer
    pacote;
  - remover somente o dispositivo e os pacotes registrados;
  - remover o certificado somente pelo thumbprint
    `7ABED3D56ECAFD8B95C7B98451237673A53F899B`;
  - desabilitar `TESTSIGNING`, reiniciar com aviso, reabilitar Secure Boot no
    firmware e validar ausencia de todos os artefatos;
  - `/force` nao sera usado sem novo consentimento.
- Bloqueio atual:
  - a auditoria inicial nao encontrou restauracao ou backup local;
  - o espaco livre e baixo;
  - desabilitar Secure Boot reduz a protecao de inicializacao e exige operacao
    manual no firmware;
  - nenhuma etapa disruptiva deve ser executada sem preparacao de recuperacao
    e consentimento explicito.
- Preparacao de recuperacao autorizada:
  - Protecao do Sistema habilitada em `C:`;
  - ponto de restauracao `PTC3527 Checkpoint 31 pre-SYSVAD` criado e
    verificado, sequencia `281`;
  - uso inicial do VSS: `58,3 MB`, alocacao `320 MB` e limite `1,13 GB`;
  - espaco livre apos a criacao: aproximadamente `11,06 GiB`;
  - BCD exportado antes de qualquer alteracao para
    `resultados/sysvad_checkpoint31/bcd_pre_sysvad.bak`;
  - SHA-256 do backup BCD:
    `98F09CF7BBCE86C67D5D7B0B187996D70691F64D6ECDFB4FB2F1BA06A4B60A26`;
  - listagem BCD preservada sem entrada `TESTSIGNING`;
  - nenhuma configuracao de boot foi alterada e nenhum reinicio foi
    solicitado.
- Compatibilidade com HVCI:
  - o log de build confirma assinatura `/ph` com SHA-256 para
    `TabletAudioSample.sys` e `sysvad.cat`;
  - Integridade de memoria deve permanecer habilitada na primeira tentativa.
- Verificacao apos alteracao manual do firmware:
  - boot do Windows em `2026-06-11 01:57:30 -03:00`;
  - Secure Boot confirmado como desabilitado;
  - BitLocker continuou desligado e `C:` totalmente descriptografado;
  - VBS e HVCI continuaram ativos;
  - ponto de restauracao `281` continuou presente;
  - `TESTSIGNING` ainda nao foi habilitado;
  - certificado e dispositivo SYSVAD continuaram ausentes;
  - espaco livre observado: `9,83 GiB`.
- Habilitacao de modo de teste:
  - `bcdedit.exe /set TESTSIGNING ON` executado em terminal elevado;
  - codigo de saida `0`;
  - BCD confirmou `testsigning Yes`;
  - Secure Boot estava desabilitado, BitLocker desligado e ponto de
    restauracao `281` presente antes da alteracao;
  - nenhum reinicio foi executado automaticamente;
  - a configuracao ainda depende de reinicializacao para entrar em vigor;
  - nenhum certificado ou driver foi instalado nesta etapa.
- Verificacao apos reinicializacao em modo de teste:
  - marca d'agua `Modo de Teste` confirmada visualmente pelo usuario;
  - BCD confirmou `testsigning Yes`;
  - Secure Boot permaneceu desabilitado;
  - BitLocker permaneceu desligado;
  - VBS e HVCI permaneceram ativos;
  - ponto de restauracao `281` permaneceu presente;
  - nenhum dispositivo SYSVAD existia antes da instalacao.
- Certificado de teste:
  - instalado exatamente uma vez em `LocalMachine\Root`;
  - instalado exatamente uma vez em `LocalMachine\TrustedPublisher`;
  - thumbprint:
    `7ABED3D56ECAFD8B95C7B98451237673A53F899B`;
  - `TabletAudioSample.sys` e `sysvad.cat` passaram a apresentar assinatura
    `Valid`;
  - nenhum driver foi instalado junto com o certificado.

### Incidente de instalacao e reversao de emergencia

- Horario da instalacao: 2026-06-11, aproximadamente `02:11 -03:00`.
- Resultado: Checkpoint 31 interrompido; o SYSVAD nao e seguro para nova
  tentativa nesta maquina principal.
- A instalacao do INF base criou:
  - dispositivo `ROOT\MEDIA\0004`;
  - pacote publicado `oem50.inf`;
  - servico `sysvad_componentizedaudiosample`.
- Ao iniciar o dispositivo, `TabletAudioSample.sys` provocou duas telas azuis
  `SYSTEM_THREAD_EXCEPTION_NOT_HANDLED` (`0x7E`).
- A reinicializacao nao foi solicitada pelo script: foi causada pelo bugcheck
  durante a inicializacao do driver.
- Os minidumps foram preservados em
  `resultados/sysvad_checkpoint31/crash_dumps`.
- Analise WinDbg com o PDB local:
  - falha identica nos dois dumps;
  - `tabletaudiosample!BthHfpDevice::Init+0x6cc`;
  - fonte `BthhfpDevice.cpp`, linha `264`;
  - `WdfIoTargetOpen` da interface Bluetooth HFP/SCO retornou
    `STATUS_ACCESS_DENIED` (`0xC0000022`);
  - o build `Debug` executou um breakpoint de kernel `INT 3`
    (`0x80000003`) no caminho de erro;
  - bucket:
    `0x7E_80000003_tabletaudiosample!unknown_function`.
- A Restauracao do Sistema foi tentada pelo usuario, mas falhou por falta de
  espaco ao restaurar `%ProgramFiles%\WindowsApps` para `AppxStaging`.
- Reversao executada por identificadores exatos:
  - removido `ROOT\MEDIA\0004`;
  - removido `oem50.inf` sem `/force`;
  - removido o servico orfao `sysvad_componentizedaudiosample`;
  - removido o certificado dos dois stores;
  - configurado `TESTSIGNING OFF`;
  - nenhum reinicio automatico foi executado.
- Verificacao antes do reinicio:
  - zero dispositivo SYSVAD;
  - zero pacote `oem50.inf`;
  - zero certificado nos stores registrados;
  - zero servico SYSVAD;
  - BCD com `testsigning No`.
- Pendencia de retorno seguro:
  - concluida em 2026-06-11.
- Erro de processo reconhecido:
  - a instalacao de um driver kernel Debug na maquina principal foi um risco
    excessivo;
  - `11 GiB` livres eram suficientes para criar o ponto VSS, mas nao
    suficientes para confiar em uma restauracao completa de aplicativos;
  - build e assinatura validos nao comprovam seguranca de execucao do driver;
  - continuidades futuras exigem VM adequada ou maquina de teste separada.
- Auditoria final de seguranca:
  - Secure Boot habilitado;
  - `TESTSIGNING` desabilitado;
  - VBS e HVCI ativos;
  - zero dispositivo, pacote, servico e certificado SYSVAD residual;
  - nenhum novo bugcheck ou desligamento inesperado desde o boot de
    `2026-06-11 02:37:00 -03:00`;
  - estado seguro confirmado pelo script
    `resultados/sysvad_checkpoint31/final_safety_audit.ps1`;
  - SHA-256 do resultado:
    `C0BB03DB7E3DEB226E43171719ACFAD239590EF1EDE837CF828923D9429965A3`.
- Decisao:
  - Checkpoint 31 nao concluido funcionalmente;
  - instalacao local na maquina principal encerrada;
  - proxima tentativa somente em VM com snapshot ou maquina fisica separada;
  - antes da VM, liberar espaco: `C:` tem aproximadamente `10,8 GiB` livres.

### Retomada segura em VM e conclusao do Checkpoint 31

- Data: 2026-06-11.
- Estado: concluido em VM, incluindo instalacao, validacao apos novo boot e
  reversao completa.
- Alvo isolado:
  - VirtualBox `7.2.8`;
  - Windows 11 Pro 25H2 x64;
  - VM `PTC3527-SYSVAD-LAB`, 8 GiB, 4 vCPUs, chipset PIIX3;
  - disco virtual no HD externo `E:`;
  - Secure Boot desativado e TPM 2.0 somente no convidado;
  - host mantido com Secure Boot, VBS e HVCI ativos.
- Snapshots:
  - `base-limpa`;
  - `pre-sysvad`;
  - `testsigning-pronto`;
  - `sysvad-instalado`;
  - `checkpoint31-revertido`.
- Instalacao validada:
  - dispositivo `ROOT\MEDIA\0000`;
  - nome `SYSVAD (with APO Extensions)`;
  - servico `sysvad_componentizedaudiosample` em `RUNNING`;
  - base `oem5.inf`, APO `oem6.inf` e extensao `oem7.inf`;
  - certificado
    `7ABED3D56ECAFD8B95C7B98451237673A53F899B` nos stores `Root` e
    `TrustedPublisher`;
  - `TESTSIGNING Yes` e marca visual de modo de teste;
  - endpoints virtuais de reproducao e captura iniciados;
  - instalacao persistiu apos desligamento e novo boot;
  - nenhuma tela azul ocorreu na VM.
- Reversao validada apos novo boot:
  - `ROOT\MEDIA\0000` removido;
  - `oem7.inf`, `oem6.inf` e `oem5.inf` removidos sem `/force`;
  - certificado removido dos dois stores pelo thumbprint exato;
  - `TESTSIGNING No`;
  - nenhum dispositivo ou pacote SYSVAD residual;
  - marca visual de modo de teste ausente.
- Incidente operacional da VM:
  - duas desconexoes fisicas do HD externo pausaram a VM e geraram erros de
    E/S no volume `E:`;
  - os deltas afetados foram descartados e `pre-sysvad` foi restaurado;
  - o volume permaneceu integro;
  - o HD deve permanecer conectado enquanto a VM estiver ligada, pausada,
    salvando snapshot ou desligando.
- Resultado:
  - o problema anterior foi contido ao host fisico e ao caminho Bluetooth HFP
    do build Debug;
  - o mesmo pacote oficial funcionou no alvo virtual sem interface Bluetooth
    HFP correspondente;
  - Checkpoint 31 concluido sem integrar o DSP e sem criar endpoint PTC.
- Proximo passo:
  - Checkpoint 32: definir e validar a ponte usuario/driver com sinal
    sintetico, restaurando `sysvad-instalado` quando o endpoint for necessario.
- Prompt de continuidade criado:
  - `prompt_continuidade_checkpoint32_ponte_usuario_driver.md`;
  - para um pacote modificado, partir de `testsigning-pronto`, nao instalar por
    cima do snapshot baseline `sysvad-instalado`.

## Checkpoint 32 - Ponte usuario/driver com PCM sintetico

- Data de abertura: 2026-06-11.
- Estado: concluido em 2026-06-11, com validacao funcional, snapshot e
  reversao completa na VM.
- Branch dedicada:
  `codex/checkpoint32-user-driver-bridge`.
- Endpoint escolhido:
  `MicIn` / `External Microphone Headphone`.
- Contrato:
  - versao `1`;
  - PCM mono, 16 bits, 16 kHz;
  - 320 frames e 640 bytes por bloco de 20 ms;
  - fila de 50 blocos;
  - underrun gera silencio;
  - overrun descarta o bloco novo;
  - um produtor por vez.
- Implementacao:
  - interface de dispositivo com GUID proprio e referencia `\ptcpcm`;
  - IOCTLs `METHOD_BUFFERED` para configurar, escrever, consultar estatisticas
    e resetar;
  - ring buffer nao paginado protegido por spin lock;
  - consumo no ponto que antes chamava `ToneGenerator::GenerateSine`;
  - produtor CLI e capturador WASAPI exclusivo.
- Verificacao:
  - teste da fila aprovado;
  - SYSVAD `Debug|x64` compilado, catalogado e assinado;
  - produtor e capturador x64 ligados com runtime estatico;
  - `ROOT\MEDIA\0000`, tres pacotes, servico e oito endpoints passaram no
    boot;
  - WAV de 12 s confirmou mono, 16 bits, 16 kHz, pico `0,25` e tom dominante
    de `440,0 Hz`;
  - versao de protocolo, tamanho de bloco e sequencia invalidos foram
    rejeitados;
  - overrun descartou blocos novos e underrun produziu silencio;
  - segundo produtor recebeu `ERROR_BUSY (170)` enquanto o dono estava
    conectado, e a reconexao funcionou apos cleanup;
  - um novo boot manteve dispositivo, servico, endpoints e produtor
    funcionais;
  - nenhum artefato instalado no host.
- Snapshots preservados:
  - `checkpoint32-pre-bridge`;
  - `checkpoint32-bridge-installed` (primeira iteracao, sem a referencia de
    abertura);
  - `checkpoint32-functional-validated-v2`;
  - `checkpoint32-revertido`.
- Reversao final:
  - removidos `ROOT\MEDIA\0000`, `oem7.inf`, `oem6.inf` e `oem5.inf`;
  - certificado removido de `Root` e `TrustedPublisher`;
  - `TESTSIGNING` desativado;
  - auditoria apos boot confirmou zero dispositivo, pacote, servico,
    endpoint e certificado residual.
- Resultados:
  `resultados/sysvad_checkpoint32/`.
- Proxima etapa:
  Checkpoint 33, ligando captura real e `CausalSTFTProcessor` ao produtor.

## Checkpoint 33 - Microfone real, DSP causal e endpoint virtual

- Data de abertura: 2026-06-12.
- Estado: concluido em 2026-06-12, com validacao funcional e tres ciclos de
  reabertura na VM.
- Escopo:
  - capturar microfone real no processo de usuario;
  - processar blocos de 20 ms com `CausalSTFTProcessor`;
  - converter `float32` para PCM16 somente na fronteira do protocolo;
  - alimentar a ponte v1 sem alterar o driver;
  - validar o endpoint por cliente externo.
- Implementacao:
  - novo cliente em `realtime_audio/ptc_pcm_bridge.py`;
  - descoberta da interface por GUID via `CfgMgr32`;
  - IOCTLs v1 empacotados com layouts de 24, 664 e 112 bytes;
  - thread de escrita desacoplada do callback de audio;
  - pacing orientado por profundidade da fila do driver;
  - fila local limitada, descartando o bloco mais antigo quando cheia;
  - novo modo `--virtual-mic` na CLI Windows.
- Verificacao host-side:
  - suite completa: `53 passed`, `11 subtests passed`;
  - autoteste causal preservado;
  - host confirmou ausencia da interface PTC PCM;
  - nenhum driver, certificado ou modo de teste instalado no host.
- Verificacao funcional na VM:
  - Python 3.12 e dependencias instalados no convidado;
  - entrada fisica nao nula confirmada por sonda direta;
  - controle sintetico de 440 Hz aprovado depois do novo boot;
  - bypass e `stft_subtraction` chegaram ao endpoint virtual;
  - STFT principal: media `9,772 ms`, p95 `18,656 ms` e latencia total
    estimada de `72 ms`;
  - `write_errors=0`, overruns e erros de sequencia iguais a zero;
  - tres ciclos estabilizados consumiram 244, 223 e 187 blocos;
  - nenhum bugcheck ou travamento.
- Limitacoes:
  - sinal fisico baixo durante a captura;
  - polling WASAPI da VM abaixo da taxa do produtor em alguns trechos;
  - descartes locais intencionais para limitar latencia, sem overrun no
    driver.
- VM na abertura:
  - `E:` saudavel;
  - VM em `poweroff`;
  - restaurado `checkpoint32-functional-validated-v2`;
  - snapshot `checkpoint33-pre-dsp-user` preservado;
  - como a restauracao repôs `audio_in=off`, a entrada foi reabilitada e um
    segundo snapshot foi criado;
  - snapshot atual `checkpoint33-pre-dsp-user-audio-in`;
  - entrada de audio do VirtualBox habilitada;
  - nenhum processo foi executado no convidado.
- Bundle:
  - `resultados/sysvad_checkpoint33/checkpoint33_python_bundle.zip`;
  - SHA-256
    `2670007743FF0E87383CF02F1A7A0A215AC156FE4760F6E9FD0213B8AED14E9E`.
- Resultados:
  - `resultados/sysvad_checkpoint33/host_mic_rerun_20260612/`;
  - snapshot final `checkpoint33-functional-validated`.
- Proxima etapa:
  Checkpoint 34, priorizando captura com nivel acustico controlado e
  refinamento do consumo/latencia antes de uma avaliacao perceptual.
- Incidente de abertura:
  - o HD externo foi desconectado durante o bootstrap;
  - Guest Control e API do VirtualBox ficaram bloqueados;
  - `E:` retornou saudavel e nao dirty;
  - desligamento ACPI nao concluiu em mais de 60 s;
  - a instancia foi encerrada e apareceu como `aborted`;
  - o delta foi descartado pela restauracao de
    `checkpoint33-pre-dsp-user-audio-in`;
  - estado recuperado: VM `poweroff`, snapshot protegido atual e
    `audio_in=on`;
  - a continuidade aguarda estabilizacao fisica da conexao do HD.

## Checkpoint 34 - Nivel controlado e refinamento de latencia

- Data: 2026-06-12.
- Estado: concluido, com matriz controlada valida, defaults congelados,
  evidencias no host e snapshot final limpo.
- Telemetria adicionada:
  - residencia media, p95 e maxima na fila local;
  - idade dos blocos descartados;
  - profundidade media, p95 e maxima da fila do driver;
  - taxas de submissao e envio;
  - descarte no timeout de drenagem;
  - latencia total incluindo buffers da ponte.
- Correcao de interpretacao:
  - os `72 ms` do Checkpoint 33 somavam apenas algoritmo e entrada;
  - a fila da ponte nao estava incluida;
  - a nova estimativa continua sendo por componentes, nao round-trip.
- Entrada controlada:
  - sinal deterministico via VB-Audio Virtual Cable;
  - pico `0,10`, RMS `0,026197`;
  - baseline eletrico reproduzivel, nao ensaio acustico fisico.
- Matriz com fila local de quatro blocos:
  - profundidade 1: 238 consumidos, 326 underruns, `181,50 ms`;
  - profundidade 2: 410 consumidos, 56 underruns, `182,36 ms`;
  - profundidade 4: 414 consumidos, 24 underruns, `201,57 ms`;
  - zero overruns, erros de escrita ou sequencia em todos os casos.
- Decisao:
  - `--bridge-target-depth 2`;
  - `--bridge-user-queue 4`;
  - profundidade 2 reduz fortemente underruns sem os 20 ms extras da
    profundidade 4.
- Tentativa inconclusiva:
  - a matriz de fila local 1/2/4 sofreu pausa anormal do Guest Control;
  - o capturador terminou antes do produtor;
  - a rodada registrou zero consumo e `input overflow`;
  - esses dados nao foram usados na decisao.
- Verificacao host-side:
  - `55 passed`, `11 subtests passed`;
  - modulos compilados sem erro.
- Artefatos:
  - `resultados/sysvad_checkpoint34/README.md`;
  - `resultados/sysvad_checkpoint34/latency_matrix_summary.csv`;
  - `checkpoint34_python_bundle.zip`, SHA-256
    `07D5B9A5BA7FE0EA2FC5E22DA90D9EE4880E35EA2DB40E88715F15DB1F1EA208`;
  - `checkpoint34_results.zip`, SHA-256
    `99D7D76DC1BC93FD37B6FEEB5D3C5801DDEBA0F4A239792DBA2BDB63E0357C85`.
- Estado final:
  - delta experimental descartado pela restauracao de
    `checkpoint34-pre-latency-refinement`;
  - snapshot `checkpoint34-latency-validated`;
  - UUID `a4354c01-6d82-4ed5-ae68-e613acdd75b3`;
  - VM em `poweroff`;
  - `E:` saudavel, `OK` e nao sujo;
  - SteelSeries Sonar restaurado como captura padrao do host.
- Proxima etapa:
  - interface minima de controle;
  - depois, avaliacao perceptual com nivel acustico fisico controlado.
- Continuidade preparada:
  - `prompt_continuidade_checkpoint35_interface_controle.md`;
  - `mensagem_novo_chat_checkpoint35.md`.

## Checkpoint 35 - Interface mínima de controle

- Data: 2026-06-12.
- Estado: concluído, com validação no host, validação funcional na VM,
  evidências e snapshot final.
- Implementação:
  - `realtime_audio/virtual_mic_control.py`;
  - `realtime_audio/virtual_mic_ui.py`;
  - controlador independente de `tkinter`;
  - estados `parado`, `iniciando`, `ativo`, `parando` e `erro`;
  - snapshots imutáveis de status e métricas;
  - captura, DSP e ponte fora da thread visual;
  - stop idempotente e fechamento com limite de três segundos;
  - persistência em `%LOCALAPPDATA%\PTC3527\virtual_mic_ui.json`;
  - configuração corrompida cai nos defaults com aviso.
- Interface:
  - seletor do microfone físico;
  - iniciar/parar;
  - agressividade explícita, mantendo `α=1,5` como padrão;
  - medidor RMS suavizado;
  - endpoint, estado, blocos, descartes, underruns, overruns, erros e
    latência estimada.
- Defaults preservados:
  - STFT causal adaptativa;
  - 16 kHz;
  - blocos de 20 ms;
  - profundidade da ponte `2`;
  - fila local `4`;
  - protocolo PCM v1 e driver inalterados.
- Verificação:
  - `62 passed`, `11 subtests passed`;
  - `compileall` aprovado;
  - host sem driver abre a UI e informa endpoint desconectado;
  - três ciclos iniciar/parar aprovados na VM;
  - medidor e métricas responsivos;
  - cliente externo recebeu 352.000 frames e 11.150 amostras não nulas;
  - persistência aprovada;
  - fechamento ativo aprovado;
  - contenção aprovada com `WinError 170`;
  - WAV privado removido após análise.
- Artefatos:
  - `resultados/sysvad_checkpoint35/README.md`;
  - `checkpoint35_python_bundle.zip`, SHA-256
    `536E4E7FC27F7D6761E9618A1CD4DCA5CDB759F9152CFFBCF5A2EA559FAB18D4`;
  - `checkpoint35_vm_results.zip`, SHA-256
    `97A60B13F401922FF8C251B59C72C9B8C000A173E5FA0B27A6C2015FEBE46302`.
- Snapshots:
  - pré-UI `checkpoint35-pre-control-ui`, UUID
    `a2242464-5d2e-4071-b65a-430e8e42ebe1`;
  - final `checkpoint35-control-ui-validated`, UUID
    `17eae767-97b4-4b16-89ba-6e4af54310f0`.
- Estado final:
  - o VirtualBox marcou a instância como `aborted` após o desligamento;
  - o snapshot funcional foi restaurado para descartar o delta terminal;
  - VM em `poweroff`;
  - `audio_in=on`;
  - `E:` saudável, `OK` e não sujo;
  - captura padrão do host em SteelSeries Sonar.
- Próximo checkpoint sugerido:
  - avaliação perceptual com nível acústico físico controlado, sem reabrir os
    parâmetros DSP congelados.

## Checkpoint 36 - Validação acústica com HyperX

- Data: 2026-06-12.
- Estado: concluído, com caminho físico completo, cenários acústicos, escuta
  A/B, estabilidade e fechamento seguro da VM.
- HyperX:
  - endpoint `Microfone (USB Audio Device)`;
  - descritor USB `HyperX Quadcast`;
  - `VID_098C&PID_16DF`;
  - identificado por nome e propriedades PnP, sem depender de índice fixo.
- Nível:
  - pico de fala `-12,52 dBFS`;
  - RMS de fala `-32,55 dBFS`;
  - RMS de silêncio `-73,99 dBFS`;
  - separação de `41,44 dB`;
  - zero clipping.
- Caminho validado:
  HyperX -> VM -> Python -> STFT causal adaptativa -> ponte PCM v1 ->
  endpoint SYSVAD -> cliente externo.
- Cenário limpo:
  - bruto `-7,14 dBFS` de pico e `-28,28 dBFS` RMS;
  - processado `-7,20 dBFS` de pico e `-29,78 dBFS` RMS;
  - áudio não nulo e sem clipping nos dois lados.
- Cenário ruidoso:
  - ruído marrom em telefone a 35 cm, volume `100/150`;
  - boca a 20 cm do HyperX;
  - redução de `2,75 dB RMS` no trecho de ruído sem fala;
  - redução de `2,14 dB RMS` durante voz com ruído.
- Estabilidade de 630 s:
  - 27.638 blocos processados;
  - 23.143 enviados;
  - 4.491 descartes locais;
  - 10.626 underruns;
  - zero overruns e zero erros de escrita;
  - latência estimada final `211,4 ms`;
  - zero processos residuais.
- Escuta A/B privada:
  - bruto claramente preferido nos dois cenários;
  - inteligibilidade `4/5` e naturalidade `5/5`;
  - ausência de artefatos `2/5`;
  - pipocos presentes nos dois caminhos e muito mais severos no processado;
  - avaliação de uma pessoa, sem validade estatística.
- Privacidade:
  - WAVs preservados somente em pasta privada autorizada fora do repositório;
  - hashes e métricas em `resultados/sysvad_checkpoint36/`;
  - todo áudio removido da VM antes do snapshot final.
- Verificação:
  - `62 passed`, `11 subtests passed`;
  - `compileall` aprovado;
  - nenhum código, driver, protocolo ou parâmetro DSP alterado.
- Snapshot final:
  - `checkpoint36-hyperx-acoustic-validated`;
  - UUID `95b7a812-c34c-4967-9c7c-15415a31b980`.
- Estado final:
  - VM em `poweroff`;
  - `audio_in=on`;
  - `E:` saudável, `OK` e não sujo;
  - SteelSeries Sonar restaurado como captura padrão;
  - host sem dispositivo, serviço ou certificado SYSVAD/PTC.
- Classificação:
  **Protótipo funcional, com validação perceptual pendente**.
  O caminho completo funciona, mas os pipocos associados a underruns e
  descartes impedem declarar qualidade acústica suficiente.

## Checkpoint 37 - Diagnóstico de pipocos

- Data: 2026-06-12.
- Estado: interrompido antes da matriz acústica por instabilidade do
  VirtualBox Guest Control.
- Concluído:
  - detector objetivo de continuidade e testes sintéticos;
  - timestamps e intervalos de callbacks;
  - rastreamento de descartes, blocos de origem e cadência da ponte;
  - polling configurável e instrumentação do cliente externo;
  - fonte determinística contínua sem voz;
  - snapshot pré-diagnóstico
    `checkpoint37-pre-pop-diagnostics`, UUID
    `e47138eb-df0d-4d27-9948-e17503b7cc25`.
- Não concluído:
  - comparação válida entre bruto, pré-ponte e endpoint;
  - correlação acústica com descartes e underruns;
  - mitigação contra o baseline;
  - retorno a ensaio físico com o HyperX;
  - snapshot final do checkpoint.
- Motivo:
  - sessões do Guest Control presas em `starting` e `VERR_TIMEOUT`;
  - nenhuma rodada produziu WAV ou métricas suficientes para inferir a
    fronteira dos pipocos.
- Estado restaurado:
  - VM em `poweroff`, no snapshot pré-diagnóstico;
  - `audio_in=on`;
  - captura padrão no HyperX direto, `Microfone (USB Audio Device)`;
  - `E:` saudável, operacional e não sujo;
  - nenhuma credencial temporária preservada.
- Classificação mantida:
  **Protótipo funcional, com validação perceptual pendente**.

## Checkpoint 37 - Retomada interativa e matriz concluída

- Data: 2026-06-12.
- A VM histórica foi preservada no HD externo e clonada de forma consolidada
  para o SSD interno como `PTC3527-SYSVAD-LAB-FAST`.
- A execução local na sessão gráfica eliminou o bloqueio do Guest Control.
- Captura bruta e saídas pré-ponte de bypass e STFT não apresentaram blocos
  zerados, ausentes, repetidos, saltos ou descontinuidades.
- A STFT pré-ponte processou 622 blocos, com p95 `5,594 ms`, pior bloco
  `13,825 ms` e zero blocos acima de 20 ms.
- A primeira fronteira com defeitos objetivos foi o endpoint após a ponte.
- No bypass, reduzir o polling do consumidor de 10 ms para 2 ms:
  - elevou blocos enviados de 509 para 580;
  - reduziu descartes locais de 97 para 26;
  - reduziu underruns de 17 para 5;
  - reduziu zeros excedentes no endpoint de 90 para 22.
- Na STFT, 2 ms reduziu underruns de 17 para 7, mas os descartes locais e zeros
  excedentes não melhoraram de forma monotônica em uma única repetição.
- Todos os cenários tiveram zero overruns, zero erros de escrita e zero erros
  de sequência.
- Decisão:
  - a origem dominante está no transporte/consumo após a saída pré-ponte;
  - polling de 2 ms é mitigação promissora, ainda não congelada como padrão;
  - parâmetros DSP, driver e protocolo PCM v1 permanecem inalterados.
- Estado final:
  - VM original e clone em `poweroff`;
  - clone rápido no snapshot `checkpoint37-pop-diagnostics-validated`, UUID
    `f3f72efa-0aed-41db-b444-4fa06f1afd62`;
  - `audio_in=on`;
  - HyperX direto restaurado como captura padrão;
  - clipboard e pasta compartilhada transitória desabilitados;
  - `E:` saudável, operacional e não sujo.
- Classificação:
  **Protótipo funcional, com validação perceptual pendente**.

## Checkpoint 38 - Polling pareado e retorno ao HyperX

- Data: 2026-06-13.
- Três pares STFT de 60 s alternaram polling de 10 ms e 2 ms.
- Agregado em 10 ms: 8.899 enviados, 95 descartes, 72 underruns e 97 zeros
  excedentes.
- Agregado em 2 ms: 8.972 enviados, 20 descartes, 54 underruns e 25 zeros
  excedentes.
- O polling de 2 ms reduziu underruns nos três pares e passa a ser a
  configuração preferida do capturador de diagnóstico.
- Retorno privado ao HyperX:
  - 998 blocos processados e 960 enviados;
  - 34 descartes locais, 4 no fechamento e 21 underruns;
  - zero overruns, erros de escrita ou sequência;
  - p95 `6,017 ms`, pior bloco `18,636 ms`;
  - nenhum bloco acima de 20 ms.
- Escuta A/B privada:
  - bruto A preferido;
  - B recebeu notas `4/5`, `4/5` e `2/5` para inteligibilidade,
    naturalidade e ausência de artefatos;
  - os pipocos desapareceram nos dois arquivos;
  - persistiram travamentos nas bordas;
  - B introduziu chiado e apresentou mais ruído de fundo.
- Guest Control voltou a funcionar no clone SSD e deve ser o modo padrão de
  operação autônoma.
- Estado final:
  - clone rápido em `poweroff`;
  - snapshot `checkpoint38-poll2-hyperx-validated`;
  - UUID `e74ea911-08a6-4778-a7a2-a5a4ab191480`;
  - áudio privado removido da VM;
  - HyperX direto como captura padrão;
  - clipboard e compartilhamentos transitórios desabilitados;
  - VM original preservada;
  - `E:` saudável, operacional e não sujo.
- Classificação:
  **Protótipo funcional, com validação perceptual pendente**.

## Checkpoint 39 - Fronteira de chiado, piso e bordas

- Data: 2026-06-13.
- Três pares determinísticos `bypass`/STFT compararam bruto, pré-bridge e
  endpoint com polling de 2 ms.
- Na STFT, o pré-bridge reduziu em média:
  - `4,12 dB` na banda de 4–8 kHz contra o bruto;
  - `1,72 dB` no piso RMS total.
- No endpoint STFT houve aumento médio de:
  - `4,00 dB` na banda de 4–8 kHz contra o pré-bridge;
  - `15,66 dB` no piso RMS total.
- A análise exploratória mostrou elevação agregada depois da saída imediata do
  DSP, mas não localizou a causa do chiado durante fala. A fronteira permanece
  aberta entre `musical noise` pré-bridge, drops/underruns, endpoint e captura
  externa.
- O par privado já autorizado mostrou deslocamento de bordas:
  - A ativo de aproximadamente 40 ms a 18,64 s;
  - B ativo de aproximadamente 1,86 s a 19,94 s.
- Foram preparados, fora do repositório, pares de corte comum e corte mais
  fade de 80 ms. Nenhuma nova voz foi gravada.
- Retorno perceptual:
  - o corte comum eliminou o travamento nas bordas;
  - o fade não trouxe benefício adicional;
  - o chiado de B persistiu durante a fala;
  - A bruto permaneceu preferido.
- O frontend GUI foi necessário para manter a cadência do áudio virtualizado;
  em `headless`, o stream desacelerou fortemente.
- A matriz terminou por Guest Control, mas o shutdown encerrou o canal antes
  do retorno e uma nova sessão encontrou `VERR_DUPLICATE`.
- O fechamento foi recuperado autonomamente por teclado virtual do
  VirtualBox, sem `poweroff` forçado na rodada válida.
- Snapshot final:
  `checkpoint39-quality-boundary-validated`, UUID
  `21ad4f02-4dfa-48d1-b683-7a6e7b502160`.
- Estado final: clone e VM original desligados; HyperX padrão; clipboard
  desabilitado; nenhum compartilhamento transitório; `E:` saudável e não
  sujo.
- Classificação mantida:
  **Protótipo funcional, com validação perceptual pendente**.

## Checkpoint 40 - Separacao entre DSP e transporte

- Data: 2026-06-13.
- Nenhuma nova voz foi gravada.
- Foi preparado um trio privado `raw`, pre-bridge e endpoint com corte comum
  de 16,86 s e sem fade.
- Uma fonte deterministica identificavel por bloco reconstruiu as listas
  exatas de envios e descartes.
- Nos blocos preservados, a correlacao mediana minima entre pre-bridge e
  endpoint foi `0,99999936`, com pior erro RMS mediano de `-95,47 dBFS`.
- As diferencas no transporte ficaram concentradas em blocos ausentes,
  underruns e lacunas zero-sinal.
- Em atividade, a STFT elevou a densidade media de picos tonais de `3,10`
  para `8,79` por bloco antes da ponte, evidencia compativel com
  `musical noise`.
- `drop-newest` foi a unica mitigacao testada e foi rejeitada:
  - underruns cairam de `260` para `199` em media;
  - descartes subiram de `97,5` para `216`;
  - preservacao ativa recuperada caiu de `18,0%` para `8,1%`;
  - a fracao de zeros nao melhorou.
- Estado final seguro:
  - clone em `poweroff`;
  - snapshot `checkpoint40-transport-separated-validated`;
  - UUID `693e8851-f905-4e98-b526-671c904965e9`;
  - VM original intocada;
  - HyperX direto restaurado;
  - `E:` saudavel e nao sujo;
  - `81 passed`, `11 subtests passed`.
- Retorno perceptual do trio:
  - A bruto foi considerado perfeito, sem chiado;
  - B pre-bridge apresentou chiado metalizado leve durante a voz;
  - C endpoint apresentou chiado metalizado consideravelmente mais intenso,
    tambem durante a voz.
- Conclusao causal:
  - o artefato nasce no DSP como `musical noise` correlacionado a fala;
  - o caminho posterior agrava perceptualmente o artefato;
  - como os blocos preservados sao equivalentes, o agravamento nao foi
    localizado como alteracao espectral dentro desses blocos;
  - perdas, lacunas, transicoes zero-sinal, endpoint e captura externa
    permanecem candidatos ao agravamento.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 41 - Limite da suavizacao temporal do ganho

- Data: 2026-06-13.
- A tomada privada autorizada do Checkpoint 38 foi reprocessada offline, sem
  nova gravacao e com o mesmo estado causal do realtime.
- A familia testada foi suavizacao temporal causal do ganho da subtracao
  espectral, com coeficientes `0.50`, `0.70`, `0.85` e `0.93`.
- O baseline offline reproduziu o pre-bridge congelado com correlacao
  `0.99999199` e erro RMS `-76.98 dBFS`.
- A reducao de densidade de picos tonais ficou entre `0.36%` e `2.91%`.
- As variantes mais fortes perderam envelope, energia e ate aproximadamente
  `1 dB` adicional em 4-8 kHz.
- Nenhuma variante atingiu o gate de 10% sem abafamento.
- Decisao:
  - familia rejeitada;
  - nenhum par privado A/B preparado;
  - nenhuma escuta humana solicitada;
  - nenhum ensaio ponta a ponta executado;
  - `gain_smoothing=0.0` preservado como default.
- Validacao: `84 passed`, `11 subtests passed` e
  `CHECKPOINT41_VM_VALIDATION=OK`.
- Estado final:
  - clone em `poweroff`;
  - snapshot `checkpoint41-musical-noise-limit-validated`;
  - UUID `12ea0826-47f6-48c1-a1b1-2701f000e19a`;
  - VM original intocada;
  - HyperX direto como captura padrao;
  - `E:` saudavel e nao sujo.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 42 - Limite do Wiener causal

- Data: 2026-06-13.
- A mesma tomada privada autorizada foi processada integralmente antes do
  corte comum de 16,86 s.
- O baseline de subtracao foi comparado ao Wiener causal existente com pisos
  `0.02`, `0.05`, `0.08` e `0.10`.
- O baseline reproduziu novamente o pre-bridge congelado com correlacao
  `0.99999199` e erro RMS de `-76.98 dBFS`.
- O Wiener elevou a flatness mediana em aproximadamente 15%, mas reduziu a
  densidade de picos tonais em somente `1.90%` a `2.13%`.
- Envelope e energia foram preservados, mas nenhuma variante atingiu o gate
  tonal de 10%.
- Decisao:
  - Wiener causal rejeitado como mitigacao deste artefato;
  - nenhum par privado preparado;
  - nenhuma escuta humana solicitada;
  - nenhum ensaio ponta a ponta executado.
- A VM validou deterministicamente o Wiener com fonte sintetica sem voz.
- Foi observada divergencia entre o registro do Checkpoint 41 e o app
  persistente: a assinatura implantada nao inclui `gain_smoothing`.
- Validacao: `84 passed`, `11 subtests passed` e
  `CHECKPOINT42_VM_VALIDATION=OK`.
- Estado final:
  - clone em `poweroff`;
  - snapshot `checkpoint42-wiener-limit-validated`;
  - UUID `b9909e84-c1d7-4948-9c5f-21870ff57f69`;
  - VM original intocada;
  - HyperX direto como captura padrao;
  - `E:` saudavel e nao sujo.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 43 - Limite da Wavelet causal

- Data: 2026-06-13.
- O caminho realtime `wavelet_soft` foi reproduzido offline com historico
  causal de 512 amostras e blocos de 320 amostras.
- Foram mantidos `db4`, limiarizacao soft, estrategia global e escala 1.0;
  somente os niveis 3, 4 e 5 variaram.
- A reducao de densidade tonal ficou entre `6.74%` e `8.34%`.
- A perda adicional ficou em aproximadamente `3.84 dB` em 2-4 kHz e
  `10.50 dB` em 4-8 kHz.
- Nenhuma variante atingiu o gate tonal de 10% ou o gate de preservacao de
  alta frequencia.
- Decisao:
  - Wavelet com escala padrao rejeitada por abafamento;
  - nenhum par privado preparado;
  - nenhuma escuta humana solicitada;
  - nenhum ensaio ponta a ponta executado.
- A VM validou deterministicamente os tres niveis com fonte sintetica sem voz.
- O aviso numerico do PyWavelets em coeficientes nulos foi registrado; a saida
  saneada permaneceu finita.
- Validacao: `84 passed`, `11 subtests passed` e
  `CHECKPOINT43_VM_VALIDATION=OK`.
- Estado final:
  - clone normalizado em `poweroff`;
  - snapshot `checkpoint43-wavelet-limit-validated`;
  - UUID `2a530e40-1981-4321-839f-88060d78cc2c`;
  - VM original intocada;
  - HyperX direto como captura padrao;
  - `E:` saudavel e nao sujo.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 44 - Limite da escala Wavelet

- Data: 2026-06-13.
- Foram mantidos `db4`, nivel 3, modo soft, estrategia global e janela causal
  de 832 amostras.
- Somente a escala do limiar variou: `0.10`, `0.25`, `0.50` e `0.75`.
- A escala `0.10` reduziu picos em `4.07%` e ainda perdeu `1.93 dB` adicionais
  em 4-8 kHz.
- A escala `0.50` atingiu `10.13%` de reducao tonal, mas perdeu `2.42 dB` em
  2-4 kHz e `7.64 dB` em 4-8 kHz.
- Nao foi encontrada regiao de compromisso sem abafamento.
- Decisao:
  - shrinkage DWT causal encerrado para este artefato;
  - nenhum par privado preparado;
  - nenhuma escuta humana solicitada;
  - nenhum ensaio ponta a ponta executado;
  - parametro nao implantado no app.
- A VM validou deterministicamente as quatro escalas com fonte sintetica.
- Validacao: `84 passed`, `11 subtests passed` e
  `CHECKPOINT44_VM_VALIDATION=OK`.
- Estado final:
  - clone em `poweroff`;
  - snapshot `checkpoint44-wavelet-threshold-limit-validated`;
  - UUID `3024cc30-6a67-436b-9154-36d3b57529c8`;
  - VM original intocada;
  - HyperX direto como captura padrao;
  - `E:` saudavel e nao sujo.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 45 - WPT causal validada

- Data: 2026-06-13.
- Foi implementada uma WPT causal minima com estado explicito, sem integracao
  ao app:
  - quadro 640, bloco 320 e contexto de 40 ms;
  - `haar`, nivel 3;
  - historico rolante de 25 blocos;
  - quantil 0.20 e piso de ganho 0.20.
- A potencia atual atualiza o estimador somente depois de gerar a saida atual.
- Sete testes novos cobrem prefixo, reset, aquecimento, finitude, memoria,
  custo e bloco parcial.
- Em sintese, a WPT obteve SNR `8.05 dB` contra `8.14 dB` da STFT, com menos
  picos tonais e p95 de `0.53 ms`.
- Na tomada privada, com configuracao congelada antes do uso:
  - reducao tonal `11.72%`;
  - flatness `3.70x`;
  - mudanca adicional 2-4 kHz `-0.27 dB`;
  - mudanca adicional 4-8 kHz `-0.24 dB`.
- Todos os gates objetivos passaram.
- Nenhum par perceptual foi criado e nenhuma integracao foi iniciada.
- Validacao: `91 passed`, `11 subtests passed`;
  VM `2.74 ms` medios e 2.144 bytes de estado.
- Estado final:
  - clone em `poweroff`;
  - snapshot `checkpoint45-causal-wpt-validated`;
  - UUID `2255a9ed-2bb7-43c5-8b2c-5d10a70c140d`;
  - VM original intocada;
  - HyperX direto como captura padrao;
  - `E:` saudavel e nao sujo.
- Proximo gate: um unico par A/B pre-bridge no Checkpoint 46.
- Classificacao mantida:
  **Prototipo funcional, com validacao perceptual pendente**.

## Checkpoint 46 - WPT rejeitada e trilha DSP encerrada

- Data: 2026-06-13.
- A tomada integral autorizada foi reprocessada com:
  - baseline STFT causal;
  - WPT causal congelada no Checkpoint 45.
- Foi criado fora do repositorio um unico par pre-bridge:
  - mono PCM16 a 16 kHz;
  - corte comum de 269.760 amostras, ou 16,86 s;
  - sem fade e sem normalizacao.
- Hash do baseline:
  `8e959dcc22566872464b2ac5a7f7baa2060cd6156f37eeabbd35a0ed50217422`.
- Hash da WPT:
  `1143240aa5bcfa8ab0eb06045f289ce20c5ee263e5ae171f32c9f063c007d325`.
- Nenhuma VM, ponte, aplicacao ou captura de endpoint foi iniciada.
- Na escuta humana, o baseline `A` venceu em todos os criterios:
  - inteligibilidade;
  - naturalidade;
  - menor chiado metalizado;
  - preferencia geral.
- Decisao explicita: rejeitar a WPT `B`.
- Os ganhos objetivos do Checkpoint 45 nao se converteram em melhoria
  perceptual.
- A WPT nao foi integrada; o Checkpoint 47 foi cancelado.
- O par privado foi removido depois da decisao, preservando somente hashes e
  metadados.
- A trilha DSP esta tecnicamente encerrada.
- Classificacao:
  **Prototipo funcional integrado, sem melhoria perceptual aprovada do DSP**.

## Checkpoint 46-R - Reabertura controlada para STFT causal

- Data: 2026-06-13.
- O usuario reabriu explicitamente a investigacao perceptual.
- A rejeicao anterior da WPT foi preservada e nao sera reinterpretada.
- Claude Code 2.1.177 foi consultado em tres rodadas somente leitura.
- A primeira proposta externa foi criticada por:
  - inverter o efeito do piso espectral sobre o residuo;
  - interpretar spectral flatness no sentido incorreto;
  - chamar variacao de piso de mudanca de lei de ganho;
  - exigir ganhos objetivos que poderiam eliminar melhoria perceptual.
- Depois da replica, houve convergencia para um ensaio causal de seis bracos:
  - estimadores `E0(q=0.22, alpha=0.30)` e
    `E1(q=0.35, alpha=0.40)`;
  - subtracao com piso 0.02;
  - subtracao com piso 0.05;
  - Wiener com piso 0.05.
- A matriz inicial tem `2 x 3 = 6` configuracoes.
- Nenhum codigo DSP foi alterado e a VM permaneceu desligada.
- Uma matriz maior so sera autorizada se o ensaio pequeno produzir candidato
  objetivo sem regressao.
- WPT permanece fora do escopo.
- Estado:
  **Investigacao STFT causal reaberta, com experimento discriminante definido**.

### Resultado do ensaio discriminante

- O avaliador causal de seis bracos foi implementado e testado.
- Foram processadas 72 condicoes publicas de validacao.
- Nenhum WAV foi gerado e nenhuma voz privada foi usada.
- Resultado:
  - `E0-S05` ficou praticamente equivalente ao baseline;
  - `E1-S02` e `E1-S05` elevaram as medias, mas tiveram `8,33%` de
    degradacoes e regressao perceptual objetiva;
  - `E0-W05` e `E1-W05` reduziram picos tonais, mas perderam SI-SDR alem do
    gate.
- Nenhum desafiante passou os gates.
- Decisao publica: `stop_no_public_candidate`.
- A VM nao foi iniciada e o split final operacional recebeu somente o
  baseline congelado.
- `E1-W05` foi registrado como hipotese futura, sem promocao post-hoc.
- Validacao: `99 passed`, `11 subtests passed`.
- Estado:
  **Investigacao 46-R encerrada no gate publico, sem novo candidato**.

## Checkpoint 46-R/LIT - Harness do benchmark de literatura

- Data: 2026-06-13.
- Foi aberto um protocolo separado para comparar:
  - baseline STFT causal congelado;
  - OM-LSA + IMCRA;
  - WebRTC APM Noise Suppression;
  - RNNoise;
  - DeepFilterNet.
- SpeexDSP ficou como reserva.
- GTCRN passou a triagem inicial de licenca, checkpoint e streaming, mas ficou
  fora da primeira bateria.
- O harness comum registra hashes das misturas, metadados dos adaptadores,
  metricas pareadas, RTF, latencia e memoria.
- A primeira execucao processou somente o baseline nas 72 condicoes publicas
  de validacao.
- As oito metricas comparadas reproduziram exatamente o `E0-S02` do ensaio
  anterior.
- `pystoi 0.4.1` foi fixado. O baseline apresentou variacao media de STOI de
  `-0,01819`, contraste que sera preservado sem decisao por metrica isolada.
- Nenhum candidato foi selecionado; split final, audio privado e VM continuam
  bloqueados.
- Estado:
  **Harness de literatura validado; integracao incremental dos algoritmos
  pendente**.

### OM-LSA + IMCRA

- A primeira implementacao seguiu os parametros publicados para 16 kHz:
  Hamming 512/128, decisao dirigida 0,92, IMCRA `D=120`, `V=15`, `U=8`,
  `alpha_s=0,9`, `alpha_d=0,85`, `beta=1,47` e
  `Gmin=-25 dB` sob ausencia de fala.
- Testes cobrem determinismo, prefixo causal, finitude, convergencia em ruido
  estacionario, limites do ganho e preservacao de comprimento.
- Resultado nas 72 condicoes de validacao:
  - SNR: `+0,8985 dB`;
  - SI-SDR: `+0,8506 dB`;
  - STOI: `-0,00499`;
  - densidade tonal: `11,5774`;
  - correlacao de envelope: `0,96008`;
  - RTF: `0,0716`;
  - zero degradacoes de SNR.
- O baseline suprimiu substancialmente mais ruido, enquanto OM-LSA/IMCRA
  preservou melhor STOI e envelope.
- A tonalidade media caiu, mas piorou no grupo `OOFFICE`; portanto nao ha
  promocao antecipada.
- Uma auditoria interna removeu clipping indevido por `Gmin` e corrigiu o
  rastreador para subjanela corrente mais `U-1` minimos anteriores.
- Os resultados corrigidos substituem os valores preliminares anteriores.
- O split final, a VM e o audio privado continuam bloqueados.

### RNNoise 0.2

- A tag `v0.2` foi fixada no commit
  `904a876dce1f9ab8860c0a5000ed151f9f6eef58`.
- O modelo oficial `0b50c45` foi baixado da Xiph e verificado por SHA-256.
- O adaptador nativo usa stdin/stdout binario `float32`, processo isolado e
  resampling central do harness.
- Um defeito inicial de modo texto do Windows foi detectado pelos gates de
  finitude/determinismo e corrigido antes da matriz.
- O atraso foi medido por impulso em `20 ms`; a saida e alinhada para metricas,
  sem esconder a latencia registrada.
- Resultado nas 72 condicoes:
  - SNR `+9,3893 dB`;
  - SI-SDR `+9,3925 dB`;
  - STOI `-0,00769`;
  - densidade tonal `18,2612`;
  - envelope `0,79418`;
  - banda 4-8 kHz `-14,0928 dB`;
  - RTF end-to-end `0,0247`;
  - pico de working set `9,39 MB`.
- A supressao e forte, mas preservacao de envelope, banda alta, tonalidade e
  STOI impedem promocao antecipada.
- O split final, a VM e o audio privado continuam bloqueados.

### WebRTC APM Noise Suppression

- WebRTC foi fixado no commit
  `eb79ac6e330baa0a6d26c53d522f9ed57495edb7` e compilado no Windows com o
  Visual Studio local.
- O adaptador habilita somente NS no nivel padrao `moderate`; AEC, AGC e HPF
  ficam desligados.
- Atraso medido: 96 amostras a 16 kHz, equivalente a `6 ms`.
- Resultado nas 72 condicoes:
  - SNR `-3,5039 dB`;
  - SI-SDR `-14,6908 dB`;
  - STOI `-0,03274`;
  - densidade tonal `11,0088`;
  - envelope `0,75281`;
  - banda 4-8 kHz `-8,1681 dB`;
  - RTF end-to-end `0,0060`.
- O metodo degradou SNR em `73,61%` das condicoes e SI-SDR em todas.
- Decisao:
  **WebRTC APM rejeitado como finalista nesta configuracao oficial**.
- Nao houve consulta ao Claude nesta etapa, pois a verificacao direta de API,
  build, atraso e metricas foi conclusiva.
- DeepFilterNet permanece como ultimo sistema principal pendente.
- Split final, escuta privada e VM continuam bloqueados.

### DeepFilterNet3 e finalistas publicos

- DeepFilterNet3 `v0.5.6` foi instalado em ambiente isolado e teve codigo,
  modelo, checkpoint e biblioteca nativa hashados.
- Atraso causal medido e materializado: `30 ms`.
- Resultado nas 72 condicoes:
  - SNR `+9,1978 dB`;
  - SI-SDR `+10,5105 dB`;
  - STOI `-0,06588`;
  - envelope `0,75312`;
  - banda 4-8 kHz `-23,2995 dB`;
  - RTF de inferencia `0,1087`;
  - memoria `255,10 MB`.
- DeepFilterNet foi rejeitado por ficar atras do RNNoise na maioria dos eixos
  de qualidade e custo, apesar do SI-SDR maior.
- Finalistas congelados:
  - `rnnoise`;
  - `omlsa_imcra`.
- Referencia obrigatoria: `baseline_stft`.
- Estado:
  **Dois finalistas publicos congelados; split final operacional liberado
  somente para baseline, RNNoise e OM-LSA/IMCRA**.

### Confirmacao publica final

- O split final operacional processou 72 condicoes para baseline, RNNoise e
  OM-LSA/IMCRA.
- RNNoise: SNR `+6,5684 dB`, SI-SDR `+5,5728 dB`, STOI `+0,01817`.
- OM-LSA/IMCRA: SNR `+0,9349 dB`, SI-SDR `+0,6896 dB`, envelope `0,94767`.
- Baseline: SNR `+3,7631 dB`, SI-SDR `+2,6476 dB`, envelope `0,94220`.
- Finalistas confirmados:
  - `rnnoise`;
  - `omlsa_imcra`.
- Estado:
  **Gate publico concluido; escuta privada cega pre-ponte autorizada, VM
  ainda bloqueada**.

### Trio privado pre-ponte

- A tomada privada autorizada existente foi processada offline, sem nova
  captura.
- Foram preparados tres arquivos cegos de 16,86 s, sem normalizacao ou fade.
- O mapeamento entre `A/B/C` e os sistemas permanece privado.
- Nenhum endpoint ou VM foi usado.
- Estado:
  **Escuta privada pendente; nenhuma integracao autorizada**.

### Decisao perceptual do Checkpoint 46-R/LIT

- Resultado cego:
  1. RNNoise;
  2. OM-LSA/IMCRA;
  3. baseline STFT.
- RNNoise foi avaliado com inteligibilidade `5`, naturalidade `5` e sem
  artefatos perceptiveis ou dropouts.
- OM-LSA/IMCRA ficou muito proximo em segundo lugar.
- O baseline foi descrito como metalizado e com chiado durante a fala.
- Decisao:
  **RNNoise aprovado para integracao incremental; OM-LSA/IMCRA mantido como
  reserva**.
- Estado:
  **Escuta aprovada; proximo gate e validacao RNNoise host pre-bridge, com VM
  ainda desligada**.

## Checkpoint 46-R/INT-HOST - RNNoise persistente aprovado no host

- Data: 2026-06-14.
- Escopo: integracao incremental antes da ponte, sem alterar driver, endpoint
  ou configuracao padrao da interface.
- Implementacao:
  - DLL em processo, carregada uma unica vez por `ctypes`;
  - um `DenoiseState` RNNoise persistente;
  - blocos externos de 320 amostras a 16 kHz;
  - dois frames RNNoise de 480 amostras a 48 kHz por bloco;
  - FIRs causais de 63 coeficientes para `16 -> 48 -> 16 kHz`;
  - buffers e estados nativos fixos, sem subprocesso ou alocacao nativa por
    bloco.
- Artefatos:
  - `scripts/native/rnnoise_realtime_adapter.c`;
  - `realtime_audio/rnnoise_processor.py`;
  - `scripts/audio/validate_rnnoise_host.py`;
  - `resultados/sysvad_checkpoint46_reopened/rnnoise_host_prebridge/`.
- O executavel offline aprovado foi preservado com SHA-256
  `6D35F2465B5A8C1E1E87F0F54418BFDF3F84D0105067E6204748987989ECF7CB`.
- DLL congelada para este gate:
  `593D387801A7D0464D2F11449E43E466811DEAEB66C39E367085E28DAAB0F84C`.
- Atraso:
  - RNNoise: `20 ms`;
  - FIRs: `1,2917 ms` nominal;
  - impulso medido: 341 amostras a 16 kHz, `21,3125 ms`.
- Ensaio prolongado, equivalente a 600 s e 30.000 blocos:
  - media `0,8184 ms`;
  - p95 `1,4240 ms`;
  - p99 `1,9510 ms`;
  - pior bloco `18,2485 ms`;
  - zero blocos acima de 20 ms;
  - RTF medio `0,04092`;
  - crescimento de RSS `225.280 bytes`.
- Passaram determinismo, causalidade por prefixo, framing, reset bit a bit,
  encerramento, continuidade, memoria e processamento prolongado.
- Suite: `128 passed`, `11 subtests passed`.
- A consulta `VBoxManage list runningvms` retornou lista vazia.
- Estado:
  **Gates host pre-ponte aprovados; ensaio VM controlado preparado, ainda nao
  executado; RNNoise nao promovido a padrao definitivo**.

## Checkpoint 46-R/INT-VM - integracao RNNoise validada com limite de cadencia

- Data: 2026-06-14.
- VM usada: `PTC3527-SYSVAD-LAB-FAST`.
- Snapshot inicial e final:
  `checkpoint45-causal-wpt-validated`.
- O bundle, a DLL e o capturador foram verificados por SHA-256 no convidado.
- DLL RNNoise preservada:
  `593D387801A7D0464D2F11449E43E466811DEAEB66C39E367085E28DAAB0F84C`.
- Gate isolado aprovado:
  - self-test de 3.000 blocos;
  - p99 `2,0207 ms`;
  - pior caso `10,6906 ms`;
  - zero blocos acima de 20 ms;
  - input-only p99 `1,9393 ms`, pior `4,0627 ms`;
  - latencia algoritmica registrada `21,2917 ms`.
- Duas matrizes deterministicas pareadas, oito cenarios no total:
  - p99 RNNoise maximo `10,6945 ms`;
  - 3 estouros em 5.882 blocos (`0,051%`) durante preempcao da VM;
  - zero erro de escrita, overrun, rejeicao ou erro de sequencia;
  - mediana de drops locais: bypass `15,42%`, RNNoise `7,05%`;
  - underruns variaram entre pares, sem regressao direcional consistente.
- A captura fisica pareada nao clipou e o RNNoise manteve p99 `2,096 ms`.
- Limite encontrado:
  - em janelas nominais de 20 s, o convidado entregou `13,36 s` no bypass e
    `24,72 s` no RNNoise;
  - a cadencia MME virtualizada alterna atraso e rajadas;
  - o nivel ambiente foi baixo e nao houve fala controlada.
- O audio fisico permaneceu somente em
  `C:\PTC3527-Private\rnnoise_vm_integration`.
- Estado final:
  - clone rapido desligado e revertido ao snapshot inicial;
  - VM original desligada e inalterada;
  - clipboard desabilitado;
  - captura padrao do host preservada.
- Decisao:
  **Integracao RNNoise na VM aprovada tecnicamente; promocao a default e
  escuta ponta a ponta permanecem bloqueadas ate estabilizar a cadencia da
  entrada fisica virtualizada**.

## Checkpoint 46-R/INT-VM-CAD - backends de entrada rejeitados

- Data: 2026-06-14.
- O probe foi separado do pipeline principal e nao salvou audio.
- Contrato preservado em todas as matrizes:
  - mono `float32`;
  - 16 kHz;
  - 320 amostras por callback;
  - nenhum driver, endpoint, PCM v1 ou parametro de fila alterado.
- Matriz de captura pura, em ordem espelhada:
  `MME, DirectSound, WASAPI, WASAPI, DirectSound, MME`.
- WASAPI a 16 kHz nao abriu no modo padrao; a variante compartilhada com
  `auto_convert` foi declarada e medida.
- Captura pura:
  - MME: razoes audio/parede `0,9999` e `1,0180`, com pausas maximas de
    `214 ms` e `326 ms`;
  - DirectSound: `0,9980` e `1,0040`, com maximos de `60 ms` e `374 ms`;
  - WASAPI: `0,8380` e `0,9730`, com maximos de `2,371 s` e `0,844 s`.
- Os timestamps `inputBufferAdcTime` e `currentTime` foram regressivos,
  repetidos ou artificiais nos tres backends e nao servem como relogio
  confiavel no convidado.
- Matriz input-only pareada, sem ponte ou endpoint:
  - MME RNNoise: `26,52 s` e `19,96 s` entregues em janelas de 20 s;
  - p99 RNNoise nessas pernas: `2,015 ms` e `1,334 ms`;
  - DirectSound bypass teve uma perna de `22,75 s` reais, `19,82 s` de audio
    e pausa maxima de `3,092 s`;
  - framing permaneceu em 320 e `status_counts` ficou vazio.
- Interpretacao:
  - a distorcao ja existe antes da fila local, driver, consumidor e endpoint;
  - nao ha relacao direcional consistente com RNNoise;
  - MME, DirectSound e WASAPI foram rejeitados como contorno imediato.
- Estado final:
  - clone desligado e restaurado a
    `checkpoint45-causal-wpt-validated`;
  - VM original desligada e inalterada;
  - clipboard desabilitado;
  - captura padrao do host inalterada;
  - nenhum audio novo salvo ou versionado.
- Decisao:
  **fala controlada, ponte e escuta cega permanecem bloqueadas; o proximo
  ensaio deve usar um relogio de entrada externo a virtualizacao e provar
  entrega causal de 50 blocos/s antes de reutilizar o endpoint**.

## Checkpoint 46-R/INT-VM-EXTCLK - relogio externo aceito

- Data: 2026-06-14.
- Foi criado um canal TCP de ensaio iniciado pelo convidado sobre a NIC NAT
  existente, sem alterar a configuracao de rede da VM.
- Contrato:
  - PCM16 mono a 16 kHz;
  - 320 amostras e 20 ms por bloco;
  - sequencia, offset programado e CRC por pacote;
  - pacing absoluto no host a 50 blocos/s.
- A matriz nominal teve quatro pernas espelhadas:
  `bypass v0, RNNoise v0, RNNoise v1, bypass v1`.
- Cada perna entregou exatamente 1.000 blocos e 20 s.
- Bypass e RNNoise receberam hashes de entrada identicos em cada variante.
- As variantes compartilharam 500 blocos iniciais e divergiram depois; os
  hashes de saida do prefixo foram identicos por metodo.
- Zero erro de sequencia, CRC ou framing.
- P99 de recepcao: `20,6861..21,5591 ms`; pior intervalo `53,5155 ms`;
  nenhum intervalo acima de `100 ms`.
- RNNoise: p99 `5,0642..7,5883 ms`, pior bloco `17,7299 ms`, zero acima de
  `20 ms`.
- Separacao de camadas:
  - a entrada fisica e o callback PortAudio da VM foram contornados;
  - processamento foi medido separadamente;
  - fila local, fila do driver e endpoint permaneceram ausentes.
- Estado final:
  - clone desligado e restaurado ao snapshot 45;
  - VM original desligada e inalterada;
  - clipboard desabilitado;
  - captura padrao do host preservada;
  - nenhum audio salvo.
- Foi preparado o replay de PCM privado sem copiar o arquivo ao convidado.
- Um smoke com 1 s de silencio sintetico confirmou hash de entrada identico
  em bypass e RNNoise; o PCM temporario privado foi removido ao final.
- O microfone USB do host aceitou WASAPI compartilhado em PCM16/16 kHz com
  conversao explicita, sem gravacao nesta etapa.
- Suite: `145 passed`, `11 subtests passed`.
- Decisao:
  **canal host-cadenciado aceito para uma captura unica de fala no host e
  replay pareado; RNNoise ainda nao e default e a escuta do endpoint continua
  bloqueada**.
- Claude nao foi usado; nao restou duvida tecnica concreta apos codigo,
  testes locais e medidas.

## Checkpoint 46-R/INT-VM-ENDPOINT - replay aceito, endpoint rejeitado

- Data: 2026-06-14.
- A tomada controlada valida foi capturada uma unica vez no host:
  - 1.000 blocos e 320.000 amostras;
  - pico `-14,16 dBFS`;
  - RMS `-33,60 dBFS`;
  - zero clipping;
  - SHA-256
    `4938B14BFA3311CFF715A569AF6A5C51C5D6930FE05DDDD472F4F7D4E237A308`.
- O replay fisico pareado foi aceito em
  `20260614-021753-host-paced-physicalpair`:
  - mesmo hash de entrada em bypass e RNNoise;
  - 1.000 blocos por perna;
  - zero erro de sequencia, CRC ou framing;
  - RNNoise p99 `1,729 ms` e pior bloco `4,842 ms`.
- A extensao incremental abriu a ponte PCM v1 com profundidade 2 e fila local
  4, sem alterar driver ou protocolo.
- O gate de endpoint
  `20260614-022436-host-paced-endpointpair` foi rejeitado:
  - bypass enviou 569 blocos e descartou 431;
  - RNNoise enviou 794 blocos e descartou 206;
  - zero erro de escrita, overrun, rejeicao ou sequencia;
  - WAVs privados mono PCM16/16 kHz de 24 s e sem clipping;
  - o consumo do driver parou antes do fim nas duas pernas.
- Como o bypass foi pior, a falha nao e atribuida ao RNNoise.
- Nenhum arquivo cego foi preparado.
- Estado final:
  - clone desligado e restaurado ao snapshot 45;
  - VM original desligada e inalterada;
  - clipboard e NIC preservados;
  - captura padrao do host inalterada;
  - audio somente em `C:\PTC3527-Private`.
- Decisao:
  **replay host-cadenciado aprovado; captura temporalmente valida do endpoint
  rejeitada; escuta ponta a ponta e promocao do RNNoise continuam bloqueadas**.

## Checkpoint 46-R/OPS-VM - historico e preflight operacional

- Data: 2026-06-14.
- Foi concluida uma auditoria dos incidentes operacionais registrados desde o
  Checkpoint 31.
- A auditoria incluiu leitura direta das threads historicas ainda disponiveis
  no Codex e cruzamento com os artefatos versionaveis do workspace.
- Artefato principal: `docs/historico_incidentes_vm.md`.
- O runbook agora distingue:
  - falha de comando recuperavel sem reboot;
  - estado desconhecido que exige encerramento;
  - fim normal de sessao que exige restauracao.
- Foi criado o preflight somente-leitura
  `scripts/vm/Test-VmAutomationPreflight.ps1`.
- Validacao real do preflight:
  - zero erros;
  - zero avisos;
  - nenhuma inicializacao ou modificacao da VM;
  - clone e original desligados;
  - snapshot, audio, seguranca, NIC, armazenamento e captura padrao corretos;
  - `Invoke-HostPacedPcmVm.ps1` parseavel e aderente aos controles estaticos.
- Decisao:
  **novos runs devem eliminar falhas no host, reutilizar a mesma sessao quando
  o estado for conhecido e reservar reboot/restore para os criterios
  documentados**.

## Checkpoint 46-R/OPS-SSD - runtime ativo migrado para o SSD

- Data: 2026-06-14.
- O clone ativo ja ocupava aproximadamente 74,6 GiB no SSD.
- A VM original e sua arvore historica, aproximadamente 51,0 GiB, foram
  preservadas integralmente no `E:` e nao foram duplicadas.
- Foi criado `C:\PTC3527-Private\vm_runtime`, com ACL restrita ao usuario
  atual, `SYSTEM` e administradores.
- Foram copiados somente:
  - XML de credencial: 12.992 bytes;
  - referencia `.vbox` da VM original: 124.533 bytes;
  - manifesto com hashes, snapshots e caminhos de origem.
- Total copiado: 137.525 bytes.
- Os tres orquestradores ativos e o preflight passaram a usar o runtime SSD.
- Quando `E:` esta presente, configuracao, estado e snapshot da VM original
  continuam auditados. Quando ausente, o fluxo ativo permanece disponivel e
  registra `external_source_unavailable`.
- Validacao:
  - tres preflights prontos, zero erros e zero avisos;
  - simulacao host-only sem fonte externa aceita;
  - `150 passed`, `11 subtests passed`;
  - nenhuma VM iniciada.
- Decisao:
  **SSD passa a ser a dependencia operacional; `E:` fica reservado ao arquivo
  historico e a auditorias ou operacoes explicitas da VM original**.

## Checkpoint 46-R/INT-VM-ENDPOINT-DIAG - janela corrigida

- Data: 2026-06-14.
- A instrumentacao separou escrita, consumo da fila, stream SYSVAD, captura
  WASAPI e pausas temporais.
- Causa da aparente parada:
  - `PtcPcmCapture` iniciava antes da inicializacao fria do cliente;
  - a rodada anterior cobria apenas `8.984 ms` dos 20 s de replay;
  - o encerramento da captura fechava o stream que drenava a ponte.
- Foi criada uma barreira de prontidao entre cliente, capturador e servidor.
- Rodada corrigida:
  `20260614-031100-host-paced-endpointdiagnostic`.
- Resultado:
  - janela de endpoint cobrindo toda a fonte;
  - 944 blocos aceitos e 943 consumidos;
  - profundidade final zero;
  - nenhum stall persistente do consumidor;
  - 56 descartes locais correlacionados a lacunas de ate `329 ms`.
- Interpretacao:
  **a falha original era de sincronizacao da captura; a limitacao restante e
  compativel com pausas transitorias de agendamento da VM que excedem os
  80 ms da fila local fixa**.
- Decisao:
  **manter escuta e promocao do RNNoise bloqueadas; proximo gate deve reduzir
  ou controlar as pausas sem alterar PCM v1, profundidade 2 ou fila local 4**.

## Checkpoint 46-R/INT-VM-TIMER-WAVERT - escritor mitigado, consumidor limitado

- Data: 2026-06-14.
- Instrumentacao QPC separou host, recepcao, escritor, capturador, driver e
  heartbeat independente.
- O MMCSS foi testado em matriz espelhada e rejeitado:
  - normal: 59 descartes em 2.000 blocos;
  - MMCSS: 269 descartes em 2.000 blocos.
- A maior pausa do escritor conteve 113 recepcoes TCP, descartando a hipotese
  de pausa global da VM.
- IOCTLs de estatistica e escrita permaneceram normalmente submilissegundo.
- A causa dominante do escritor foi wakeup tardio do timer de 2 ms.
- Substituir a espera por timer por yield, mantendo o periodo de 2 ms:
  - reduziu descartes de 142 para 36;
  - reduziu lacunas do escritor acima de 30 ms de 56 para 1;
  - preservou profundidade 2, fila local 4 e PCM v1.
- O gate de 1.000 blocos ainda nao passou:
  - pernas yield: 983/1.000 e 981/1.000 enviados;
  - 17 e 19 descartes.
- Um prefill de dois blocos reduziu perdas, mas nao as eliminou:
  - controle: 74 descartes;
  - prefill: 38 descartes.
- A limitacao restante foi localizada na cadencia de consumo fresco
  WaveRT/SYSVAD:
  - `48,55..49,20 Hz`;
  - profundidade do driver em 2 por cerca de 90% da janela;
  - escritor sem pausa persistente.
- Classificacao:
  `writer_wakeup_mitigated_consumer_cadence_deficit_remains`.
- O VirtualBox operou por NEM/Windows Hypervisor Platform porque VT-x direto
  estava indisponivel; isso permanece hipotese ambiental, nao causa provada.
- `yield`, MMCSS e prefill continuam opt-in; nenhum default de produto mudou.
- Nenhum replay privado ou escuta cega foi executado.
- Suite: `158 passed`, `11 subtests passed`.
- Estado final:
  - clone desligado e restaurado ao snapshot 45;
  - VM original desligada;
  - audio, clipboard, drag-and-drop, NIC e captura padrao preservados.
- Decisao:
  **manter replay privado e escuta bloqueados; o proximo gate deve atuar na
  cadencia do consumidor WaveRT ou no backend NEM do VirtualBox, sem aumentar
  filas e sem alterar driver ou PCM v1**.

## Checkpoint 46-R/INT-VM-NEM-VCPU - 3 vCPUs reduzem, mas nao zeram perdas

- Data: 2026-06-14.
- A leitura do caminho WaveRT confirmou:
  - consumo do ring governado pelo avanco QPC do timer do miniport;
  - ring vazio produz zeros e incrementa `Underruns`;
  - nao ha repeticao silenciosa de blocos antigos.
- O analisador passou a separar underruns finais dos ocorridos dentro da
  janela util da fonte.
- Gate de 2 vCPUs:
  `20260614-041534-host-paced-endpointprefill`.
  - convidado nao concluiu boot;
  - Guest Additions e rede nao ficaram prontas;
  - zero byte de rede;
  - configuracao rejeitada operacionalmente antes dos cenarios.
- Gate aceito de 3 vCPUs:
  `20260614-042924-host-paced-endpointprefill`.
- Nas duas pernas com prefill, contra o controle de 4 vCPUs:
  - descartes: `38 -> 11`;
  - gaps do scheduler acima de 30 ms: `54 -> 11`;
  - gaps da captura acima de 30 ms: `67 -> 28`;
  - underruns WaveRT na janela util: `77 -> 30`;
  - gaps do escritor acima de 30 ms permaneceram `3`.
- Reducoes:
  - descartes: `71,1%`;
  - scheduler: `79,6%`;
  - captura: `58,2%`;
  - underruns: `61,0%`.
- As pernas de 3 vCPUs ainda descartaram 7 e 4 blocos.
- Classificacao:
  `three_vcpu_reduced_pauses_but_zero_drop_not_reached`.
- Validacao: `159 passed`, `11 subtests passed`; 24 scripts PowerShell
  parseaveis; preflight final com zero erros e zero avisos.
- Tres vCPUs nao foram promovidas a configuracao persistente; o clone foi
  restaurado a 4 vCPUs.
- Nenhum audio privado foi reproduzido ou versionado.
- Decisao:
  **3 vCPUs sao uma mitigacao ambiental promissora sob NEM/WHP, mas precisam
  de repeticao e de um gate complementar antes de liberar replay privado**.

## Checkpoint 46-R/INT-VM-NEM-VCPU-REPEAT - melhora nao replicada

- Data: 2026-06-14.
- Repeticao:
  `20260614-094007-host-paced-endpointprefill`.
- O preflight host-only passou com zero erros e zero avisos.
- O manifesto confirmou `vm_cpu_count=3`.
- As quatro pernas sinteticas terminaram com evidencia completa.
- Nas duas pernas com prefill, contra o controle fixo de 4 vCPUs:
  - descartes: `38 -> 54`;
  - gaps do scheduler acima de 30 ms: `54 -> 21`;
  - gaps da captura acima de 30 ms: `67 -> 27`;
  - underruns WaveRT na janela util: `77 -> 52`;
  - gaps do escritor: `3 -> 3`.
- As pernas com prefill enviaram 952 e 994 blocos, descartando 48 e 6.
- Uma pausa de aproximadamente 886 ms dominou a primeira perna com prefill.
- Classificacao:
  `three_vcpu_not_confirmed_as_mitigation`.
- A reducao de pausas de scheduler e captura foi direcionalmente repetida,
  mas nao produziu reducao reprodutivel de descartes.
- O gate A/B de afinidade do `VirtualBoxVM` foi adiado porque a precondicao
  de repeticao da melhora falhou.
- O teardown exigiu uma segunda restauracao do snapshot 45, sem boot, depois
  de uma consulta externa observar `VMState=aborted`. Estado final:
  `poweroff`, snapshot 45 e 4 vCPUs.
- VM original desligada, captura padrao inalterada, VBS/HVCI preservados e
  nenhum replay privado ou escuta executado.
- Decisao:
  **nao promover 3 vCPUs e nao abrir o gate de afinidade; manter replay
  privado bloqueado ate duas pernas de 1.000 blocos terminarem sem
  descartes**.

## Checkpoint 46-R/INT-VM-CAPTURE-YIELD - transporte sem descartes

- Data: 2026-06-14.
- A pausa extrema da repeticao de 3 vCPUs atingiu o scheduler probe e o
  capturador, ambos com `Sleep(2 ms)`, mas nao o writer em yield.
- O capturador recebeu uma estrategia opt-in de yield cadenciado por QPC.
- Driver, PCM v1, profundidade 2, fila local 4 e prioridades nao mudaram.
- Matriz ABBA:
  `20260614-095256-host-paced-endpointcapturetimer`.
- Controle sleep:
  - 1.968 de 2.000 blocos enviados;
  - 32 descartes;
  - 43 gaps de polling acima de 30 ms;
  - 56 underruns na janela util.
- Captura yield:
  - 2.000 de 2.000 blocos enviados e aceitos;
  - zero descarte;
  - 1 gap de polling acima de 30 ms;
  - 23 underruns na janela util.
- Reducoes:
  - descartes: `100%`;
  - gaps de polling: `97,7%`;
  - underruns: `58,9%`.
- As duas pernas yield terminaram em `1000/1000`, com zero erro de escrita.
- Classificacao:
  `capture_poll_yield_completed_without_drops`.
- O gate de transporte para replay privado foi atingido, mas a escuta
  permanece bloqueada pelos underruns.
- Treze dos 23 underruns ocorreram nos primeiros 2,5 ms da fonte.
- Proximo gate:
  **confirmar profundidade 2 antes de iniciar o `IAudioClient`, mantendo
  todas as filas e formatos atuais, para separar a corrida de partida dos
  eventos esparsos restantes**.

## Checkpoint 46-R/INT-VM-CAPTURE-BARRIER - partida mitigada

- Data: 2026-06-14.
- Run: `20260614-100628-host-paced-endpointstartbarrier`.
- Foi criada uma barreira opt-in entre inicializacao e
  `IAudioClient::Start`.
- A captura somente inicia depois de a ponte confirmar profundidade 2.
- Controle imediato:
  - 2.000/2.000 blocos;
  - zero descarte;
  - 34 underruns na janela util.
- Barreira:
  - 2.000/2.000 blocos;
  - zero descarte;
  - 7 underruns na janela util, distribuidos em 0 e 7.
- Classificacao:
  `capture_start_barrier_reduced_but_did_not_zero_underruns`.
- Decisao:
  **manter a barreira opt-in; ela remove a corrida inicial, mas nao libera
  escuta enquanto houver underruns durante a fonte**.

## Checkpoint 46-R/INT-VM-SEND-LEAD - antecipacao rejeitada

- Data: 2026-06-14.
- Run: `20260614-101531-host-paced-endpointsendlead`.
- O envio fisico foi antecipado em 10 ms sem alterar o offset logico de
  20 ms entre blocos.
- Controle: 1.942 enviados, 58 descartes e 49 underruns.
- Lead: 1.978 enviados, 22 descartes e 15 underruns.
- Uma perna lead completou 1.000/1.000; a outra descartou 22 blocos durante
  uma pausa de polling de aproximadamente 447 ms.
- Classificacao: `ten_ms_send_lead_not_confirmed`.
- Decisao:
  **nao promover lead; antecipacao curta nao controla pausas longas e
  variaveis**.

## Checkpoint 46-R/INT-VM-HOST-AFFINITY - P-cores nao confirmados

- Data: 2026-06-14.
- Run aceito: `20260614-102925-host-paced-endpointhostaffinity`.
- Matriz ABBA, 4 vCPUs, uma sessao GUI.
- Processo primario `VirtualBoxVM.exe` selecionado pelo UUID da VM e pelo
  primeiro token da linha de comando.
- Afinidades verificadas:
  - controle: `0xFFFFF`;
  - CPUs de desempenho: `0xFFF`.
- Prioridade efetiva `Normal` em todas as pernas; sem elevacao
  administrativa.
- Controle: 1.902 enviados, 98 descartes e 44 underruns.
- P-cores: 1.999 enviados, 1 descarte e 54 underruns.
- Somente uma perna de cada grupo completou 1.000/1.000.
- A ultima perna controle teve pausa de captura de aproximadamente 1,33 s,
  sem pausa equivalente no probe geral do convidado.
- Classificacao: `performance_core_affinity_not_confirmed`.
- Uma tentativa anterior abortou antes dos cenarios ao detectar tres
  processos VirtualBox com o mesmo UUID; foi restaurada e descartada.
- Estado final:
  - clone desligado, snapshot 45 e 4 vCPUs;
  - afinidade original restaurada;
  - VM original desligada;
  - captura padrao e configuracoes protegidas preservadas.
- Decisao:
  **rejeitar a afinidade como mitigacao e instrumentar as chamadas internas
  do capturador antes de outro gate de execucao**.

## Checkpoint 46-R/INT-VM-CAPTURE-TIMING-HOST - instrumentacao pronta

- Data: 2026-06-14.
- Trabalho executado somente no host; nenhum boot novo.
- `PtcPcmCapture` recebeu trace QPC em memoria para:
  - intervalo entre iteracoes;
  - `GetNextPacketSize`;
  - `GetBuffer`;
  - copia e analise do PCM;
  - escrita dos traces existentes;
  - `ReleaseBuffer`;
  - escrita final do WAV e do timing trace.
- O schema v1 registra inicio, fim, duracao, HRESULT, poll, pacote, frames,
  bytes e flags.
- O analisador dedicado valida integridade temporal e classifica stalls acima
  de 30 ms como WASAPI, I/O, trabalho interno, atraso compartilhado ou
  desagendamento especifico do capturador.
- O proximo gate `EndpointCaptureTiming` possui duas pernas sinteticas
  identicas, sem sintonia de CPU:
  - 4 vCPUs;
  - prioridade Normal;
  - afinidade inalterada;
  - writer e captura em yield;
  - barreira em profundidade 2;
  - prefill 2 e fila local 4.
- Gate de evidencia:
  - dois traces completos;
  - indices contiguos;
  - uma frequencia QPC positiva;
  - spans e duracoes coerentes;
  - todas as fases obrigatorias.
- Decisao:
  **instrumentacao pronta para um unico gate diagnostico planejado; replay
  privado e escuta continuam bloqueados, inclusive se a rodada nao reproduzir
  um stall longo**.
- Build Release x64 concluido sem erros ou avisos.
- SHA-256:
  `1D6025481F4546BFE9FB266CD093D7032E872E0F37B56C98D8FA8E0CDD4F3217`.
- Validacao:
  - 19 testes direcionados;
  - parser PowerShell e `compileall` aprovados;
  - preflight final com zero falhas e zero avisos.
- Estado final:
  - clone desligado, snapshot 45, 4 vCPUs e afinidade original;
  - VM original desligada;
  - audio input ligado, clipboard e drag-and-drop desabilitados, NIC NAT;
  - captura padrao inalterada;
  - VBS/HVCI preservados e Secure Boot nao alterado;
  - nenhuma credencial residual.

## Checkpoint 46-R/INT-VM-CAPTURE-TIMING-1 - WASAPI e I/O excluidos

- Data: 2026-06-14.
- Run: `20260614-121252-host-paced-endpointcapturetiming`.
- Duas pernas: 2.000/2.000 blocos, zero descarte e zero erro de escrita.
- Primeira perna: zero underrun.
- Segunda perna: 13 underruns e dois gaps entre iteracoes:
  `31,339 ms` e `34,714 ms`.
- Durante os gaps:
  - scheduler geral ativo;
  - writer ativo;
  - nenhum bloqueio interno acima de 3,34 ms;
  - pacotes acumulados foram drenados depois do retorno.
- Classificacao conservadora:
  `capture_wait_path_delay_without_external_overlap`.
- WASAPI, copia PCM, analise, I/O dos traces e `ReleaseBuffer` foram
  excluidos como origem dos dois stalls.
- Refinamento preparado:
  - duracao total de `poll_wait`;
  - maior chamada de `SwitchToThread` por poll;
  - vetor de eventos reservado antecipadamente.
- SHA-256 do build refinado:
  `BBFC9622470913B9E969150809B6AB2A5261393B79CF20909B919026E697F574`.
- Decisao:
  **repetir somente o mesmo gate para localizar um eventual novo gap dentro
  ou fora de `SwitchToThread`; nao abrir escuta nem testar outra sintonia**.

## Checkpoint 46-R/INT-VM-CAPTURE-SWITCH - causa de espera confirmada

- Data: 2026-06-14.
- Run:
  `20260614-122013-host-paced-endpointcapturetiming`.
- Duas pernas completas:
  - 2.000/2.000 blocos;
  - zero descarte;
  - zero erro de escrita.
- Underruns uteis: 15 e 8.
- Tres stalls da primeira perna foram localizados dentro de uma unica chamada
  de `SwitchToThread`:
  - `32,739 ms`;
  - `33,944 ms`;
  - `32,089 ms`.
- Esperas totais correspondentes: `33,211`, `34,373` e `33,705 ms`.
- Scheduler geral e writer continuaram ativos nas tres janelas.
- Segunda perna nao teve stall acima de 30 ms, mas ainda teve 8 underruns.
- Classificacao:
  `capture_thread_delayed_inside_switch_to_thread`.
- Estado final restaurado sem incidente.
- Decisao:
  **preparar no proximo checkpoint uma estrategia opt-in de spin QPC e um
  gate ABBA contra yield; nao elevar prioridade, nao alterar filas e nao
  liberar escuta enquanto houver underruns**.

## Checkpoint 46-R/INT-VM-CAPTURE-SPIN - spin rejeitado

- Data: 2026-06-14.
- Run aceito:
  `20260614-123752-host-paced-endpointcapturespin`.
- Matriz ABBA:
  `yield controle A`, `spin A`, `spin B`, `yield controle B`.
- Configuracao preservada:
  - bypass sintetico, 20 s por perna;
  - 4 vCPUs, prioridade Normal e afinidade original;
  - writer yield, barreira em profundidade 2, prefill 2 e fila local 4;
  - PCM16 mono, 16 kHz e blocos de 320 amostras.
- Controles yield:
  - 2.000/2.000 blocos, zero descarte;
  - zero gap de polling da captura acima de 30 ms;
  - 32 underruns uteis.
- Spin:
  - 1.991/2.000 blocos, 9 descartes;
  - 5 gaps de polling e 9 gaps entre pacotes acima de 30 ms;
  - 74 underruns uteis.
- Impacto:
  - writer `2 -> 8` gaps;
  - scheduler na fonte `16 -> 42` gaps;
  - recepcao `7 -> 13` gaps.
- `poll_wait_spin` excedeu 30 ms quatro vezes:
  `89,040`, `43,989`, `44,684` e `48,310 ms`.
- Todas essas janelas coincidiram com atraso do scheduler e do writer.
- Classificacao:
  `capture_spin_not_confirmed`.
- Decisao:
  **rejeitar spin como mitigacao; nao promover, nao repetir o gate e nao
  liberar replay privado ou escuta**.
- Estado final protegido confirmado com preflight de zero falhas e zero
  avisos.

## Checkpoint 46-R/INT-VM-CAPTURE-SPIN-BUFFERED - rejeicao confirmada

- Data: 2026-06-14.
- Run:
  `20260614-130602-host-paced-endpointcapturespin`.
- Alteracao diagnostica:
  - buffers de 4 MiB nos CSVs de captura e polling;
  - flush somente depois de `IAudioClient::Stop`;
  - nenhuma mudanca em driver, PCM v1 ou caminho de audio.
- Build Release x64:
  `0F44BEC1B9F6242D3ADC6C328D4C94824352CB88CE10351CB146BA26C9E219F6`.
- Validacao:
  - 30 testes direcionados;
  - build sem erro ou aviso;
  - parser PowerShell e `compileall` aprovados;
  - preflight inicial e final com zero falhas e zero avisos.
- O I/O diagnostico ficou abaixo de `8,285 ms` e nao produziu stall.
- Controles yield:
  - 1.998/2.000 blocos;
  - 2 descartes;
  - 41 underruns uteis.
- Spin:
  - 1.996/2.000 blocos;
  - 4 descartes;
  - 58 underruns uteis;
  - esperas spin de `82,093` e `32,737 ms`.
- Classificacao confirmada:
  `capture_spin_not_confirmed`.
- Decisao:
  **encerrar sintonias de CPU e espera; preparar no host uma alternativa
  WASAPI exclusiva orientada a evento, opt-in, mantendo yield como controle
  e sem novo boot ate concluir schema, testes, build, hashes e preflight**.
- Estagio macro:
  - benchmark publico e escolha perceptual concluidos;
  - RNNoise persistente aprovado no host, mas nao promovido a default;
  - driver, endpoint virtual e ponte PCM v1 funcionais;
  - bloqueador atual: confiabilidade temporal ponta a ponta na captura do
    endpoint, ainda com perdas e underruns esparsos;
  - replay privado e escuta ponta a ponta continuam bloqueados.

## Checkpoint 46-R/INT-VM-CAPTURE-EVENT - evento rejeitado

- Data: 2026-06-14.
- Run:
  `20260614-132705-host-paced-endpointcaptureevent`.
- Matriz:
  `yield A`, `evento A`, `evento B`, `yield B`.
- Implementacao:
  - captura exclusiva com `AUDCLNT_STREAMFLAGS_EVENTCALLBACK`;
  - evento auto-reset, `SetEventHandle` e timeout de 1.000 ms;
  - fase QPC `poll_wait_endpoint_event`;
  - modo opt-in, sem mudar o default.
- Build:
  `046681AB92B7E4D20F1AA408E3B2E373900CD4E4B01450EABD244BA1E629EB4F`.
- Yield:
  - 1.998/2.000 blocos, 2 descartes e 22 underruns uteis.
- Evento:
  - 1.918/2.000 blocos, 82 descartes e 137 underruns uteis.
- Zero timeout ou falha da API, mas waits sinalizados chegaram a
  `220,532 ms` e `158,404 ms`.
- Das 59 esperas acima de 30 ms:
  - 36 coincidiram com pausa do scheduler geral;
  - 23 nao coincidiram com scheduler nem writer.
- Classificacao:
  `capture_event_not_confirmed`.
- Decisao:
  **rejeitar evento e encerrar sintonias de espera, CPU e produtor nesta VM;
  a validacao temporal final exige Windows nativo com driver assinado ou
  ambiente fisico equivalente**.
- Estado protegido confirmado com preflight final de zero falhas e zero
  avisos.

## 2026-06-14 - Contrafactual SYSVAD versus HDA preparado no host

- O fechamento foi reaberto somente para separar uma limitacao global da VM
  de um problema especifico do caminho SYSVAD/PortCls.
- Foi criado o executavel independente `PtcEndpointEventProbe`.
- O probe enumera endpoints de captura ativos e abre somente um ID exato
  selecionado depois da enumeracao.
- A captura usa modo compartilhado, `GetMixFormat`,
  `AUDCLNT_STREAMFLAGS_EVENTCALLBACK`, duracao zero e periodicidade zero.
- As amostras sao drenadas e descartadas; nenhum WAV ou PCM e criado.
- O criterio tardio foi congelado em
  `intervalo > max(30 ms, 2,5 x periodo)`.
- A matriz unica e ABBA:
  SYSVAD A, HDA A, HDA B, SYSVAD B, com 40 s por perna.
- Um probe independente de scheduler de 2 ms acompanha cada perna.
- O analisador implementa somente:
  `virtualbox_event_timing_supported`,
  `sysvad_event_path_specific` ou `mixed_or_inconclusive`.
- Build `Release|x64`: zero erros e zero avisos.
- SHA-256 do executavel:
  `A3967D5979BF7AE04598198753E351E0618057EAB002AC7E432F6BDBF4ED4674`.
- Validacao host-only:
  23 testes direcionados, `compileall`, parser PowerShell, enumeracao sem
  stream e preflight com zero falhas e zero avisos.
- A revisao Claude foi parcial: revisou Python e PowerShell, mas nao obteve
  acesso ao C++. Dois pontos confirmados localmente foram corrigidos.
- Nenhuma VM foi iniciada nesta preparacao.
- Manifesto:
  `resultados/sysvad_checkpoint46_reopened/`
  `endpoint_event_contrafactual/host_only_manifest.json`.
- Proximo passo autorizado:
  uma unica sessao GUI, sem sintonia intermediaria, executando
  `scripts/vm/Invoke-EndpointEventContrafactualVm.ps1`.

## 2026-06-14 - Contrafactual SYSVAD versus HDA concluido

- Run aceito:
  `20260614-144937-endpoint-event-contrafactual`.
- Quatro pernas compartilhadas orientadas a evento completaram em ordem ABBA.
- Periodos:
  - SYSVAD: `10,0000 ms`;
  - HDA: `10,1587 ms`.
- Sinais tardios:
  - SYSVAD A/B: 21 e 48;
  - HDA A/B: 22 e 23.
- Maximos:
  - SYSVAD A/B: `2.302,083 ms` e `437,176 ms`;
  - HDA A/B: `7.554,401 ms` e `834,825 ms`.
- Periodos perdidos equivalentes:
  - SYSVAD: 381 e 304;
  - HDA: 1.121 e 248.
- O HDA teve atrasos repetidos nas duas pernas e maximos normalizados da mesma
  ordem de grandeza do SYSVAD.
- Classificacao:
  `virtualbox_event_timing_supported`.
- Interpretacao:
  reforca limitacao global VirtualBox/NEM ou do scheduler convidado; nao prova
  correcao do driver SYSVAD.
- Nenhum audio foi salvo ou escutado.
- Estado final:
  clone desligado, snapshot 45, 4 vCPUs, configuracoes protegidas preservadas,
  captura padrao do host inalterada e preflight com zero falhas e avisos.

## 2026-06-14 - Consolidacao da migracao para Windows nativo

- Natureza: checkpoint documental pos-fechamento, sem novo ensaio de endpoint.
- Foi explicitado que a migracao nativa nao exige reimplementar a arquitetura.
- Componentes congelados para a primeira repeticao:
  - RNNoise persistente;
  - blocos de 20 ms e PCM16 mono a 16 kHz;
  - protocolo PCM v1, IOCTLs e ring buffer;
  - ponte Python-driver, UI e analisadores;
  - polling, profundidades e politica de descarte usados no ultimo baseline.
- Adaptacoes esperadas:
  - build e empacotamento para o Windows/WDK da bancada;
  - assinatura de teste, instalacao e reversao;
  - enumeracao de dispositivos e backend nativo;
  - substituicao da automacao do VirtualBox por execucao local;
  - medicao fisica de latencia.
- Regra metodologica:
  **executar primeiro a configuracao congelada, sem retuning, para preservar a
  comparacao com a VM**.
- Interpretacao predefinida:
  - baseline e SYSVAD continuos: evidencia favoravel a limitacao da VM;
  - baseline continuo e SYSVAD irregular: investigar WaveRT/PortCls, ring
    buffer e captura do endpoint;
  - baseline e SYSVAD irregulares: investigar scheduler, DPC/ISR, energia,
    backend e drivers do host;
  - falha somente com RNNoise: comparar bypass/RNNoise antes de atribuir causa
    ao DSP.
- A demonstracao pre-ponte ganhou uma CLI para qualquer WAV:
  `python -m realtime_audio.process_wav_rnnoise`.
- Exemplo local:
  - SNR de entrada: `2,31 dB`;
  - SNR de saida alinhada: `7,33 dB`;
  - melhoria: `5,02 dB`;
  - RTF total: `0,020`;
  - zero blocos acima de 20 ms.
- Documentos atualizados:
  - `README.md`;
  - `docs/demonstracao_academica.md`;
  - `docs/validacao_windows_nativo.md`;
  - `docs/migracao_windows_nativo.md`;
  - `entrega3.tex`;
  - `apresentacao_fechamento.tex`.

## 2026-06-14 - Revisao integral do escopo final

- Titulo consolidado:
  **Prototipo de Reducao de Ruido Local para Voz Humana no Windows:
  Avaliacao Algoritmica, RNNoise e Microfone Virtual**.
- A expressao `tempo real` foi retirada do titulo porque a continuidade
  temporal e a latencia fisica ponta a ponta ainda nao foram comprovadas.
- O escopo embarcado foi removido do relatorio final, da apresentacao, do
  onboarding e do checklist de liberacao.
- Resumo, objetivos, problema, hipotese, metodologia, resultados, limitacoes,
  riscos, questionario, proximos passos e conclusao foram relidos e alinhados
  ao prototipo Windows.
- A validacao foi organizada em tres gates independentes:
  qualidade do DSP, integracao funcional e continuidade temporal.
- A proxima etapa permanece a repeticao congelada em Windows nativo, seguida
  de diagnostico comparativo do gargalo observado na VM.
- Referencias a embarcados em checkpoints e diarios anteriores foram mantidas
  apenas como registro historico da evolucao do projeto.
- Uma revisao externa via Claude CLI confirmou a ausencia de referencias
  embarcadas residuais e de alegacoes indevidas de baixa latencia.

## 2026-06-28 - Questionario extensionista em GitHub Pages

- Foi consolidada uma pagina estatica em `docs/questionario/` para coleta
  extensionista sem etapa de build.
- A pagina usa players nativos de audio e comparacao perceptual cega entre:
  referencia ruidosa, RNNoise, OM-LSA/IMCRA, STFT causal adaptativa, STFT Wiener
  e Wavelet soft.
- O manifesto `questionario.config.js` foi atualizado para a versao
  `2026-06-28.4`, com hashes SHA-256 para os MP3 publicados.
- O exemplo RNNoise do questionario foi regenerado com `startup_preroll_ms = 200`
  em `realtime_audio/process_wav_rnnoise.py`.
- O pre-roll usa os primeiros 200 ms reais do proprio arquivo para aquecer o
  estado RNNoise e descarta essa saida antes do passe principal. O comprimento
  final do audio e preservado.
- Essa decisao corrige um transiente audivel no inicio do exemplo RNNoise sem
  alterar os benchmarks historicos, pois o novo parametro permanece desativado
  por padrao.
- O teste local com audio proprio foi mantido desativado para a versao inicial;
  processamento local em navegador fica para fase posterior.
- O fluxo visual, os players, o embaralhamento cego e a validacao local do
  formulario foram verificados manualmente antes da ativacao de envio real.

## 2026-06-28 - Camada de analise do questionario

- Foi adicionada a funcao `rebuildDashboard()` ao Apps Script do receptor do
  questionario.
- A reconstrucao usa `responses_raw` como fonte canonica e preserva o receptor
  `doPost`, `responses_raw` e `responses_wide`.
- Foram previstas as abas `dashboard_metrics`, `dashboard` e
  `coded_open_answers`.
- As metricas incluem frequencias, percentuais, distribuicoes de escala, media,
  mediana, ranking de preferencia por metodo e notas de auditoria por schema.
- As respostas abertas foram estruturadas para codificacao manual, sem tentativa
  de conclusao automatica fraca.
- O dashboard registra `questionnaireId`, `schemaVersion`, data/hora de
  atualizacao, total de respostas, `N` por metrica e a observacao de que audios
  dos usuarios nao sao coletados.

## 2026-06-28 - Reducao de friccao no questionario mobile

- Foi adicionado avanco automatico apos resposta em perguntas de escolha unica,
  comparacao de audio e escala.
- Perguntas de multipla selecao e respostas abertas permanecem com navegacao
  manual, para nao cortar escolhas do participante.
- A escala de 1 a 5 ganhou layout mobile em grade de cinco botoes maiores, com
  rotulos extremos alinhados lado a lado.
- A nota introdutoria de audio proprio foi ajustada para deixar claro que a fase
  atual usa apenas exemplos publicos preparados e nao solicita nem envia audio
  do usuario.

## 2026-06-28 - Avaliacao de loudness dos audios do questionario

- Foi criada uma rotina local de avaliacao em
  `scripts/audio/prepare_questionario_loudness_eval.py`.
- A rotina usa o filtro `loudnorm` do FFmpeg em dois passes para gerar copias
  temporarias dos audios com alvo de `-16 LUFS`, `LRA = 7 LU` e true peak maximo
  de `-1 dBTP`.
- As saidas foram geradas em `tmp/questionario_loudness_eval/`, sem substituir
  os MP3 publicados em `docs/questionario/assets/audio/`.
- O relatorio `tmp/questionario_loudness_eval/loudness_report.json` registrou os
  ganhos aproximados aplicados; o RNNoise recebeu cerca de `+3,08 dB`, coerente
  com a percepcao de que a versao anterior soava mais baixa.
- A decisao metodologica permanece pendente de escuta comparativa antes de
  substituir arquivos do questionario ou atualizar hashes no manifesto.

## 2026-06-28 - Variantes genericas RNNoise para avaliacao de timbre

- Foi criada a rotina generica
  `scripts/audio/prepare_rnnoise_variants_eval.py`.
- A rotina recebe qualquer WAV de entrada e gera tres variantes auditaveis:
  RNNoise puro, RNNoise com loudness equalizado e RNNoise com EQ de presenca mais
  loudness final equalizado.
- A etapa de EQ usa, por padrao, filtro `equalizer` do FFmpeg centrado em
  `3000 Hz`, `Q = 1.0` e ganho de `+2 dB`, parametros alteraveis por CLI.
- Para manter comparacao justa, a variante com EQ termina com normalizacao de
  loudness, evitando confundir ganho de presenca com simples aumento de volume.
- A execucao de teste foi feita com entrada
  `tmp/questionario_audio_work/amostra_noisy_reference.wav` e referencia limpa
  `resultados/audio/exemplo_clean.wav`.
- As saidas foram geradas em
  `tmp/rnnoise_variants_eval/questionario_amostra/`, com relatorio auditavel em
  `variant_report.json` contendo hashes, parametros, loudness, RMS e metricas
  espectrais.
- Os MP3 oficiais do questionario ainda nao foram substituidos.

## 2026-06-28 - Questionario preparado com RNNoise + EQ de presenca

- Apos escuta comparativa, a variante preferida para o questionario foi
  `questionario_amostra_rnnoise_presence_eq_loudnorm.mp3`.
- O arquivo `docs/questionario/assets/audio/amostra_rnnoise.mp3` foi substituido
  por essa variante.
- O manifesto `docs/questionario/questionario.config.js` foi atualizado para
  `schemaVersion = 2026-06-28.5`.
- O hash SHA-256 registrado para `amostra_rnnoise.mp3` passou a ser
  `cb9ed5a5481186f6e8c7e657aa99c33b09dad943d1cc5e398a8981afaa3f85f9`.
- O label do RNNoise no questionario passou a indicar normalizacao de loudness e
  equalizacao leve de presenca, deixando claro que ha pos-processamento
  auditavel sobre a saida RNNoise.
- O README do questionario foi atualizado com o comando reprodutivel para gerar
  as variantes e com a origem da amostra publicada.
- A avaliacao com DeepFilterNet fica em trilha separada/offline e nao bloqueia a
  publicacao do questionario atual.

## 2026-06-28 - Trilha offline DeepFilterNet preparada

- Antes da implementacao, foi feita uma revisao tecnica via Claude CLI em modo
  de planejamento/leitura, sem alteracao de arquivos pelo Claude.
- Decisao metodologica: DeepFilterNet fica como avaliacao exploratoria offline,
  separada do questionario publicado e sem qualquer promessa de tempo real,
  baixa latencia ou compatibilidade com microfone virtual Windows.
- Foi criada a rotina:
  `scripts/audio/prepare_deepfilternet_eval.py`.
- A rotina aceita WAV de entrada, referencia limpa opcional e gera apenas saidas
  dentro de `tmp/deepfilternet_eval/<nome>/`.
- O script recusa `--output-dir` fora de `tmp/`, para impedir substituicao
  acidental de audios publicados ou resultados versionados.
- O fluxo de sample rate ficou explicito:
  - entrada original registrada no relatorio;
  - entrada convertida para mono em 48 kHz para o DeepFilterNet;
  - comparacoes finais renderizadas em 16 kHz, alinhadas ao pipeline principal
    do projeto.
- Limitacao registrada: quando a entrada original e 16 kHz, o upsample para
  48 kHz nao cria conteudo acima de 8 kHz; ele apenas satisfaz a entrada usual
  do DeepFilterNet.
- Comparacoes previstas:
  - referencia ruidosa com loudness equalizado;
  - RNNoise + EQ leve de presenca + loudness;
  - DeepFilterNet + loudness;
  - DeepFilterNet + EQ leve de presenca + loudness;
  - referencia limpa com loudness equalizado, quando fornecida.
- O relatorio JSON `deepfilternet_report.json` registra caminhos, hashes
  SHA-256, sample rates, parametros de loudness/EQ, loudness/LUFS, RMS, pico,
  centroide espectral, energia em 3-8 kHz, tempos de processamento, RTF,
  ambiente e limitacoes metodologicas.
- Dependencia pesada nao foi adicionada a `requirements.txt`. O caminho seguro e
  usar uma venv isolada em `tmp/.venv_deepfilternet`.
- Comandos sugeridos de instalacao isolada:

```powershell
python -m venv tmp\.venv_deepfilternet
tmp\.venv_deepfilternet\Scripts\python -m pip install --upgrade pip
tmp\.venv_deepfilternet\Scripts\python -m pip install -r requirements.txt
tmp\.venv_deepfilternet\Scripts\python -m pip install deepfilternet
```

- Comando de reproducao planejado:

```powershell
tmp\.venv_deepfilternet\Scripts\python scripts\audio\prepare_deepfilternet_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name questionario_amostra
```

- Validacoes executadas nesta etapa:
  - `python -m compileall scripts/audio/prepare_deepfilternet_eval.py`;
  - `python scripts/audio/prepare_deepfilternet_eval.py --help`;
  - execucao com a amostra local confirmou falha limpa quando `deepFilter` nao
    esta instalado, antes de gerar artefatos.
- O Apps Script, o questionario, o manifesto `2026-06-28.5` e os audios
  publicados em `docs/questionario/assets/audio/` nao foram alterados.

## 2026-06-28 - DeepFilterNet instalado e avaliacao offline executada

- Foi criada e usada a venv isolada `tmp/.venv_deepfilternet`.
- Dependencias instaladas na venv:
  - `deepfilternet==0.5.6`;
  - `DeepFilterLib==0.5.6`;
  - `torch==2.5.1+cpu`;
  - `torchaudio==2.5.1+cpu`;
  - `soundfile==0.12.1`.
- O primeiro par `torch==2.12.1+cpu` e `torchaudio==2.11.0+cpu` foi substituido
  porque nao expos o modulo de backend esperado por `deepfilternet==0.5.6`.
- Antes de instalar `soundfile`, `torchaudio.list_audio_backends()` retornava
  lista vazia; depois passou a retornar `['soundfile']`.
- A CLI `deepFilter.exe --help` respondeu corretamente. O warning interno sobre
  `torchaudio.backend.common.AudioMetaData` foi registrado, mas nao bloqueou a
  execucao.
- A primeira execucao completa revelou um bug local da rotina: o relatorio
  tentava medir MP3 com `scipy.io.wavfile`, que so aceita RIFF/RIFX/RF64.
- `scripts/audio/prepare_deepfilternet_eval.py` foi corrigido para medir WAV
  diretamente com `scipy` e arquivos comprimidos, como MP3, via
  `ffprobe`/`ffmpeg` decodificando para `float32` mono.
- Validacao apos correcao:
  - `tmp/.venv_deepfilternet/Scripts/python.exe -m compileall scripts/audio/prepare_deepfilternet_eval.py`.
- A avaliacao offline foi executada com referencia limpa:

```powershell
tmp\.venv_deepfilternet\Scripts\python.exe scripts\audio\prepare_deepfilternet_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name questionario_amostra
```

- Saidas geradas em:
  `tmp/deepfilternet_eval/questionario_amostra/`.
- MP3s gerados para escuta comparativa:
  - `questionario_amostra_noisy_reference_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_presence_eq_loudnorm.mp3`;
  - `questionario_amostra_deepfilternet_loudnorm.mp3`;
  - `questionario_amostra_deepfilternet_presence_eq_loudnorm.mp3`;
  - `questionario_amostra_clean_reference_loudnorm.mp3`.
- Relatorio auditavel:
  `tmp/deepfilternet_eval/questionario_amostra/deepfilternet_report.json`.
- Resultado de custo computacional nesta execucao offline:
  - DeepFilterNet: RTF aproximadamente `2,342`;
  - RNNoise: RTF aproximadamente `0,106`.
- Loudness final ficou controlado em torno de `-16 LUFS` nas variantes geradas.
- Interpretacao metodologica:
  **DeepFilterNet foi executado com sucesso como trilha offline exploratoria,
  mas o RTF medido nesta rodada nao sustenta qualquer alegacao de tempo real ou
  baixa latencia no prototipo Windows.**
- O Apps Script, o questionario, o manifesto `2026-06-28.5` e os audios
  publicados em `docs/questionario/assets/audio/` continuaram inalterados.

## 2026-06-28 - Variantes anti-metalizacao RNNoise geradas

- Decisao de continuidade: DeepFilterNet permanece apenas como comparacao
  offline exploratoria, pois o RTF medido de aproximadamente `2,342` nao
  sustenta continuidade como candidato pratico ao microfone virtual atual.
- O foco voltou integralmente para RNNoise, que combina boa reducao perceptual
  de ruido e custo computacional baixo.
- Foi criada a rotina:
  `scripts/audio/prepare_rnnoise_antimetallic_eval.py`.
- A rotina mantem RNNoise como nucleo e testa apenas pos-processamento auditavel
  para reduzir percepcao de voz metalizada:
  - normalizacao de loudness;
  - EQ de pico atual em 3 kHz;
  - mistura RNNoise/original 90/10;
  - mistura RNNoise/original 85/15;
  - high-shelf suave;
  - high-shelf com reforco leve de corpo;
  - low-pass suave no topo da banda;
  - reforco leve de corpo;
  - combinacao 90/10 com shelf e corpo.
- O script recusa saida fora de `tmp/` e nao altera o questionario publicado.
- Ajuste de compatibilidade: o FFmpeg local nao aceitou `amix=normalize=0`; como
  os volumes da mistura ja sao definidos explicitamente, a rotina passou a usar
  `amix=inputs=2`.
- Validacoes executadas:
  - `python -m compileall scripts/audio/prepare_rnnoise_antimetallic_eval.py`;
  - `python scripts/audio/prepare_rnnoise_antimetallic_eval.py --help`.
- Execucao com a amostra do questionario:

```powershell
python scripts\audio\prepare_rnnoise_antimetallic_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name questionario_amostra
```

- Saidas geradas em:
  `tmp/rnnoise_antimetallic_eval/questionario_amostra/`.
- MP3s gerados:
  - `questionario_amostra_noisy_reference_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_peak_eq_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_mix90_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_mix85_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_shelf_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_shelf_warm_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_lowpass_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_warm_loudnorm.mp3`;
  - `questionario_amostra_rnnoise_mix90_shelf_warm_loudnorm.mp3`.
- Relatorio auditavel:
  `tmp/rnnoise_antimetallic_eval/questionario_amostra/antimetallic_report.json`.
- Loudness final ficou controlado em torno de `-16 LUFS` nas variantes.
- RTF RNNoise medido nesta execucao da rotina: aproximadamente `0,0276`.
- Observacao para escuta manual: as variantes `mix90` e `mix85` aumentam a
  energia em 3-8 kHz em relacao ao RNNoise puro, o que pode recuperar naturalidade
  de voz, mas tambem pode devolver um pouco de ruido residual. A escolha deve ser
  feita por escuta comparativa.
- O Apps Script, o questionario, o manifesto `2026-06-28.5` e os audios
  publicados em `docs/questionario/assets/audio/` continuaram inalterados.

## 2026-06-28 - Feedback de escuta anti-metalizacao e pendencias

- Feedback manual de escuta:
  - `questionario_amostra_rnnoise_mix90_loudnorm.mp3` ficou com ruido de fundo
    perceptivel;
  - `questionario_amostra_rnnoise_mix85_loudnorm.mp3` ficou com ruido de fundo
    perceptivel;
  - `questionario_amostra_rnnoise_mix90_shelf_warm_loudnorm.mp3` tambem ficou
    com ruido de fundo perceptivel.
- Decisao: as variantes com mistura wet/dry usando o sinal original nao devem
  seguir como candidatas principais, pois devolvem ruido demais para o objetivo
  perceptual atual.
- Foi percebido um barulho curto tipo `tick` imediatamente depois da palavra
  `two`. O tick nao existe no audio original e parece estar presente nos audios
  tratados por RNNoise.
- Revisao via Claude CLI, sem edicao de arquivos, sugeriu investigar primeiro:
  - fronteira de bloco do RNNoise;
  - diferenca entre `rnnoise_base.wav`, WAV pos-loudnorm e MP3 decodificado;
  - possivel efeito de pre-roll, reamostragem, loudnorm/EQ ou encoder MP3.
- Diagnostico rapido inicial com diferencas e maiores saltos de amostra foi
  inconclusivo: nao confirmou de forma direta alinhamento exato do maior evento
  com fronteira de bloco, portanto a causa do tick ainda nao deve ser afirmada.
- Pendencia tecnica criada:
  **montar uma rotina diagnostica dedicada em `tmp/` para localizar o tick por
  janela temporal, comparar original, RNNoise base, RNNoise loudnorm, EQ e MP3
  decodificado, e verificar se o evento aparece antes ou depois do
  pos-processamento.**
- Para reduzir metalizacao sem devolver ruido, as proximas alternativas devem
  evitar wet/dry mix e priorizar:
  - EQ pos-RNNoise mais conservador, sem pico agressivo em 3 kHz;
  - atenuacao leve na regiao alta associada ao brilho metalico;
  - eventual controle de piso de supressao/ganho minimo no wrapper RNNoise,
    somente apos diagnostico offline;
  - nova matriz pequena, sem reintroduzir sinal original ruidoso.
- O Apps Script, o questionario, o manifesto `2026-06-28.5` e os audios
  publicados em `docs/questionario/assets/audio/` continuaram inalterados.

## 2026-06-28 - Diagnostico inicial do tick RNNoise

- Foi criada a rotina:
  `scripts/audio/diagnose_rnnoise_tick.py`.
- Objetivo: isolar o `tick` percebido logo apos a palavra `two/to`, comparando
  janela curta do audio original, RNNoise processado no arquivo completo,
  RNNoise processado apenas na janela, MP3 decodificado e variantes RNNoise ja
  geradas.
- A rotina grava apenas em `tmp/rnnoise_tick_diag/<nome>/` e nao altera o
  questionario publicado.
- Validacoes executadas:
  - `python -m compileall scripts/audio/diagnose_rnnoise_tick.py`;
  - `python scripts/audio/diagnose_rnnoise_tick.py --help`.
- Execucao inicial:

```powershell
python scripts\audio\diagnose_rnnoise_tick.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --name questionario_amostra `
  --center-s 1.82 `
  --window-s 0.50 `
  --also-file tmp\rnnoise_antimetallic_eval\questionario_amostra\wav\questionario_amostra_rnnoise_loudnorm.wav `
  --also-file tmp\rnnoise_antimetallic_eval\questionario_amostra\wav\questionario_amostra_rnnoise_peak_eq_loudnorm.wav
```

- Saidas geradas em:
  `tmp/rnnoise_tick_diag/questionario_amostra/`.
- Relatorio gerado:
  `tmp/rnnoise_tick_diag/questionario_amostra/tick_diag_report.json`.
- Janelas WAV geradas para escuta:
  - `questionario_amostra_original_window.wav`;
  - `questionario_amostra_rnnoise_full_window.wav`;
  - `questionario_amostra_rnnoise_window_only.wav`;
  - `questionario_amostra_rnnoise_full_window_mp3decoded.wav`;
  - janelas extras das variantes `rnnoise_loudnorm` e `rnnoise_peak_eq_loudnorm`.
- Resultado inicial:
  - o evento forte aparece no RNNoise base e permanece no MP3 decodificado;
  - o evento nao parece ser criado exclusivamente pelo encoder MP3;
  - loudnorm/EQ parecem amplificar o evento, mas nao necessariamente cria-lo;
  - os maiores saltos detectados na janela nao ficaram exatamente alinhados com
    uma fronteira de bloco RNNoise, portanto a hipotese de fronteira de bloco
    ainda nao esta confirmada.
- Proxima acao recomendada: escutar as janelas curtas geradas e, se necessario,
  ajustar `--center-s` para o ponto exato percebido manualmente antes de tentar
  remocao/correcao.

## 2026-06-28 - Pre-checagem local do questionario GitHub Pages

- A URL esperada para GitHub Pages, a partir do `origin`, e:
  `https://gamathias14.github.io/reducao-de-ruido-algoritmica/questionario/`.
- Pre-checagem local do manifesto:
  - `submission.enabled` esta `true`;
  - `schemaVersion` esta em `2026-06-28.5`;
  - os 6 MP3s declarados no manifesto existem;
  - todos os hashes SHA-256 declarados no manifesto batem com os arquivos locais.
- Esta checagem nao substitui o teste real no navegador apos o deploy do GitHub
  Pages, especialmente o teste de envio para Apps Script/Google Sheets.

## 2026-06-28 - Confirmacao manual do Pages e do tick isolado

- O teste manual no navegador do GitHub Pages foi bem-sucedido: o questionario
  carregou corretamente e o fluxo inicial esta funcional.
- O tick foi confirmado por escuta manual nas janelas curtas geradas pela rotina
  `scripts/audio/diagnose_rnnoise_tick.py`.
- Com isso, a etapa de localizacao deixou de ser apenas teorica: ha um trecho
  curto reproduzivel em `tmp/rnnoise_tick_diag/questionario_amostra/wav/` para
  guiar a correcao.
- Proxima frente tecnica: testar remocao/correcao do tick primeiro nessa janela
  curta, antes de alterar a cadeia completa RNNoise ou qualquer audio publicado.
- Possiveis estrategias de correcao a avaliar offline:
  - atenuacao localizada do transiente;
  - interpolacao curta ao redor do clique;
  - filtro de de-click em janela estreita;
  - ajuste no pos-processamento para nao amplificar o evento.
- O questionario publicado permanece como esta ate haver uma variante RNNoise
  corrigida e aprovada por escuta manual.

## 2026-06-28 - Primeira tentativa de remocao do tick RNNoise

- Foi criada a rotina experimental:
  `scripts/audio/prepare_rnnoise_tick_declick_eval.py`.
- Objetivo: aplicar correcoes localizadas no tick identificado, gerando variantes
  em `tmp/` para escuta manual antes de qualquer substituicao de audio publicado.
- Validacao executada:
  - `python -m compileall scripts/audio/prepare_rnnoise_tick_declick_eval.py`.
- Execucao inicial:

```powershell
python scripts\audio\prepare_rnnoise_tick_declick_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --processed-rnnoise tmp\rnnoise_tick_diag\questionario_amostra\wav\questionario_amostra_rnnoise_full.wav `
  --name questionario_amostra `
  --tick-time-s 1.8171 `
  --search-ms 90
```

- Tick detectado automaticamente em aproximadamente `1,817125 s`, amostra
  `29074` no audio completo.
- Saidas geradas em:
  `tmp/rnnoise_tick_declick_eval/questionario_amostra/`.
- Relatorio gerado:
  `tmp/rnnoise_tick_declick_eval/questionario_amostra/tick_declick_report.json`.
- Variantes geradas para escuta de janela curta:
  - `questionario_amostra_rnnoise_uncorrected_window.mp3`;
  - `questionario_amostra_interp_5_samples_window.mp3`;
  - `questionario_amostra_interp_9_samples_window.mp3`;
  - `questionario_amostra_interp_15_samples_window.mp3`;
  - `questionario_amostra_attenuate_2ms_window.mp3`;
  - `questionario_amostra_microfade_9_samples_window.mp3`.
- A rotina tambem gerou arquivos completos com a cadeia de EQ atual + loudnorm
  para verificar se a correcao se mantem no formato de avaliacao do questionario.
- Resultado objetivo inicial: nas variantes corrigidas, o maior salto da janela
  deixou de ocorrer exatamente no ponto do tick detectado e passou para outro
  evento posterior de fala. Isso sugere que o transiente local foi reduzido,
  mas a aprovacao depende de escuta manual.
- Feedback manual posterior: todas as variantes iniciais ainda mantiveram o tick
  audivel por volta de `1,817125 s`, logo a correcao de poucos samples foi
  insuficiente.
- A rotina foi ampliada para uma segunda rodada com correcoes de milissegundos:
  - interpolacao agressiva de 8 ms e 16 ms;
  - atenuacao localizada de 8 ms e 20 ms;
  - suavizacao local de 8 ms;
  - patch curto usando o audio original ruidoso em 6 ms, 12 ms e 24 ms.
- Segunda execucao:

```powershell
python scripts\audio\prepare_rnnoise_tick_declick_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --processed-rnnoise tmp\rnnoise_tick_diag\questionario_amostra\wav\questionario_amostra_rnnoise_full.wav `
  --name questionario_amostra_round2 `
  --tick-time-s 1.8171 `
  --search-ms 90
```

- Saidas da segunda rodada:
  `tmp/rnnoise_tick_declick_eval/questionario_amostra_round2/`.
- Relatorio da segunda rodada:
  `tmp/rnnoise_tick_declick_eval/questionario_amostra_round2/tick_declick_report.json`.
- Observacao objetiva: os patches com audio original ruidoso aumentaram bastante
  os saltos locais, portanto podem remover a percepcao de tick, mas tendem a
  reintroduzir transientes/ruido e devem ser avaliados com cautela.
- Nada foi alterado no questionario publicado.


## 2026-06-28 - Revisao Claude high sobre tick persistente

- A segunda rodada de de-click ainda manteve o tick perceptivel em todas as
  variantes indicadas para escuta.
- Foi chamada uma revisao via Claude CLI em modo de planejamento/leitura, sem
  edicao de arquivos pelo Claude.
- Conclusao principal: a falha das correcoes de poucos samples e tambem das
  correcoes de ate 24 ms indica que o problema provavelmente nao e um clique
  pontual simples.
- Hipoteses prioritarias levantadas:
  - artefato espectral/tonal criado pelo RNNoise na transicao de fala para
    silencio/ruido;
  - localizacao errada do evento, pois `argmax(abs(processado - original))` pode
    localizar a maior diferenca numerica e nao o centro perceptual do tick;
  - artefato multi-frame do RNNoise, possivelmente com duracao de 30 a 60 ms;
  - costuras das tentativas de patch criando ou mantendo artefatos;
  - pre-echo ou redistribuicao perceptual introduzida pelo MP3;
  - necessidade de alinhar patches a fronteiras de frame equivalentes a blocos
    do RNNoise.
- Proxima estrategia recomendada:
  1. gerar espectrogramas da janela `1,75 s` a `1,95 s` para original, RNNoise e
     diferenca;
  2. criar uma varredura perceptual com clipes curtos deslizantes para localizar
     onset/offset reais do tick, em vez de confiar apenas na maior diferenca de
     amostra;
  3. testar patches maiores de `40 ms`, `60 ms`, `80 ms` e `100 ms` com crossfade
     longo, somente apos confirmar a localizacao;
  4. comparar WAV diretamente contra MP3 para verificar se o codec esta mantendo
     ou espalhando o artefato;
  5. testar patches alinhados a fronteiras de frame se a evidencia apontar para
     artefato de frame/bloco.
- Criterio de parada sugerido: se mesmo patches grandes e localizados por escuta
  falharem, considerar trocar a amostra de audio usada no questionario, em vez de
  continuar tentando mascarar um artefato estrutural dessa fala especifica.
- Nada foi alterado no questionario publicado.

## 2026-06-28 - Diagnostico profundo do tick RNNoise executado

- Foi criada a rotina:
  `scripts/audio/prepare_rnnoise_tick_deepdiag.py`.
- Objetivo: dar continuidade ao plano Claude high com diagnostico por
  espectrograma, varredura perceptual de clipes deslizantes e patches maiores /
  alinhados a frames.
- Validacao executada:
  - `python -m compileall scripts/audio/prepare_rnnoise_tick_deepdiag.py`.
- Execucao inicial:

```powershell
python scripts\audio\prepare_rnnoise_tick_deepdiag.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --processed-rnnoise tmp\rnnoise_tick_diag\questionario_amostra\wav\questionario_amostra_rnnoise_full.wav `
  --name questionario_amostra `
  --range-start-s 1.70 `
  --range-end-s 2.02 `
  --scan-clip-ms 60 `
  --scan-step-ms 20 `
  --tick-time-s 1.817125
```

- Saidas geradas em:
  `tmp/rnnoise_tick_deepdiag/questionario_amostra/`.
- Relatorio:
  `tmp/rnnoise_tick_deepdiag/questionario_amostra/deepdiag_report.json`.
- Guia de escuta:
  `tmp/rnnoise_tick_deepdiag/questionario_amostra/README.md`.
- Espectrogramas gerados:
  - `png/questionario_amostra_spectrogram_original.png`;
  - `png/questionario_amostra_spectrogram_rnnoise.png`;
  - `png/questionario_amostra_spectrogram_difference_gain4.png`.
- Varredura perceptual gerada em `mp3/scan/`, com clipes de `60 ms` a cada
  `20 ms`, em formato `original -> pausa -> RNNoise`.
- Patches maiores gerados em `mp3/patches/`, incluindo:
  - patches com original ruidoso de `40`, `60`, `80` e `100 ms`;
  - fades para silencio nos mesmos intervalos;
  - patches e fades alinhados a frames RNNoise equivalentes.
- Observacao inicial do relatorio: os maiores scores espectrais de diferenca
  aparecem antes de `1,817125 s`, especialmente por volta de `1,784 s` a
  `1,796 s` em energia total/presenca, enquanto a banda baixa tambem apresenta
  diferencas relevantes mais tarde, entre `1,872 s` e `1,908 s`.
- Proxima acao: escuta manual da varredura em `mp3/scan/` para identificar em
  qual clipe o tick fica mais evidente e assim localizar onset/offset reais.
- Nada foi alterado no questionario publicado.

## 2026-06-28 - Preparacao para teste com gravacao propria

- Objetivo da nova frente: verificar se o tick percebido na transicao `two -> three`
  e especifico da amostra atual do questionario ou se tambem aparece em uma
  gravacao nova feita localmente.
- Estado confirmado por inspecao local:
  - scripts RNNoise/tick existentes em `scripts/audio/`;
  - nucleo RNNoise existente em `realtime_audio/process_wav_rnnoise.py` e
    `realtime_audio/rnnoise_processor.py`;
  - saidas temporarias anteriores preservadas em `tmp/rnnoise_tick_diag/`,
    `tmp/rnnoise_tick_declick_eval/` e `tmp/rnnoise_tick_deepdiag/`.
- Ferramentas locais confirmadas:
  - Python `3.11.4`;
  - FFmpeg/FFprobe `4.2.9`;
  - DLL RNNoise default encontrada em
    `%USERPROFILE%\.cache\ptc3527-benchmark\bin\ptc3527-rnnoise-v0.2.dll`.
- Observacao operacional: `realtime_audio/process_wav_rnnoise.py` deve ser
  executado como modulo (`python -m realtime_audio.process_wav_rnnoise`), pois a
  execucao direta do arquivo nao encontra o pacote `realtime_audio`.
- Proxima acao: o usuario deve gravar um audio curto proprio, entre `10` e
  `20 s`, preferencialmente em WAV/PCM ou M4A/MP3 sem efeitos, e salvar/copiar o
  arquivo bruto para `tmp/user_recordings/` antes da rodada experimental.
- Restricoes preservadas: nada foi alterado em `docs/questionario/`, Apps Script,
  manifesto `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Rodada RNNoise com gravacao propria executada

- Arquivo bruto encontrado em:
  `tmp/user_recordings/teste_audio_augusto.m4a`.
- Metadados de entrada:
  - codec: AAC;
  - taxa de amostragem: `48 kHz`;
  - canais: `2`;
  - duracao: `8,469 s`.
- Observacao: a duracao ficou abaixo da faixa ideal de `10` a `20 s`, mas foi
  considerada suficiente para esta rodada experimental.
- Foi criada a rotina:
  `scripts/audio/prepare_user_recording_rnnoise_eval.py`.
- Validacao executada:
  - `python -m compileall scripts/audio/prepare_user_recording_rnnoise_eval.py`;
  - `python scripts/audio/prepare_user_recording_rnnoise_eval.py --help`.
- Execucao:

```powershell
python scripts\audio\prepare_user_recording_rnnoise_eval.py `
  --input tmp\user_recordings\teste_audio_augusto.m4a `
  --name teste_audio_augusto `
  --snr-db 5.0
```

- Saidas geradas em:
  `tmp/user_recording_rnnoise_eval/teste_audio_augusto/`.
- Relatorio completo:
  `tmp/user_recording_rnnoise_eval/teste_audio_augusto/metrics/user_recording_rnnoise_eval_report.json`.
- WAVs principais gerados:
  - `wav/teste_audio_augusto_clean_16k_mono.wav`;
  - `wav/teste_audio_augusto_clean_normalized.wav`;
  - `wav/teste_audio_augusto_artificial_noise_only.wav`;
  - `wav/teste_audio_augusto_noisy_artificial.wav`;
  - `wav/teste_audio_augusto_rnnoise_base.wav`;
  - `wav/teste_audio_augusto_rnnoise_loudnorm.wav`;
  - `wav/teste_audio_augusto_rnnoise_eq_loudnorm.wav`;
  - `wav/teste_audio_augusto_rnnoise_shelf_warm_loudnorm.wav`;
  - `wav/teste_audio_augusto_rnnoise_lowpass_loudnorm.wav`.
- MP3s para escuta manual gerados em:
  `tmp/user_recording_rnnoise_eval/teste_audio_augusto/mp3/`.
- Ruido artificial:
  - modelo: banda larga colorida + hum `60/120 Hz` + tom fraco tipo ventilacao;
  - SNR solicitado: `5,0 dB`;
  - SNR obtido: aproximadamente `5,0 dB`.
- RTF RNNoise medido nesta rodada: aproximadamente `0,0288`.
- Loudness/RMS/pico e hashes foram registrados no relatorio JSON.
- Interpretacao tecnica limitada: a rodada gerou material para escuta comparativa,
  mas ainda nao sustenta conclusao sobre presenca ou ausencia de tick sem escuta
  manual dos MP3s/WAVs gerados.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Metalizacao intrinseca RNNoise: reparo ativo e caminho 48 kHz

- Feedback manual do usuario sobre o diagnostico de normalizacao:
  - `rnnoise_raw_no_norm` tambem soou metalizado;
  - conclusao provisoria: a normalizacao/loudnorm nao e a causa principal,
    embora possa agravar/expor o artefato.
- Decisao tecnica: tratar a metalizacao como artefato intrinseco da saida
  RNNoise ou do caminho atual de adaptacao 16 kHz <-> 48 kHz.
- Foi criada a rotina:
  `scripts/audio/prepare_rnnoise_active_repair_eval.py`.
- Objetivo da rotina: testar mitigacoes que atuem em fala ativa sem `loudnorm`
  dinamico e sem gate/release que corte pausas.
- Familias testadas:
  - suavizacao temporal leve/media da magnitude espectral;
  - suavizacao cepstral leve de envelope;
  - atenuacao de picos tonais estreitos entre `1,6` e `6,5 kHz`;
  - restauracao fraca/leve de residuo speech-like do sinal original, limitada a
    bins harmonicamente plausiveis e fala ativa.
- Execucao:

```powershell
python scripts\audio\prepare_rnnoise_active_repair_eval.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\rnnoise_active_repair_eval `
  --startup-preroll-ms 200
```

- Saidas:
  `tmp/rnnoise_active_repair_eval/teste_audio_augusto/`.
- Relatorio:
  `tmp/rnnoise_active_repair_eval/teste_audio_augusto/metrics/active_repair_report.json`.
- MP3s principais:
  - `mp3/clean_reference.mp3`;
  - `mp3/noisy_reference.mp3`;
  - `mp3/rnnoise_raw.mp3`;
  - `mp3/tonal_tame_mild.mp3`;
  - `mp3/tonal_tame_medium.mp3`;
  - `mp3/cepstral_smooth_mild.mp3`;
  - `mp3/temporal_smooth_mild.mp3`;
  - `mp3/temporal_smooth_medium.mp3`;
  - `mp3/speech_residual_restore_weak.mp3`;
  - `mp3/speech_residual_restore_mild.mp3`.
- Resultado objetivo inicial:
  - `tonal_tame_mild` e `tonal_tame_medium` alteraram pouco o sinal
    (`delta_vs_rnnoise_relative_db` entre aproximadamente `-48 dB` e `-41 dB`)
    e reduziram levemente a participacao ativa em `3-8 kHz`;
  - suavizacao temporal reduziu um pouco a modulacao/energia de alta banda, mas
    mexeu mais no sinal;
  - suavizacao cepstral foi mais invasiva e piorou metricas contra a referencia;
  - restauracao speech-like preservou custo baixo, mas deve ser ouvida com
    cautela por risco de devolver ruido.
- RTF RNNoise nesta rodada: aproximadamente `0,0258`.
- RTF do pos-processamento: aproximadamente `0,005` a `0,019`, ainda abaixo do
  tempo real em PC, mas as familias mais caras exigiriam otimizacao antes de
  prototipo realtime.
- Tambem foi criada a rotina:
  `scripts/audio/prepare_rnnoise_path_compare.py`.
- Objetivo: separar artefato do modelo RNNoise de possivel artefato do adaptador
  atual 16 kHz -> 48 kHz -> 16 kHz.
- A rotina compara:
  - caminho atual via DLL `ptc3527-rnnoise-v0.2.dll`, com up/downsample FIR no
    adaptador;
  - caminho alternativo via executavel RNNoise nativo 48 kHz, com resampling
    externo `scipy.signal.resample_poly` e mesmo `startup_preroll_ms`.
- Execucao:

```powershell
python scripts\audio\prepare_rnnoise_path_compare.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\rnnoise_path_compare `
  --startup-preroll-ms 200
```

- Saidas:
  `tmp/rnnoise_path_compare/teste_audio_augusto/`.
- Relatorio:
  `tmp/rnnoise_path_compare/teste_audio_augusto/metrics/path_compare_report.json`.
- MP3s principais:
  - `mp3/rnnoise_dll_16k_adapter.mp3`;
  - `mp3/rnnoise_exe_48k_resample_poly.mp3`.
- Resultado objetivo inicial:
  - os dois caminhos ficaram com RMS/pico semelhantes;
  - o caminho `exe_48k_resample_poly` diferiu bastante da DLL
    (`delta_vs_dll_rms_dbfs` em torno de `-15 dBFS`);
  - a diferenca objetiva torna obrigatoria a escuta comparativa: se o caminho
    48 kHz externo soar menos metalizado, o proximo foco deve ser o adaptador ou
    o resampling interno, nao apenas pos-processamento.
- Conclusao honesta do ciclo:
  - nao e possivel garantir que o RNNoise stock nao introduza metalizacao apenas
    por pos-processamento simples;
  - se as variantes de reparo ativo e o caminho 48 kHz tambem falharem por
    escuta, deve-se registrar RNNoise como limitado perceptualmente nessa
    condicao e avaliar alternativas: controle de agressividade no adaptador,
    exposicao/alteracao de ganhos internos, retreino/fine-tuning do RNNoise ou
    selecao de outro nucleo com RTF aceitavel.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Diagnostico da normalizacao/loudnorm no RNNoise

- Feedback manual do usuario sobre a rodada temporal de cauda:
  - todas as variantes ainda mantiveram a voz metalizada;
  - as variantes de release/gate ficaram truncadas/picotadas entre momentos de
    silencio;
  - portanto, a estrategia de cortar cauda por VAD/release nao deve seguir como
    candidata principal neste audio.
- Nova hipotese levantada pelo usuario: a normalizacao/loudnorm apos o RNNoise
  pode estar agravando ou causando a percepcao de voz metalizada ao elevar
  residuos/artefatos da saida processada.
- Foi feita uma consulta curta ao Claude CLI em modo `high`, sem edicao pelo
  Claude. A recomendacao foi comparar RNNoise cru, ganho fixo, peak normalize,
  RMS-match e loudnorm atual, porque apenas remover loudnorm pode enviesar a
  escuta por diferenca de volume.
- Inspecao dos relatorios existentes mostrou que as variantes RNNoise com
  `loudnorm` atual estavam registrando `normalization_type: dynamic`, nao
  apenas ganho linear. Isso torna a hipotese de agravamento por normalizacao
  tecnicamente plausivel, embora ainda nao prove causalidade perceptual.
- Foi criada a rotina:
  `scripts/audio/prepare_rnnoise_loudness_diagnosis.py`.
- A rotina:
  - processa a entrada pelo RNNoise;
  - gera MP3s sem loudnorm e com alternativas de ganho fixo;
  - gera variantes `loudnorm` atuais e com LRA mais folgado;
  - mede RMS, pico, loudness, banda ativa de `3-8 kHz`, centroide espectral,
    SI-SDR contra a referencia limpa e RTF;
  - nao aplica release, gate ou cortes entre palavras.
- Validacoes executadas:
  - `python -m compileall scripts\audio\prepare_rnnoise_loudness_diagnosis.py`;
  - `python scripts\audio\prepare_rnnoise_loudness_diagnosis.py --help`.
- Execucao principal:

```powershell
python scripts\audio\prepare_rnnoise_loudness_diagnosis.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\rnnoise_loudness_diagnosis `
  --startup-preroll-ms 200
```

- Saidas geradas em:
  `tmp/rnnoise_loudness_diagnosis/teste_audio_augusto/`.
- Relatorio principal:
  `tmp/rnnoise_loudness_diagnosis/teste_audio_augusto/metrics/loudness_diagnosis_report.json`.
- MP3s principais para escuta manual:
  - `mp3/clean_reference_no_norm.mp3`;
  - `mp3/noisy_reference_no_norm.mp3`;
  - `mp3/rnnoise_raw_no_norm.mp3`;
  - `mp3/rnnoise_fixed_loudnorm_offset.mp3`;
  - `mp3/rnnoise_peak_m1.mp3`;
  - `mp3/rnnoise_active_rms_match_clean.mp3`;
  - `mp3/rnnoise_half_active_rms_match_clean.mp3`;
  - `mp3/rnnoise_all_rms_match_clean.mp3`;
  - `mp3/rnnoise_active_rms_match_noisy.mp3`;
  - `mp3/rnnoise_loudnorm_current.mp3`;
  - `mp3/rnnoise_loudnorm_lra20.mp3`;
  - `mp3/rnnoise_loudnorm_i20_lra20.mp3`.
- RTF RNNoise medido nesta rodada: aproximadamente `0,0280`.
- Resultado objetivo inicial:
  - RNNoise cru: RMS aproximadamente `-18,04 dBFS`, pico `-1,52 dBFS`,
    loudness aproximado `-16,89 LUFS`;
  - a referencia limpa tinha RMS ativo apenas cerca de `0,9 dB` acima do RNNoise
    cru, portanto a saida RNNoise nao estava dramaticamente baixa;
  - o ganho fixo para igualar RMS ativo a referencia limpa foi de apenas
    aproximadamente `+0,90 dB`;
  - `rnnoise_loudnorm_current` entrou em `normalization_type: dynamic`;
  - `rnnoise_loudnorm_lra20` tambem entrou em `dynamic` nesta versao do FFmpeg;
  - `rnnoise_loudnorm_i20_lra20` entrou em `linear`, mas ficou mais baixo
    (`-20 LUFS`, pico aproximadamente `-4,63 dBFS`);
  - a participacao espectral ativa em `3-8 kHz` ficou praticamente igual nas
    variantes de ganho fixo, como esperado, e um pouco maior no loudnorm atual
    (`~2,16%` contra `~2,07%`), diferenca objetiva pequena.
- Interpretacao honesta:
  - se `rnnoise_raw_no_norm`, `rnnoise_peak_m1` ou
    `rnnoise_active_rms_match_clean` soarem menos metalizados que
    `rnnoise_loudnorm_current`, o loudnorm atual deve ser tratado como agravante;
  - se todos continuarem metalizados, inclusive o RNNoise cru, a causa principal
    provavelmente esta na propria saida RNNoise/modelo/amostra, e a normalizacao
    apenas expõe o defeito;
  - a variante `rnnoise_loudnorm_i20_lra20` serve para testar loudnorm linear
    mais baixo, mas pode parecer menos cheia por estar cerca de 4 LU abaixo do
    alvo anterior.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Avaliacao temporal de cauda/metalizacao RNNoise

- Objetivo: investigar a hipotese de que a voz metalizada percebida na gravacao
  propria vem de artefatos temporais em transicoes fala -> pausa, e nao apenas
  de EQ fixo ou de falta de mistura com o sinal ruidoso.
- Foi feita uma consulta curta ao Claude CLI em modo conceitual. A consulta
  longa com leitura do projeto excedeu o tempo limite, mas a consulta curta
  convergiu para a abordagem de VAD/envelope/hold-release pos-RNNoise.
- Foi criada a rotina:
  `scripts/audio/prepare_rnnoise_temporal_tail_eval.py`.
- A rotina:
  - processa o WAV ruidoso pelo RNNoise;
  - detecta regioes de fala e offsets por VAD de energia em blocos de 20 ms;
  - mede eventos de cauda usando a referencia limpa quando disponivel;
  - aplica variantes causais de hold/release sobre a saida RNNoise;
  - gera WAVs crus, WAVs loudnorm, MP3s para escuta e JSON com metricas;
  - registra RTF do RNNoise e RTF do pos-processamento temporal.
- Validacoes executadas:
  - `python -m compileall scripts\audio\prepare_rnnoise_temporal_tail_eval.py`;
  - `python scripts\audio\prepare_rnnoise_temporal_tail_eval.py --help`.
- Rodada principal executada com VAD de controle no sinal ruidoso:

```powershell
python scripts\audio\prepare_rnnoise_temporal_tail_eval.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\rnnoise_temporal_tail_eval `
  --startup-preroll-ms 200 `
  --control-vad-source input `
  --analysis-vad-source clean
```

- Saidas principais:
  `tmp/rnnoise_temporal_tail_eval/teste_audio_augusto/`.
- Relatorio principal:
  `tmp/rnnoise_temporal_tail_eval/teste_audio_augusto/metrics/temporal_tail_eval_report.json`.
- MP3s principais para escuta manual:
  - `mp3/clean_reference_loudnorm.mp3`;
  - `mp3/noisy_reference_loudnorm.mp3`;
  - `mp3/rnnoise_base_loudnorm.mp3`;
  - `mp3/tail_release30_loudnorm.mp3`;
  - `mp3/tail_release45_loudnorm.mp3`;
  - `mp3/tail_release60_loudnorm.mp3`;
  - `mp3/tail_release15_loudnorm.mp3`;
  - `mp3/tail_release30_floor_m60_loudnorm.mp3`;
  - `mp3/speechmix3_release30_loudnorm.mp3`.
- Foram detectados `3` eventos de cauda pela referencia limpa.
- RTF RNNoise medido na rodada principal: aproximadamente `0,0330`.
- RTF do pos-processamento temporal: ordem de `0,0002` a `0,0007`, portanto
  custo computacional desprezivel frente ao RNNoise nesta medicao offline.
- Resultado objetivo da rodada principal:
  - RNNoise base: mediana de energia de cauda aproximadamente `-22,03 dB`
    contra a janela de fala anterior;
  - `tail_release30`: mediana de cauda aproximadamente `-53,01 dB`;
  - `tail_release45`: mediana de cauda aproximadamente `-42,01 dB`;
  - `tail_release60`: mediana de cauda aproximadamente `-37,00 dB`;
  - `tail_release15`: reducao extrema, aproximadamente `-81,65 dB`, mas com
    alto risco de corte perceptual/artificialidade;
  - `speechmix3_release30` manteve a reducao de cauda do release de 30 ms, mas
    piorou metricas contra a referencia limpa por reintroduzir parte do sinal
    ruidoso durante fala ativa. Deve ser ouvido com cautela, nao tratado como
    candidato automatico.
- Rodada comparativa executada com VAD de controle na propria saida RNNoise:

```powershell
python scripts\audio\prepare_rnnoise_temporal_tail_eval.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto_rnnoisevad `
  --output-dir tmp\rnnoise_temporal_tail_eval `
  --startup-preroll-ms 200 `
  --control-vad-source rnnoise `
  --analysis-vad-source clean
```

- Saidas comparativas:
  `tmp/rnnoise_temporal_tail_eval/teste_audio_augusto_rnnoisevad/`.
- Observacao tecnica importante: com VAD de controle no RNNoise, o gate quase
  nao atuou; as variantes ficaram praticamente iguais ao RNNoise base. Isso
  sugere que a propria saida RNNoise tende a manter regioes de cauda como fala
  ativa/energia relevante, reforcando a hipotese de artefato temporal de
  transicao.
- Interpretacao honesta:
  - a nova familia nao devolve ruido em pausas por mistura fixa com o original;
  - as variantes de release atacam diretamente a cauda artificial;
  - a metrica favorece `tail_release30`, mas a escuta pode preferir
    `tail_release45` ou `tail_release60` se `30 ms` soar truncado;
  - `15 ms` e diagnostico agressivo, nao candidato primario;
  - a decisao final permanece perceptual, especialmente para verificar se
    consoantes finais e respiracoes naturais foram cortadas.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Feedback manual: tick ausente e metalizacao perceptivel

- Feedback manual do usuario sobre a gravacao propria:
  - o artefato tipo `tick` nao ocorreu;
  - a voz ficou metalizada nos audios tratados;
  - a percepcao descrita foi de um resquicio/cauda no fim da fala, como um eco
    mais grosso, sem resultado `crystal clear`.
- Interpretacao provisoria:
  - o tick provavelmente foi infelicidade especifica da primeira amostra de
    benchmark;
  - o foco volta a ser reduzir metalizacao/cauda residual do RNNoise sem criar
    novos problemas.
- Nova rodada anti-metalizacao executada sobre a gravacao propria:

```powershell
python scripts\audio\prepare_rnnoise_antimetallic_eval.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\rnnoise_antimetallic_eval `
  --startup-preroll-ms 200 `
  --peak-eq-gain-db 1.0 `
  --shelf-gain-db 1.0 `
  --warmth-gain-db 1.0 `
  --lowpass-freq-hz 7000
```

- Saidas geradas em:
  `tmp/rnnoise_antimetallic_eval/teste_audio_augusto/`.
- MP3s principais para escuta manual:
  - `teste_audio_augusto_rnnoise_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_peak_eq_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_mix90_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_mix85_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_shelf_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_shelf_warm_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_lowpass_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_warm_loudnorm.mp3`;
  - `teste_audio_augusto_rnnoise_mix90_shelf_warm_loudnorm.mp3`.
- RTF RNNoise nessa execucao: aproximadamente `0,0252`.
- Observacao tecnica: variantes com mistura RNNoise/original podem recuperar
  naturalidade, mas tambem podem devolver ruido; a decisao depende de escuta
  manual.
- Foi criado um prompt de apoio para Claude em:
  `tmp/rnnoise_antimetallic_eval/teste_audio_augusto/PROMPT_CLAUDE_INVESTIGAR_METALIZACAO.md`.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-28 - Pivo para candidatos nao-RNNoise contra metalizacao

- Feedback manual consolidado do usuario:
  - todos os audios da leva com cauda/release continuaram metalizados;
  - a estrategia de cauda introduziu tambem voz truncada/picotada entre pausas;
  - `rnnoise_raw_no_norm` tambem soou metalizado, indicando que a normalizacao
    nao e a causa principal;
  - 16 kHz via DLL/adaptador e 48 kHz via executavel nativo/resampling soaram
    indistinguiveis;
  - conclusao operacional: RNNoise stock passa a ser tratado como referencia
    negativa para essa gravacao, nao como candidato principal.
- Foi feita uma consulta ao Claude CLI em modo `high`, sem edicao pelo Claude.
  A recomendacao convergiu para abandonar o RNNoise stock como supressor
  principal nesse caso e priorizar WebRTC APM NS, depois OMLSA/IMCRA e STFT
  causal; DeepFilterNet fica como teto de qualidade, mas fora da linha principal
  por RTF ja observado alto.
- Foi criada a rotina:
  `scripts/audio/prepare_non_rnnoise_candidates_eval.py`.
- A rotina:
  - gera referencias limpa/ruidosa;
  - gera `rnnoise_reference_raw` apenas como referencia negativa;
  - gera `webrtc_apm_ns_raw`, `omlsa_imcra_raw` e `baseline_stft_raw`;
  - nao aplica `loudnorm` dinamico nem gate/release;
  - grava WAV, MP3 e relatorio JSON com RTF, latencia declarada, RMS ativo e
    inativo, banda ativa de `3-8 kHz` e SI-SDR contra a referencia limpa.
- Validacao executada:
  - `python -m py_compile scripts\audio\prepare_non_rnnoise_candidates_eval.py`.
- Execucao principal:

```powershell
python scripts\audio\prepare_non_rnnoise_candidates_eval.py `
  --input tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_artificial.wav `
  --clean-reference tmp\user_recording_rnnoise_eval\teste_audio_augusto\wav\teste_audio_augusto_clean_normalized.wav `
  --name teste_audio_augusto `
  --output-dir tmp\non_rnnoise_candidates_eval
```

- Saidas geradas em:
  `tmp/non_rnnoise_candidates_eval/teste_audio_augusto/`.
- Relatorio principal:
  `tmp/non_rnnoise_candidates_eval/teste_audio_augusto/metrics/non_rnnoise_candidates_report.json`.
- MP3s principais para escuta manual:
  - `mp3/clean_reference.mp3`;
  - `mp3/noisy_reference.mp3`;
  - `mp3/rnnoise_reference_raw.mp3`;
  - `mp3/webrtc_apm_ns_raw.mp3`;
  - `mp3/omlsa_imcra_raw.mp3`;
  - `mp3/baseline_stft_raw.mp3`.
- Resultado objetivo inicial:
  - `rnnoise_reference_raw`: RTF `~0,0211`, latencia algoritmica `20 ms`,
    RMS inativo `~-53,83 dBFS`, SI-SDR ativo `~10,34 dB`;
  - `webrtc_apm_ns_raw`: RTF `~0,0024`, latencia algoritmica `6 ms`, RMS
    inativo `~-37,78 dBFS`, SI-SDR ativo `~-14,71 dB`;
  - `omlsa_imcra_raw`: RTF `~0,0643`, latencia algoritmica `32 ms`, RMS
    inativo `~-26,52 dBFS`, SI-SDR ativo `~11,27 dB`;
  - `baseline_stft_raw`: RTF `~0,1120`, latencia algoritmica `32 ms`, RMS
    inativo `~-32,15 dBFS`, SI-SDR ativo `~9,58 dB`.
- Checagem adicional de alinhamento por correlacao:
  - RNNoise, OMLSA/IMCRA e STFT ficaram com lag maximo `0` amostras;
  - WebRTC APM NS ficou com lag maximo de aproximadamente `12` amostras
    (`0,75 ms`), insuficiente para explicar sozinho o SI-SDR ativo negativo.
- Interpretacao honesta:
  - a decisao continua sendo perceptual, porque SI-SDR pode punir fortemente
    mudancas nao lineares que talvez ainda soem aceitaveis;
  - WebRTC APM NS e o candidato prioritario por latencia e custo, mas a metrica
    objetiva desfavoravel precisa ser confrontada com a escuta;
  - OMLSA/IMCRA tem a melhor metrica ativa entre os processados, mas deixa muito
    mais energia residual em pausas, portanto pode soar mais natural e mais
    ruidoso;
  - STFT causal fica como alternativa conservadora e leve, possivelmente menos
    metalizada, mas sem a supressao agressiva do RNNoise.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto
  `2026-06-28.5` ou audios publicados.

## 2026-06-29 - DeepFilterNet3 como candidato principal e plano de runtime nativo

- Contexto perceptual consolidado:
  - RNNoise stock e variantes pos-processadas/internas foram rejeitados por voz
    metalizada;
  - o veredito perceptual do usuario permanece soberano;
  - DeepFilterNet3 default, sem `--atten-lim`, tornou-se o novo candidato
    principal depois da escuta dos arquivos da rodada em `tmp/dfn_aug/`;
  - `dfn3_atten18` e `dfn3_atten12` foram rejeitados por devolverem
    metalizacao e ruido de fundo.
- Benchmark de viabilidade executado em area temporaria:
  - script: `tmp/dfn_realtime_benchmark/benchmark_dfn_realtime.py`;
  - resumo: `tmp/dfn_realtime_benchmark/README.md`;
  - CSV: `tmp/dfn_realtime_benchmark/dfn_realtime_stream_summary.csv`;
  - JSON completo:
    `tmp/dfn_realtime_benchmark/dfn_realtime_benchmark_results.json`.
- Achados computacionais locais:
  - instalacao atual: `DeepFilterNet==0.5.6`, `torch==2.5.1+cpu`,
    `torchaudio==2.5.1+cpu`;
  - modelo local: 48 kHz, `fft_size=960`, `hop_size=480`, 32 bandas ERB,
    96 bins DF, ordem DF 5, `df_lookahead=2`;
  - chamada direta com 10 ms falha no modelo PyTorch com
    `narrow(): length must be non-negative`;
  - streaming simulado acumula pelo menos 2 frames, isto e, processamento
    minimo de 20 ms;
  - melhor medicao local: 4 threads, captura/processamento de 20 ms, RTF
    aproximadamente `0,512`, media `10,24 ms`, p95 `13,55 ms`, p99
    `14,76 ms`, pior caso `16,49 ms`, zero underruns simulados;
  - CLI `deep-filter-py.exe` e API Python sao adequadas para prototipo e
    validacao offline, mas nao como nucleo final do microfone virtual.
- Investigacao de runtime nativo:
  - o ambiente local atual possui `deep-filter-py.exe` e
    `libdf.cp311-win_amd64.pyd`, mas nao possui `deep-filter.exe`;
  - o repositorio oficial do DeepFilterNet documenta `libDF` em Rust,
    `pyDF`, modelos para `libDF/deep-filter` e plugin LADSPA em tempo real;
  - releases oficiais registram versao Rust-only com loop real-time e
    correcao de divergencia entre implementacao nativa e PyTorch;
  - OpenVINO possui modelos IR para DeepFilterNet2/3, mas a reproducao de
    estado/streaming precisa ser validada antes de qualquer uso no pipeline;
  - projetos externos com FFmpeg/libDF e Rust/ONNX Runtime sao referencias
    uteis, nao decisoes automaticas.
- Documento tecnico criado:
  `docs/viabilidade_deepfilternet_tempo_real.md`.
- Integracao com a VM:
  - a VM `PTC3527-SYSVAD-LAB-FAST` continua sendo o laboratorio seguro para
    SYSVAD/endpoint;
  - nao iniciar nova tentativa de driver no host;
  - devido aos checkpoints 46-R, nao depender de captura fisica virtualizada
    como relogio inicial;
  - o proximo ensaio funcional deve seguir a disciplina host-cadenciada antes
    de reabrir ponte PCM v1 e endpoint.
- Proximo plano:
  - DFN-2: obter/compilar runtime nativo DeepFilterNet3 e reproduzir o
    processamento offline do mesmo WAV;
  - DFN-3: medir streaming nativo simulado com blocos de 20 ms;
  - DFN-4: validar host-cadenciado sem endpoint na VM;
  - DFN-5: reabrir ponte PCM v1/SYSVAD somente se os gates anteriores forem
    aprovados;
  - DFN-6: escuta controlada, mantendo a avaliacao perceptual como criterio
    soberano.
- Nada foi alterado em `entrega3.tex`, `entrega3.pdf`,
  `docs/questionario/`, assets publicados ou Apps Script.

## 2026-06-29 - DFN-2 runtime nativo oficial offline obtido

- Objetivo: resolver a pendencia operacional de nao haver `deep-filter.exe`
  nativo local para seguir a trilha DeepFilterNet3.
- Foi verificado que `rustc`/`cargo` nao estavam disponiveis no ambiente atual;
  portanto, a primeira rota escolhida foi baixar o binario oficial Windows em
  vez de compilar.
- Binario oficial baixado em area temporaria:
  `tmp/dfn_native/deep-filter-0.5.6-x86_64-pc-windows-msvc.exe`.
- Modelo oficial para runtime nativo baixado em area temporaria:
  `tmp/dfn_native/DeepFilterNet3_onnx.tar.gz`.
- Hashes:
  - binario: `75E11FA16445F560CB6B021521DDB89E89270D13B83089705D98776F58FD7915`;
  - modelo: `C94D91F70911001C946E0FABB4AA9ADC37045F45A03B56008CB0C8244CB63616`.
- Smoke test offline executado sobre:
  `tmp/dfn_aug/dfn3_default/wav/dfn3_default_deepfilternet_input_48000hz.wav`.
- Resultados:
  - execucao nativa com `-D`: `exit_code=0`, tempo total inicial
    aproximadamente `1441,85 ms`;
  - execucao nativa sem `-D`: `exit_code=0`, tempo total inicial
    aproximadamente `1812,08 ms`;
  - saida sem `-D` preserva o comprimento (`406527` amostras);
  - saida com `-D` alinha com a saida Python, mas fica `1440` amostras
    menor, equivalente a `30 ms`;
  - correlacao alinhada contra a saida Python: aproximadamente `0,995438`;
  - diferenca RMS alinhada: aproximadamente `-34,87 dBFS`.
- Benchmark repetido da CLI nativa:
  - sem `-D`: RTF total `0,1489`, `0,1716`, `0,1404`;
  - com `-D`: RTF total `0,1769`, `0,1427`, `0,1474`.
- Arquivos gerados:
  - `tmp/dfn_native/README.md`;
  - `tmp/dfn_native/native_cli_repeated_benchmark.csv`;
  - `tmp/dfn_native/out_dfn3_default_D/`;
  - `tmp/dfn_native/out_dfn3_default_noD/`.
- Documento tecnico atualizado:
  `docs/viabilidade_deepfilternet_tempo_real.md`.
- Interpretacao:
  - a falta de binario nativo offline foi resolvida;
  - a CLI nativa prova disponibilidade do motor e RTF favoravel em arquivo;
  - o fonte oficial v0.5.6 foi clonado em
    `tmp/dfn_native/DeepFilterNet-v0.5.6-source`;
  - `libDF/src/capi.rs` expoe `df_create`, `df_get_frame_length`,
    `df_process_frame`, controles de atenuacao/post-filter e `df_free`;
  - `libDF/Cargo.toml` possui feature `capi`, mas o release baixado nao trouxe
    uma DLL C API pronta;
  - `ladspa/src/lib.rs` confirma loop persistente com `DfTract::process()` e
    filas, mas LADSPA nao e a interface natural para o pipeline Windows/SYSVAD;
  - a proxima pendencia real e compilar ou obter uma DLL/API persistente para
    processar blocos com estado preservado, sem iniciar processo por arquivo;
  - VM, SYSVAD, ponte PCM v1 e endpoint continuam fora desta etapa.
- Nada foi alterado em `entrega3.tex`, `entrega3.pdf`,
  `docs/questionario/`, assets publicados ou Apps Script.


## 2026-06-29 - Fase A aprovada: host nativo C++ cadenciado por QPC

- Objetivo: substituir a bancada Python host-cadenciada por um loop nativo C++ minimalista para medir DeepFilterNet3 C API sem contaminação do scheduler Python.
- Diretório criado:
  `tmp/dfn_native/native_host_bench/`.
- Executável gerado:
  `tmp/dfn_native/native_host_bench/bin/native_host_bench.exe`.
- Relatório:
  `tmp/dfn_native/native_host_bench/PHASE_A_RESULTS.md`.
- Resumo consolidado:
  `tmp/dfn_native/native_host_bench/results/suite_summary.json`.
- Configuração preservada:
  - `post_filter_beta = 1.0`;
  - `atten_lim = 100.0`;
  - frame DeepFilterNet3 C API: `480` amostras a 48 kHz, isto é, `10 ms`;
  - preroll descartado: `96000` amostras, isto é, `2 s`;
  - atraso causal descartado: `1440` amostras, isto é, `30 ms`.
- Resultados da Fase A:
  - `dfn3_default`: p99 `1,650 ms`, máximo `2,013 ms`, over budget `0`, missed deadline `0`;
  - `clean_lufs16`: p99 `1,811 ms`, máximo `2,514 ms`, over budget `0`, missed deadline `0`;
  - `noisy_reference_lufs16`: p99 `1,593 ms`, máximo `1,684 ms`, over budget `0`, missed deadline `0`.
- Conclusão: Fase A aprovada. O C++ nativo resolveu a dúvida de cadência que contaminava a bancada Python.
- Próximo passo aprovado: iniciar Fase B com WASAPI/MMCSS antes de qualquer retorno a VM, SYSVAD, ponte PCM v1 ou microfone virtual final.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto `2026-06-28.5` ou áudios publicados.

## 2026-06-29 - Fase B1 iniciada: WASAPI render bench com MMCSS

- Objetivo: validar DeepFilterNet3 C API sob o relógio real do Windows Audio Engine usando WASAPI event-driven e MMCSS, ainda sem VM, SYSVAD, ponte PCM v1 ou microfone virtual final.
- Diretório criado:
  `tmp/dfn_native/wasapi_render_bench/`.
- Executável gerado:
  `tmp/dfn_native/wasapi_render_bench/bin/wasapi_render_bench.exe`.
- Documentação/relatório:
  - `tmp/dfn_native/wasapi_render_bench/README.md`;
  - `tmp/dfn_native/wasapi_render_bench/PHASE_B_RESULTS.md`.
- Script reproduzível:
  `tmp/dfn_native/wasapi_render_bench/run_shared_suite.ps1`.
- Resumo consolidado da última suite:
  `tmp/dfn_native/wasapi_render_bench/results/shared_muted_gate_suite_summary.json`.
- O render é mudo por padrão: segue o relógio do endpoint WASAPI, mas escreve silêncio no alto-falante. Para render audível, é necessário passar `--audible-render` explicitamente.
- Probe do endpoint shared:
  - formato: `48000 Hz`, `2 ch`, `32 bit`, `float32`;
  - período default: `100000 hns`, isto é, `10 ms`;
  - período mínimo: `30000 hns`, isto é, `3 ms`.
- Configuração testada:
  - WASAPI shared render event-driven;
  - buffer de `4800` frames, isto é, `100 ms`;
  - MMCSS `Pro Audio`: OK;
  - `timeBeginPeriod(1)`: OK;
  - `post_filter_beta = 1.0` preservado;
  - gate estável ignora `1` frame inicial de métrica, porque esse frame está dentro do preroll de `2 s` descartado depois do DFN; o CSV completo continua registrando todos os frames.
- Última suite shared/muted/MMCSS:
  - `dfn3_default`: p99 `2,813 ms`, máximo `11,941 ms`, over budget `1`, missed deadline `1`, underflow `0`, status `CHECK`;
  - `clean_lufs16`: p99 `2,582 ms`, máximo `3,348 ms`, over budget `0`, missed deadline `0`, underflow `0`, status `PASS`;
  - `noisy_reference_lufs16`: p99 `3,588 ms`, máximo `4,052 ms`, over budget `0`, missed deadline `0`, underflow `0`, status `CHECK`.
- Execuções individuais anteriores passaram nos três inputs, mas a suite reproduzível mostrou jitter/outlier real no modo WASAPI shared síncrono.
- Conclusão honesta: Fase B1 está implementada e funcional, mas ainda não fecha gate final nos três inputs. O caminho é promissor, mas precisa endurecimento antes de promoção.
- Caminho exclusive:
  - implementado no mesmo executável via `--mode exclusive`;
  - tentou formatos 48 kHz estéreo `float32`, `PCM16`, `PCM24` e `PCM32`;
  - o endpoint/driver atual recusou todos com `0x8889000E`;
  - interpretação: exclusive está bloqueado pelo endpoint atual, não pelo DeepFilterNet3.
- Próximo passo: B2 com separação entre thread WASAPI e worker DFN por ring buffer/fila, ou host-paced PCM usando relógio real, ainda sem SYSVAD; só depois reabrir ponte PCM v1/endpoint.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto `2026-06-28.5` ou áudios publicados.


## 2026-06-29 - Revisão externa da Fase B1 via Claude CLI

- Objetivo: consultar o Claude Code CLI como revisor técnico externo antes de avançar da B1 para B2.
- Prompt salvo em:
  `tmp/dfn_native/wasapi_render_bench/PROMPT_CLAUDE_REVIEW_B1.md`.
- Parecer salvo em:
  `tmp/dfn_native/wasapi_render_bench/CLAUDE_REVIEW_B1.md`.
- Veredito do Claude: **parcialmente aprovado**.
- Principais pontos do parecer:
  - a interpretação “B1 implementada e funcional, mas ainda não fecha gate final” está correta;
  - o desenho síncrono atual, no qual o evento WASAPI chama diretamente `ensure_samples()`/`df_process_frame()`, é causa plausível dos outliers;
  - o spike de `11,9 ms` no `dfn3_default` é compatível com jitter/preempção do Windows, não com bug evidente do DeepFilterNet3;
  - ignorar o frame 0 no gate estável é defensável porque ele está dentro do preroll descartado, desde que o CSV completo continue registrando todos os frames;
  - o bloqueio do exclusive mode deve ser tratado como limitação do endpoint/driver atual, não como falha do projeto.
- Recomendação do Claude para B2:
  - separar thread/evento WASAPI do worker DeepFilterNet3;
  - usar ring buffer/fila entre worker e render;
  - event thread deve apenas copiar amostras já processadas para `IAudioRenderClient`;
  - medir separadamente `dfn_proc_us`, `callback_us`, nível do ring buffer, p99/p999/max e underflows.
- Gate B2 sugerido:
  - worker DFN p99 <= `4 ms`;
  - worker DFN p999 <= `8 ms`;
  - worker DFN max <= `10 ms`;
  - callback WASAPI p99 <= `1 ms`;
  - underflow = `0`;
  - nível mínimo do ring buffer >= `1` frame;
  - três inputs aprovados na suite reproduzível.
- Decisão operacional: não avançar para SYSVAD/ponte PCM v1 ainda; primeiro endurecer B2 com ring buffer/fila ou, se o objetivo for VM, tratar host-paced PCM como trilha separada.

## 2026-06-29 - Fase B2 aprovada: WASAPI worker/ring buffer

- Objetivo: implementar a recomendação da revisão externa da B1, separando o event thread WASAPI do processamento DeepFilterNet3.
- Diretório criado:
  `tmp/dfn_native/wasapi_worker_bench/`.
- Executável gerado:
  `tmp/dfn_native/wasapi_worker_bench/bin/wasapi_worker_bench.exe`.
- Arquivos principais:
  - `tmp/dfn_native/wasapi_worker_bench/CMakeLists.txt`;
  - `tmp/dfn_native/wasapi_worker_bench/build_release.ps1`;
  - `tmp/dfn_native/wasapi_worker_bench/run_worker_suite.ps1`;
  - `tmp/dfn_native/wasapi_worker_bench/src/main.cpp`;
  - `tmp/dfn_native/wasapi_worker_bench/README.md`;
  - `tmp/dfn_native/wasapi_worker_bench/PHASE_B2_RESULTS.md`.
- Arquitetura implementada:
  - worker thread DeepFilterNet3 com `df_process_frame()`;
  - ring buffer SPSC de amostras float;
  - event thread WASAPI apenas copia amostras do ring buffer para `IAudioRenderClient`;
  - render mudo por padrão;
  - `post_filter_beta = 1.0` preservado;
  - warm-up aumentado para `10` frames.
- Observação de endpoint:
  - nesta rodada, o endpoint shared apareceu como `96000 Hz`, `8 ch`, `float32`;
  - o cliente 48 kHz shared não foi aceito exatamente;
  - para manter o DFN intacto, o worker continua em 48 kHz e o render mudo duplica amostras para seguir o relógio de 96 kHz;
  - isso não altera o processamento DFN nem os WAVs salvos em 48 kHz.
- Gate B2 usado:
  - worker p99 <= `4 ms`;
  - worker p999 <= `8 ms`;
  - worker max <= `10 ms`;
  - callback WASAPI p99 <= `1 ms`;
  - underflow = `0`;
  - ring buffer antes do callback >= `480` amostras.
- Resultados da suite local:
  - `dfn3_default`: worker p99 `1,782 ms`, p999 `2,121 ms`, max `2,227 ms`, callback p99 `0,137 ms`, underflow `0`, status `PASS`;
  - `clean_lufs16`: worker p99 `1,648 ms`, p999 `1,933 ms`, max `1,946 ms`, callback p99 `0,165 ms`, underflow `0`, status `PASS`;
  - `noisy_reference_lufs16`: worker p99 `1,823 ms`, p999 `4,056 ms`, max `6,073 ms`, callback p99 `0,140 ms`, underflow `0`, status `PASS`.
- Resumo consolidado:
  `tmp/dfn_native/wasapi_worker_bench/results/worker_ring_suite_summary.json`.
- Conclusão: B2 aprovada na suite local. A separação worker/ring buffer resolveu a falha estrutural da B1, reduzindo o callback p99 para menos de `0,2 ms` nos três inputs e mantendo underflow zero.
- Próximo passo recomendado: antes de SYSVAD, rodar teste mais longo/pior caso ou iniciar trilha host-paced PCM rumo à VM.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto `2026-06-28.5` ou áudios publicados.

## 2026-06-29 - Fase B3 pré-VM aprovada: teste longo de 60 s

- Objetivo: fechar a validação local imediatamente anterior à VM com um teste mais longo sobre a arquitetura B2 worker/ring buffer.
- Input composto gerado:
  `tmp/dfn_native/wasapi_worker_bench/b3_inputs/mixed_60s_capi_input48.wav`.
- Composição do input:
  - `dfn3_default`;
  - `clean_lufs16`;
  - `noisy_reference_lufs16`;
  - repetidos/cortados até `60 s` em mono PCM16 48 kHz.
- Arquivos de reprodução:
  - `tmp/dfn_native/wasapi_worker_bench/make_b3_mixed_input.py`;
  - `tmp/dfn_native/wasapi_worker_bench/run_b3_pre_vm.ps1`.
- Resultado bruto:
  - `summary.json` ficou `CHECK` porque o frame `0` do worker teve `14,451 ms`;
  - esse frame fica dentro do preroll descartado e não chega ao `output_aligned_raw48.wav`.
- Resultado estável, ignorando apenas o frame `0` e mantendo o CSV completo para auditoria:
  - duração: `60 s`;
  - worker frames totais: `6000`;
  - worker frames no gate estável: `5999`;
  - worker p99: `1,875 ms`;
  - worker p999: `2,508 ms`;
  - worker max: `3,306 ms`;
  - worker > `4 ms`: `0`;
  - worker > `8 ms`: `0`;
  - worker > `10 ms`: `0`;
  - callback p99: `0,039 ms`;
  - callback p999: `0,076 ms`;
  - callback max: `0,158 ms`;
  - underflow: `0`;
  - ring mínimo antes do callback: `480` samples;
  - status estável: `PASS`.
- Arquivos de resultado:
  - `tmp/dfn_native/wasapi_worker_bench/results/b3_mixed_60s_worker/summary.json`;
  - `tmp/dfn_native/wasapi_worker_bench/results/b3_mixed_60s_worker/b3_stable_summary.json`;
  - `tmp/dfn_native/wasapi_worker_bench/results/b3_mixed_60s_worker/worker_metrics.csv`;
  - `tmp/dfn_native/wasapi_worker_bench/results/b3_mixed_60s_worker/wasapi_events.csv`;
  - `tmp/dfn_native/wasapi_worker_bench/PHASE_B3_PRE_VM_RESULTS.md`.
- Conclusão: B3 pré-VM aprovada no gate estável. A validação local do motor fica encerrada o suficiente para preparar a trilha de VM.
- Handoff para VM criado:
  `tmp/dfn_native/VM_HANDOFF_NEXT_STEPS.md`.
- Decisão operacional para a VM: não entrar direto em SYSVAD. Primeiro validar transporte host-paced PCM com sequência, CRC/hash, timing, WAV reconstruído e underflow/backlog; só depois reabrir ponte PCM v1/SYSVAD.
- Nada foi alterado em `docs/questionario/`, Apps Script, manifesto `2026-06-28.5` ou áudios publicados.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K executada com gate `check`

- Objetivo: validar somente transporte host -> guest para DeepFilterNet3, sem SYSVAD, sem ponte PCM v1, sem driver e sem RNNoise.
- Scripts criados:
  - `scripts/audio/host_guest_pcm_stream_dfn48.py`;
  - `scripts/audio/analyze_dfn48_vm_transport.py`;
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1`.
- Input: `tmp/dfn_native/wasapi_worker_bench/b3_inputs/mixed_60s_capi_input48.wav`.
- Contrato efetivo: PCM16 mono, `48 kHz`, `480 samples/bloco`, `10 ms/bloco`, `100 blocos/s`.
- Observacao: a anotacao anterior de `50 blocos/s` era incompativel com `480 samples @ 48 kHz = 10 ms`; a rodada preservou o contrato de 10 ms.
- Resultado de integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, duracao reconstruida `60,0 s`.
- Hash de payload origem/recebido: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Resultado de timing: envio host p99 `13,447 ms`, max `36,280 ms`; recepcao guest p99 `18,722 ms`, max `442,938 ms`; um stall acima de `100 ms`; `188` rajadas abaixo de `5 ms`.
- Gate final: `resultados/dfn3_vm_transport_48k/vm_transport_gate.json` = `check`.
- Interpretacao: transporte logico aceito, mas jitter de chegada ainda impede promover a fase para `accepted`.
- Teardown: o orquestrador teve timeout aguardando `poweroff`, mas a recuperacao posterior restaurou `checkpoint45-causal-wpt-validated` e confirmou VM em `poweroff`, `audio_in=on`, clipboard/drag-and-drop desabilitados e NIC NAT.
- Decisao operacional: nao reabrir SYSVAD, ponte PCM v1 ou DFN dentro da VM antes de resolver/repetir o transporte classificado como `check`.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R2-JITTER manteve gate `check`

- Rodada: `resultados/dfn3_vm_transport_48k/runs/20260629-134254-dfn3-transport-48k-r2-jitter`.
- Objetivo: repetir o transporte DFN48 com sonda interna de scheduler no convidado.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, WAV `60,0 s`.
- Hash de payload: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Timing: envio host p99 `12,554 ms`, max `107,175 ms`; recepcao guest p99 `20,646 ms`, max `110,346 ms`.
- Sonda scheduler convidado: 37 gaps acima de `30 ms`, 2 acima de `100 ms`, max `569,455 ms`.
- Correlacao: 3 stalls de recepcao acima de `50 ms`; apenas 1 coincidiu com gap de scheduler acima de `30 ms` na mesma janela.
- Gate final: `check`.
- Interpretacao: payload e duracao estao corretos, mas a cadencia segue insuficiente para promover a etapa a `accepted`.
- Teardown: Windows ficou preso em `Desligando`; apos shutdown normal e ACPI falharem, foi usado `poweroff` forcado com autorizacao do usuario e restore imediato do snapshot 45. Estado final seguro confirmado.
- Decisao: ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R4-HOSTSEND isolou host/send

- Rodada: `resultados/dfn3_vm_transport_48k/runs/20260629-141223-dfn3-transport-48k-r4-hostsend`.
- Objetivo: testar transporte DFN48 com servidor host em prioridade `High` e instrumentacao fina do receive no convidado.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, WAV `60,0 s`.
- Hash de payload: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: p99 `10,015 ms`, max `10,532 ms`, lateness max `0,542 ms`, zero stall acima de `20 ms`.
- Guest receive: p99 `21,297 ms`, max `428,577 ms`, dois stalls acima de `50 ms`, um acima de `100 ms`.
- Os stalls relevantes ficaram em `header_wait_ms`, nao em payload read, CRC, hash ou WAV.
- Correlacao: os dois stalls relevantes tiveram envio host normal e nao coincidiram com gap de scheduler acima de `30 ms` na janela medida.
- Gate final: `check`.
- Classificacao: `guest_receive_or_nat_jitter`.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff forcado.
- Decisao: ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD; proximo gate deve isolar `recv`/NAT com receptor receive-only em memoria ou receptor nativo simples.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R5-RECEIVE-ONLY isolou escrita WAV

- Rodada: `resultados/dfn3_vm_transport_48k/runs/20260629-142556-dfn3-transport-48k-r5-receive-only`.
- Objetivo: testar transporte DFN48 com cliente `sink=memory`, sem escrita WAV no loop.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, duracao logica `60,0 s`.
- Hash de payload: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: prioridade `High`, p99 `10,023 ms`, max `10,789 ms`, zero stall acima de `20 ms`.
- Guest receive: p99 `16,896 ms`, max `473,736 ms`, dois stalls acima de `100 ms`.
- Os stalls ficaram em `header_wait_ms`, nao em payload read, CRC, hash ou WAV.
- Correlacao: os dois stalls relevantes tiveram envio host normal e nao coincidiram com gap de scheduler acima de `30 ms` na janela medida.
- Gate final: `check`.
- Classificacao: `guest_recv_or_nat_header_wait_jitter`.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff forcado.
- Decisao: ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD; proximo gate deve remover Python do receptor ou testar transporte alternativo/batching controlado.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R6-BATCH4 diagnosticou wakeups/NAT

- Rodada: `resultados/dfn3_vm_transport_48k/runs/20260629-143939-dfn3-transport-48k-r6-batch4-diagnostic`.
- Objetivo: testar transporte DFN48 com cliente `sink=memory` e empacotamento diagnostico de `4` blocos logicos por pacote TCP, sem alterar o contrato logico de `480` amostras, `10 ms` e `100 blocos/s`.
- Natureza do gate: diagnostico por design; `blocks_per_packet > 1` nao pode promover a fase a `accepted`.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, duracao logica `60,0 s`.
- Hash de payload: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send no nivel de pacote: p99 `40,020 ms`, max `40,513 ms`, lateness max `0,528 ms`.
- Guest packet receive: p99 `49,413 ms`, max `138,401 ms`; ainda houve `15` stalls acima de `50 ms` e `1` acima de `100 ms`.
- Os stalls permaneceram em `header_wait_ms`; payload read, CRC e hash nao explicam o problema.
- Correlacao: `12/15` stalls acima de `50 ms` foram `unaccounted_receive_or_nat`; `3/15` coincidiram com gap de scheduler do convidado; nenhum foi atribuido ao host/send.
- Gate final: `check`.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff forcado.
- Interpretacao: batching reduziu o pior outlier em relacao a R5, mas nao eliminou jitter de recepcao; a causa restante segue antes do DSP, no caminho `recv`/NAT/scheduler do convidado.
- Decisao: ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD. Proximo passo recomendado: receptor nativo minimo ou transporte alternativo para remover Python/Guest socket do caminho critico.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R7-NATIVE removeu Python do receptor

- Artefatos de codigo:
  - `scripts/native/dfn48_native_receiver/CMakeLists.txt`;
  - `scripts/native/dfn48_native_receiver/build_release.ps1`;
  - `scripts/native/dfn48_native_receiver/src/main.cpp`;
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` atualizado com `ClientImplementation=Native|Python`.
- Receptor nativo: WinSock TCP, contrato `PTCDFN3`, ACK `PTCDAK3`, CRC32, SHA-256 via BCrypt, temporizacao QPC, sonda de scheduler com `timeBeginPeriod(1)` e JSON compativel com o analisador existente.
- Build validado: MSVC Release com runtime estatico (`/MT`); dependencias do `.exe`: `WS2_32.dll`, `bcrypt.dll`, `WINMM.dll`, `KERNEL32.dll`.
- Validacao local host-only: gate `accepted`, sem warnings; integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`; hash `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`; recepcao p99 `10,107 ms`, max `13,764 ms`.
- Preflight antes da VM: `ready=true`, `failures=0`, `warnings=0`, snapshot `checkpoint45-causal-wpt-validated`, runtime `C:\PTC3527-Private\vm_runtime`.
- Tentativa abortada: `runs/20260629-150318-dfn3-transport-48k-r7-native-receiver` falhou antes do transporte com exit code `-1073741515` por runtime DLL ausente; teardown limpo, sem poweroff forcado. Essa tentativa nao foi usada como resultado experimental.
- Rodada valida: `resultados/dfn3_vm_transport_48k/runs/20260629-150919-dfn3-transport-48k-r7-native-receiver`.
- Objetivo: remover Python do receptor convidado, mantendo transporte DFN48, `sink=memory`, `BlocksPerPacket=1`, sem SYSVAD, sem ponte PCM v1, sem RNNoise e sem DeepFilterNet3 dentro da VM.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`, framing `0`, duracao logica `60,0 s`.
- Hash de payload: `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: p99 `10,018 ms`, max `10,482 ms`, lateness max `0,488 ms`, zero stall acima de `20 ms`.
- Guest receive nativo: p99 `14,936 ms`, max `186,643 ms`; `7` stalls acima de `20 ms`, `1` acima de `50 ms`, `1` acima de `100 ms`.
- Stall dominante: bloco `2246`, `header_wait_ms=186,609 ms`, payload read `0,023 ms`, CRC `0,004 ms`, envio host normal e sem gap de scheduler acima de `30 ms` na janela.
- Correlacao: `1/1` stall acima de `50 ms` classificado como `unaccounted_receive_or_nat`; nenhum atribuido ao host/send.
- Gate final: `check`, com warning `client_receive_stall_over_100ms`.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff forcado.
- Interpretacao: remover Python melhorou fortemente o p99 de recepcao, mas nao eliminou o outlier de `header_wait`; o bloqueio restante segue antes do DSP, no caminho `recv`/NAT/entrega TCP do convidado.
- Decisao: nao promover a fase; ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD. Proximo passo recomendado: transporte alternativo controlado, preferencialmente UDP diagnostico com sequencia/CRC/hash, ou repeticao R7 para medir variancia.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R8-UDP diagnosticou transporte alternativo

- Objetivo: testar transporte alternativo diagnostico para isolar o outlier de
  `header_wait` observado na R7 TCP nativa, ainda sem SYSVAD, sem ponte PCM v1,
  sem RNNoise e sem DeepFilterNet3 dentro da VM.
- Implementacao:
  - `scripts/audio/host_guest_pcm_stream_dfn48.py` ganhou `--transport tcp|udp`;
  - `scripts/native/dfn48_native_receiver/src/main.cpp` ganhou cliente UDP;
  - o controle permanece TCP para preambulo e ACK final;
  - os blocos PCM seguem por UDP com sequencia, CRC32 e hash SHA-256;
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` ganhou `-Transport tcp|udp`,
    mantendo `tcp` como padrao;
  - `scripts/audio/analyze_dfn48_vm_transport.py` marca UDP como diagnostico
    por design com warning `udp_transport_diagnostic_not_realtime_gate`.
- Validacoes antes da VM:
  - `python -m compileall scripts/audio/host_guest_pcm_stream_dfn48.py scripts/audio/analyze_dfn48_vm_transport.py`;
  - parse de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo com runtime estatico (`/MT`);
  - teste host-only UDP curto: `100/100` blocos, perda zero, sequencia zero,
    CRC zero, framing zero e hash origem/recebido igual;
  - preflight VM: `ready=true`, `failures=0`, `warnings=0`, snapshot
    `checkpoint45-causal-wpt-validated`, runtime
    `C:\PTC3527-Private\vm_runtime`.
- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver`.
- Gate final: `check`, apenas com warning deliberado de UDP diagnostico.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`,
  framing `0`, duracao logica `60,0 s`.
- Hash de payload origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: p99 `10,044 ms`, max `10,387 ms`, lateness max `0,413 ms`.
- Guest receive UDP nativo: p99 `14,400 ms`, max `70,537 ms`; `14` stalls
  acima de `20 ms`, `1` acima de `50 ms` e `0` acima de `100 ms`.
- Stall dominante: bloco `5107`, `header_wait_ms=70,526 ms`, payload read
  `0,000 ms`, CRC `0,011 ms`, envio host normal e sem gap de scheduler acima de
  `30 ms` na janela.
- Correlacao: `1/1` stall acima de `50 ms` classificado como
  `unaccounted_receive_or_nat`; nenhum atribuido ao host/send.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`,
  `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff
  forcado.
- Interpretacao: UDP removeu o outlier acima de `100 ms` visto na R7 TCP e
  manteve integridade perfeita, mas ainda preservou um stall relevante antes do
  DSP. O problema restante nao deve ser atribuido ao DeepFilterNet3, SYSVAD,
  ponte PCM v1, RNNoise, WAV, CRC ou hash.
- Decisao: nao promover a fase; ainda nao acoplar DeepFilterNet3 dentro da VM,
  ponte PCM v1 ou SYSVAD. Proximo passo recomendado: repetir R8 para medir
  variancia e/ou adicionar jitter buffer diagnostico minimo no receptor UDP para
  separar atraso de chegada de viabilidade de consumo em cadencia de `10 ms`.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R8-JITTER-BUFFER posthoc e repeticao UDP

- `scripts/audio/analyze_dfn48_vm_transport.py` passou a gerar
  `jitter_buffer_diagnosis` a partir de `client_trace.json`.
- A simulacao e posthoc e nao altera o gate de integridade: ela estima underflows
  para consumo ordenado com buffers de `1,2,4,6,8,12,16` blocos DFN48.
- Na primeira R8 UDP
  `runs/20260629-185315-dfn3-transport-48k-r8-udp-native-receiver`:
  - integridade permaneceu perfeita, `6000/6000` blocos;
  - max phase error: `58,789 ms`;
  - buffer de `1` bloco: `20` underflows;
  - buffer de `2` blocos: `8` underflows;
  - buffer de `4` blocos: `2` underflows;
  - buffer de `6` blocos (`60 ms`): `0` underflows;
  - interpretacao: aquela execucao era absorvivel por buffer, mas com latencia
    diagnostica alta para microfone em tempo real.
- Repeticao UDP executada em:
  `runs/20260629-190754-dfn3-transport-48k-r8-udp-native-receiver`.
- Resultado da repeticao: gate `rejected`.
- Integridade da repeticao:
  - recebidos `5913/6000` blocos;
  - perdas `87`;
  - erros de sequencia `1`;
  - CRC `0`;
  - framing `0`;
  - hash recebido diferente do hash de origem.
- Timing da repeticao:
  - host/send p99 `10,018 ms`, max `13,107 ms`;
  - guest receive p99 `17,813 ms`, max `1554,858 ms`;
  - `36` stalls acima de `20 ms`, `2` acima de `50 ms`, `1` acima de `100 ms`;
  - stall dominante no bloco `2607`, `header_wait_ms=1554,840 ms`, envio host
    normal e sem gap de scheduler acima de `30 ms` na janela.
- Jitter buffer posthoc da repeticao:
  - blocos observados `5913`;
  - max phase error `1545,294 ms`;
  - nenhum buffer testado ate `16` blocos absorveu a rodada;
  - minimo teorico pelo maior atraso: `155` blocos, ainda sem recuperar os
    `87` datagramas ausentes.
- Teardown da repeticao: o orquestrador falhou na consulta final de `VMState`,
  mas auditoria posthoc confirmou VM em `poweroff`, snapshot
  `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
  desabilitados, NIC NAT e sem poweroff forcado.
- Conclusao: UDP puro nao deve seguir como transporte de promocao. O caminho
  mais promissor e voltar a transporte confiavel e separar recepcao/consumo no
  convidado com fila/ring buffer, medindo backlog e underflows antes de qualquer
  acoplamento com DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R9-TCP-QUEUE validou fila diagnostica

- Implementacao:
  - receptor nativo ganhou `--queue-diagnostic`,
    `--queue-buffer-blocks` e `--consumer-trace`;
  - a thread de recepcao continua validando sequencia, CRC e hash;
  - uma consumer thread separada consome um bloco logico a cada `10 ms` apos o
    prebuffer configurado;
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` ganhou `-QueueDiagnostic` e
    `-QueueBufferBlocks`;
  - o orquestrador copia `consumer_trace.json` quando a fila diagnostica esta
    ativa.
- Validacao local host-only TCP de `1 s`: gate `accepted`, perda zero,
  `consumer_underflows=0`, profundidade minima `1` bloco e `consumer_trace.json`
  gerado.
- Rodada valida:
  `resultados/dfn3_vm_transport_48k/runs/20260629-193111-dfn3-transport-48k-r9-tcp-native-receiver-queue20-diagnostic`.
- Gate final: `accepted`.
- Integridade: `6000/6000` blocos, perda `0`, sequencia `0`, CRC `0`,
  framing `0`.
- Hash de payload origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Transporte: TCP, receptor nativo, `BlocksPerPacket=1`, `sink=memory`.
- Fila/consumer:
  - prebuffer `20` blocos (`200 ms`);
  - blocos consumidos `6000`;
  - underflows `0`;
  - profundidade minima antes do consumo `1` bloco;
  - profundidade media antes do consumo `22,113` blocos;
  - profundidade maxima antes do consumo `105` blocos.
- Timing:
  - host/send p99 `10,042 ms`, max `10,551 ms`;
  - guest receive p99 `13,794 ms`, max `73,402 ms`;
  - `1` stall acima de `50 ms`, `0` acima de `100 ms`;
  - o stall relevante foi correlacionado a gap de scheduler do convidado, nao
    ao envio host.
- Teardown limpo: VM em `poweroff`, snapshot `checkpoint45-causal-wpt-validated`,
  `audio_in=on`, clipboard/drag-and-drop desabilitados, NIC NAT, sem poweroff
  forcado.
- Interpretacao: transporte confiavel com recepcao separada e fila absorveu o
  jitter desta rodada sem perda e sem underflow. A arquitetura e promissora, mas
  `200 ms` de prebuffer ainda e margem alta demais para ser assumida como alvo
  final de microfone em tempo real.
- Tentativa abortada:
  `resultados/dfn3_vm_transport_48k/runs/20260629-193509-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`.
  Objetivo: testar `8` blocos (`80 ms`). O servidor host falhou aguardando ACK
  final (`TimeoutError: timed out`) e a execucao externa atingiu timeout antes
  do teardown. Nao houve `client.json`, `consumer_trace.json`, hash nem gate;
  portanto a tentativa nao e resultado experimental. Recuperacao por ACPI
  shutdown, restore do snapshot 45 e invariantes finais confirmados sem poweroff
  forcado.
- Decisao: nao acoplar ainda DeepFilterNet3 dentro da VM, ponte PCM v1 ou
  SYSVAD. Proximo passo: depurar a variante de menor prebuffer com host-only
  longo ou telemetria de progresso no guest antes de nova rodada VM com latencia
  menor.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R9-QUEUE8/7/6 fechou faixa de prebuffer

- Implementacao adicional:
  - receptor nativo ganhou `--progress-output` e
    `--progress-interval-blocks`, escrevendo `progress.json` atomico com estado
    de recepcao, fila e consumer;
  - orquestrador ganhou `-ProgressIntervalBlocks` e
    `-GuestLaunchMode Run|Start`;
  - `GuestLaunchMode=Start` inicia o receptor nativo em modo destacado no
    convidado e aguarda `guest_exit.json` antes de copiar artefatos, evitando
    manter uma sessao Guest Control longa presa durante os `60 s` de audio.
- Validacoes:
  - build nativo Release com runtime estatico (`/MT`);
  - parse de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - `python -m compileall` dos scripts de audio;
  - auditorias VM antes/depois: `poweroff`,
    `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
    drag-and-drop desabilitados, NIC NAT.
- Host-only longo:
  - queue8:
    `runs/20260629-200210-dfn3-transport-48k-r9-local-tcp-native-receiver-queue8-progress`,
    gate `check`, `6000/6000`, underflows `0`, profundidade media `8,977`;
  - queue6:
    `runs/20260629-205039-dfn3-transport-48k-r9-local-tcp-native-receiver-queue6-progress`,
    gate `accepted`, `6000/6000`, underflows `0`, profundidade media `6,291`.
- Rodada VM queue8 valida:
  `runs/20260629-204534-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`.
  Gate `accepted`, sem warnings, integridade `6000/6000`, perda `0`,
  sequencia `0`, CRC `0`, framing `0`, hash
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
  Host/send p99 `10,016 ms`, max `10,251 ms`; guest receive p99
  `16,784 ms`, max `38,016 ms`; stalls acima de `100 ms`: `0`.
  Consumer com prebuffer `8` blocos (`80 ms`): underflows `0`, profundidade
  minima `1`, media `10,313`, maxima `86`. `progress.json` terminou em
  `completed`, `guest_exit_code=0`, teardown limpo e sem poweroff forcado.
- Rodada VM queue6:
  `runs/20260629-205157-dfn3-transport-48k-r9-tcp-native-receiver-queue6-diagnostic`.
  Integridade perfeita, mas gate `check` com warning
  `client_receive_stall_over_100ms`; guest receive max `187,201 ms`, `2`
  stalls acima de `100 ms`; consumer prebuffer `6` blocos (`60 ms`) teve
  `12` underflows e profundidade minima `0`. Teardown limpo.
- Rodada VM queue7:
  `runs/20260629-205700-dfn3-transport-48k-r9-tcp-native-receiver-queue7-diagnostic`.
  Integridade perfeita, mas gate `check` com warning
  `client_receive_stall_over_100ms`; guest receive max `147,170 ms`, `2`
  stalls acima de `100 ms`; consumer prebuffer `7` blocos (`70 ms`) teve
  `7` underflows e profundidade minima `0`. Teardown limpo.
- Tentativas nao experimentais:
  - `runs/20260629-200352-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
    modo `Run` ainda ficou preso no fechamento de sessao Guest Control
    (`VERR_TIMEOUT`), sem artefatos de cliente/gate; houve poweroff forcado no
    teardown automatico e restore correto do snapshot;
  - `runs/20260629-202446-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
    falha antes do transporte por separador `--` passado incorretamente ao
    `guestcontrol start`; nao conta como experimento;
  - `runs/20260629-203639-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`:
    evidenciou corrida de copia no modo destacado; servidor recebeu ACK
    perfeito e `progress.json` chegou a `completed`, mas faltou `client.json`
    no momento da copia obrigatoria, portanto sem gate experimental.
- Conclusao: TCP confiavel com recepcao separada e fila diagnostica e o caminho
  mais promissor. Nesta serie, `80 ms` foi o menor prebuffer observado sem
  underflow na VM; `60 ms` e `70 ms` preservaram integridade, mas falharam como
  playout continuo. Ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1
  ou SYSVAD. Proximo passo recomendado: repetir queue8 para variancia e, em
  paralelo, desenhar ring buffer real com margem configuravel antes do DSP.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R9-QUEUE8 repeticao nao promoveu margem

- Rodada:
  `resultados/dfn3_vm_transport_48k/runs/20260629-213620-dfn3-transport-48k-r9-tcp-native-receiver-queue8-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `QueueDiagnostic`, `QueueBufferBlocks=8`, `ProgressIntervalBlocks=100`,
  `GuestLaunchMode=Start`.
- Gate final: `check`.
- Warning: `client_receive_stall_over_100ms`.
- Integridade permaneceu perfeita: `6000/6000` blocos, perda `0`, sequencia
  `0`, CRC `0`, framing `0`, hash origem/recebido
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Timing:
  - host/send p99 `10,291 ms`, max `10,919 ms`;
  - guest receive p99 `14,588 ms`, max `184,038 ms`;
  - `1` stall acima de `100 ms`;
  - stall dominante no bloco `796`, `header_wait_ms=184,005 ms`, envio host
    normal e sem gap de scheduler acima de `30 ms` na janela.
- Classificacao: `unaccounted_receive_or_nat`.
- Fila/consumer: prebuffer `8` blocos (`80 ms`), `6` underflows, profundidade
  minima `0`, media `17,074`, maxima `113`.
- `progress.json` terminou em `completed` e `guest_exit_code=0`.
- Teardown: a VM ficou na tela de atualizacao/desligamento do Windows e exigiu
  `forced_poweroff`; a auditoria final confirmou `poweroff`, snapshot
  `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard/drag-and-drop
  desabilitados e NIC NAT.
- Decisao: queue8 nao esta promovido. A arquitetura TCP confiavel com recepcao
  separada continua promissora, mas `80 ms` deve ser tratado como margem fragil.
  Ainda nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## 2026-06-29 - VM-DFN3-TRANSPORT-48K-R9-QUEUE12 absorveu sem underflow, mas nao promoveu

- Tentativa operacional abortada:
  `resultados/dfn3_vm_transport_48k/runs/20260629-224057-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic`.
- Motivo: `Guest Additions or interactive logon did not become ready`; a rodada
  nao chegou ao transporte e nao gerou `server.json`, `client.json`, traces, hash
  ou gate. Nao usar como resultado experimental.
- Rodada valida:
  `resultados/dfn3_vm_transport_48k/runs/20260629-225852-dfn3-transport-48k-r9-tcp-native-receiver-queue12-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `QueueDiagnostic`, `QueueBufferBlocks=12`, `ProgressIntervalBlocks=100`,
  `GuestLaunchMode=Start`.
- Gate final: `check`.
- Warning: `client_receive_stall_over_100ms`.
- Integridade permaneceu perfeita: `6000/6000` blocos, perda `0`, sequencia
  `0`, CRC `0`, framing `0`, hash origem/recebido
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Timing:
  - host/send p99 `10,035 ms`, max `10,279 ms`;
  - guest receive p99 `17,611 ms`, max `593,981 ms`;
  - `1` stall acima de `100 ms`;
  - stall dominante no bloco `2892`, `header_wait_ms=593,950 ms`, envio host
    normal e sem gap de scheduler acima de `30 ms` na janela.
- Classificacao: `unaccounted_receive_or_nat`.
- Fila/consumer: prebuffer `12` blocos (`120 ms`), `0` underflows, profundidade
  minima `1`, media `13,713`, maxima `75`.
- Teardown da rodada valida: limpo, sem poweroff forcado; VM final em
  `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`,
  clipboard/drag-and-drop desabilitados e NIC NAT.
- Decisao: queue12 mostra que a separacao recepcao/consumo absorve jitter, mas
  nao deve ser promovida diretamente porque acumulou backlog de ate `75` blocos
  para sobreviver ao outlier. Proxima etapa: ring buffer real com limite de
  profundidade, politica de recuperacao/drop e telemetria de latencia efetiva,
  ainda sem DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD.

## 2026-06-30 - VM-DFN3-TRANSPORT-48K-R10-RING desenhou buffer real limitado

- Implementacao:
  - receptor nativo ganhou `--ring-diagnostic`,
    `--ring-capacity-blocks` e `--ring-prebuffer-blocks`;
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` ganhou `-RingDiagnostic`,
    `-RingCapacityBlocks` e `-RingPrebufferBlocks`;
  - o modo ring e mutuamente exclusivo com `QueueDiagnostic`;
  - o producer mantem validacao de sequencia, CRC e hash;
  - o consumer separado consome a cada `10 ms`;
  - overflow/atraso excessivo aplica politica `drop_oldest`;
  - underflow aplica `recover_with_silence` diagnostico;
  - o analisador marca ring como diagnostico por design e adiciona warnings
    para drops, recoveries, underflows e alcance do limite de latencia.
- Telemetria adicionada:
  - capacidade, prebuffer e limite de latencia;
  - fill level minimo/medio/maximo;
  - drops de overflow;
  - recoveries/underflows;
  - `ring_playout_latency_ms_*`;
  - `consumer_deadline_lateness_ms_*`;
  - campos por bloco em `consumer_trace.json`.
- Validacoes:
  - `python -m compileall scripts/audio/host_guest_pcm_stream_dfn48.py scripts/audio/analyze_dfn48_vm_transport.py`;
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo com runtime estatico (`/MT`);
  - smoke host-only em `tmp/dfn48_ring_local_smoke`.
- Smoke host-only:
  - parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
    `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`;
  - gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - hash origem/recebido
    `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`;
  - overflow drops `0`;
  - recoveries/underflows `0`;
  - fill minimo/media/maximo `1` / `8,994` / `9` blocos;
  - latencia de playout p99 `81,603 ms`, max `82,142 ms`;
  - consumer deadline lateness p99 `0,412 ms`, max `0,997 ms`.
- Decisao:
  - nao houve acoplamento com DeepFilterNet3 dentro da VM, ponte PCM v1,
    SYSVAD, driver ou RNNoise;
  - a proxima rodada VM deve ser conservadora, com `Transport=tcp`,
    `ClientImplementation=Native`, `sink=memory`, `BlocksPerPacket=1`,
    `GuestLaunchMode=Start`, `RingCapacityBlocks=12` e
    `RingPrebufferBlocks=8`;
  - nao promover se houver latencia acumulada no limite, drops, recoveries ou
    underflows.

## 2026-06-30 - VM-DFN3-TRANSPORT-48K-R10-RING VM revelou atraso do consumer

- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260630-222946-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `ProgressIntervalBlocks=100`, `GuestLaunchMode=Start`.
- Preflight: `ready=true`, `failures=0`, `warnings=0`, snapshot
  `checkpoint45-causal-wpt-validated`, runtime
  `C:\PTC3527-Private\vm_runtime`.
- Gate final: `check`.
- Warnings: `ring_buffer_diagnostic_not_realtime_gate`,
  `ring_buffer_overflow_drops`, `ring_buffer_recoveries`,
  `ring_buffer_underflows`, `ring_buffer_reached_latency_cap`.
- Integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`.
- Hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: p99 `10,180 ms`, max `10,569 ms`, sem stalls acima de `20 ms`.
- Guest receive: p99 `13,822 ms`, max `70,085 ms`, `0` stalls acima de
  `100 ms`.
- Ring/consumer:
  - overflow drops `103`;
  - recoveries/underflows `103`;
  - profundidade maxima `12/12`;
  - latencia de playout p99 `87,842 ms`, max `120,139 ms`;
  - consumer deadline lateness p99 `152,040 ms`, max `394,744 ms`.
- Diagnostico:
  - transporte logico segue correto;
  - os dois stalls de recepcao acima de `50 ms` foram classificados como
    `unaccounted_receive_or_nat`;
  - a simulacao posthoc de chegada indicava absorcao com `6` blocos, mas o
    consumer real teve pausas de scheduler e executou deadlines vencidos em
    rajada;
  - o ring cumpriu a funcao de impedir latencia ilimitada, mas expôs perda de
    cadencia do consumer no convidado.
- Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
  drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - nao promover `RingCapacityBlocks=12`/`RingPrebufferBlocks=8`;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: politica diagnostica de ressincronizacao do
    consumer quando `deadline_lateness_ms` exceder limite explicito, separando
    atraso de chegada, drop por limite de latencia e atraso do consumidor.

## 2026-06-30 - VM-DFN3-TRANSPORT-48K-R10-RING-RESYNC testou ressincronizacao

- Implementacao:
  - receptor nativo ganhou `--ring-resync-lateness-ms`;
  - orquestrador ganhou `-RingResyncLatenessMs`;
  - a politica `shift_schedule_to_now` desloca os proximos deadlines quando o
    consumer acorda com `deadline_lateness_ms` acima do limite;
  - o analisador passou a registrar `ring_buffer_consumer_resyncs`.
- Validacoes:
  - `python -m compileall scripts/audio/host_guest_pcm_stream_dfn48.py scripts/audio/analyze_dfn48_vm_transport.py`;
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo com runtime estatico (`/MT`);
  - smoke host-only em `tmp/dfn48_ring_resync_local_smoke`.
- Smoke host-only com `RingResyncLatenessMs=40`:
  - gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
  - drops `0`;
  - recoveries/underflows `0`;
  - resyncs `0`;
  - latencia de playout p99 `80,552 ms`, max `81,078 ms`.
- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260630-224628-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ProgressIntervalBlocks=100`,
  `GuestLaunchMode=Start`.
- Gate final: `check`.
- Integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`.
- Hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Guest receive: p99 `16,561 ms`, max `181,180 ms`, `1` stall acima de
  `100 ms`.
- Ring/consumer:
  - overflow drops `260`;
  - recoveries/underflows `260`;
  - resyncs `26`;
  - profundidade maxima `12/12`;
  - latencia de playout p99 `115,709 ms`, max `125,275 ms`;
  - consumer deadline lateness p99 `25,556 ms`, max `393,831 ms`.
- Interpretacao:
  - resync reduziu o p99 de lateness do consumer frente a rodada sem resync,
    mas nao promoveu playout;
  - os resyncs ocorreram com ring cheio, exigindo drops para manter o limite de
    latencia;
  - por ser um teste finito, deslocar a agenda empurrou parte do playout para
    alem do fim da transmissao, gerando recoveries de cauda.
- Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
  drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - nao promover `resync40`;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: isolar cadencia do consumer com prioridade de
    thread/processo e/ou timer dedicado antes de aumentar margem de buffer.

## 2026-07-01 - VM-DFN3-TRANSPORT-48K-R10-WAITABLE-TIMER isolou consumer mas nao NAT

- Implementacao:
  - receptor nativo ganhou `--consumer-wait-mode hybrid|waitable_timer`;
  - receptor nativo ganhou `--consumer-thread-priority normal|above_normal|highest|time_critical`;
  - orquestrador ganhou `-ConsumerWaitMode` e `-ConsumerThreadPriority`;
  - `progress.json` registra `consumer_priority_applied` e
    `consumer_waitable_timer_created`.
- Validacoes anteriores a VM:
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo;
  - smoke host-only em `tmp/dfn48_ring_waittimer_local_smoke`.
- Smoke host-only com ring12/pre8/resync40/waitable timer/highest:
  - gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
  - drops `0`;
  - recoveries/underflows `0`;
  - resyncs `0`;
  - latencia de playout p99 `82,625 ms`, max `83,869 ms`;
  - consumer deadline lateness p99 `1,134 ms`, max `2,363 ms`.
- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260701-001024-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
  `ConsumerThreadPriority=highest`, `ProgressIntervalBlocks=100`,
  `GuestLaunchMode=Start`.
- Preflight: `ready=true`, `failures=0`, `warnings=0`, snapshot
  `checkpoint45-causal-wpt-validated`, runtime
  `C:\PTC3527-Private\vm_runtime`.
- Gate final: `check`.
- Warnings: `client_receive_stall_over_100ms`,
  `ring_buffer_diagnostic_not_realtime_gate`, `ring_buffer_overflow_drops`,
  `ring_buffer_recoveries`, `ring_buffer_underflows`,
  `ring_buffer_consumer_resyncs`, `ring_buffer_reached_latency_cap`.
- Integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`.
- Hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Confirmacao no convidado:
  - `consumer_priority_applied=true`;
  - `consumer_waitable_timer_created=true`.
- Host/send: p99 `10,030 ms`, max `10,657 ms`.
- Guest receive: p99 `15,237 ms`, max `552,461 ms`, `1` stall acima de
  `100 ms`.
- Ring/consumer:
  - overflow drops `585`;
  - recoveries/underflows `585`;
  - resyncs `55`;
  - profundidade maxima `12/12`;
  - latencia de playout p99 `118,874 ms`, max `132,298 ms`;
  - consumer deadline lateness p99 `32,449 ms`, max `552,801 ms`.
- Diagnostico:
  - o waitable timer e prioridade `highest` foram aplicados e funcionaram bem
    no smoke host-only;
  - a VM ainda teve stall de recepcao/NAT de aproximadamente `552 ms`,
    classificado como `unaccounted_receive_or_nat`;
  - o ring limitado conteve a latencia via `drop_oldest` e
    `recover_with_silence`, mas isso significa perda diagnostica, nao promocao.
- Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
  drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - nao promover waitable timer/highest como solucao;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: investigar o stall `unaccounted_receive_or_nat`
    antes de aumentar buffers ou tratar ring12/pre8 como caminho de producao.

## 2026-07-01 - VM-DFN3-TRANSPORT-48K-R10-NAT/SCHED confirmou gargalo de outliers

- Analise local da janela do maior stall da rodada `waitable_timer/highest`:
  - host manteve envio regular a cada `10 ms`;
  - guest ficou cerca de `552 ms` sem receber cabecalhos TCP;
  - apos a pausa, dezenas de blocos foram recebidos em rajada;
  - `TCP_NODELAY` ja estava ativo nos dois lados.
- Rodada diagnostica com reducao de taxa de pacotes:
  `resultados/dfn3_vm_transport_48k/runs/20260701-002426-dfn3-transport-48k-r9-tcp-native-receiver-batch2-diagnostic-ring12-pre8-resync40-waitwaitabletimer-priohighest-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=2`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
  `ConsumerThreadPriority=highest`, `GuestLaunchMode=Start`.
- Resultado batch2:
  - gate `check`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - max receive interval `96,693 ms`, sem stall acima de `100 ms`;
  - `3` stalls acima de `50 ms`;
  - classes: `1` `guest_scheduler_correlated`, `2` `unaccounted_receive_or_nat`;
  - ring drops `328`;
  - recoveries/underflows `328`;
  - resyncs `49`;
  - playout latency p99 `116,508 ms`, max `611,530 ms`;
  - consumer lateness p99 `33,304 ms`, max `723,548 ms`.
- Implementacao adicional:
  - receptor nativo ganhou `--process-priority normal|above_normal|high|realtime`;
  - orquestrador ganhou `-ReceiverProcessPriority`;
  - `progress.json` e `client.json` registram `process_priority` e
    `process_priority_applied`.
- Validacoes:
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo;
  - `python -m compileall` dos scripts de transporte/analise;
  - smoke host-only em `tmp/dfn48_ring_proc_high_local_smoke`.
- Smoke host-only com `process_priority=high`:
  - gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
  - drops/recoveries/underflows/resyncs `0`;
  - `process_priority_applied=true`;
  - playout latency p99 `81,755 ms`;
  - consumer lateness p99 `1,236 ms`.
- Rodada VM com prioridade de processo:
  `resultados/dfn3_vm_transport_48k/runs/20260701-003416-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
  `ConsumerThreadPriority=highest`, `ReceiverProcessPriority=high`,
  `GuestLaunchMode=Start`.
- Resultado process high:
  - gate `check`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - `process_priority=high`, `process_priority_applied=true`;
  - guest receive p99 `14,997 ms`, max `290,142 ms`, `2` stalls acima de
    `100 ms`;
  - classes: `1` `guest_scheduler_correlated`, `1` `unaccounted_receive_or_nat`;
  - ring drops `565`;
  - recoveries/underflows `565`;
  - resyncs `36`;
  - playout latency p99 `118,036 ms`, max `399,763 ms`;
  - consumer lateness p99 `27,456 ms`, max `620,868 ms`.
- Teardown das duas VMs: limpo, `forced_poweroff_used=false`; VM final em
  `poweroff`, snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`,
  clipboard e drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - reduzir pacotes ajudou o pior stall de recepcao, mas nao estabilizou o
    playout;
  - prioridade de processo `high` tambem nao promoveu a fase;
  - integridade TCP nativa segue perfeita e promissora, mas baixa latencia esta
    bloqueada por outliers de scheduler/recepcao;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: testar afinidade/isolamento do processo da VM ou
    rota de transporte alternativa ao NAT antes de aumentar buffers.

## 2026-07-01 - VM-DFN3-TRANSPORT-48K-R10-AFFINITY testou isolamento da VM

- Implementacao:
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` ganhou `-VmProcessAffinityMask`;
  - ganhou tambem `-VmProcessPriority unchanged|Normal|AboveNormal|High|RealTime`;
  - o wrapper grava `vm_process_scheduling.json` com PID, mascara/prioridade
    solicitadas, valores efetivos e erro, se houver;
  - `deployment_manifest.json` e `host_result.json` registram os novos
    parametros.
- Validacao previa:
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`.
- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260701-005021-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
  `ConsumerThreadPriority=highest`, `ReceiverProcessPriority=high`,
  `VmProcessAffinityMask=0xF0000`, `VmProcessPriority=High`,
  `GuestLaunchMode=Start`.
- Confirmacao host:
  - processo `VirtualBoxVM`, PID `53020`;
  - `affinity_applied=true`, `effective_affinity_mask=0xF0000`;
  - `priority_applied=true`, `effective_priority=High`.
- Gate final: `check`.
- Integridade: `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`.
- Hash origem/recebido:
  `e1a6a4774daa8049814126c0685aa5f7a54b0b41164feff8d5814260e1477dae`.
- Host/send: p99 `10,029 ms`, max `10,898 ms`.
- Guest receive: p99 `20,648 ms`, max `76,382 ms`, `0` stalls acima de
  `100 ms`, `2` stalls acima de `50 ms`.
- Diagnostico:
  - classes: `1` `guest_scheduler_correlated`, `1` `unaccounted_receive_or_nat`;
  - scheduler probe no guest ainda registrou max `485,653 ms`;
  - a simulacao posthoc indicou absorcao com `8` blocos, mas o consumer real
    continuou sofrendo pausas.
- Ring/consumer:
  - overflow drops `453`;
  - recoveries/underflows `453`;
  - resyncs `57`;
  - profundidade maxima `12/12`;
  - latencia de playout p99 `119,088 ms`, max `154,464 ms`;
  - consumer deadline lateness p99 `37,635 ms`, max `480,843 ms`.
- Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
  drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - afinidade/prioridade do processo da VM reduziram o pior stall de recepcao,
    mas nao estabilizaram o playout;
  - nao promover `VmProcessAffinityMask=0xF0000`/`VmProcessPriority=High`;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: comparar rota sem NAT ou matriz pequena de
    afinidades, mantendo todas as rodadas como diagnosticas.

## 2026-07-01 - VM-DFN3-TRANSPORT-48K-R10-PRE-READ separou pausa de thread e NAT

- Implementacao:
  - receptor nativo passou a registrar `read_start_qpc_ns` e
    `pre_read_gap_ms` no `client_trace.json`;
  - `client.json` passou a incluir estatisticas `pre_read_gap_ms_*`;
  - analisador passou a classificar stalls como
    `client_receiver_thread_pre_recv_gap` quando a pausa ocorre antes da
    chamada a `recv`;
  - receptor nativo ganhou `--receiver-thread-priority`;
  - orquestrador ganhou `-ReceiverThreadPriority`.
- Validacoes:
  - `python -m compileall scripts/audio/host_guest_pcm_stream_dfn48.py scripts/audio/analyze_dfn48_vm_transport.py`;
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`;
  - build Release do receptor nativo.
- Reanalise da rodada de afinidade anterior:
  - o stall da sequencia `3800`, antes `unaccounted_receive_or_nat`, passou a
    `client_receiver_thread_pre_recv_gap`;
  - intervalo `76,382 ms`;
  - `header_wait_ms=0,011 ms`;
  - `pre_read_gap_ms=76,362 ms`.
- Rodada VM com telemetria medida:
  `resultados/dfn3_vm_transport_48k/runs/20260701-010404-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic`.
- Resultado da rodada com telemetria:
  - gate `check`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - receive p99 `14,734 ms`, max `69,195 ms`;
  - `0` stalls acima de `100 ms`, `2` acima de `50 ms`;
  - `pre_read_gap_ms` p99 `0,704 ms`, max `63,254 ms`;
  - classes: `1` `client_receiver_thread_pre_recv_gap`, `1`
    `unaccounted_receive_or_nat`;
  - ring drops/recoveries `810`, resyncs `65`;
  - teardown limpo.
- Tentativa abortada:
  `resultados/dfn3_vm_transport_48k/runs/20260701-010950-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-rxpriohighest-prochigh-vmaffF0000-vmprioHigh-diagnostic`.
  - objetivo: combinar `ReceiverThreadPriority=highest` com afinidade da VM;
  - falha antes da coleta: Windows negou `ProcessorAffinity` para
    `VirtualBoxVM`;
  - teardown limpo, `forced_poweroff_used=false`, snapshot restaurado.
- Rodada VM isolando apenas `ReceiverThreadPriority=highest`, sem afinidade da
  VM:
  `resultados/dfn3_vm_transport_48k/runs/20260701-011440-dfn3-transport-48k-r9-tcp-native-receiver-ring12-pre8-resync40-waitwaitabletimer-priohighest-rxpriohighest-prochigh-diagnostic`.
- Resultado:
  - gate `check`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - receive p99 `13,664 ms`, max `154,765 ms`;
  - `6` stalls acima de `50 ms`, `3` acima de `100 ms`;
  - `pre_read_gap_ms` p99 `0,779 ms`, max `57,141 ms`;
  - classes: `1` `client_receiver_thread_pre_recv_gap`, `2`
    `guest_scheduler_correlated`, `3` `unaccounted_receive_or_nat`;
  - ring drops/recoveries `469`, resyncs `31`;
  - teardown limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
    snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
    drag-and-drop desabilitados, NIC NAT.
- Decisao:
  - manter `pre_read_gap_ms` como telemetria diagnostica;
  - nao promover `ReceiverThreadPriority=highest`;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: comparar rota sem NAT ou voltar a afinidade da
    VM apenas quando a alteracao de `ProcessorAffinity` estiver permitida.

## 2026-07-01 - VM-DFN3-TRANSPORT-48K-R10-HOSTONLY comparou rota sem NAT

- Implementacao:
  - `scripts/vm/Invoke-Dfn3TransportVm.ps1` ganhou `-GuestConnectHost`;
  - ganhou tambem `-TemporaryHostOnlyAdapterName`, que ativa NIC2 host-only
    temporariamente antes da partida da VM;
  - `host_result.json`, `deployment_manifest.json` e `teardown_result.json`
    registram a rota e `nic2`.
- Ambiente:
  - host-only existente: `VirtualBox Host-Only Ethernet Adapter`;
  - IP do host: `192.168.56.1`;
  - DHCP host-only ativo em `192.168.56.101-254`;
  - VM base: `nic1=nat`, `nic2=none`.
- Validacao previa:
  - parse limpo de `scripts/vm/Invoke-Dfn3TransportVm.ps1`.
- Rodada VM:
  `resultados/dfn3_vm_transport_48k/runs/20260701-012549-dfn3-transport-48k-r9-tcp-native-receiver-guesthost192p168p56p1-hostonly-ring12-pre8-resync40-waitwaitabletimer-priohighest-prochigh-diagnostic`.
- Parametros: TCP, receptor nativo, `sink=memory`,
  `GuestConnectHost=192.168.56.1`, `TemporaryHostOnlyAdapterName=VirtualBox Host-Only Ethernet Adapter`,
  `BlocksPerPacket=1`, `RingDiagnostic`, `RingCapacityBlocks=12`,
  `RingPrebufferBlocks=8`, `RingResyncLatenessMs=40`,
  `ConsumerWaitMode=waitable_timer`, `ConsumerThreadPriority=highest`,
  `ReceiverProcessPriority=high`, `GuestLaunchMode=Start`.
- Resultado:
  - gate `check`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - receive p99 `14,845 ms`, max `116,378 ms`;
  - `14` stalls acima de `20 ms`, `1` acima de `50 ms`, `1` acima de
    `100 ms`;
  - `pre_read_gap_ms` p99 `1,143 ms`, max `23,591 ms`;
  - unico stall acima de `50 ms`: `guest_scheduler_correlated`, sequencia
    `961`, intervalo `116,378 ms`, `header_wait_ms=116,294 ms`,
    `pre_read_gap_ms=0,008 ms`, scheduler gap max `106,761 ms`;
  - ring drops/recoveries `564`, resyncs `66`;
  - playout latency p99 `119,022 ms`;
  - consumer deadline lateness p99 `44,476 ms`.
- Teardown: limpo, `forced_poweroff_used=false`; VM final em `poweroff`,
  snapshot `checkpoint45-causal-wpt-validated`, `audio_in=on`, clipboard e
  drag-and-drop desabilitados, `nic1=nat`, `nic2=none`.
- Decisao:
  - host-only reduziu a ambiguidade e removeu `unaccounted_receive_or_nat`
    nesta rodada, mas nao estabilizou baixa latencia;
  - NAT nao e a unica causa do bloqueio;
  - manter rota host-only como diagnostico, nao como promocao;
  - nao acoplar DeepFilterNet3 dentro da VM, ponte PCM v1 ou SYSVAD;
  - proximo passo recomendado: focar scheduler/afinidade quando permitido ou
    priorizar validacao fora do VirtualBox/NEM.

## 2026-07-01 - DFN3-TRANSPORT-48K-R11-LOCAL-LOOPBACK validou baseline nativo

- Escopo:
  - teste user-mode no host Windows;
  - sem VM;
  - sem SYSVAD;
  - sem ponte PCM v1;
  - sem driver;
  - sem alterar BIOS, Secure Boot, Hyper-V ou configuracao de boot;
  - servidor Python e receptor C++ nativo via TCP `127.0.0.1`.
- Observacao operacional:
  - a primeira tentativa dentro do caminho do OneDrive falhou antes do teste
    porque o receptor nativo usa `argv` estreito no Windows e nao criou
    diretorios com caracteres acentuados no caminho;
  - as rodadas validas foram gravadas em
    `C:\PTC3527-Private\local_loopback_runs\`.
- Rodada transport-only:
  `C:\PTC3527-Private\local_loopback_runs\20260701-020331-dfn3-local-loopback-transport-only`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`, sem
  ring/consumer.
- Resultado transport-only:
  - gate `accepted`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - receive p99 `10,152 ms`;
  - receive max `11,052 ms`;
  - stalls acima de `20/50/100 ms`: `0/0/0`;
  - scheduler max `4,500 ms`.
- Rodada ring diagnostic:
  `C:\PTC3527-Private\local_loopback_runs\20260701-020131-dfn3-local-loopback-ring12-pre8-resync40`.
- Parametros: TCP, receptor nativo, `sink=memory`, `BlocksPerPacket=1`,
  `RingDiagnostic`, `RingCapacityBlocks=12`, `RingPrebufferBlocks=8`,
  `RingResyncLatenessMs=40`, `ConsumerWaitMode=waitable_timer`,
  `ConsumerThreadPriority=highest`, `ReceiverProcessPriority=high`.
- Resultado ring:
  - gate `check`, apenas por `ring_buffer_diagnostic_not_realtime_gate`;
  - integridade `6000/6000`, perda `0`, sequencia `0`, CRC `0`, framing `0`;
  - receive p99 `10,153 ms`;
  - receive max `10,819 ms`;
  - stalls acima de `20/50/100 ms`: `0/0/0`;
  - ring drops `0`;
  - recoveries/underflows `0`;
  - resyncs `0`;
  - playout latency p99 `80,987 ms`;
  - consumer deadline lateness p99 `0,977 ms`;
  - consumer interval max `11,507 ms`;
  - scheduler max `4,413 ms`.
- Decisao:
  - o baseline nativo confirmou que o transporte/receptor C++ mantem cadencia
    no host Windows quando VirtualBox/NEM e removido;
  - a fase VM fica congelada como integridade funcional validada, mas tempo
    real nao validavel de forma confiavel no VirtualBox/NEM;
  - os outliers da VM nao devem ser atribuidos ao protocolo/ring/receptor sem
    nova evidencia;
  - proximo passo recomendado: medir DFN3 inline em user-mode usando o baseline
    nativo antes de qualquer retorno a SYSVAD/driver.

## 2026-07-01 - DFN3-LOCAL-R12-INLINE-USERMODE validou custo nativo do DFN3

- Escopo:
  - host Windows, user-mode;
  - sem VM;
  - sem SYSVAD;
  - sem ponte PCM v1;
  - sem driver;
  - sem alterar BIOS, Secure Boot, Hyper-V ou configuracao de boot;
  - DeepFilterNet3 C API persistente em worker/ring.
- Comando:
  `powershell -NoProfile -ExecutionPolicy Bypass -File tmp\dfn_native\wasapi_worker_bench\run_b3_pre_vm.ps1`.
- Artefatos:
  `tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\`;
  resumo em `resultados\dfn3_local_dfn_inline\README.md`.
- Parametros:
  - `df.dll` em `tmp\t_release\x86_64-pc-windows-msvc\release\df.dll`;
  - modelo `tmp\dfn_native\DeepFilterNet3_onnx.tar.gz`;
  - frame DFN3 de `480` amostras, `10 ms` a 48 kHz;
  - `post_filter_beta=1.0`;
  - `atten_lim=100.0`;
  - worker e callback com MMCSS;
  - render mudo;
  - input composto de `60 s`.
- Resultado bruto:
  - gate `PASS`;
  - frames DFN3 `6000`;
  - worker mean `0,982 ms`;
  - worker p95 `1,801 ms`;
  - worker p99 `2,189 ms`;
  - worker p999 `2,617 ms`;
  - worker max `5,168 ms`;
  - worker acima de `4/8/10 ms`: `1/0/0`;
  - callback p99 `0,043 ms`;
  - callback p999 `0,087 ms`;
  - callback max `0,155 ms`;
  - underflow `0`;
  - ring minimo antes do callback `480` amostras.
- Resultado estavel B3, ignorando apenas o primeiro frame do worker:
  - gate estavel `PASS`;
  - frames no gate estavel `5999`;
  - worker p99 `2,188 ms`;
  - worker p999 `2,598 ms`;
  - worker max `3,957 ms`;
  - worker acima de `4/8/10 ms`: `0/0/0`;
  - callback p99 `0,043 ms`;
  - underflow `0`.
- Decisao:
  - o custo nativo do DeepFilterNet3 C API esta aprovado em user-mode;
  - combinado com R11, o host validou transporte/receptor/ring e custo DFN3;
  - o bloqueio restante da trilha VM continua sendo ambiente
    VirtualBox/NEM/scheduler/rede, nao DFN3 basico;
  - retorno a ponte PCM v1/SYSVAD deve iniciar nova fase controlada.

## 2026-07-01 - DFN3-LOCAL-R13-PCM-BRIDGE-SIM aprovou stub pre-ponte

- Escopo:
  - host Windows, user-mode;
  - sem VM;
  - sem SYSVAD;
  - sem driver;
  - sem abrir a ponte PCM v1 real;
  - sem alterar BIOS, Secure Boot, Hyper-V, test-signing ou configuracao de
    boot;
  - reutilizacao do contrato Python `PtcPcmBridgeClient` e
    `BridgePacedWriter` com backend simulado em memoria.
- Implementacao:
  - novo script `scripts/audio/dfn3_pcm_bridge_simulator.py`;
  - entrada DFN3 48 kHz ja produzida pela bancada R12:
    `tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\output_full_raw48.wav`;
  - conversao deterministica de `48 kHz/480 samples/10 ms` para o contrato PCM
    v1 `16 kHz/320 samples/20 ms`;
  - backend simulado com fila de driver, consumo a cada `20 ms`, estatisticas
    compativeis com `IOCTL_PTC_PCM_GET_STATS`, hash de payload aceito e
    contadores de underrun/overrun/rejeicao/erro de sequencia.
- Validacoes:
  - `python -m compileall scripts/audio/dfn3_pcm_bridge_simulator.py`;
  - smoke de `20` blocos com `bridge_target_depth=6`, `bridge_user_queue=16`;
  - rodada principal de `60 s` em
    `resultados\dfn3_pcm_bridge_simulator\`;
  - variantes diagnosticas em
    `resultados\dfn3_pcm_bridge_simulator_depth2_queue16\` e
    `resultados\dfn3_pcm_bridge_simulator_depth6\`.
- Rodada principal:
  - comando:
    `python scripts/audio/dfn3_pcm_bridge_simulator.py --output-dir resultados\dfn3_pcm_bridge_simulator`;
  - `bridge_target_depth=2`;
  - `bridge_user_queue=4`;
  - `bridge_poll_interval_ms=2`;
  - `timeBeginPeriod(1)` aplicado;
  - prioridade de processo `high` aplicada;
  - prioridade da thread de submissao `highest` aplicada;
  - writer thread com MMCSS aplicado.
- Resultado principal:
  - gate `PASS`;
  - blocos PCM v1 esperados/enviados/aceitos: `3000/3000/3000`;
  - blocos consumidos no snapshot final: `2998`;
  - profundidade final do backend simulado: `2` blocos;
  - drops da fila de usuario `0`;
  - underruns `0`;
  - overruns `0`;
  - rejeicoes `0`;
  - erros de sequencia `0`;
  - hash aceito igual ao payload PCM16 esperado;
  - submit interval p99 `20,172 ms`, max `25,001 ms`;
  - submit call p99 `0,107 ms`;
  - profundidade media/p95/max `1,5 / 2 / 2` blocos;
  - residencia p95/max na fila de usuario `2,743 / 3,368 ms`;
  - latencia estimada de ponte `42,743 ms`;
  - consumer lateness p99/max `2,537 / 2,810 ms`.
- Variantes diagnosticas:
  - depth2/fila16: gate `PASS`, `3000/3000` enviados/aceitos, sem drops,
    underruns, overruns, rejeicoes ou erro de sequencia, hash correto;
  - depth6/fila16: gate `PASS`, `3000/3000` enviados/aceitos, sem drops,
    underruns, overruns, rejeicoes ou erro de sequencia, hash correto, mas
    latencia estimada de ponte maior (`122,759 ms`).
- Decisao:
  - R13 aprova o stub user-mode pre-ponte para o caminho
    `DFN3 48 kHz -> adaptacao PCM v1 16 kHz -> writer -> consumidor simulado`;
  - o teste nao valida SYSVAD, WaveRT, PortCls, IOCTL real, endpoint de captura
    ou latencia fisica ponta a ponta;
  - nao promove nenhuma configuracao de VM para tempo real;
  - proximo passo recomendado: somente com decisao explicita, reabrir uma
    bancada controlada da ponte PCM v1 real dentro da VM/lab, preservando a
    separacao entre custo DFN3, pacing user-mode e comportamento do driver.

## 2026-07-01 - DFN3/SYSVAD-R14-BRIDGE-REAL-VM reabriu ponte v1 sem DFN3

- Escopo:
  - clone `PTC3527-SYSVAD-LAB-FAST`;
  - snapshot esperado `checkpoint45-causal-wpt-validated`;
  - ponte PCM v1 real exercitada dentro da VM;
  - sem DeepFilterNet3 dentro da VM;
  - sem modificar driver/SYSVAD/ponte real;
  - sem instalar driver no host;
  - sem alterar BIOS, Secure Boot, Hyper-V, TESTSIGNING ou boot.
- Preflight:
  - comando:
    `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Test-VmAutomationPreflight.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -OrchestratorPath scripts\vm\Invoke-HostPacedPcmVm.ps1 -AudioRun`;
  - resultado final `ready=true`, falhas `0`, warnings `0`;
  - clone em `poweroff`, snapshot aprovado, `audio_in=on`, clipboard e
    drag-and-drop desabilitados, NIC1 NAT.
- Ajuste operacional:
  - `scripts\vm\Invoke-HostPacedPcmVm.ps1` passou a exigir a DLL RNNoise apenas
    quando algum cenario usa metodo `rnnoise`;
  - `scripts\vm\guest\Invoke-HostPacedEndpointScenario.ps1` passou a exigir a
    DLL somente quando `-Method rnnoise`;
  - motivacao: remover dependencia falsa nos cenarios `bypass` que exercitam
    apenas a ponte real;
  - parse PowerShell limpo nos dois scripts.
- Rodada `EndpointDiagnostic`:
  - run:
    `resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-101012-host-paced-endpointdiagnostic`;
  - comando:
    `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointDiagnostic -DurationSeconds 20`;
  - `host_result`: `succeeded=true`, `bridge_exercised=true`,
    `pipeline_modified=false`, default capture do host inalterado, clone final
    em `poweroff` no snapshot aprovado;
  - cliente recebeu `1000/1000` blocos, sequencia `0`, CRC `0`, framing `0`;
  - bypass p99 `1,728 ms`, max `5,235 ms`;
  - writer submeteu `1000`, enviou `831`, com `169` drops locais;
  - driver aceitou `831`, consumiu `829`;
  - write errors `0`, rejected requests `0`, sequence errors do driver `0`;
  - underruns do driver `147`;
  - classificacao:
    `transient_scheduling_pauses_with_queue_overflow`.
- Rodada `EndpointCaptureEvent`:
  - run:
    `resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-101500-host-paced-endpointcaptureevent`;
  - comando:
    `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointCaptureEvent -DurationSeconds 20`;
  - `host_result`: `succeeded=true`, clone final restaurado;
  - gate `completed`;
  - classificacao `capture_event_not_confirmed`;
  - pernas `yield`: `998/1000` enviados nas duas pernas, drops `2` e `2`,
    underruns `33` e `23`;
  - pernas `event`: `953/1000` e `969/1000` enviados, drops `47` e `31`,
    underruns `124` e `67`.
- Rodada `EndpointScheduling`:
  - run:
    `resultados\sysvad_checkpoint46_reopened\host_paced_pcm\runs\20260701-102253-host-paced-endpointscheduling`;
  - comando:
    `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\vm\Invoke-HostPacedPcmVm.ps1 -RuntimeRoot C:\PTC3527-Private\vm_runtime -Mode EndpointScheduling -DurationSeconds 20`;
  - `host_result`: `succeeded=true`, clone final restaurado;
  - gate `completed`;
  - classificacao
    `writer_wakeup_mitigated_consumer_cadence_deficit_remains`;
  - writer normal: `867/1000` enviados com `133` drops e `165` underruns na
    primeira perna; `968/1000` enviados com `32` drops e `106` underruns na
    segunda;
  - writer MMCSS: `961/1000` enviados com `39` drops e `141` underruns;
    `973/1000` enviados com `27` drops e `122` underruns.
- Decisao:
  - a ponte PCM v1 real foi reaberta e aceitou blocos sem erros de contrato,
    escrita, rejeicao ou sequencia;
  - as rodadas nao promovem tempo real porque a VM ainda apresenta pausas de
    scheduler/cadencia e deficit no consumidor/endpoint;
  - nao acoplar DFN3 a ponte real dentro desta VM como gate de baixa latencia;
  - o proximo teste de integracao final deve ocorrer em instalacao Windows
    nativa/lab dedicada ou ambiente virtual com garantias temporais melhores;
  - ate la, manter aprovados como caminho tecnico principal os gates host-native
    user-mode R11, R12 e R13.

## 2026-07-01 - DFN3-LOCAL-R15-CPP-PCM-BRIDGE-SIM aproximou fluxo final sem driver

- Escopo:
  - host Windows nativo, user-mode;
  - sem VM;
  - sem driver;
  - sem SYSVAD;
  - sem abrir a ponte PCM v1 real;
  - sem alterar BIOS, Secure Boot, Hyper-V, TESTSIGNING ou boot.
- Objetivo:
  - executar um ensaio incremental alem do R13, removendo o pacing Python;
  - manter DeepFilterNet3 real via C API persistente;
  - testar worker/ring C++ e adaptacao para contrato PCM v1
    `16 kHz/320 samples/20 ms`;
  - simular driver PCM v1 com target depth `2`, fila de driver e consumidor
    periodico de `20 ms`.
- Implementacao:
  - nova bancada versionavel em
    `scripts\native\dfn3_pcm_bridge_sim_bench\`;
  - executavel:
    `scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe`;
  - artefatos principais em
    `resultados\dfn3_pcm_bridge_cpp_simulator\`;
  - repeticao de confirmacao em
    `resultados\dfn3_pcm_bridge_cpp_simulator_repeat1\`;
  - documentacao:
    `resultados\dfn3_pcm_bridge_cpp_simulator\README.md`.
- Build e smoke:
  - build Release CMake/NMake aprovado;
  - smoke inicial de `100` blocos no prototipo: gate `PASS`, `100/100`
    aceitos, underruns `0`,
    worker p99 `0,699 ms`, worker max `3,734 ms`.
  - smoke da fonte versionavel em
    `tmp\dfn3_pcm_bridge_cpp_smoke_versioned`: gate `PASS`, `100/100`
    aceitos, underruns `0`, worker p99 `0,753 ms`, worker max `0,787 ms`.
- Rodada principal:
  - comando:
    `scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe --output-dir resultados\dfn3_pcm_bridge_cpp_simulator`;
  - gate `CHECK`;
  - motivo: `worker_max_over_10ms`;
  - blocos PCM v1 aceitos `3000/3000`;
  - worker frames `6000`;
  - underruns `0`;
  - overruns `0`;
  - rejeicoes `0`;
  - erros de sequencia `0`;
  - profundidade final/max `2/2`;
  - hash PCM16
    `144017e02a1731141f1abc0f44571f4c635a2cb24ef5af197922daf2773aa227`;
  - worker p99 `2,943 ms`;
  - worker p999 `3,851 ms`;
  - worker max `11,786 ms`;
  - um unico frame acima de `10 ms`, no frame `285`;
  - bridge write interval p99/max `20,261 / 20,766 ms`;
  - consumer lateness p99/max `0,993 / 1,188 ms`.
- Repeticao de confirmacao:
  - comando:
    `scripts\native\dfn3_pcm_bridge_sim_bench\bin\dfn3_pcm_bridge_sim_bench.exe --output-dir resultados\dfn3_pcm_bridge_cpp_simulator_repeat1`;
  - gate `PASS`;
  - blocos PCM v1 aceitos `3000/3000`;
  - underruns, overruns, rejeicoes e erros de sequencia `0`;
  - worker p99 `3,093 ms`;
  - worker p999 `3,807 ms`;
  - worker max `6,234 ms`;
  - frames acima de `8 ms`: `0`;
  - frames acima de `10 ms`: `0`;
  - bridge write interval p99/max `20,247 / 20,881 ms`;
  - hash PCM16 igual ao da rodada principal.
- Decisao:
  - R15 valida a menor bancada adicional util sem instalacao de driver:
    DFN3 real C++ nativo, worker/ring e simulador PCM v1;
  - a rodada principal teve um outlier bruto isolado de CPU/scheduler, absorvido
    pelo ring e sem impacto funcional;
  - a repeticao passou no gate rigido, indicando que o outlier nao formou um
    padrao recorrente na bancada;
  - nao ha novo indicio para atribuir risco principal ao protocolo local, ao
    custo basico do DFN3, ao ring user-mode ou ao empacotamento PCM v1 simulado;
  - o proximo salto que valida SYSVAD/ponte real de ponta a ponta continua
    dependendo de Windows nativo/lab dedicado ou de ambiente virtual com
    garantias temporais melhores.
