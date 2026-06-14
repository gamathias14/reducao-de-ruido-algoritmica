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

## 2026-06-06 - Auditoria da atualizacao do relatorio

- O relatorio foi atualizado para declarar explicitamente que os resultados sao preliminares.
- A tabela de resultados e as figuras foram inseridas a partir dos arquivos gerados automaticamente em `resultados/`.
- O texto diferencia resultado observado, interpretacao e limitacao:
  - observado: STFT subtracao e STFT Wiener melhoraram SNR neste experimento;
  - interpretacao: os baselines STFT foram mais efetivos que a Wavelet soft com os parametros atuais;
  - limitacao: ruidos sinteticos, silencio inicial e ausencia de avaliacao perceptual formal.
- A conclusao sobre hardware nao promete prototipo imediato:
  - Raspberry Pi aparece como primeira plataforma plausivel;
  - ESP32/ESP32-S3 aparece como etapa posterior;
  - Arduino Uno R3 aparece como impraticavel para o pipeline atual.
- O PDF foi compilado e verificado visualmente em paginas representativas.
- Risco residual: como `entrega3.tex` usa formato/preambulo local, a reproducao completa do PDF fora deste computador pode exigir organizar tambem o preambulo e ativos graficos do modelo LaTeX.

## 2026-06-06 - Auditoria da migracao para graficos LaTeX nativos

### 1. Coerencia entre texto teorico e implementacao

- Resultado observado: o texto descreve STFT por subtracao espectral, ganho espectral tipo Wiener e DWT Wavelet com limiarizacao soft, que sao exatamente os metodos presentes em `benchmark_audio/run_benchmark.py`.
- A estimativa de ruido por silencio inicial esta declarada como escolha preliminar e aparece tambem como limitacao.
- A teoria nao promete superioridade geral de STFT ou Wavelet; ela apresenta hipoteses e trade-offs, coerentes com um benchmark inicial.
- Conclusao: coerente.

### 2. Metricas do relatorio versus CSVs

- `resultados/tabelas/resumo_por_metodo_snr.csv` confirma os valores narrados no relatorio:
  - STFT subtracao: melhorias medias de 9,63, 8,42, 7,15 e 5,89 dB para SNRs alvo -5, 0, 5 e 10 dB;
  - STFT Wiener: 7,46, 6,89, 6,22 e 5,49 dB;
  - Wavelet soft: 2,15, 1,16, 0,15 e -0,92 dB;
  - baseline ruidoso: melhoria zero.
- Os valores da tabela LaTeX em `entrega3.tex` seguem o resumo por metodo/SNR.
- Conclusao: bate com os CSVs.

### 3. Figuras nativas versus dados tabulados

- `resultados/pgfplots/melhoria_snr.csv` e uma tabela pivotada diretamente do resumo por metodo/SNR.
- `resultados/pgfplots/rtf_por_metodo.csv` agrega o RTF medio por metodo e exporta tambem `rtf_medio_x1000` para leitura do eixo vertical.
- `resultados/pgfplots/formas_onda_exemplo.csv` usa sinais decimados para manter a compilacao leve.
- `resultados/pgfplots/espectrograma_*.csv` usa matrizes reduzidas, com 48 frequencias por 40 instantes, normalizadas em dB relativo ao pico global do exemplo.
- Os quatro blocos principais em `entrega3.tex` foram migrados para `grafico` + `tikzpicture`/`pgfplots`; nao ha mais `\includegraphics` para os PNGs principais.
- Conclusao: os graficos nativos reproduzem os dados exportados pelo pipeline, com reducao deliberada apenas em formas de onda e espectrogramas.

### 4. Captions e listas

- As captions descrevem origem dos dados, script gerador, parametros do benchmark e carater preliminar.
- Foram usadas captions curtas opcionais para manter a lista de graficos legivel.
- O indice de ilustracoes inclui lista de figuras, tabelas, graficos e codigos.
- A lista de figuras fica vazia porque os elementos visuais principais foram classificados como `grafico`, conforme o ambiente existente em `cab.tex`.
- Conclusao: captions informativas e nao redundantes; listas corretas.

### 5. Conclusao sobre STFT, Wavelet e hardware

- O relatorio afirma apenas que, neste benchmark preliminar, os baselines STFT melhoraram SNR de modo mais consistente que a Wavelet soft.
- A Wavelet nao e descartada; o relatorio registra necessidade de testar `sym4`, Coiflets, limiar hard, limiares por escala e escolha sistematica de nivel.
- O hardware e tratado como continuidade: Raspberry Pi primeiro, ESP32/ESP32-S3 depois de estimativas em C/C++, Arduino Uno R3 como inviabilidade ou trabalho simplificado.
- Conclusao: proporcional aos dados.

### 6. Arduino Uno R3

- A afirmacao de inviabilidade esta sustentada por restricoes concretas:
  - 2 KB de SRAM;
  - 32 KB de flash;
  - ausencia de FPU;
  - falta de I2S nativo;
  - buffers e coeficientes incompativeis com STFT/DWT de voz no escopo atual.
- Conclusao: sustentada por estimativas e limites de plataforma.

### 7. Diferenciacao entre observado, interpretacao e limitacao

- Observado: CSVs mostram melhoria de SNR dos metodos STFT e baixo RTF em PC.
- Interpretacao: os baselines STFT foram mais efetivos que a Wavelet soft com estes parametros e estes ruidos.
- Limitacao: ruidos sinteticos, silencio inicial garantido, poucos falantes, ausencia de validacao separada e ausencia de avaliacao perceptual formal.
- Conclusao: diferenciacao adequada.

### 8. Compilacao e verificacao do PDF

- `entrega3.tex` foi compilado com `pdflatex -interaction=nonstopmode entrega3.tex` ate estabilizar sumario, listas e referencias.
- Resultado final:
  - `entrega3.pdf` com 28 paginas;
  - sem erro fatal;
  - sem referencias indefinidas;
  - sem `Overfull \hbox` remanescente apos ajustes;
  - avisos remanescentes: `microtype` em `footnote` e alguns `Underfull \hbox`.
- Foram renderizadas paginas de sumario, indice de ilustracoes, graficos e codigo com `pdftoppm`.
- Conclusao: PDF compilado e verificado visualmente.

### Limitacoes remanescentes

- O espectrograma nativo e reduzido por necessidade de compilacao; ele nao substitui analise espectral completa.
- Os PNGs antigos continuam existindo como figuras diagnosticas geradas pelo Python, mas nao sao mais usados como graficos principais do PDF.
- A reproducao fora deste computador ainda depende do preambulo `cab.tex` e de ativos locais, como o logo importado pelo modelo.

## 2026-06-06 - Auditoria da separacao do nucleo reutilizavel

### Escopo da mudanca

- A etapa foi uma refatoracao controlada de codigo, nao uma nova rodada experimental.
- As funcoes de processamento, metricas e utilitarios de audio foram movidas para `benchmark_audio/denoise.py`.
- O benchmark offline continuou responsavel por preparo de dados, tabelas, graficos e metadados.

### Verificacao tecnica

- `python -m compileall benchmark_audio` concluiu sem erro.
- `python -m unittest discover -s tests` executou 2 testes com sucesso.
- `python -m benchmark_audio.run_benchmark --export-pgfplots-only` concluiu sem erro.
- Um smoke test em diretorio temporario executou `run_benchmark` de ponta a ponta com uma amostra sintetica curta, um ruido e uma SNR, sem sobrescrever os resultados oficiais.

### Achado durante a verificacao

- O smoke test revelou que o benchmark assumia pelo menos duas SNRs ao selecionar o exemplo representativo.
- A correcao passou a aceitar subconjuntos pequenos: usa a segunda SNR quando existe, ou a primeira quando a configuracao contem apenas uma SNR.
- Esse ajuste melhora a testabilidade sem alterar o protocolo padrao de quatro SNRs.

### Conclusao de auditoria

- A Fase 1 nao altera conclusoes sobre STFT, Wiener ou Wavelet, pois nao houve nova medicao oficial.
- O ganho principal e arquitetural: o futuro prototipo em tempo real pode importar `benchmark_audio.denoise` sem carregar pandas, Matplotlib, download de dados ou rotinas de relatorio.
- Risco remanescente: os metodos ainda sao os mesmos baselines offline; a adaptacao real para streaming exigira estimativa de ruido por blocos, buffers e medicao de latencia.

## 2026-06-06 - Auditoria do prototipo CLI em tempo real

### Escopo

- Foi criado um prototipo CLI para Windows em `realtime_audio/windows_realtime.py`.
- O prototipo tem dois modos:
  - autoteste sintetico por blocos, sem audio fisico;
  - captura/reproducao local por `sounddevice`, pendente de instalacao e teste com dispositivo.

### Verificacao executada

- `python -m compileall benchmark_audio realtime_audio` concluiu sem erro.
- `python -m unittest discover -s tests` executou 4 testes com sucesso.
- `python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --duration 1 --block-ms 20 --no-save` concluiu sem erro.
- `python -m realtime_audio.windows_realtime --help` exibiu a interface de CLI.
- `sounddevice` foi verificado como ausente no ambiente atual.

### Metricas do autoteste

- O autoteste sintetico gerou 50 blocos de 20 ms.
- Tempo medio de processamento por bloco: aproximadamente 0,357 ms.
- Pior caso por bloco: aproximadamente 0,676 ms.
- Desvio padrao: aproximadamente 0,209 ms.
- RTF medio por bloco: aproximadamente 0,0179.
- RTF pior caso por bloco: aproximadamente 0,0338.
- Latencia algoritmica estimada para STFT: 32 ms.

### Interpretacao

- Os numeros indicam folga computacional no autoteste sintetico em PC, mas nao comprovam funcionamento em tempo real com microfone.
- A medicao ainda nao inclui latencia de driver, dispositivo de entrada, dispositivo de saida, escalonamento do sistema operacional ou underruns/overruns reais.
- A conclusao permitida e: a arquitetura de processamento por blocos e a instrumentacao inicial estao funcionando em teste sintetico.

### Pendencias de auditoria

- Instalar `sounddevice` e listar dispositivos.
- Rodar teste curto de captura/reproducao com `--method bypass` para medir estabilidade de I/O.
- Rodar teste curto com `stft_subtraction` e salvar logs de status do stream.
- Comparar bypass versus STFT com a mesma configuracao de bloco antes de atualizar o relatorio.

## 2026-06-06 - Auditoria da captura real input-only no Windows

### Escopo

- Foi validado o caminho de captura real sem playback, usando `--input-only`.
- O objetivo foi medir custo computacional por bloco e estabilidade inicial sem salvar audio de voz.
- A tabela consolidada foi salva em `resultados/tabelas/realtime_windows_input_only.csv`.

### Reprodutibilidade

- Dependencias instaladas via `python -m pip install -r requirements.txt`.
- Dispositivos listados via `python -m realtime_audio.windows_realtime --list-devices`.
- Testes executados com:
  - taxa de amostragem 16 kHz;
  - audio mono;
  - blocos de 20 ms;
  - duracao de 3 s por metodo;
  - `--no-save`, portanto sem WAV de voz.

### Resultados auditados

- `bypass`:
  - 148 blocos;
  - media 0,034 ms/bloco;
  - pior caso 0,160 ms/bloco;
  - RTF medio 0,00170;
  - latencia de entrada reportada 40 ms;
  - nenhum status de erro.
- `stft_subtraction`:
  - 148 blocos;
  - media 0,486 ms/bloco;
  - pior caso 2,026 ms/bloco;
  - RTF medio 0,0243;
  - RTF pior caso 0,1013;
  - latencia algoritmica estimada 32 ms;
  - latencia total input-only estimada 72 ms;
  - nenhum status de erro.

### Interpretacao permitida

- O prototipo ja captura audio real e processa blocos no Windows sem underruns/overruns reportados nesses testes curtos.
- A STFT por subtracao ainda ficou abaixo de RTF 1 com folga no notebook.
- O teste input-only nao comprova qualidade perceptual nem reproducao em tempo real para o usuario.

### Limitacoes e proximos cuidados

- A duracao de 3 s e curta; a proxima rodada deve usar 30 s ou mais por metodo.
- Ainda faltam `stft_wiener` e `wavelet_soft` no teste real input-only.
- Ainda falta testar modo duplex com fones ou saida controlada para evitar feedback.
- Nao atualizar o relatorio final com conclusoes fortes antes de comparar os quatro metodos e registrar estabilidade por duracao maior.

## 2026-06-06 - Auditoria da estabilidade input-only por 30 s no Windows

### Escopo

- Foi executada uma rodada real input-only de 30 s por metodo no Windows/notebook.
- Foram comparados `bypass`, `stft_subtraction`, `stft_wiener` e `wavelet_soft`.
- A rodada preservou a restricao de privacidade e seguranca: `--no-save`, sem WAV de voz e sem playback.

### Reprodutibilidade

- Antes da rodada, foram executados:
  - `git status --short`
  - `python -m compileall benchmark_audio realtime_audio`
  - `python -m unittest discover -s tests`
- O ambiente listou como padroes:
  - entrada: `SteelSeries Sonar - Microphone`, indice 1, MME;
  - saida: `SteelSeries Sonar - Gaming`, indice 7, MME.
