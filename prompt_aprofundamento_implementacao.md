# Prompt para aprofundamento com implementação, benchmarks e atualização do relatório

Você é o Codex atuando como assistente técnico, científico e de implementação para dar continuidade ao projeto de formatura em PTC3527 - Anteprojeto de Formatura em Telecomunicações.

O projeto atual está descrito em `entrega3.tex` e compilado em `entrega3.pdf`. Antes de escrever código ou alterar o relatório, leia com atenção `entrega3.tex`, especialmente:

- a seção de fundamentação teórica e matemática;
- a seção 6, "Metodologia experimental proposta";
- a subseção 6.1, "Pipeline em ambiente computacional convencional";
- a seção de métricas e análise de custo computacional;
- a seção de atividades realizadas, que atualmente afirma que ainda não há resultados experimentais;
- o cronograma do segundo semestre.

## Objetivo desta etapa

Transformar o relatório de um anteprojeto essencialmente metodológico em um relatório com avanços concretos de implementação em PC, contendo scripts, dados de experimento, tabelas, gráficos, áudios processados e discussão técnica preliminar.

O objetivo não é entregar uma solução final embarcada agora. O objetivo é cumprir, em ambiente computacional convencional, o pipeline previsto na subseção 6.1 de `entrega3.tex` e deixar o caminho tecnicamente pavimentado para futura integração em Raspberry Pi, investigação em ESP32 e avaliação realista das dificuldades do Arduino Uno R3.

Ao final, o projeto deve ter algo demonstrável para apresentação: gráficos, tabelas, exemplos de áudio antes/depois, métricas comparativas e uma discussão honesta sobre viabilidade.

## Diagnóstico do estado atual

O `entrega3.tex` está bom como reformulação de escopo: ele delimita voz humana, compara Fourier/STFT e Wavelet, inclui fundamentação matemática, métricas, questionário e cronograma. Porém, ainda está predominantemente prospectivo. A seção de atividades realizadas diz que ainda não há resultados experimentais de desempenho.

Esta próxima etapa deve corrigir isso com resultados preliminares reais. O relatório atualizado não deve apenas dizer "será implementado"; ele deve dizer "foi implementado um pipeline inicial", mostrar resultados e discutir limitações.

## Escopo técnico obrigatório

Implemente, em PC, todos os itens do pipeline descrito na subseção 6.1:

1. carregar fala limpa e ruído em arquivos WAV;
2. padronizar sinais para áudio mono, taxa de amostragem de 16 kHz e amplitude normalizada;
3. selecionar trechos de duração controlada, por exemplo entre 3 s e 10 s;
4. misturar fala e ruído em níveis de SNR definidos;
5. aplicar método baseado em STFT e método baseado em Wavelet sob os mesmos sinais de entrada;
6. reconstruir os sinais processados;
7. calcular métricas, tempo de processamento e estatísticas por condição;
8. gerar formas de onda, espectrogramas, gráficos de barras e tabelas comparativas.

## Estrutura de arquivos sugerida

Crie uma estrutura simples e reprodutível, por exemplo:

- `codigo/` ou `benchmark_audio/`: scripts Python do pipeline;
- `docs/diario_tecnico.md`: registro cronológico do que foi feito, por que foi feito, comandos executados, decisões tomadas, problemas encontrados e próximos passos;
- `docs/auditoria_resultados.md`: revisão crítica dos resultados, limitações, hipóteses frágeis, possíveis fontes de erro e itens que ainda precisam ser verificados;
- `docs/checkpoints.md`: lista organizada de checkpoints do projeto, com data, estado do código, arquivos gerados, resultados principais e pendências;
- `dados/README.md`: instruções para obter ou inserir bases de áudio, sem versionar bases grandes;
- `resultados/tabelas/`: CSVs com métricas por amostra, ruído, SNR e método;
- `resultados/figuras/`: gráficos de forma de onda, espectrogramas, barras de métricas e tempo;
- `resultados/audio/`: poucos exemplos curtos de áudio ruidoso e processado para demonstração;
- `requirements.txt`: dependências mínimas;
- `README_benchmark.md`: como reproduzir os experimentos.

Evite depender apenas de notebook. Se usar notebook para exploração, também forneça scripts executáveis por linha de comando.

## Registro detalhado, auditoria e checkpoints

Não basta relatar apenas o que foi feito e apresentar resultados finais. Registre como cada parte foi feita, para que o trabalho possa ser auditado, retomado e corrigido depois.

Durante a execução:

1. mantenha um diário técnico em `docs/diario_tecnico.md`;
2. registre comandos relevantes, parâmetros, bibliotecas usadas, versões, hipóteses e decisões;
3. registre também tentativas que falharam e por que foram abandonadas;
4. sempre diferencie resultado observado, interpretação e hipótese;
5. quando gerar gráficos ou tabelas, registre qual script gerou cada arquivo;
6. quando alterar o relatório, registre quais seções foram atualizadas e quais evidências sustentam a mudança;
7. ao final de cada bloco relevante, atualize `docs/checkpoints.md`.

