# Avaliacao da Entrega 3 apos benchmark preliminar

Data: 2026-06-06

## Estado consolidado

O projeto avancou de forma relevante em relacao ao anteprojeto puramente metodologico. O repositorio agora contem:

- pipeline Python em `benchmark_audio/run_benchmark.py`;
- documentacao de reproducao em `README_benchmark.md`;
- registros de diario, auditoria e checkpoints em `docs/`;
- tabelas de resultados em `resultados/tabelas/`;
- figuras geradas em `resultados/figuras/`;
- exemplos curtos de audio em `resultados/audio/`;
- `entrega3.tex` atualizado com resultados preliminares e `entrega3.pdf` recompilado.

O benchmark demonstrativo usou 5 trechos de fala humana do FSDD, 4 ruidos sinteticos, SNRs de -5, 0, 5 e 10 dB e 4 metodos: ruidoso, STFT por subtracao espectral, STFT Wiener simples e Wavelet soft.

## Pontos fortes

- A comparacao foi pareada: os metodos processaram as mesmas misturas.
- O baseline ruidoso validou a metrica, pois a melhoria de SNR ficou igual a zero.
- O pipeline e reproduzivel por linha de comando.
- Os parametros principais foram registrados em `metadata_benchmark.json`.
- O relatorio agora apresenta evidencias concretas, nao apenas planejamento.
- A auditoria reconhece corretamente que os resultados sao preliminares e nao devem ser generalizados.
- A analise de viabilidade embarcada ja separa PC, Raspberry Pi, ESP32/ESP32-S3 e Arduino Uno R3.

## Limitacoes tecnicas observadas

- Os ruidos ainda sao sinteticos. Isso valida o pipeline, mas nao substitui DEMAND, VoiceBank-DEMAND ou outra base ambiental real.
- A STFT possui vantagem estrutural no benchmark atual, pois usa silencio inicial para estimativa de ruido.
- A Wavelet foi testada apenas com `db4`, nivel 5 e limiarizacao soft. Ainda falta avaliar outras familias, limiar hard, limiares por escala e ajuste em validacao.
- Nao houve separacao formal entre conjunto de validacao e conjunto final.
- STOI e PESQ ainda nao foram calculados.
- As figuras inseridas no PDF sao PNGs gerados pelo Python, o que reduz integracao tipografica, qualidade vetorial, padronizacao visual e rastreabilidade no LaTeX.

## Ajuste editorial necessario

Para este projeto, os graficos de audio, sinais, frequencia, melhoria de SNR, RTF e espectrogramas devem ser gerados nativamente no LaTeX sempre que possivel, usando `pgfplots` e `tikzpicture`, a partir de dados tabulados exportados pelo pipeline Python. O Python deve continuar responsavel por calcular sinais, metricas e matrizes numericas, mas nao deve ser a fonte final das figuras do relatorio.

O arquivo `cab.tex` ja carrega `tikz`, `pgfplots`, `newfloat` e declara o ambiente `grafico`. Portanto, a proxima etapa deve evitar recarregar pacotes ja definidos no preambulo e deve reaproveitar a configuracao existente. O padrao de listas e codigos pode seguir o exemplo de `PTC5719 - Identificacao de Sistemas/lista1/lista1.tex`, com cuidado para nao duplicar configuracoes de `caption`.

## Proximos passos tecnicos recomendados

1. Exportar dados leves para graficos nativos:
   - barras de melhoria de SNR por metodo e SNR;
   - barras ou escala logaritmica de RTF;
   - formas de onda decimadas;
   - espectrograma reduzido para matriz compativel com `pgfplots`.
2. Substituir `\includegraphics` dos PNGs por ambientes `grafico` com `tikzpicture`/`pgfplots`.
3. Inserir indice de ilustracoes com listas de figuras, tabelas, graficos e codigos.
4. Criar ambiente `codigo` caso ele ainda nao exista no preambulo carregado.
5. Incluir no PDF a descricao dos assets visuais: origem dos dados, script gerador, parametros usados e relacao com os CSVs.
6. Incluir apendice ou secao curta com codigos pertinentes, usando `\captionof{codigo}` e `\lstinputlisting` para o script principal ou trechos essenciais.
7. Avancar o benchmark com ruidos reais, preferencialmente DEMAND, e refinamento de Wavelet.

## Criterios de aceitacao da proxima etapa

- O PDF nao deve depender de PNGs de graficos para os resultados principais.
- Os graficos principais devem ser vetoriais e gerados pelo LaTeX.
- O relatorio deve ter listas de figuras, tabelas, graficos e codigos.
- A compilacao deve ser verificada apos duas passagens de LaTeX.
- O tempo de compilacao deve permanecer aceitavel; se espectrogramas nativos ficarem pesados, usar matrizes reduzidas.
- Toda conclusao deve continuar proporcional ao tamanho e as limitacoes do benchmark.