- Parametros comuns:
  - taxa de amostragem: 16 kHz;
  - audio mono;
  - bloco: 20 ms;
  - duracao configurada: 30 s por metodo;
  - calibracao STFT: 250 ms;
  - STFT: `n_fft=512`, `hop_length=160`;
  - WAV salvo: nao.

### Resultados auditados da rodada de 30 s

- `bypass`: 1498 blocos, media 0,031 ms/bloco, pior caso 0,134 ms, desvio 0,024 ms, RTF medio 0,00157, RTF pior caso 0,00670, latencia total estimada 40 ms, sem status de erro.
- `stft_subtraction`: 1498 blocos, media 0,471 ms/bloco, pior caso 1,929 ms, desvio 0,175 ms, RTF medio 0,0236, RTF pior caso 0,0964, latencia total estimada 72 ms, sem status de erro.
- `stft_wiener`: 1498 blocos, media 0,412 ms/bloco, pior caso 1,423 ms, desvio 0,175 ms, RTF medio 0,0206, RTF pior caso 0,0711, latencia total estimada 72 ms, sem status de erro.
- `wavelet_soft`: 1498 blocos, media 0,258 ms/bloco, pior caso 14,749 ms, desvio 0,394 ms, RTF medio 0,0129, RTF pior caso 0,737, latencia total estimada 60 ms, sem status de erro.

### Interpretacao permitida

- Os quatro metodos testados permaneceram abaixo de RTF 1 na captura real input-only de 30 s.
- `stft_wiener` foi ligeiramente mais leve que `stft_subtraction` nesta rodada.
- `wavelet_soft` teve menor media que os metodos STFT, mas apresentou um pico isolado muito maior no primeiro bloco medido; ainda assim, esse pior caso ficou abaixo de 20 ms.
- A ausencia de eventos em `status_counts` sugere estabilidade de captura no periodo observado, mas nao substitui testes mais longos nem teste duplex.

### Alertas e limitacoes

- O `wavelet_soft` emitiu um `RuntimeWarning` do PyWavelets durante limiarizacao soft. A busca no CSV de blocos nao encontrou `NaN` ou infinito, portanto a rodada foi mantida, mas o comportamento merece investigacao antes de conclusoes finais.
- O agregador consolidou tanto as medicoes novas de 30 s quanto as medicoes curtas anteriores de 3 s em `resultados/tabelas/realtime_windows_input_only.csv`; analises de estabilidade devem preferir as linhas de 1498 blocos.
- A latencia total ainda e uma estimativa input-only: entrada reportada pelo stream mais latencia algoritmica aproximada. Nao ha latencia de saida nem round-trip medido.
- Nao houve avaliacao perceptual, salvamento de WAV ou reproducao local.
- O relatorio `entrega3.tex` deve continuar sem atualizacao ate a etapa de estabilidade e eventual duplex estarem consolidados.

## 2026-06-06 - Auditoria do teste duplex curto no Windows

### Escopo

- Foi executado um teste duplex de 5 s com captura, processamento e reproducao no fone Bluetooth.
- Foram testados `bypass` e `stft_subtraction`, sem salvar WAV.
- A tabela consolidada foi salva em `resultados/tabelas/realtime_windows_duplex.csv`.

### Condicao de seguranca

- O usuario confirmou o uso de fone Bluetooth `HUAWEI FreeBuds SE 2`.
- O usuario informou que os alto-falantes do notebook nao funcionam.
- A saida foi fixada explicitamente no indice 7, `Fones de ouvido (HUAWEI FreeBuds SE 2)`, via MME.

### Resultados auditados

- `bypass`: 248 blocos, media 0,032 ms/bloco, pior caso 0,107 ms, desvio 0,024 ms, RTF medio 0,00162, RTF pior caso 0,00536, latencia de entrada 40 ms, latencia de saida 200 ms, latencia total estimada 240 ms, sem status de erro.
- `stft_subtraction`: 248 blocos, media 0,472 ms/bloco, pior caso 1,463 ms, desvio 0,209 ms, RTF medio 0,0236, RTF pior caso 0,0731, latencia de entrada 40 ms, latencia de saida 200 ms, latencia algoritmica 32 ms, latencia total estimada 272 ms, sem status de erro.

### Interpretacao permitida

- A CLI demonstrou funcionamento tecnico do caminho captura-processa-reproduz no Windows por 5 s.
- O custo computacional do `stft_subtraction` continuou muito abaixo de RTF 1 mesmo em modo duplex.
- A latencia total estimada ficou dominada pela saida Bluetooth, nao pelo algoritmo.
- A verificacao operacional subjetiva foi positiva: o usuario repetiu a captura localmente e informou que correu tudo muito bem.

### Limitacoes

- O teste duplex foi curto e cobre apenas dois metodos.
- A latencia e estimada por valores reportados pelo stream; ainda nao ha medicao fisica de round-trip.
- Bluetooth e uma saida conveniente para seguranca acustica, mas nao e ideal para demonstrar baixa latencia perceptual.
- A avaliacao subjetiva positiva e informal; ainda nao substitui protocolo perceptual formal nem teste com saida cabeada de menor latencia.
- Antes de atualizar `entrega3.tex`, convem decidir se a demonstracao sera apresentada como validacao tecnica curta ou se sera repetida com saida cabeada/menor latencia.

## 2026-06-06 - Auditoria da atualizacao cautelosa do relatorio

### Coerencia das conclusoes

- O relatorio passou a incluir os resultados realtime, mas manteve a distincao entre metricas de qualidade offline e metricas de estabilidade por bloco.
- As tabelas realtime nao afirmam melhoria de SNR, pois a captura real nao tem referencia limpa.
- O texto declara que o duplex curto valida funcionamento da CLI, nao baixa latencia perceptual.
- A latencia Bluetooth foi tratada como limitacao central, com recomendacao de repetir testes com saida de menor atraso.

### Rastreabilidade

- A tabela input-only do relatorio usa os valores de 30 s de `resultados/tabelas/realtime_windows_input_only.csv`.
- A tabela duplex do relatorio usa `resultados/tabelas/realtime_windows_duplex.csv`.
- O relato do usuario foi registrado como avaliacao subjetiva informal, nao como protocolo perceptual formal.
- O warning do PyWavelets em `wavelet_soft` foi mantido como limitacao.

### Verificacao do PDF

- A compilacao final foi feita com `pdflatex -interaction=nonstopmode -jobname=entrega3_build entrega3.tex`, para evitar auxiliares antigos `entrega3.*` inconsistentes.
- O log final nao apresentou referencias indefinidas nem `Overfull`.
- O PDF resultante foi copiado para `entrega3.pdf`.
- Foram renderizadas paginas da secao realtime; as tabelas ficaram legiveis.

### Risco residual

- A atualizacao do relatorio depende de resultados em um unico notebook Windows.
- A estabilidade input-only ja cobre 30 s por metodo, mas o duplex ainda e curto.
- A saida Bluetooth torna a latencia total pouco representativa de uma demonstracao de baixa latencia.
- Ainda falta validar com ruidos ambientais reais e, idealmente, em Raspberry Pi.

## 2026-06-07 - Auditoria da preparacao DEMAND

### Escopo

- A etapa criou infraestrutura para usar ruidos ambientais reais, nao uma nova rodada experimental oficial.
- A base escolhida para a proxima fase foi DEMAND, por oferecer gravacoes de ruido ambiental multicanal em diferentes cenarios.
- O preparador trabalha por padrao com arquivos 16 kHz para reduzir custo de armazenamento e evitar resampling desnecessario no protocolo principal.

### Rastreabilidade e reproducibilidade

- `resultados/tabelas/demand_archives_manifest.csv` registra ambiente, categoria, tamanho, MD5, URL de download, URL do registro, DOI e observacao de licenca.
- `resultados/tabelas/demand_noise_prepared.csv` registra o estado da preparacao dos quatro ambientes padrao.
- O download e opcional e explicito; rodar o preparador sem `--download` nao falha quando os ZIPs estao ausentes, apenas registra `missing_archive`.
- Os ZIPs grandes ficam em `dados/external/demand/` e os snippets derivados em `dados/demo/noise_demand/`, ambos fora do Git.

### Verificacao tecnica

- `python -m compileall benchmark_audio realtime_audio` concluiu sem erro.
- `python -m unittest discover -s tests` executou 8 testes com sucesso.
- O teste automatizado inclui um ZIP temporario com WAV mono, validando preparo local sem rede.
- O benchmark foi testado em raiz temporaria com `--noise-dir`, confirmando que WAVs de ruido real podem substituir os ruidos sinteticos sem alterar o restante do protocolo.

### Limitacoes

- Nenhum arquivo grande do DEMAND foi baixado nesta etapa.
- Ainda nao ha resultados de SNR, SI-SDR, RTF ou graficos comparando STFT/Wavelet em ruidos ambientais reais.
- O texto descritivo do registro DEMAND no Zenodo informa `CC BY-SA 3.0`, mas o metadado atual de direitos no Zenodo tambem deve ser conferido antes de redistribuir derivados.
- Os snippets preparados usam um unico canal por ambiente e normalizacao de pico; isso e adequado para mistura controlada por SNR, mas nao preserva niveis absolutos originais de pressao sonora.

### Conclusao permitida

- Permitido afirmar que o projeto esta pronto para uma primeira rodada controlada com ruidos ambientais reais locais.
- Nao permitido afirmar ainda que os resultados sinteticos se repetem em DEMAND, nem que ha superioridade de STFT ou Wavelet em ambientes reais.

## 2026-06-07 - Auditoria da primeira rodada DEMAND

### Integridade da matriz

- A rodada ambiental foi isolada em `resultados/demand/`; o Git nao indicou modificacao dos CSVs sinteticos rastreados em `resultados/tabelas/`.
- `metricas_por_condicao.csv` contem 960 linhas:
  - 5 amostras de fala;
  - 12 segmentos de ruido;
  - 4 SNRs;
  - 4 metodos.
- Cada metodo possui 240 linhas.
- O baseline `noisy` manteve melhoria de SNR igual a zero.
- Nao foram encontrados `NaN` ou infinito nas tabelas DEMAND.

### Resultados auditados

- Melhoria media de SNR da subtracao espectral: 7,69, 7,31, 6,82 e 6,21 dB para SNRs alvo -5, 0, 5 e 10 dB.
- Melhoria media do ganho Wiener: 4,62, 4,50, 4,33 e 4,07 dB.
- Wavelet soft: 0,28, 0,14, -0,05 e -0,38 dB.
- Considerando todas as 240 condicoes por metodo:
  - subtracao espectral: melhoria media 7,00 dB, minimo 1,88 dB e maximo 13,19 dB;
  - Wiener: melhoria media 4,38 dB, minimo 1,36 dB e maximo 8,84 dB;
  - Wavelet soft: melhoria media aproximadamente 0,00 dB, minimo -1,88 dB e maximo 0,93 dB.

### Dependencia do ambiente

- A subtracao espectral teve melhoria media agregada de:
  - 10,00 dB em `DKITCHEN`;
  - 8,45 dB em `OOFFICE`;
  - 4,11 dB em `PCAFETER`;
  - 5,47 dB em `STRAFFIC`.
- A diferenca entre ambientes e maior que pequenas variacoes de tempo de processamento e deve aparecer na interpretacao.
- O resultado sugere maior facilidade nos trechos de cozinha/escritorio selecionados e menor ganho em cafeteria/trafego, mas nao identifica sozinho a causa espectral.

### Conclusoes permitidas

- Nesta primeira matriz DEMAND, os dois baselines STFT mantiveram melhoria positiva de SNR em media.
- A subtracao espectral permaneceu acima do Wiener e da Wavelet soft com os parametros atuais.
- O desempenho varia por ambiente; portanto, uma unica media global esconde diferencas relevantes.

### Conclusoes nao permitidas

- Nao afirmar superioridade geral de STFT sobre Wavelet.
- Nao tratar os 12 segmentos como 12 ambientes independentes: sao tres segmentos contiguos de quatro ambientes e um canal por ambiente.
- Nao considerar os parametros otimizados, pois nao houve conjunto de validacao separado.
- Nao atribuir os ganhos apenas ao metodo: o silencio inicial da fala favorece a estimativa de ruido STFT.
- Nao substituir avaliacao perceptual por melhoria de SNR.

## 2026-06-07 - Auditoria do refinamento validacao/final

### Integridade do protocolo

- O benchmark historico de cinco falantes foi preservado.
- O refinamento usa seis falantes em pasta separada.
- Falantes e grupos de ruido sao disjuntos entre validacao e conjunto final operacional.
- Cada divisao possui 72 condicoes.
- A busca avaliou 144 configuracoes apenas na validacao.
- A comparacao padrao/refinada possui 1008 linhas: 144 condicoes multiplicadas por 7 configuracoes/baselines.
- Nao foram encontrados `NaN` ou infinito.

### STFT sem silencio inicial

- A retirada do prefixo de 0,30 s reduziu fortemente o desempenho dos parametros antigos.
- No conjunto final:
  - subtracao inicial: +1,82 dB de SNR, -0,16 dB de SI-SDR e 33,3% de degradacoes;
  - Wiener inicial: +1,30 dB de SNR, -0,40 dB de SI-SDR e 27,8% de degradacoes.