Depois de concluir uma etapa, faça uma auditoria crítica em `docs/auditoria_resultados.md`. Essa auditoria deve responder:

- os resultados podem ser reproduzidos do zero?
- as comparações usam exatamente as mesmas entradas?
- os parâmetros dos métodos foram registrados?
- há risco de erro na fórmula das métricas?
- há risco de comparação injusta entre STFT e Wavelet?
- algum resultado parece bom demais ou ruim demais e precisa ser investigado?
- alguma conclusão está mais forte do que os dados permitem?
- quais limitações devem aparecer explicitamente no relatório?

Se encontrar inconsistências, corrija antes de atualizar o relatório. Se não for possível corrigir, registre a limitação e não a esconda.

## Fluxo com Git e GitHub

Use Git para criar checkpoints limpos. Antes de começar, verifique se a pasta é um repositório Git. Se não for, inicialize o repositório local, configure o remoto correto e faça o primeiro commit de organização.

Fluxo recomendado:

1. configurar identidade local do Git com nome e e-mail corretos do projeto;
2. criar ou atualizar `.gitignore` para excluir arquivos temporários de LaTeX, caches Python, ambientes virtuais, bases de áudio grandes e resultados pesados que não devem ir para o GitHub;
3. fazer commits pequenos e temáticos, por exemplo:
   - `docs: registrar plano de benchmark e checkpoints`;
   - `code: adicionar pipeline de mistura e métricas`;
   - `code: implementar baselines STFT e Wavelet`;
   - `results: gerar tabelas e figuras preliminares`;
   - `tex: atualizar relatório com resultados preliminares`;
4. antes de cada commit, rodar `git status` e revisar os arquivos alterados;
5. não versionar bases de dados grandes nem arquivos sensíveis;
6. se precisar versionar arquivos de áudio de demonstração, use apenas amostras curtas, públicas ou sintéticas, e documente a origem;
7. após cada commit importante, atualizar `docs/checkpoints.md` com hash do commit, resumo e pendências.

O histórico de commits deve permitir entender a evolução do trabalho. Não faça um único commit enorme misturando código, resultados, relatório e limpeza.

## Dados de áudio

Priorize bases públicas e bem documentadas. Use amostras pequenas para manter a execução leve.

Opções aceitáveis:

- NOIZEUS, por ser uma base clássica de fala ruidosa para avaliação de speech enhancement;
- VoiceBank-DEMAND, se o download e a organização forem viáveis;
- DEMAND para ruídos ambientais;
- LibriSpeech ou Common Voice para fala limpa, se for necessário criar misturas;
- sinais de teste sintéticos apenas como fallback, nunca como única evidência principal de "voz humana".

Não colete voz própria de participantes nesta etapa. Não peça nem armazene dados pessoais. Se não for viável baixar bases automaticamente, implemente o pipeline com uma pasta de entrada documentada e inclua um modo de demonstração com amostras pequenas obtidas de fonte pública ou fornecidas localmente.

## Métodos mínimos a implementar

Implemente pelo menos:

1. **Baseline ruidoso sem processamento**, para comparação.
2. **STFT - subtração espectral**, com janela Hann, FFT de 256 ou 512 pontos, salto coerente com 10 ms a 16 ms e reconstrução por iSTFT/overlap-add.
3. **STFT - ganho espectral simples inspirado em Wiener**, se viável sem inflar o escopo.
4. **Wavelet - DWT com limiarização soft e/ou hard**, usando PyWavelets ou biblioteca equivalente, com famílias como `db4`, `sym4` ou similares.

Registre todos os parâmetros. A comparação deve ser pareada: os mesmos arquivos, ruídos e SNRs devem ser usados para todos os métodos.

## Condições experimentais mínimas

Use um experimento pequeno, mas defensável:

- pelo menos 3 a 5 trechos de fala;
- pelo menos 2 a 4 tipos de ruído;
- níveis de SNR de entrada: preferencialmente -5, 0, 5 e 10 dB;
- taxa de amostragem de 16 kHz;
- trechos de 3 s a 10 s;
- semente fixa para reprodutibilidade.

Se o tempo de execução ou download for um problema, reduza a matriz experimental, mas preserve a comparação pareada e explique a limitação.

## Métricas e medições

Calcule e salve, no mínimo:

- SNR de entrada;
- SNR de saída;
- melhoria de SNR;
- MSE;
- SI-SDR, se a implementação for simples e confiável;
- tempo total de processamento por arquivo;
- fator de tempo real, `RTF = T_proc / T_audio`;
- estimativa simples de latência algorítmica;
- estimativa aproximada de memória ou footprint por método, quando viável.