- Em SNR alvo de 10 dB, a subtracao inicial piorou a SNR em media 2,45 dB e o Wiener inicial piorou 1,87 dB.
- Conclusao: a hipotese anterior de vantagem artificial por silencio inicial foi confirmada.

### Estimativa por baixa energia

- A selecao de 35% dos quadros de menor energia foi escolhida para as duas STFTs.
- No conjunto final:
  - subtracao: +4,85 dB de SNR e +3,72 dB de SI-SDR;
  - Wiener: +2,92 dB de SNR e +2,25 dB de SI-SDR;
  - nenhuma condicao com melhoria de SNR negativa.
- O custo permaneceu muito abaixo de RTF 1 em processamento offline de arquivos.
- Limitacao central: o estimador examina o trecho completo e nao pode ser tratado como implementacao realtime causal.

### Refinamento Wavelet

- Foram testadas 72 configuracoes envolvendo tres familias, dois niveis, soft/hard, global/por escala e tres fatores.
- A melhor configuracao de validacao foi `sym4`, nivel 3, hard, global, fator 0,50.
- Ela melhorou a estabilidade em relacao ao padrao:
  - SI-SDR final passou de -0,46 dB para aproximadamente 0,01 dB;
  - degradacoes de SNR caíram de 19,4% para 11,1%.
- A melhoria media de SNR final ficou em apenas 0,03 dB.
- Conclusao: o refinamento reduziu dano, mas nao demonstrou capacidade relevante de supressao no protocolo atual.
- Precisao metodologica apos revisao com Gabriel: essa conclusao vale para a
  DWT com shrinkage por limiarizacao universal/MAD. Ela nao descarta uma trilha
  Wavelet mais adaptativa, como WPT com rastreamento temporal de ruido por
  subbanda e ganho Wiener.

### Selecao tecnica permitida

- Subtracao espectral adaptada e a candidata principal para continuidade no PC e futura aproximacao causal.
- Wiener adaptado e alternativa menos agressiva, com ganho objetivo menor.
- A DWT limiarizada deve permanecer como baseline leve e objeto de analise de
  trade-off, nao como candidata principal com os resultados atuais.
- A proxima investigacao Wavelet passa a ser `Wavelet Packet Transform +`
  rastreamento temporal de ruido por subbanda `+` ganho Wiener, conforme
  `docs/plano_wavelet_packet_wiener.md`.

### Cautelas

- O conjunto final operacional nao e historicamente cego: os ambientes ja tinham sido analisados na rodada exploratoria.
- Os segmentos por ambiente continuam contiguos e de um canal.
- A selecao foi guiada por SNR, com SI-SDR, degradacao e RTF como desempate; ainda falta avaliacao perceptual.
- Tempos de arquivo nao equivalem a latencia causal por bloco.

### Verificacao de fechamento

- 12 testes e 4 subtestes aprovados.
- 144 linhas em `validation_candidates.csv`.
- 1008 linhas em `comparison_metrics.csv`.
- Nenhum `NaN` ou infinito nas colunas numericas auditadas.
- Relatorio final com 32 paginas, sem `Overfull` e sem referencias ou citacoes indefinidas.

## 2026-06-07 - Auditoria do estimador causal PC-1

### Integridade da selecao

- `validation_candidates.csv` contem 21 linhas:
  - 20 configuracoes adaptativas;
  - uma calibracao curta.
- A selecao usou apenas `jackson`, `nicolas`, `theo`, `DKITCHEN` e
  `OOFFICE`.
- O conjunto `final_operational` foi avaliado somente depois da escolha.
- Nenhuma Sessao B, voz autoral ou gravacao futura foi usada.
- A comparacao final contem 1152 linhas:
  - 144 condicoes;
  - oito metodos/baselines.
- Nao ha `NaN` ou infinito nas colunas numericas.
- O bypass final tem melhoria exatamente zero, confirmando neutralidade.

### Comportamento exigido

- Silencio:
  - estimativa finita e positiva pelo epsilon.
- Fala continua:
  - teste unitario confirma atualizacao lenta/congelada quando a energia
    ultrapassa o piso causal.
- Mudanca de ruido:
  - teste unitario confirma crescimento da estimativa depois que o historico
    antigo expira.
- Blocos curtos:
  - comprimentos de 1, 3, 5, 7 e 11 amostras preservados.
- Causalidade:
  - sinais com prefixo igual e futuros diferentes produzem saidas identicas
    no prefixo compartilhado.
- Determinismo:
  - `reset()` seguido dos mesmos blocos reproduz a saida bit a bit.

### Resultados permitidos

- A subtracao adaptativa causal e a candidata principal da PC-1:
  - validacao: +3,74 dB SNR e +3,15 dB SI-SDR;
  - final operacional: +3,76 dB SNR e +2,65 dB SI-SDR;
  - zero degradacoes de SNR nas duas divisoes.
- O Wiener causal e alternativa menos agressiva:
  - final operacional: +1,68 dB SNR e +1,35 dB SI-SDR;
  - zero degradacoes.
- A calibracao curta nao e robusta sem silencio inicial:
  - +0,96 dB SNR;
  - -2,38 dB SI-SDR;
  - 33,3% de degradacao no final operacional.
- A baixa energia offline continua sendo limite superior operacional:
  - +4,85 dB SNR e +3,72 dB SI-SDR;
  - nao pode ser chamada de implementacao realtime.

### Custo e jitter

- Estado maximo reportado: 60.900 bytes, aproximadamente 59,5 KiB.
- Subtracao causal no final operacional:
  - RTF medio 0,068;
  - p99 medio 3,08 ms;
  - pior bloco 13,31 ms.
- Na validacao em lote:
  - RTF medio 0,078;
  - p99 medio 3,74 ms;
  - pico isolado 104,12 ms.
- O pico de 104,12 ms nao invalida as metricas de qualidade, mas impede
  afirmar estabilidade realtime prolongada.
- O autoteste posterior de 1 s teve pior bloco 4,62 ms e nenhum excesso de
  20 ms.
- PC-6 continua necessaria para medir estabilidade real prolongada, eventos de
  stream, CPU e memoria do processo com o estimador congelado.

### Interpretacao e limites

- Permitido afirmar que existe estimador causal deterministico, sem acesso a
  blocos futuros e sem dependencia de silencio inicial fixo.
- Permitido afirmar que ele recupera parte substancial do ganho offline no
  conjunto operacional existente.
- Nao permitido chamar o conjunto final de historicamente cego.
- Nao permitido extrapolar o estado NumPy para memoria total em Raspberry Pi.
- Nao permitido inferir qualidade perceptual das metricas objetivas.
- Nao permitido afirmar estabilidade de 10 minutos ou baixa latencia fisica;
  nenhum teste humano/fisico foi executado nesta etapa.

### Fechamento

- 21 testes e 4 subtestes aprovados.
- Relatorio com 33 paginas, compilado em tres passagens.
- Sem `Overfull`, referencias ou citacoes indefinidas.
- Codigo, resultados, testes e relatorio no commit `a03f05a`.

## 2026-06-07 - Auditoria do processamento WAV em blocos PC-2

### Integridade do caminho

- O arquivo e a captura Windows compartilham
  `benchmark_audio.causal.CausalSTFTProcessor`.
- Nao foi criada segunda implementacao de estimador, subtracao ou Wiener.
- O helper de tempos compartilhado nao altera o DSP.
- O processador e reinicializado a cada arquivo.
- O bloco atual atualiza o estimador somente para blocos seguintes, mantendo a
  semantica causal da PC-1.

### E/S e alinhamento

- Estereo e convertido por media de canais.
- Taxas diferentes sao reamostradas para 16 kHz.
- A CLI nao normaliza o pico.
- O ultimo bloco curto nao recebe amostras futuras.
- Todas as 22 linhas da matriz preservaram comprimento.
- O deslocamento de indice registrado foi zero.
- Bypass e exato em float32 antes da escrita.
- A escrita PCM16 limita somente valores fora de `[-1,1]` e registra a
  contagem.
- A execucao representativa teve zero amostras fora da faixa e zero nao
  finitos.

### Matriz e resultados

- Matriz:
  - uma fala publica FSDD;
  - um trecho DEMAND PCAFETER;
  - duas SNRs;
  - tres blocos;
  - tres metodos causais;
  - duas referencias offline.
- Bypass teve melhoria exatamente zero.
- Subtracao causal:
  - media de +3,36, +3,27 e +3,25 dB de SNR para 10, 20 e 32 ms;
  - media de +1,22, +1,27 e +1,35 dB de SI-SDR.
- Wiener causal:
  - media de +1,54, +1,33 e +1,27 dB de SNR;
  - media de +0,74, +0,67 e +0,68 dB de SI-SDR.
- Limite offline:
  - subtracao +4,31 dB SNR e +2,14 dB SI-SDR;
  - Wiener +2,85 dB SNR e +1,68 dB SI-SDR.
- A diferenca causal/offline permaneceu positiva, como esperado:
  - subtracao: 0,94 a 1,06 dB de SNR no agregado;
  - Wiener: 1,31 a 1,58 dB de SNR.
- Nenhum bloco excedeu o orcamento.
- Estado maximo: 60.900 bytes.

### Efeito do tamanho de bloco

- O RTF total diminuiu com blocos maiores:
  - subtracao: 0,111, 0,081 e 0,068;
  - Wiener: 0,107, 0,078 e 0,069.
- O p99 em milissegundos aumentou em geral com blocos maiores, mas permaneceu
  muito abaixo dos respectivos orcamentos.
- A qualidade variou pouco:
  - 10 ms apresentou leve vantagem de SNR;
  - 32 ms apresentou leve vantagem de SI-SDR na subtracao.
- Nao e permitido tratar essa matriz pequena como nova selecao de bloco ou
  parametros.

### Reprodutibilidade

- CSVs e JSONs foram auditados sem `NaN` ou infinito.
- O manifesto dos vetores contem SHA-256, tamanhos e tolerancias.
- O bypass esperado tem o mesmo SHA-256 da entrada PCM16.
- A saida CLI e o vetor causal esperado possuem exatamente:
  - `47f70c20306c7a602d2b1bb6a320ca6451f8c4f4229e8992ca8a856fb476a3ed`.
- A suite final aprovou 30 testes e 9 subtestes.

### Interpretacao permitida

- Existe um caminho de arquivo reproduzivel que usa o mesmo nucleo da captura.
- Comprimento e alinhamento sao preservados depois da conversao de entrada.
- Os tres tamanhos de bloco operam com os parametros congelados.
- A subtracao causal continua mais proxima do limite offline que o Wiener
  causal nesta amostra.
- Os vetores sao adequados para testar uma futura implementacao equivalente.

### Interpretacao nao permitida

- Nao chamar tempo de arquivo de latencia fisica ou estabilidade de stream.
- Nao generalizar a diferenca entre blocos a outros falantes ou ruidos.
- Nao tratar o offline de baixa energia como causal.
- Nao inferir qualidade perceptual.
- Nao afirmar prontidao Raspberry Pi; os vetores apenas preparam a transicao.

### Privacidade e limites

- Nenhuma voz autoral ou privada foi usada.
- Vetores sao integralmente sinteticos.
- Nao houve microfone, fone, playback ou julgamento humano.
- Arquivos antigos nao rastreados permaneceram fora dos commits.

## 2026-06-07 - Auditoria da preparacao de voz autoral

### Escopo auditado

- Esta etapa entrega protocolo e ingestao, nao resultados de voz.
- Nenhum consentimento, dispositivo ou WAV real foi inferido.
- A avaliacao objetiva autoral permanece pendente.

### Separacao metodologica

- `raw_quiet`:
  - referencia limpa aproximada;
  - elegivel para misturas controladas.
- `raw_noise`:
  - ruido ambiente sem fala;
  - elegivel como fonte conhecida de mistura.
- `raw_live_noisy`:
  - fala e ruido capturados juntos;
  - sem SNR ou SI-SDR pareada na ausencia de referencia.
- Sessao A:
  - depuracao da ingestao e niveis.
- Sessao B:
  - confirmacao final;
  - proibida para nova selecao de parametros.

### Privacidade

- Pastas brutas, preparadas e privadas estao no `.gitignore`.
- Manifestos versionaveis nao possuem campo de nome real.
- `consent_record_id` e obrigatorio para ingestao.
- A autorizacao distingue uso local, banca e trecho publico.
- `public_excerpt` nao implica publicacao automatica.
- Termos assinados devem permanecer fora do Git.

### Integridade da ingestao

- WAV PCM e validado pelo cabecalho e pelo decodificador.
- Arquivos vazios, truncados, ausentes e fora da raiz sao rejeitados ou
  registrados como erro.
- O hash do bruto e calculado antes do derivado.
- O bruto nao e reescrito.
- O derivado usa somente:
  - conversao para float;
  - media de canais;
  - remocao de DC;
  - reamostragem;
  - quantizacao PCM16.
- Nao ha:
  - normalizacao;
  - denoising;
  - gate;
  - equalizacao;
  - compressao.

### Qualidade e rastreabilidade

- Registrados:
  - taxa, canais, profundidade, frames e dtype;
  - duracao;
  - pico e RMS em amplitude e dBFS;
  - DC removido;
  - amostras clipadas;
  - silencio;
  - hashes bruto e preparado;
  - nivel de autorizacao;
  - avisos e erros.
- Divergencias entre manifesto e WAV sao avisos explicitos.
- Clipping e silencio nao sao corrigidos silenciosamente.
- Saidas existentes exigem `--overwrite`.
- Regeneracao do mesmo manifesto produziu hashes identicos nos testes.

### Verificacao

- PCM16 estereo 48 kHz:
  - convertido para mono 16 kHz;
  - DC removido;
  - amplitude nao normalizada.
- PCM24:
  - profundidade reconhecida e preparada.
- Clipping e silencio:
  - detectados e registrados.
- Suite:
  - 39 testes e 9 subtestes aprovados.
- Smoke test sintetico:
  - uma linha preparada;
  - zero erros;
  - nenhuma dependencia de rede ou microfone.

### Conclusoes permitidas

- O projeto esta pronto para receber arquivos autorais de forma controlada.
- A ingestao preserva o bruto e gera derivados reproduziveis.
- Os modelos impedem nomes reais no manifesto por desenho.
- A Sessao B pode ser mantida fora do ajuste.

### Conclusoes nao permitidas

- Nao afirmar que os participantes autorizaram a coleta.
- Nao afirmar que existe corpus autoral preparado.
- Nao relatar qualidade, SNR, SI-SDR ou preferencia de voz autoral.
- Nao atualizar o relatorio com resultados inexistentes.
- Nao iniciar Checkpoint 22 antes da coleta e revisao dos metadados.

## 2026-06-07 - Auditoria do ferramental de avaliacao autoral

### Escopo auditado

- Esta etapa prepara a avaliacao objetiva e perceptual, mas nao gera resultados
  de voz autoral.
- Nenhum arquivo WAV real, termo assinado, dispositivo ou julgamento de escuta
  foi inferido.
- O objetivo foi reduzir risco operacional antes da coleta: comandos,
  manifestos, metricas permitidas e formulario de escuta.

### Coerencia metodologica

- `raw_quiet` e usado como referencia limpa aproximada somente em misturas
  controladas com ruido conhecido.
- `raw_noise` e fonte conhecida de ruido, escalada por SNR alvo.
- `raw_live_noisy` nao recebe SNR, melhoria de SNR, SI-SDR ou MSE pareados.
- A Sessao B permanece bloqueada para ajuste de parametros.
- A CLI inclui o estimador offline de baixa energia somente como referencia
  nao causal e identifica a Wavelet como baseline leve.

### Privacidade

- A avaliacao grava CSV/JSON por padrao, nao WAV processado.
- Identificadores continuam em `spkXX`, sessao, tipo e `utterance_id`.
- O formulario perceptual usa `blind_label`, nao nomes reais.
- Se uma chave cega apontar para WAVs privados, ela deve ficar em area
  privada e ignorada pelo Git.

### Verificacao tecnica

- `pytest.ini` restringe a coleta do pytest a `tests/`, corrigindo a falha
  causada por copias nao rastreadas em `revisao_wavelets_gabriel/tests/`.
- A suite sintetica da nova CLI confirma:
  - geracao de `controlled_metrics.csv`, `controlled_summary.csv` e metadata;
  - bypass neutro em melhoria de SNR;
  - comprimento preservado;
  - separacao de metricas operacionais em `raw_live_noisy`;
  - recusa de `prepared_with_warnings` sem autorizacao explicita.
- Verificacao final da etapa: 41 testes e 9 subtestes aprovados.

### Conclusoes permitidas

- Permitido afirmar que existe ferramental automatizado para executar a
  avaliacao autoral depois da ingestao.
- Permitido afirmar que a CLI evita metricas pareadas em fala naturalmente
  ruidosa.
- Permitido afirmar que o comando `python -m pytest -q` voltou a ser
  reproduzivel no workspace atual.

### Conclusoes nao permitidas

- Nao afirmar que a avaliacao autoral foi executada.
- Nao afirmar que a escuta critica ocorreu.
- Nao atualizar `entrega3.tex` com resultados inexistentes.
- Nao tratar a Sessao B como confirmacao enquanto autorizacoes, WAVs, ingestao
  e revisao de qualidade nao existirem.

## 2026-06-07 - Auditoria da primeira rodada WPT + Wiener

### Escopo auditado

- A etapa implementou uma nova candidata Wavelet, `wavelet_packet_wiener`.
- A DWT historica continua em `wavelet_soft`.
- A rodada foi salva em `resultados/wpt_refinement/`, sem sobrescrever
  `resultados/demand_refinement/tabelas/`.
- A implementacao e offline; ela ainda nao deve ser descrita como causal ou
  realtime.

### Protocolo

- Comando executado:
  `python -m benchmark_audio.run_refinement --include-wpt --results-dir resultados/wpt_refinement`.
- Divisao preservada:
  - validacao: `jackson`, `nicolas`, `theo` com `DKITCHEN` e `OOFFICE`;
  - final operacional: `george`, `lucas`, `yweweler` com `PCAFETER` e
    `STRAFFIC`.
- Foram avaliados 180 candidatos:
  - 72 STFT;
  - 72 DWT limiarizada;
  - 36 WPT + Wiener.

### Resultados medidos

- Melhor WPT por validacao:
  `wpt_wiener_sym4_l3_rolling_q0.2_w31_f0.1`.
- Na validacao:
  - SNR medio: +0,878 dB;
  - SI-SDR medio: +0,200 dB;
  - degradacoes de SNR: 25,0%.
- No final operacional:
  - SNR medio: +0,366 dB;
  - SI-SDR medio: -0,248 dB;
  - degradacoes de SNR: 25,0%.
- Comparacao final de contexto:
  - DWT refinada historica: +0,026 dB SNR e +0,008 dB SI-SDR;
  - STFT subtracao offline de baixa energia: +4,848 dB SNR e +3,716 dB
    SI-SDR;
  - STFT Wiener offline de baixa energia: +2,920 dB SNR e +2,253 dB SI-SDR.

### Verificacao tecnica

- `python -m compileall benchmark_audio realtime_audio`.
- `python -m pytest -q`: 44 testes e 10 subtestes aprovados.

### Conclusoes permitidas

- A formulacao WPT + tracking + Wiener testada melhora SNR medio em relacao a
  DWT limiarizada.
- A DWT antiga nao deve ser usada para descartar toda a familia Wavelet.
- A primeira WPT ainda nao supera as STFTs no protocolo atual.
- O SI-SDR negativo no final e a fracao de degradacao exigem cautela e escuta
  critica antes de qualquer conclusao de qualidade perceptual.

### Conclusoes nao permitidas

- Nao afirmar que WPT e a melhor candidata do projeto.
- Nao afirmar que a implementacao WPT e causal.
- Nao usar estes resultados para atualizar `entrega3.tex` com conclusao forte.
- Nao ignorar a degradacao de SI-SDR apenas porque houve ganho medio de SNR.
- Nao reinterpretar os CSVs antigos como se ja contivessem WPT.

## 2026-06-07 - Auditoria do benchmark Wavelet pesado

### Escopo auditado

- Esta etapa responde a revisao de Gabriel de que as ondaletas precisavam ser
  testadas mais profundamente.
- A rodada completa considerada e `resultados/wavelet_heavy_refinement/`.
- A tentativa `max` em `resultados/wavelet_heavy_max_refinement/` foi
  interrompida antes de gerar resultados e esta marcada como incompleta.
- Nenhum resultado historico em `resultados/demand_refinement/tabelas/` foi
  sobrescrito.

### Protocolo

- Script: `benchmark_audio/run_wavelet_heavy_refinement.py`.
- Comando principal:
  `python -m benchmark_audio.run_wavelet_heavy_refinement --profile focused --results-dir resultados/wavelet_heavy_refinement --screening-speakers 1 --screening-noises-per-group 1 --full-per-family 16`.
- O final operacional nao foi usado na selecao.
- A selecao ocorreu em duas etapas:
  - triagem ampla em subconjunto da validacao;
  - reavaliacao dos melhores na validacao completa;
  - comparacao final somente depois.
- Escore robusto registrado:
  `snr_mean + si_sdr_mean + 0.25 * snr_min - 2.0 * degradation_fraction`.

### Grade

- 2556 candidatos na triagem:
  - 720 DWT;
  - 972 WPT por coeficiente;
  - 864 WPT em quadros.
- 86 candidatos foram reavaliados na validacao completa.
- 11 candidatos foram comparados no final operacional, incluindo referencias
  STFT e baselines Wavelet historicos.

### Resultados medidos

- DWT pesada:
  - melhor final: `dwt_coif3_l2_soft_global_s0.25`;
  - +0,055 dB SNR, +0,008 dB SI-SDR, 4,2% degradacoes.
- WPT por coeficiente robusta:
  - `wpt_coeff_bior4p4_l2_rolling_quantile_q0.1_w31_f0.05_sm0`;
  - +0,393 dB SNR, +0,132 dB SI-SDR, 9,7% degradacoes.
- WPT em quadros robusta:
  - `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - validacao: +2,236 dB SNR, +0,796 dB SI-SDR, 0,0% degradacoes;
  - final: +3,210 dB SNR, +1,753 dB SI-SDR, 0,0% degradacoes.
- WPT em quadros com maior SNR:
  - `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - final: +3,524 dB SNR, +1,785 dB SI-SDR, 4,2% degradacoes.
- Referencias finais:
  - STFT subtracao baixa energia offline: +4,848 dB SNR, +3,716 dB SI-SDR;
  - STFT subtracao causal adaptativa: +3,763 dB SNR, +2,648 dB SI-SDR;
  - STFT Wiener baixa energia offline: +2,920 dB SNR, +2,253 dB SI-SDR.

### Verificacao tecnica

- `python -m compileall benchmark_audio realtime_audio`.
- `python -m pytest -q`: 48 testes e 11 subtestes aprovados.

### Conclusoes permitidas

- E permitido afirmar que a DWT limiarizada continua praticamente neutra mesmo
  com busca ampliada.
- E permitido afirmar que a WPT por coeficiente nao resolveu a limitacao.
- E permitido afirmar que WPT em quadros com overlap tem desempenho objetivo
  decente no protocolo DEMAND atual.
- E permitido corrigir a narrativa: os resultados antigos nao enfraquecem a
  familia Wavelet como um todo, apenas a DWT limiarizada testada.
- E permitido manter STFT subtracao causal como candidata PC principal por
  enquanto, pois ela ja e causal e ainda tem SI-SDR final maior.

### Conclusoes nao permitidas

- Nao afirmar que WPT em quadros e causal.
- Nao afirmar que WPT em quadros supera a subtracao STFT offline.
- Nao trocar a candidata PC principal sem escuta critica e sem versao causal ou
  rolante da WPT.
- Nao usar a tentativa `max` incompleta como resultado.
- Nao atualizar `entrega3.tex` com conclusao forte sem registrar essas
  limitacoes.

## 2026-06-08 - Auditoria do perfil max Wavelet pesado completo

### Escopo auditado

- A rodada auditada e `resultados/wavelet_heavy_max_refinement_full/`.
- A pasta foi criada separadamente e nao sobrescreveu resultados historicos.
- A tentativa antiga `resultados/wavelet_heavy_max_refinement/` continua
  incompleta e nao deve ser confundida com esta rodada.
- Nenhum resultado de voz autoral foi usado.
- A WPT em quadros permanece implementacao offline; nao e causal.

### Integridade da rodada

- `metadata_wavelet_heavy.json` registra:
  - perfil `max`;
  - 8784 candidatos;
  - 113 candidatos em validacao completa;
  - 12 candidatos em comparacao final;
  - 72 condicoes de validacao e 72 finais;
  - `elapsed_s = 8929.7535528`.
- `selected_wavelet_configs.csv` contem duas selecoes por familia quando
  necessario: robusta e por SNR medio.
- `comparison_overall.csv` contem linhas de `validation` e `final`, incluindo
  baselines STFT e Wavelet.

### Comparacao com focused

- Melhor robusta `focused`:
  - `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - final: +3,210 dB SNR, +1,753 dB SI-SDR, 0,0% degradacoes.
- Melhor robusta `max`:
  - `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - validacao: +2,288 dB SNR, +1,127 dB SI-SDR, 0,0% degradacoes;
  - final: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes.
- Melhor por SNR `focused`:
  - `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - final: +3,524 dB SNR, +1,785 dB SI-SDR, 4,2% degradacoes.
- Melhor por SNR `max`:
  - `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - validacao: +2,685 dB SNR, +1,050 dB SI-SDR, 4,2% degradacoes;
  - final: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes.

### Contexto contra STFT

- STFT subtracao offline de baixa energia:
  - +4,848 dB SNR, +3,716 dB SI-SDR, 0,0% degradacoes.
- STFT Wiener offline de baixa energia:
  - +2,920 dB SNR, +2,253 dB SI-SDR, 0,0% degradacoes.
- STFT subtracao causal adaptativa:
  - +3,763 dB SNR, +2,648 dB SI-SDR, 0,0% degradacoes.

### Conclusoes permitidas