STOI e PESQ podem ser implementadas apenas se as bibliotecas e restrições práticas permitirem. Se forem citadas mas não usadas, explique por quê.

## Gráficos e tabelas obrigatórios

Gere arquivos de saída prontos para entrar no relatório e na apresentação:

1. tabela CSV com uma linha por método, amostra, ruído e SNR;
2. tabela resumida com médias por método e SNR;
3. gráfico de barras de melhoria de SNR por método;
4. gráfico de tempo de processamento ou RTF por método;
5. exemplo de forma de onda: limpa, ruidosa, STFT, Wavelet;
6. exemplo de espectrograma: limpa, ruidosa, STFT, Wavelet;
7. tabela comparativa de viabilidade para PC, Raspberry Pi, ESP32 e Arduino Uno R3.

Os gráficos devem ter título, eixos, unidades e legenda. Evite figuras decorativas. Cada figura deve servir para sustentar uma conclusão.

## Análise de viabilidade embarcada

Além do benchmark em PC, faça uma análise técnica preliminar para hardware:

- **PC:** serve como ambiente de validação e geração de referência.
- **Raspberry Pi:** deve ser tratado como primeira plataforma embarcada plausível, por ter Linux, Python/C++, memória suficiente, bibliotecas maduras e facilidade de depuração.
- **ESP32/ESP32-S3:** deve ser avaliado como etapa posterior, exigindo simplificação, buffers pequenos, C/C++, possível ponto fixo ou uso cuidadoso de ponto flutuante, e eliminação de dependências pesadas.
- **Arduino Uno R3:** investigue concretamente a dificuldade. Não diga apenas que é limitado; mostre por estimativa. Considere 2 KB de SRAM, 32 KB de flash, ausência de FPU, taxa de amostragem, tamanho de buffers, custo de FFT/DWT e armazenamento de coeficientes. A conclusão provável é que STFT/Wavelet para voz em tempo real no Uno R3 é impraticável sem simplificações severas, áudio de baixíssima taxa ou hardware externo.

Crie uma tabela com critérios como RAM, flash, ponto flutuante, áudio/I2S, bibliotecas, esforço de portabilidade, risco e recomendação.

## Atualização do relatório

Depois de implementar e gerar resultados, atualize `entrega3.tex` ou crie uma cópia versionada, por exemplo `entrega3_com_resultados.tex`, preservando a estrutura e a formatação existentes.

Atualize principalmente:

- seção de atividades realizadas e resultados obtidos;
- seção de metodologia experimental, trocando futuro por passado quando o item tiver sido implementado;
- seção de métricas, incluindo valores reais obtidos;
- cronograma, indicando o que foi antecipado do segundo semestre para esta entrega;
- riscos técnicos, incluindo dificuldades encontradas;
- considerações finais;
- referências, se novas ferramentas, bases ou métricas forem usadas.

Inclua no relatório:

- pelo menos uma tabela de resultados;
- pelo menos dois gráficos;
- breve descrição dos scripts e como reproduzir;
- discussão sobre o que os resultados preliminares indicam;
- limitações dos resultados;
- caminho claro para Raspberry Pi, ESP32 e Arduino Uno R3.

## Critérios de qualidade

Não escreva conclusões fortes a partir de poucos dados. Use linguagem como "resultado preliminar", "amostra inicial", "indício", "limitação" e "próxima etapa" quando apropriado.

Evite:

- resultados sem reprodutibilidade;
- comparar STFT e Wavelet com entradas diferentes;
- esconder parâmetros importantes;
- usar gráficos sem unidades ou legenda;
- tratar Arduino Uno R3 de forma superficial;
- transformar a parte embarcada em promessa de protótipo completo imediato.

Prefira:

- scripts simples, legíveis e executáveis;
- tabelas CSV que possam ser verificadas;
- figuras geradas automaticamente;
- poucas amostras bem controladas;
- discussão técnica honesta sobre trade-offs;
- separação clara entre resultado obtido em PC e viabilidade futura em hardware.

## Verificação final

Antes de finalizar:

1. rode o pipeline de ponta a ponta;
2. confirme que os CSVs foram gerados;
3. confirme que as figuras foram geradas;
4. confirme que há ao menos alguns arquivos de áudio de exemplo;
5. atualize `docs/diario_tecnico.md`, `docs/auditoria_resultados.md` e `docs/checkpoints.md`;
6. revise `git status` e faça commit temático do checkpoint concluído;
7. compile o LaTeX atualizado;
8. abra ou verifique o PDF resultante;
9. relate no final o que foi implementado, onde estão os resultados, quais comandos reproduzem o benchmark, qual commit/checkpoint marca o estado atual e quais limitações permanecem.

O resultado ideal desta etapa é que a apresentação do projeto deixe de mostrar apenas planejamento e passe a mostrar evidências concretas: sinais processados, gráficos, tabelas, medição de tempo real e uma análise madura sobre o caminho para embarcados.