- E permitido afirmar que o `max` encontrou configuracoes WPT em quadros
  melhores que o `focused`.
- E permitido afirmar que a configuracao robusta `max` e estavel no protocolo
  medido: 0,0% degradacoes em validacao e final.
- E permitido afirmar que a configuracao `db6` elevou o teto final de SNR WPT,
  mas precisa de ressalva por ter degradacoes na validacao.
- E permitido manter a WPT em quadros como resultado Wavelet mais forte ate
  agora, porem offline.
- E permitido manter a STFT subtracao causal como candidata PC principal,
  porque ja tem estado causal e SI-SDR final superior.

### Conclusoes nao permitidas

- Nao afirmar que WPT em quadros e causal.
- Nao afirmar que o `max` derrubou a STFT offline.
- Nao afirmar que a WPT em quadros e a candidata PC principal sem versao
  causal/rolante e sem escuta critica.
- Nao apagar a distincao entre candidata robusta (`haar`) e candidata de maior
  SNR (`db6`).
- Nao usar resultados de voz autoral inexistentes para reforcar esta conclusao.

## 2026-06-08 - Auditoria do fechamento tecnico PC

### Escopo auditado

- Esta etapa nao executa nova busca nem nova avaliacao numerica.
- O objetivo e consolidar a decisao de implementacao PC depois das rodadas:
  - estimador causal STFT;
  - processamento WAV em blocos PC-2;
  - preparacao do protocolo autoral;
  - WPT + Wiener inicial;
  - Wavelet pesada `focused` e `max`.
- Nenhuma voz autoral real foi usada.

### Decisao permitida

- A subtracao STFT causal adaptativa e a candidata principal para PC.
- Razoes auditaveis:
  - estado causal explicito em `benchmark_audio.causal.CausalSTFTProcessor`;
  - parametros congelados depois da divisao de validacao;
  - processamento reproduzivel por blocos de WAV;
  - resultado final operacional de +3,763 dB SNR, +2,648 dB SI-SDR e 0,0%
    degradacoes;
  - SI-SDR final maior que as melhores WPT em quadros medidas ate agora.

### Leitura da WPT

- A WPT em quadros e um achado importante e corrige a narrativa antiga sobre
  Wavelets.
- O perfil `max` confirma que a familia Wavelet nao deve ser reduzida a DWT
  limiarizada:
  - robusta `haar`: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes;
  - maior SNR `db6`: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes no
    final.
- Limitacao central: a WPT em quadros ainda e offline. A melhor formulacao usa
  informacao temporal do arquivo e nao tem estado causal validado.

### Leitura da voz autoral

- A voz autoral deve entrar como validacao complementar posterior.
- A ausencia de gravacoes autorais nao bloqueia a decisao PC, porque a decisao
  se apoia em DEMAND, FSDD publico, protocolos de validacao/final e ferramentas
  ja testadas.
- Quando executada, a avaliacao autoral deve usar parametros congelados e nao
  fazer nova busca oportunista.

### Conclusoes permitidas

- E permitido afirmar que STFT causal e o caminho PC atual.
- E permitido afirmar que WPT em quadros e o resultado Wavelet offline mais
  forte ate agora.
- E permitido afirmar que voz autoral valida e complementa a decisao depois,
  sem ser pre-condicao para fecha-la.

### Conclusoes nao permitidas

- Nao afirmar que WPT em quadros e causal.
- Nao afirmar que WPT em quadros substituiu a STFT PC.
- Nao afirmar resultados de voz autoral ainda inexistentes.
- Nao reabrir parametros da STFT causal por causa da avaliacao autoral futura.

## 2026-06-08 - Auditoria da validacao Windows prolongada PC-24

### Escopo auditado

- A etapa avaliou estabilidade operacional do caminho PC ja congelado.
- Metodo auditado:
  - `stft_subtraction`;
  - `noise-mode adaptive`;
  - bloco de 20 ms;
  - STFT 512/160;
  - alpha 1,5 e piso 0,02;
  - estimador causal com aquecimento 250 ms, historico 500 ms, quantil 0,22 e
    parametros PC-1.
- Nao houve nova busca de parametros.
- Nao houve uso de voz autoral.
- WPT em quadros nao foi executada nem reinterpretada como causal.

### Integridade dos artefatos

- Todos os artefatos foram gravados em pasta nova:
  `resultados/windows_realtime_longrun/`.
- A rodada sintetica curta gerou:
  - `synthetic_stft_subtraction_20ms_20260608_100642_metrics.json`;
  - CSV de blocos correspondente.
- A rodada sintetica longa gerou:
  - `synthetic_stft_subtraction_20ms_20260608_100737_metrics.json`;
  - CSV de blocos correspondente.
- A rodada fisica curta gerou:
  - `windows_input_only_stft_subtraction_20ms_20260608_100911_metrics.json`;
  - CSV de blocos correspondente.
- A rodada fisica longa gerou:
  - `windows_input_only_stft_subtraction_20ms_20260608_101937_metrics.json`;
  - CSV de blocos correspondente.
- As rodadas com microfone usaram `--no-save`; nenhum WAV de entrada ou saida
  foi salvo.

### Self-test sintetico

- Rodada de 60 s:
  - 3.000 blocos;
  - media 0,977 ms;
  - p95 1,260 ms;
  - p99 1,573 ms;
  - pior bloco 3,669 ms;
  - zero blocos acima de 20 ms.
- Rodada de 600 s:
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

### Captura fisica input-only

- Dispositivo usado na rodada valida:
  - `Microfone (USB Audio Device), MME`, indice 2.
- Tentativa descartada:
  - `Microfone (USB Audio Device), Windows WASAPI`, indice 49;
  - falhou por `Invalid sample rate` em 16 kHz;
  - a falha pertence ao pareamento driver/taxa, nao ao nucleo DSP.
- Rodada de 30 s:
  - 1.498 blocos;
  - media 1,215 ms;
  - p95 2,019 ms;
  - p99 3,354 ms;
  - pior bloco 6,013 ms;
  - zero blocos acima de 20 ms;
  - `status_counts` vazio.
- Rodada de 600 s:
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
  - fracao `speech_probable`: 0,254;
  - latencia de entrada reportada: 40 ms;
  - latencia total estimada no JSON: 72 ms.

### Conclusoes permitidas

- Permitido afirmar que a subtracao STFT causal adaptativa sustentou 600 s de
  self-test sintetico sem estouro do orcamento de 20 ms por bloco.
- Permitido afirmar que a mesma configuracao sustentou 600 s de captura fisica
  de entrada no Windows, em modo `input-only`, sem underflow/overflow reportado
  pela CLI e sem bloco acima de 20 ms.
- Permitido afirmar que o pior bloco fisico medido foi 6,799 ms, abaixo do
  orcamento externo de 20 ms.
- Permitido afirmar que o estado causal maximo observado permaneceu em
  60.900 bytes.
- Permitido manter a STFT causal como caminho PC principal depois do
  Checkpoint 24.

### Conclusoes nao permitidas

- Nao afirmar baixa latencia ponta a ponta: a rodada fisica foi `input-only` e
  nao mediu playback, loopback ou round-trip.
- Nao usar a latencia total estimada de 72 ms como latencia fisica final do
  sistema.
- Nao tratar Bluetooth como evidencia de latencia; nenhum teste Bluetooth foi
  usado para essa conclusao.
- Nao afirmar qualidade perceptual ou inteligibilidade a partir desses logs.
- Nao afirmar resultados de voz autoral.
- Nao promover WPT em quadros a metodo causal ou candidato PC principal.

### Fechamento

- A validacao PC-24 resolve a pendencia operacional apontada no Checkpoint 23:
  existe evidencia de longa duracao no Windows para o nucleo STFT causal
  congelado.
- O proximo passo pode ser consolidacao no relatorio/defesa ou uma rodada
  full-duplex cabeada separada, se a equipe quiser medir caminho de saida e
  round-trip fisico.

## Checkpoint 34 - auditoria de latencia da ponte

### Evidencia valida

- O sinal controlado foi injetado eletricamente pelo VB-Audio Virtual Cable.
- A matriz valida comparou profundidades 1, 2 e 4 com fila local 4.
- Todos os casos tiveram zero overrun, erro de escrita e erro de sequencia.
- Profundidade 2 consumiu 410 blocos e registrou 56 underruns.
- Profundidade 4 consumiu 414 blocos e registrou 24 underruns, mas adicionou
  20 ms a estimativa de buffer do driver.
- O novo total de `182,36 ms` para profundidade 2 inclui algoritmo, stream,
  residencia p95 local e profundidade p95 do driver.

### Decisao permitida

- Fixar profundidade 2 e fila local 4 como defaults operacionais.
- Afirmar que profundidade 2 foi o melhor compromisso observado entre
  continuidade e atraso na matriz controlada.
- Afirmar que a estimativa anterior de `72 ms` era incompleta para o caminho
  virtual porque nao contabilizava a ponte.

### Conclusoes nao permitidas

- Nao chamar `182,36 ms` de latencia fisica ponta a ponta.
- Nao tratar a injecao pelo VB-Audio Cable como ensaio acustico.
- Nao usar a tentativa `user_queue=1` como evidencia: o consumidor nao estava
  ativo, houve `input overflow` e a sessao Guest Control ficou bloqueada.
- Nao afirmar qualidade perceptual ou melhoria de inteligibilidade.

### Risco residual

- O polling WASAPI do capturador permaneceu abaixo da taxa nominal em partes
  da matriz.
- Descartes locais ainda ocorrem e indicam desequilibrio entre producao e
  consumo.
- Uma futura medicao acustica deve controlar fonte, distancia, nivel e
  dispositivo, preservando os parametros DSP e de fila agora congelados.

## Checkpoint 35 - interface mínima de controle

### Evidência autorizada

- A UI abre no host sem driver e informa endpoint desconectado sem crash.
- A suíte completa terminou com `62 passed` e `11 subtests passed`.
- Na VM, três ciclos iniciar/parar atualizaram nível e métricas sem congelar a
  janela.
- O primeiro ciclo observado mostrou 329 blocos processados, 311 enviados,
  15 descartes locais, 76 underruns, zero overruns e zero erros de escrita.
- A latência exibida, `184,6 ms` nessa captura, é estimativa por componentes.
- O cliente externo recebeu 352.000 frames e 11.150 amostras não nulas.
- Persistência, fechamento ativo e contenção com `WinError 170` foram
  confirmados.
- O WAV privado foi removido depois da análise numérica.

### Evidência preservada

- `resultados/sysvad_checkpoint35/README.md`;
- `resultados/sysvad_checkpoint35/checkpoint35_python_bundle.zip`;
- `resultados/sysvad_checkpoint35/checkpoint35_vm_results.zip`;
- screenshots do host desconectado, ciclos ativos, persistência, fechamento e
  contenção.

### Limites

- O nível físico disponível na VM permaneceu baixo, perto de `-96 dBFS`.
- A captura externa confirma transporte de amostras, não qualidade
  perceptual.
- O Checkpoint 35 não mede latência física ponta a ponta.
- O estado `aborted` observado após o desligamento foi descartado pela
  restauração do snapshot funcional; não deve ser tratado como estado final
  válido.

## Checkpoint 36 - validação acústica real

### Evidência autorizada

- O dispositivo foi identificado como `HyperX Quadcast` por descritor USB,
  com endpoint `Microfone (USB Audio Device)` e `VID_098C&PID_16DF`.
- A fala atingiu pico de `-12,52 dBFS`, com zero clipping e separação de
  `41,44 dB` entre RMS de fala e silêncio.
- O cliente externo recebeu áudio processado não nulo nos cenários limpo e
  ruidoso.
- O trecho de ruído marrom sem fala caiu de `-57,14` para `-59,88 dBFS` RMS,
  redução de `2,75 dB`.
- A rodada de estabilidade durou 630 s, com zero overruns, zero erros de
  escrita e zero processos residuais.

### Limites e achados negativos

- A estabilidade acumulou 4.491 descartes locais e 10.626 underruns.
- A escuta identificou pipocos nos dois caminhos, muito mais intensos no
  processado.
- O bruto foi claramente preferido nos dois cenários.
- A redução objetiva foi moderada e não compensou os artefatos operacionais.
- Os deslocamentos usados para alinhar os WAVs decorrem do início assíncrono
  dos gravadores e não medem latência física.
- Uma tomada com mute físico foi invalidada; silêncio digital não foi tratado
  como piso acústico.
- A escuta de uma pessoa não constitui estudo perceptual formal.

### Conclusões permitidas

- O caminho HyperX -> DSP -> ponte -> endpoint -> cliente externo funciona.
- A UI e o stop permaneceram operacionais por mais de dez minutos.
- A STFT congelada produziu redução mensurável de ruído marrom neste cenário.
- O protótipo é reproduzível na VM e preserva privacidade dos WAVs.

### Conclusões não permitidas

- Não declarar baixa latência física ponta a ponta.
- Não declarar qualidade perceptual suficiente para demonstração final.
- Não atribuir todos os pipocos exclusivamente ao DSP: os contadores mostram
  forte contribuição do transporte, com underruns e descartes.
- Não extrapolar as notas de um avaliador para eficácia estatística.
- Não confundir protótipo acadêmico com produto distribuível.

### Decisão auditada

Classificação: **Protótipo funcional, com validação perceptual pendente**.

A conectividade e a operação estão aprovadas. A qualidade processada permanece
pendente porque os artefatos são severos, apesar da inteligibilidade,
naturalidade e redução objetiva moderada.

## Checkpoint 37 - limite da evidência

### Evidência válida

- detector objetivo e testes sintéticos foram implementados;
- a fonte determinística contínua foi executada sem conteúdo privado;
- a VM enumerou a entrada WASAPI esperada;
- houve timeouts reproduzíveis antes da geração de WAVs ou métricas acústicas;
- o bloqueio do Guest Control foi observado como `starting` e
  `VERR_TIMEOUT`;
- o host e a VM foram restaurados após cada tentativa.

### Conclusões não permitidas

- não atribuir os pipocos à captura, ao DSP, à ponte, ao endpoint ou à
  reprodução;
- não comparar polling de 10 ms e 2 ms sem WAVs e contadores completos;
- não declarar mitigação aprovada;
- não promover a classificação do protótipo;
- não usar os timeouts de orquestração como medida de qualidade de áudio.

### Decisão auditada

O Checkpoint 37 não atingiu os critérios de conclusão. A instrumentação está
pronta, mas a matriz deve ser repetida por uma sessão interativa estável da
VM. A classificação permanece **Protótipo funcional, com validação
perceptual pendente**.

## Checkpoint 37 - matriz interativa concluída

### Evidência válida

- A captura bruta e as saídas pré-ponte de bypass e STFT não apresentaram
  falhas objetivas de continuidade.
- A STFT pré-ponte permaneceu abaixo do orçamento de 20 ms em todos os blocos.
- Os defeitos apareceram primeiro no endpoint após a ponte.
- No bypass, polling de 2 ms reduziu:
  - descartes locais de 97 para 26;
  - underruns de 17 para 5;
  - zeros excedentes no endpoint de 90 para 22.
- Todos os cenários mantiveram zero overruns, zero erros de escrita e zero
  erros de sequência.

### Limites

- Os 200 blocos silenciosos de margem decorrem do capturador de 16 s envolvendo
  o produtor de 12 s e não são classificados como falha.
- A comparação STFT 10 ms versus 2 ms teve somente uma repetição por condição.
- Polling de 2 ms melhorou fortemente o bypass, mas não produziu resultado
  monotônico na STFT.
- Não houve retorno ao HyperX nem nova escuta perceptual nesta retomada.

### Decisão auditada

- É permitido localizar a fronteira dominante depois da saída pré-ponte, no
  transporte/consumo do endpoint.
- É permitido afirmar correlação entre descartes, underruns e silêncio
  adicional no WAV do endpoint.
- Polling de 2 ms pode ser descrito como mitigação promissora, não como novo
  padrão aprovado.
- Não é permitido atribuir os pipocos principalmente à STFT.
- A classificação permanece **Protótipo funcional, com validação perceptual
  pendente**.

## Checkpoint 38 - repetição e limite perceptual

### Evidência válida

- Três pares longos confirmaram melhoria consistente de 2 ms sobre 10 ms.
- Descartes locais caíram de 95 para 20 no agregado.
- Underruns caíram de 72 para 54.
- Zeros excedentes caíram de 97 para 25.
- No retorno ao HyperX, não houve pipocos no bruto nem no processado.
- O DSP permaneceu dentro do orçamento de 20 ms.
- Não houve overrun, erro de escrita ou erro de sequência.

### Limites

- O processado continuou não preferido.
- Foram percebidos chiado, mais ruído de fundo e artefatos de início/fim.
- A escuta foi realizada por uma pessoa e não possui validade estatística.
- O alinhamento por envelope não mede latência física.

### Decisão auditada

- É permitido adotar 2 ms nos próximos ensaios do capturador de diagnóstico.
- É permitido afirmar que a mitigação eliminou os pipocos nesta tomada.
- Não é permitido afirmar que a qualidade processada está aprovada.
- Não é permitido atribuir chiado e travamentos de borda a uma causa única
  antes de nova matriz objetiva.
- A classificação permanece **Protótipo funcional, com validação perceptual
  pendente**.

## Checkpoint 39 - localização do chiado e das bordas

### Evidência válida

- Três pares determinísticos preservaram os parâmetros congelados.
- O pré-bridge STFT reduziu energia de alta frequência e piso total.
- O aumento de alta frequência e de piso apareceu no endpoint, depois do
  pré-bridge.
- A tomada privada existente mostrou deslocamento temporal relevante entre A
  e B nas bordas.
- O corte comum e o fade foram aplicados apenas a cópias privadas para escuta.
- A matriz foi concluída antes da falha de fechamento do Guest Control.

### Limites

- A matriz mostra elevação agregada depois do pré-bridge, mas não localiza a
  fronteira causal do chiado durante fala.
- O transporte continuou variável, com descartes e underruns; os valores
  espectrais do endpoint não devem ser tratados como resposta de frequência
  do driver.
- O alinhamento por envelope não mede latência física.
- Corte e fade não podem substituir as métricas dos arquivos originais.
- A confirmação humana mostrou que o corte remove o travamento, mas não o
  chiado durante a fala. O fade não trouxe benefício adicional.

### Decisão auditada

- É permitido afirmar que o pré-bridge reduziu piso e alta frequência nas
  métricas agregadas da fonte determinística.
- Não é permitido concluir que o chiado durante fala nasce depois do
  pré-bridge: a métrica anterior avaliou janelas de ruído e o alinhamento
  global é inadequado diante de perdas não uniformes.
- A fronteira causal do chiado permanece aberta entre `musical noise` do DSP,
  drops/underruns, endpoint e captura externa.
- É permitido atribuir a maior parte dos travamentos de borda ao deslocamento
  assíncrono e ao transporte/preparo do par.
- É permitido dispensar o fade na preparação dos próximos pares.
- É permitido tratar o chiado como persistente em regime ativo.
- Não é permitido declarar a ponte ou o driver como causa única.
- A classificação permanece **Protótipo funcional, com validação perceptual
  pendente**.

## Checkpoint 40 - separacao causal por blocos

### Evidencia valida

- A fonte deterministica tornou cada bloco de ruido ou atividade recuperavel
  por indice.
- As listas de blocos enviados e descartados foram publicadas diretamente
  pela ponte.
- A comparacao amostra a amostra foi restrita a correspondencias com
  correlacao maior ou igual a `0,985`.
- Nos blocos preservados, endpoint e pre-bridge foram equivalentes dentro do
  erro de quantizacao/captura.
- A STFT criou mais picos tonais durante atividade antes da ponte.
- Lacunas e zeros adicionais acompanharam perdas e underruns.
- `drop-newest` foi testado isoladamente e rejeitado pelos criterios
  predefinidos.

### Limites

- A taxa de recuperacao cai em rodadas com muitos underruns; blocos nao
  recuperados nao participam da comparacao amostra a amostra.
- A fonte sintetica nao substitui fala humana para avaliacao de chiado.
- Flatness e densidade tonal indicam estrutura espectral, mas nao provam
  sozinhas qual componente sera percebida como chiado.
- A escuta foi feita por uma pessoa e nao constitui estudo perceptual formal.
- O agravamento em C foi perceptualmente claro, mas ainda nao foi separado
  entre lacunas, endpoint e capturador externo.

### Decisao auditada

- E permitido afirmar que o endpoint nao altera materialmente os blocos que
  chegam preservados.
- E permitido afirmar que o transporte introduz perdas e lacunas.
- E permitido afirmar que a STFT cria estrutura tonal adicional antes da
  ponte, compativel com `musical noise`.
- A escuta confirmou chiado metalizado leve no pre-bridge durante fala e
  intensidade consideravelmente maior no endpoint.
- E permitido localizar a origem do artefato no DSP e afirmar agravamento
  perceptual no caminho posterior.
- Nao e permitido atribuir o agravamento a alteracao espectral dos blocos
  preservados, pois eles permaneceram equivalentes.
- Nao e permitido escolher entre lacunas, endpoint e capturador externo sem
  novo ensaio que os separe.
- `drop-newest` nao deve substituir o baseline.
- A classificacao permanece **Prototipo funcional, com validacao perceptual
  pendente**.

## Checkpoint 41 - suavizacao temporal rejeitada

### Evidencia valida

- A avaliacao reutilizou a tomada autorizada e processou o arquivo integral
  antes do corte comum.
- Baseline offline e pre-bridge congelado ficaram praticamente equivalentes.
- Quatro coeficientes da mesma familia foram comparados com parametros STFT e
  estimador congelados.
- Nenhuma variante reduziu a densidade tonal em pelo menos 10%.
- O dano de envelope, energia e banda alta cresceu com a suavizacao.

### Decisao auditada

- E permitido afirmar que esta formulacao de suavizacao temporal nao mitiga
  de forma suficiente o `musical noise` observado.
- Nao e permitido afirmar melhora perceptual, pois nenhum par atingiu o gate e
  nenhuma escuta foi solicitada.
- Nao e permitido promover a variante ao endpoint ou atribuir qualquer efeito
  ao transporte, que nao participou deste ensaio.
- O baseline realtime permanece `gain_smoothing=0.0`.
- O proximo checkpoint pode comparar o Wiener causal existente como mudanca
  de metodo.

## Checkpoint 42 - Wiener causal rejeitado

### Evidencia valida

- A avaliacao reutilizou exatamente a tomada, o corte, o estado causal e a
  deteccao de atividade dos checkpoints anteriores.
- Apenas o piso Wiener variou dentro de uma faixa conservadora.
- Todos os pisos melhoraram flatness e preservaram envelope e energia.
- A reducao tonal maxima foi `2.13%`, muito abaixo do gate de 10%.
- A VM confirmou execucao deterministica do Wiener sem captura de audio.

### Limites e decisao auditada

- E permitido afirmar que o Wiener testado altera menos a tomada que o
  baseline e produz espectro ligeiramente mais plano.
- Nao e permitido afirmar mitigacao suficiente do `musical noise`, pois a
  densidade tonal caiu menos de 2.2%.
- Nao e permitido afirmar melhora perceptual, pois nenhum par foi criado e
  nenhuma escuta foi solicitada.
- Nao e permitido promover o Wiener ao endpoint com base neste ensaio.
- A divergencia da assinatura `gain_smoothing` no app persistente deve ser
  mantida visivel; ela nao invalida o Wiener nem as metricas offline.
- A classificacao permanece **Prototipo funcional, com validacao perceptual
  pendente**.

## Checkpoint 43 - Wavelet causal rejeitada

### Evidencia valida

- A avaliacao usou o caminho causal `wavelet_soft` existente no realtime.
- Somente o nivel variou; familia, modo, estrategia e escala permaneceram
  congelados.
- A reducao tonal maxima foi `8.34%`.
- A banda de 4-8 kHz perdeu aproximadamente `10.5 dB` adicionais em todos os
  niveis.
- A VM confirmou saida finita e deterministica apos o saneamento realtime.

### Limites e decisao auditada

- E permitido afirmar que a Wavelet escala 1.0 reduz mais picos que a
  suavizacao e o Wiener testados.
- Nao e permitido tratar essa reducao como melhora, pois ela veio acompanhada
  de perda severa de alta frequencia e nao atingiu o gate tonal.
- Nao e permitido solicitar escuta ou promover o metodo ao endpoint.
- O aviso numerico do PyWavelets deve permanecer documentado, embora nenhum
  nao finito tenha escapado do processador realtime.
- Uma proxima avaliacao pode variar somente a escala do limiar abaixo de 1.0,
  sem implantar o parametro antes de existir candidato objetivo.
- A classificacao permanece **Prototipo funcional, com validacao perceptual
  pendente**.

## Checkpoint 44 - escala Wavelet sem compromisso util

### Evidencia valida

- Somente `wavelet_threshold_scale` variou.
- A escala `0.50` ultrapassou o gate tonal por margem pequena.
- Essa mesma escala removeu `7.64 dB` adicionais em 4-8 kHz e `2.42 dB` em
  2-4 kHz.
- Escalas menores preservaram mais espectro, mas ficaram abaixo do gate tonal.
- Nenhuma configuracao foi implantada no app.

### Limites e decisao auditada

- E permitido afirmar que o shrinkage DWT global apresenta compromisso
  desfavoravel entre reducao tonal e abafamento nesta tomada.
- Nao e permitido afirmar melhora perceptual para a escala `0.50`.
- Nao e permitido preparar par, promover ao endpoint ou expor o parametro.
- A WPT em quadros existente nao pode ser usada como proximo candidato causal:
  ela observa todos os quadros antes de calcular os ganhos.
- Qualquer continuidade WPT deve primeiro implementar estado causal explicito
  e provar independencia do futuro com vetores sinteticos.
- A classificacao permanece **Prototipo funcional, com validacao perceptual
  pendente**.

## Checkpoint 45 - WPT causal apta a escuta

### Evidencia valida

- A implementacao tem estado limitado e nao observa amostras futuras.
- Prefixos identicos produzem saidas identicas diante de futuros diferentes.
- Reset reproduz a saida bit a bit.
- Host e VM ficaram abaixo do orcamento de 20 ms.
- A configuracao foi congelada antes do primeiro uso da tomada privada.
- A reducao tonal privada foi `11.72%`, sem perda relevante de banda alta.

### Decisao auditada

- E permitido chamar esta implementacao de causal.
- E permitido preparar um unico par perceptual pre-bridge.
- Nao e permitido ainda afirmar melhora perceptual.
- Nao e permitido integrar ao app, ponte ou endpoint antes da escuta.
- Se a escuta rejeitar a WPT, a trilha DSP deve ser encerrada.

## Checkpoint 46 - WPT rejeitada perceptualmente

### Evidencia

- Um unico par privado foi gerado a partir da tomada integral autorizada.
- O baseline e a WPT foram processados integralmente antes da aplicacao do
  corte comum de 16,86 s.
- Formato dos dois arquivos: mono PCM16, 16 kHz, 269.760 amostras.
- Nao houve fade, normalizacao, nova gravacao ou copia de WAV ao repositorio.
- Hash baseline:
  `8e959dcc22566872464b2ac5a7f7baa2060cd6156f37eeabbd35a0ed50217422`.
- Hash WPT:
  `1143240aa5bcfa8ab0eb06045f289ce20c5ee263e5ae171f32c9f063c007d325`.
- O preparador e os testes causais focados passaram: `9 passed`.

### Resultado humano

- O baseline `A` foi escolhido para inteligibilidade.
- O baseline `A` foi escolhido para naturalidade.
- O baseline `A` apresentou menor chiado metalizado.
- O baseline `A` foi a preferencia geral.
- A decisao explicita foi rejeitar a WPT `B`.

### Decisao auditada

- Nao e permitido afirmar melhoria perceptual da WPT causal.
- A reducao objetiva de picos tonais deve ser reportada como resultado
  instrumental que nao se confirmou na escuta.
- Nao houve integracao ao app, ponte ou endpoint.
- O Checkpoint 47 foi cancelado.
- A trilha de melhoria DSP esta encerrada para este prototipo.
- O baseline permanece somente como demonstrador funcional, com limitacao
  perceptual explicita.

## Checkpoint 46-R - Escopo reaberto sem apagar a rejeicao

### Evidencia preservada

- A WPT causal continua rejeitada pelo resultado perceptual 4-0.
- Nenhuma afirmacao de melhoria WPT foi restaurada.
- Nenhuma integracao WPT foi autorizada.

### Nova hipotese

- O caminho reaberto investiga somente a STFT causal.
- O primeiro ensaio separa estimador, piso da subtracao e lei Wiener em seis
  configuracoes.
- A consulta ao Claude Code foi revisada criticamente; recomendacoes
  tecnicamente inconsistentes nao foram aceitas.

### Limites

- Nao executar uma grade ampla antes do ensaio discriminante.
- Nao usar spectral flatness isoladamente como proxy de qualidade perceptual.
- Nao exigir aumento simultaneo de SNR e SI-SDR como condicao de escuta.
- Nao reutilizar voz privada antes de congelar os candidatos.
- Nao iniciar integracao ou endpoint antes de aprovacao perceptual.

### Resultado auditado do ensaio publico

- Seis configuracoes causais foram avaliadas em 72 condicoes de validacao.
- O split final nao participou da selecao.
- Nenhum desafiante passou todos os gates predefinidos.
- O resultado `stop_no_public_candidate` deve ser preservado.
- Nao e permitido promover `E1-W05` nesta rodada: apesar da reducao tonal e
  melhor envelope, ele perdeu SI-SDR alem do limite predefinido.
- Relaxar o gate depois de observar esse resultado seria selecao post-hoc.
- A VM e o audio privado permaneceram fora da rodada.
- Uma nova investigacao de Wiener exige protocolo separado e pre-registrado.

## Checkpoint 46-R/LIT - Auditoria do harness de literatura

### Escopo

- Protocolo novo, sem reinterpretar o resultado
  `stop_no_public_candidate`.
- Corpus publico congelado e mesmas 72 misturas de validacao.
- Somente o baseline foi executado neste incremento.
- Nenhum WAV, audio privado, endpoint ou VM foi usado.

### Reprodutibilidade

- Cada mistura recebeu hash SHA-256 sobre `float32` little-endian.
- O registry registra versao, revisao, licenca, taxa nativa, framing,
  causalidade e backend.
- O split final operacional e recusado pela CLI sem `--allow-final`.
- Sistemas ainda nao implementados sao recusados, em vez de produzirem
  resultados parciais silenciosos.

### Resultado

- As diferencas contra o `E0-S02` anterior foram exatamente zero em:
  - melhoria media e minima de SNR;
  - fracao de degradacoes;
  - melhoria media de SI-SDR;
  - densidade tonal;
  - spectral flatness;
  - distancia log-espectral;
  - correlacao de envelope.
- Com `pystoi 0.4.1`, o STOI medio caiu de `0,94269` na mistura para
  `0,92450` na saida do baseline, variacao de `-0,01819`.
- Essa divergencia em relacao a SNR/SI-SDR deve permanecer visivel e nao pode
  ser usada isoladamente para aprovar ou rejeitar um sistema.
- Memoria de estado observada: `60.900 bytes`.
- Latencia algoritmica declarada do baseline: `32 ms`.

### Limites

- Pico de working set ainda nao foi medido para o baseline.
- Atraso por impulso ainda nao foi implementado.
- WebRTC APM e DeepFilterNet ainda nao foram executados.
- Nao existe candidato, ranking ou autorizacao para split final, audio privado
  ou VM.

### Auditoria OM-LSA + IMCRA

- Implementacao baseada nas publicacoes originais, sem codigo de terceiros.
- Parametros congelados antes da matriz:
  - 16 kHz, Hamming 512/128;
  - decisao dirigida 0,92;
  - IMCRA `D=120`, `V=15`, `U=8`;
  - `alpha_s=0,9`, `alpha_d=0,85`, `beta=1,47`;
  - ganho hipotetico de ausencia `Gmin=-25 dB`.
- A matriz usou os mesmos hashes de mistura do baseline.
- Foram observados:
  - `+0,8985 dB` de SNR;
  - `+0,8506 dB` de SI-SDR;
  - `-0,00499` de STOI;
  - densidade tonal `11,5774`;
  - envelope `0,96008`;
  - RTF `0,0716`;
  - zero degradacoes de SNR.
- O metodo nao supera o baseline em supressao objetiva.
- O metodo preserva melhor STOI e envelope na media.
- A reducao tonal agregada nao e uniforme: `OOFFICE` piorou.
- Nao e permitido promover OM-LSA/IMCRA antes de medir os demais sistemas e
  aplicar o protocolo multicriterio completo.
- A primeira implementacao aplicava `Gmin` como clipping do ganho condicional
  e final, o que contraria a Eq. 16, e mantinha uma subjanela excedente.
- Os resultados anteriores foram substituidos depois da correcao; eles nao
  devem ser citados.

### Auditoria RNNoise 0.2

- Codigo e modelo foram obtidos de fontes oficiais e mantidos fora do
  repositorio.
- Commit, modelo, arquivo baixado e executavel foram hashados.
- O wrapper usa a API C oficial e escala `float32 [-1,1]` para a amplitude
  PCM esperada.
- O modo binario de stdin/stdout e obrigatorio no Windows; o gate detectou a
  falha antes de qualquer resultado oficial.
- O atraso por impulso foi `20 ms` e permanece registrado separadamente do
  alinhamento usado nas metricas pareadas.
- Resultado:
  - SNR `+9,3893 dB`;
  - SI-SDR `+9,3925 dB`;
  - STOI `-0,00769`;
  - envelope `0,79418`;
  - banda 4-8 kHz `-14,0928 dB`;
  - densidade tonal `18,2612`;
  - RTF end-to-end `0,0247`;
  - pico de working set `9,39 MB`.
- E permitido afirmar supressao objetiva forte neste corpus.
- Nao e permitido afirmar melhor inteligibilidade ou naturalidade.
- A queda de STOI em `63,89%`, a baixa preservacao de envelope e a forte
  atenuacao de alta frequencia devem permanecer visiveis.
- RNNoise nao pode ser congelado como finalista antes de WebRTC APM e
  DeepFilterNet.
- A revisao Claude posterior as 17h nao concluiu: as chamadas com e sem Chrome
  expiraram sem resposta. Nao existe parecer externo aprovando OM-LSA/IMCRA ou
  RNNoise nesta etapa.

### Auditoria WebRTC APM Noise Suppression

- Fonte oficial fixada no commit
  `eb79ac6e330baa0a6d26c53d522f9ed57495edb7`, licenca BSD-3-Clause.
- O adaptador usa `BuiltinAudioProcessingBuilder`, API float mono de 16 kHz e
  somente Noise Suppression habilitado.
- O nivel congelado e o padrao da API, `moderate`; nao houve varredura de
  niveis. O ensaio preliminar em `high` nao integra o resultado oficial.
- A janela interna e 256 amostras, com quadro de 160 e atraso estrutural de
  96 amostras. O atraso de `6 ms` foi confirmado por impulso e compensado
  somente nas metricas pareadas.
- O executavel final tem SHA-256
  `D2FCB649518676BC0BD5951F1392F6BEB27023CEE97F5648D79AB5A572EB889C`.
- Resultado nas 72 condicoes:
  - SNR `-3,5039 dB`;
  - SI-SDR `-14,6908 dB`;
  - STOI `-0,03274`;
  - densidade tonal `11,0088`;
  - envelope `0,75281`;
  - banda 4-8 kHz `-8,1681 dB`;
  - RTF end-to-end `0,0060`;
  - pico de working set `8,24 MB`.
- Houve degradacao de SNR em 53 de 72 condicoes e degradacao de SI-SDR em
  todas as 72.
- A menor densidade tonal nao compensa as perdas de SNR, SI-SDR, STOI,
  envelope e banda alta.
- WebRTC APM e rejeitado como finalista desta bateria.
- A rejeicao nao autoriza testar niveis post-hoc. Uma configuracao diferente
  exigiria protocolo novo e justificativa independente.
- DeepFilterNet permanece pendente; RNNoise e OM-LSA/IMCRA continuam medidos,
  sem promocao.
- Split final, escuta privada e VM continuam bloqueados.

### Auditoria DeepFilterNet3 e decisao de candidatos

- Codigo, wheel, modelo, checkpoint e biblioteca nativa foram fixados e
  hashados a partir da tag oficial `v0.5.6`.
- O atraso causal total e `30 ms`: 480 amostras da STFT e 960 amostras dos
  dois quadros de lookahead.
- O backend offline foi explicitamente atrasado para materializar a
  causalidade; nenhum contexto futuro foi obtido sem custo de latencia.
- Resultado:
  - SNR `+9,1978 dB`;
  - SI-SDR `+10,5105 dB`;
  - STOI `-0,06588`;
  - envelope `0,75312`;
  - banda 4-8 kHz `-23,2995 dB`;
  - densidade tonal `17,1685`;
  - RTF de inferencia `0,1087`;
  - pico de memoria `255,10 MB`.
- DeepFilterNet melhora SI-SDR mais que RNNoise, mas e inferior em SNR, STOI,
  envelope, preservacao de bandas, latencia, velocidade e memoria.
- Houve seis degradacoes de SNR, contra zero no RNNoise.
- DeepFilterNet e rejeitado nesta bateria.
- Fronteira de Pareto congelada, sem escore agregado:
  - `rnnoise`, pela supressao forte;
  - `omlsa_imcra`, pela preservacao de envelope/STOI e menor tonalidade.
- `baseline_stft` permanece referencia obrigatoria na proxima comparacao.
- A selecao respeita o limite de dois finalistas e foi registrada antes do
  split final.
- Claude nao foi acionado: fontes oficiais, testes de impulso e dominancia
  multicriterio foram suficientes.

### Confirmacao no split final operacional

- O split foi aberto somente depois de gravar `candidate_decision.json`.
- Participaram baseline, RNNoise e OM-LSA/IMCRA; nenhum sistema rejeitado foi
  reintroduzido.
- RNNoise manteve vantagem de supressao e apresentou STOI medio `+0,01817`.
- OM-LSA/IMCRA manteve a maior correlacao de envelope (`0,94767`) e a menor
  atenuacao de bandas entre os finalistas.
- Nao houve degradacao de SNR em nenhum dos tres sistemas.
- A estabilidade entre validacao e final confirma os dois finalistas, mas nao
  autoriza integracao.
- A proxima decisao depende de escuta privada cega. Endpoint e VM permanecem
  fora do ensaio.

### Preparacao da escuta privada

- Fonte: tomada autorizada do Checkpoint 38, hash
  `BA9C2D1307C19844894B5659AEECF298450394A8439542C044B1DA932B617E80`.
- O trio contem exatamente baseline, RNNoise e OM-LSA/IMCRA em ordem
  aleatoria.
- Todos os arquivos usam o mesmo corte, comprimento, taxa e formato.
- Nao houve normalizacao ou fade que pudesse mascarar diferencas de nivel ou
  artefatos.
- O mapeamento cego permanece somente na area privada.
- Nenhuma decisao humana foi preenchida ou inferida.
- A integracao continua proibida ate a escuta registrar inteligibilidade,
  naturalidade, ruido residual, artefatos e preferencia.

### Resultado perceptual cego

- A chave foi aberta somente depois do formulario estar completo e coerente.
- Mapeamento: `A=baseline`, `B=RNNoise`, `C=OM-LSA/IMCRA`.
- O RNNoise foi escolhido sem conhecimento previo do rotulo.
- O baseline ficou em ultimo e foi descrito como metalizado, com chiado
  durante a fala.
- RNNoise e OM-LSA/IMCRA receberam inteligibilidade e naturalidade maximas.
- RNNoise ficou em primeiro; OM-LSA/IMCRA ficou em segundo e muito proximo.
- Nao houve relato de clipping ou dropouts em nenhum sistema.
- A escuta resolve a divergencia entre as metricas:
  - a baixa correlacao de envelope e a atenuacao de banda alta do RNNoise nao
    impediram preferencia nesta tomada;
  - os ganhos objetivos do RNNoise se converteram em melhoria perceptual;
  - o baseline, apesar de envelope objetivo superior, manteve o chiado
    metalizado percebido.
- RNNoise esta aprovado para integracao incremental.
- Isso nao autoriza alterar o driver ou iniciar diretamente a VM: primeiro
  deve passar por framing, resampling, continuidade, latencia e RTF no host.

## Checkpoint 46-R/INT-HOST - auditoria da integracao RNNoise

### Evidencia valida

- O caminho realtime usa a API oficial RNNoise em DLL, no mesmo processo.
- O estado e criado uma vez e preservado entre blocos.
- Cada bloco de 320 amostras a 16 kHz gera exatamente 960 amostras nativas e
  dois frames RNNoise.
- Os resamplers FIR mantem estado continuo e nao reinicializam por bloco.
- O wrapper C usa buffers fixos e nao aloca durante `process`.
- O atraso medido e `21,3125 ms`, incluindo RNNoise e resampling.
- Em 30.000 blocos, nenhum excedeu 20 ms; p99 foi `1,9510 ms`, pior caso
  `18,2485 ms` e o crescimento de RSS foi `225.280 bytes`.
- Determinismo, causalidade de prefixo e reset foram bit a bit.
- Nao houve descontinuidade de borda no ensaio continuo.
- A VM, a ponte e a captura fisica nao participaram do gate.

### Limites

- O ensaio prolongado foi sintetico e executado em tempo acelerado.
- O gate nao mede ainda cadencia MME, fila da ponte, endpoint ou captura
  externa com RNNoise.
- O atraso total do produto continuara incluindo entrada, filas e consumo do
  endpoint alem dos `21,3125 ms` algoritmicos.
- A DLL e um novo artefato e deve manter o hash registrado durante o primeiro
  ensaio VM.

### Decisao auditada

- E permitido avancar para um ensaio VM controlado e reversivel.
- Nao e permitido promover RNNoise a padrao definitivo antes desse ensaio.
- Nao e permitido alterar driver, protocolo PCM v1, profundidade 2 ou fila
  local 4 com base neste gate.
- OM-LSA/IMCRA permanece reserva.
- A classificacao passa a:
  **RNNoise aprovado no host pre-ponte; validacao de integracao na VM
  pendente**.

## Checkpoint 46-R/INT-VM - auditoria da integracao na VM

### Evidencia valida

- O mesmo hash da DLL aprovado no host foi verificado em cada implantacao.
- O self-test no convidado processou 3.000 blocos sem estouro do orcamento.
- O input-only RNNoise final teve p99 `1,9393 ms`, pior caso `4,0627 ms` e
  nenhum status de callback.
- Duas matrizes pareadas produziram oito cenarios deterministas.
- Em 5.882 blocos RNNoise, o p99 maximo foi `10,6945 ms`.
- Nao houve erro de escrita, overrun, rejeicao ou erro de sequencia.
- A fila do driver terminou com no maximo dois blocos pendentes, igual a
  profundidade alvo.
- O clone foi revertido ao snapshot 45; a VM original e o endpoint padrao
  permaneceram inalterados.

### Interpretacao

- Os tres blocos RNNoise acima de 20 ms ocorreram em uma unica rodada com
  pior pausa de `100,915 ms`.
- O bypass tambem apresentou pausas e forte variacao de callbacks, logo o
  pior caso isolado nao pode ser atribuido ao custo sustentado do RNNoise.
- A taxa mediana de drops locais foi menor com RNNoise.
- A taxa de underruns variou de sinal entre os pares e nao sustenta uma
  regressao causal do DSP.
- Blocos de ruido identificaveis perdem correlacao depois da supressao
  RNNoise; por isso a preservacao de ruido por correlacao nao e usada como
  gate de transporte.

### Limites

- A entrada fisica MME virtualizada nao preservou a duracao de parede.
- O controle bypass entregou 13,36 s e o RNNoise 24,72 s em janelas nominais
  de 20 s.
- O ambiente capturado estava abaixo de aproximadamente `-52 dBFS` e nao
  continha uma elocucao controlada.
- A captura valida carregamento, processamento, ponte, endpoint, fechamento e
  ausencia de clipping; ela nao valida qualidade perceptual ponta a ponta.

### Decisao auditada

- A integracao RNNoise na VM e tecnicamente aprovada.
- Driver, protocolo PCM v1, profundidade de fila e defaults permanecem
  congelados.
- RNNoise nao e promovido a default definitivo.
- O proximo gate obrigatorio e corrigir ou contornar a cadencia fisica da VM,
  seguido de fala controlada e escuta cega no endpoint.

## Checkpoint 46-R/INT-VM-CAD - auditoria da cadencia por backend

### Evidencia valida

- O probe nao usa ponte, driver ou endpoint e nao salva audio.
- Todos os callbacks mantiveram 320 amostras a 16 kHz.
- MME e DirectSound preservaram aproximadamente o total na captura pura,
  mas nao preservaram a cadencia de callbacks.
- WASAPI compartilhado com conversao explicita nao preservou o tempo.
- Nenhum backend reportou status PortAudio, mesmo diante de pausas de
  centenas de milissegundos ou segundos.
- A matriz input-only repetiu bypass e RNNoise em ordem pareada.
- O RNNoise permaneceu com p99 baixo nas duas pernas MME que divergiram em
  duracao: `2,015 ms` e `1,334 ms`.
- Uma perna DirectSound bypass teve a maior pausa observada, `3,092 s`.
- Os timestamps ADC/current do PortAudio nao foram monotonicos e nao podem
  sustentar reconstrucao temporal no convidado.

### Separacao causal das camadas

- Dispositivo de entrada e backend PortAudio:
  apresentam rajadas, pausas, sobre-entrega e subentrega.
- Callback:
  recebe sempre 320 amostras, mas em cadencia nao confiavel.
- Processamento:
  RNNoise nao explica a anomalia; bypass tambem falha e as repeticoes RNNoise
  mudam de comportamento sem aumento proporcional de custo.
- Fila local:
  ausente neste gate.
- Fila do driver:
  ausente neste gate.
- Consumo e captura do endpoint:
  ausentes neste gate.

### Limites

- O teste nao identifica ainda se a origem final e o dispositivo HDA
  virtual, o backend de audio do VirtualBox, o resampling do PortAudio ou uma
  combinacao com preempcao da VM.
- DirectSound nao pode ser chamado de estavel apenas por preservar a media;
  houve pausa multissegundo em controle bypass.
- WASAPI foi medido com conversao compartilhada, pois 16 kHz nativo foi
  recusado.
- Nao houve fala, ponte ou escuta.

### Decisao auditada

- Nenhum backend esta elegivel para o proximo gate de endpoint.
- Nao alterar driver, PCM v1, profundidade 2 ou fila local 4.
- Nao promover RNNoise a default.
- O proximo contorno deve retirar o relogio de captura da VM e entregar ao
  convidado blocos causais de 320 amostras a 50 Hz por um canal de teste
  validado.
- Somente depois de uma matriz bypass/RNNoise temporalmente valida esse canal
  podera alimentar uma captura de fala controlada e a escuta cega.

## Checkpoint 46-R/INT-VM-EXTCLK - auditoria do canal externo

### Evidencia valida

- O host foi a unica referencia de pacing, com deadlines absolutos de 20 ms.
- O protocolo de ensaio transportou exatamente 320 amostras PCM16 por pacote,
  com numero de sequencia, offset programado e CRC.
- A matriz nominal entregou 1.000 blocos em cada uma das quatro pernas.
- Os hashes provam que bypass e RNNoise receberam a mesma entrada dentro de
  cada variante.
- Duas entradas com prefixo comum e futuro divergente produziram prefixos de
  saida identicos por metodo, confirmando causalidade.
- Nao houve erro de sequencia, CRC, framing, perda ou duplicacao.
- O maior intervalo de recepcao foi `53,5155 ms`; a duracao final continuou
  exatamente 20 s.
- O RNNoise teve pior bloco de `17,7299 ms` e nenhum estouro de 20 ms.

### Separacao causal das camadas

- Dispositivo de entrada virtualizado:
  contornado; nao participa do relogio desta matriz.
- Callback PortAudio:
  ausente.
- Processamento:
  medido por bloco no convidado, separado do intervalo de recepcao.
- Fila local:
  ausente.
- Fila do driver:
  ausente.
- Consumo e captura do endpoint:
  ausentes.

### Limites

- TCP e um canal de ensaio, nao o protocolo PCM v1 do produto.
- Rajadas compensatorias ainda aparecem quando host ou convidado sao
  preemptados; o gate garante comprimento e integridade, nao jitter zero.
- Nao houve captura fisica, fala, ponte ou endpoint.
- O resultado nao autoriza promocao do RNNoise a default.
- O caminho de replay privado foi testado separadamente com silencio
  sintetico; isso valida o transporte do arquivo, nao qualidade de fala.

### Decisao auditada

- O relogio externo foi aceito para a proxima captura controlada.
- A fala deve ser capturada uma unica vez no host e reutilizada de forma
  identica em bypass e RNNoise.
- O audio deve permanecer em `C:\PTC3527-Private`.
- Ponte e endpoint somente podem ser reabertos depois desse replay pareado
  preservar comprimento, framing e causalidade.

## Checkpoint 46-R/INT-VM-ENDPOINT - auditoria do replay e endpoint

### Evidencia aceita

- A tomada controlada valida teve 1.000 blocos, 20 s, RMS `-33,60 dBFS`,
  pico `-14,16 dBFS`, zero clipping e SHA-256
  `4938B14BFA3311CFF715A569AF6A5C51C5D6930FE05DDDD472F4F7D4E237A308`.
- O replay pareado entregou exatamente essa entrada a bypass e RNNoise.
- Houve zero erro de sequencia, CRC ou framing.
- Bypass teve p99 de processamento `0,857 ms` e pior bloco `4,059 ms`.
- RNNoise teve p99 `1,729 ms` e pior bloco `4,842 ms`.
- O replay fisico, sem ponte, esta aceito.

### Evidencia rejeitada

- A captura de endpoint abriu a ponte PCM v1 sem alterar profundidade 2 ou
  fila local 4.
- O transporte TCP continuou integro e os WAVs tiveram 24 s, formato correto
  e zero clipping.
- A perna bypass enviou somente 569 de 1.000 blocos; houve 427 descartes
  locais e 4 no fechamento.
- A perna RNNoise enviou 794 de 1.000 blocos; houve 202 descartes locais e 4
  no fechamento.
- A fila do driver terminou em profundidade 2 nas duas pernas, sem overrun,
  erro de escrita, rejeicao ou erro de sequencia.
- O consumo do driver parou antes do fim em momentos diferentes, embora o
  capturador continuasse ate 24 s.

### Interpretacao e decisao

- O bypass foi materialmente pior que o RNNoise; nao e permitido atribuir a
  falha ao DSP.
- Aumentar a fila, mudar profundidade, bloquear o transporte ou aceitar
  lacunas violaria o protocolo congelado ou esconderia a distorcao temporal.
- O gate de endpoint permanece rejeitado.
- Nenhum par cego foi preparado.
- RNNoise nao e promovido a default e a escuta ponta a ponta permanece
  bloqueada.

## Checkpoint 46-R/OPS-SSD - auditoria da migracao operacional

- O clone experimental ativo permanece em
  `C:\PTC3527-VM\PTC3527-SYSVAD-LAB-FAST`.
- A VM original, seus discos e snapshots permanecem inalterados em `E:`.
- O runtime local contem apenas 137.525 bytes de entradas operacionais, mais
  o manifesto:
  - credencial SHA-256
    `14855A0CCEA5EF609B5558EF1B0F17F856024B10B37D5CE9ACCBBB64D3FB514F`;
  - configuracao de referencia SHA-256
    `BEF7E0F9FAA29E9CA832B31624EBDC9D97DB035F9961781AF83B32502E864DD6`.
- Os hashes das copias coincidem com as fontes.
- A ACL nao herda permissoes e contem somente usuario atual, `SYSTEM` e
  administradores.
- Os orquestradores ativos nao contem caminho operacional fixo para `E:`.
- A fonte externa, quando conectada, continua sendo verificada antes e depois
  do run; sua ausencia nao bloqueia o clone no SSD.
- Resultado: tres preflights aprovados, nenhuma VM iniciada e
  `150 passed`, `11 subtests passed`.
