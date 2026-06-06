# Prompt para construção do segundo relatório

Você é um assistente acadêmico e técnico ajudando a redigir a terceira entrega da disciplina PTC3527 - Anteprojeto de Formatura em Telecomunicações, que consiste na construção do segundo relatório do anteprojeto.

O projeto é desenvolvido por Augusto Massayoshi Yojo de Lima (№USP 12487121); Gabriel Almeida Mathias (№USP 14543284) e
Lucas Galvão de França (№USP 4784490) (integrado ao time a pedido do professor), sob orientação do professor Juan Luis Poletti Soto.

## Contexto principal

O tema anterior era amplo demais: revisão sistemática da literatura sobre redução de ruído de sinais unidimensionais no tempo. Após feedback do professor e discussões internas, o escopo deve ser reformulado para algo mais delimitado, defensável e tecnicamente progressivo:

**redução de ruído local em tempo real para voz humana, com análise comparativa entre Transformada de Fourier/STFT e Transformada Wavelet, visando futura execução em sistemas embarcados.**

Nesta etapa do anteprojeto, o foco não deve ser prometer um protótipo embarcado completo. A estratégia correta é:

1. desenvolver e validar o pipeline em ambiente convencional, como Windows ou Linux;
2. comparar abordagens de processamento de sinais, especialmente Fourier/STFT e Wavelet, aplicadas a voz humana ruidosa;
3. produzir métricas, gráficos, benchmarks e discussão técnica;
4. avaliar viabilidade para tempo real e sistemas embarcados;
5. deixar a integração em hardware para o próximo semestre, começando preferencialmente por Raspberry Pi;
6. considerar ESP32 como etapa posterior;
7. deixar Arduino Uno R3 apenas como possibilidade de trabalhos futuros, devido a limitações de hardware, ponto flutuante, bibliotecas, memória e custo de implementação.

Não assumir mais compromisso com PIBITI. O arquivo `dossie_tecnico_pibiti.pdf` pode ser usado apenas como insumo técnico para entender a reformulação do tema, mas o relatório não deve ser escrito como proposta PIBITI, não deve prometer bolsa, edital, submissão ou obrigações de iniciação tecnológica.

## Arquivos a considerar

Leia e use criticamente os seguintes arquivos do projeto:

- `entrega2.pdf` e/ou `entrega2.tex`: primeiro relatório/segunda entrega, com estrutura, linguagem, objetivos anteriores, cronograma, referências e questionário original.
- `Anteprojeto_reformulado.pdf`: reformulação do tema, mudança de escopo e direcionamento para voz, tempo real e embarcados.
- `questionario_extensionista_pibiti.pdf` e/ou `pibiti/questionario_extensionista_pibiti.tex`: questionário reformulado, que deve servir como ponto de partida, mas precisa ser refinado.
- `dossie_tecnico_pibiti.pdf` e/ou `pibiti/dossie_tecnico_pibiti.tex`: usar apenas como dossiê técnico, filtrando tudo que for específico de PIBITI.
- `roteiro_apresentacao_entrega2.md`: usar para preservar continuidade narrativa, mas atualizar o escopo.

## Feedback recebido

O professor avaliou o questionário anterior com a seguinte crítica central:

O público-alvo e as perguntas sofriam do mesmo problema do tema: escopo excessivamente amplo. Com uma definição melhor do tipo de sinal a ser trabalhado para mitigação do ruído, seria mais simples definir tanto o público-alvo quanto as perguntas. Apesar disso, várias perguntas eram razoáveis, e a formatação/apresentação do questionário estavam boas.

Portanto, o novo relatório deve mostrar que o grupo entendeu a crítica e respondeu a ela:

- abandonar a abrangência genérica de sinais 1D;
- concentrar o trabalho em voz humana;
- tornar o questionário mais útil para levantar requisitos reais de aplicações de voz;
- evitar perguntas retóricas, óbvias ou que dificilmente gerem informação acionável;
- explicar que a mudança de escopo é uma evolução técnica do anteprojeto, não uma ruptura desorganizada.

## Entrega esperada

Produza um segundo relatório completo, em português acadêmico, claro e sóbrio, seguindo as orientações da disciplina. O relatório deve conter:

1. Título do projeto.
2. Orientador.
3. Resumo e objetivos do projeto.
4. Atividades realizadas e resultados obtidos nesta fase.
5. Avaliação e andamento do projeto, considerado o cronograma proposto, com justificativas de eventuais desvios.
6. Cronograma detalhado para o segundo semestre.

Além desses itens obrigatórios, inclua quando fizer sentido:

- contextualização da reformulação do escopo;
- comparação entre o escopo antigo e o novo;
- metodologia proposta para comparação Fourier/STFT versus Wavelet;
- fundamentação matemática suficiente para explicar por que cada abordagem faz sentido para voz ruidosa;
- critérios de avaliação: qualidade da redução de ruído, SNR, custo computacional, uso de memória, latência e viabilidade embarcada;
- papel do questionário extensionista como levantamento de requisitos;
- plano para geração de gráficos, tabelas e resultados experimentais;
- riscos técnicos e estratégias de mitigação.

## Direção técnica desejada

O relatório deve apresentar o projeto como uma sequência progressiva:

No primeiro momento, será implementado em PC um pipeline de redução de ruído para voz humana. Esse pipeline deve permitir carregar amostras de áudio, adicionar ou selecionar ruídos, aplicar métodos baseados em Fourier/STFT e Wavelet, reconstruir o sinal, calcular métricas e gerar gráficos comparativos.

Depois, será avaliada a viabilidade de tempo real, considerando tamanho de janelas, buffers, custo computacional, memória e latência.

No próximo semestre, o método mais promissor poderá ser levado para hardware embarcado. A plataforma inicial recomendada é Raspberry Pi, pois oferece Linux, bibliotecas maduras de áudio, maior memória e melhor facilidade de depuração. O ESP32 pode aparecer como etapa posterior, caso o pipeline esteja suficientemente simples e otimizado. O Arduino Uno R3 deve aparecer apenas como limitação ou trabalho futuro.

Evite prometer implementação completa em Raspberry Pi, ESP32 e Arduino ainda nesta etapa. O tom deve ser realista: primeiro benchmark algorítmico, depois integração embarcada.

## Como conduzir a construção do relatório

Não escreva o relatório de forma superficial. Antes de redigir a versão final, conduza o trabalho em etapas e deixe essas etapas refletidas no texto. O relatório deve demonstrar que o grupo sabe o que pretende implementar, por que as técnicas escolhidas são pertinentes e como a comparação será feita.

Siga esta estratégia:

1. **Leitura crítica do material existente.** Identifique o que deve ser preservado da `entrega2` e o que deve ser reformulado. Preserve a continuidade da disciplina, mas reescreva objetivos, problema, metodologia, questionário e cronograma para o foco em voz humana.
2. **Delimitação científica do problema.** Modele explicitamente o sinal observado como fala contaminada por ruído, por exemplo \(y[n] = x[n] + r[n]\), em que \(x[n]\) representa a fala limpa e \(r[n]\) o ruído. Explique que o objetivo não é "remover todo ruído", mas estimar uma versão de \(x[n]\) que preserve inteligibilidade e naturalidade com custo computacional viável.
3. **Fundamentação matemática da abordagem por Fourier/STFT.** Apresente a ideia de análise tempo-frequência por janelamento, STFT, espectrograma, estimativa de magnitude, preservação ou limitação da fase ruidosa, reconstrução por overlap-add e relação com métodos como subtração espectral e filtragem de Wiener. Inclua equações essenciais, mas sem transformar o relatório em apostila.
4. **Fundamentação matemática da abordagem por Wavelet.** Explique por que wavelets podem ser relevantes para sinais não estacionários, transientes e estruturas localizadas no tempo. Apresente decomposição multirresolução, coeficientes de aproximação e detalhe, escolha de família wavelet, níveis de decomposição e limiarização hard/soft. Use o estudo de "Ondas e Ondaletas", do professor Pedro A. Morettin, como uma das bases conceituais para amadurecer essa parte.
5. **Definição do protocolo experimental.** Especifique como serão escolhidas amostras de voz, ruídos, níveis de SNR, taxa de amostragem, duração dos trechos, normalização, repetições e controle de variáveis. O texto deve deixar claro que Fourier/STFT e Wavelet serão avaliadas sob as mesmas condições.
6. **Definição das métricas.** Use pelo menos métricas objetivas simples e reprodutíveis, como SNR de entrada/saída, melhoria de SNR, erro quadrático médio ou SI-SDR quando adequado. Se forem citadas métricas perceptuais como STOI ou PESQ, explique limitações, dependência de referência limpa e possíveis restrições de uso.
7. **Análise de custo computacional.** Defina como medir tempo de processamento, fator de tempo real, uso de memória aproximado, tamanho de janela, sobreposição, latência algorítmica e complexidade qualitativa. Relacione esses pontos com a viabilidade futura em Raspberry Pi e, depois, ESP32.
8. **Refinamento do questionário.** Para cada pergunta, explique qual decisão do projeto ela informa. Se uma pergunta não ajudar a escolher ruídos, latência, privacidade, offline, custo, naturalidade, acessibilidade ou cenários de teste, reescreva ou remova.
9. **Síntese crítica.** Ao final, o relatório deve mostrar trade-offs, não apenas listar técnicas. Discuta em que condições Fourier/STFT tende a ser simples e eficiente, em que condições Wavelet pode ser promissora, e quais dúvidas permanecerão para a fase experimental.

## Densidade matemática e científica esperada

O relatório deve ter densidade suficiente para convencer que a comparação não será apenas empírica ou intuitiva. Inclua, quando adequado:

- modelo de sinal ruidoso no tempo discreto;
- definição operacional de redução de ruído para voz;
- expressão da STFT e interpretação de seus parâmetros: janela, salto, tamanho da FFT e sobreposição;
- descrição de subtração espectral ou ganho espectral como baseline no domínio de Fourier;
- descrição de decomposição wavelet discreta, coeficientes por escala e limiarização;
- fórmulas das métricas centrais, especialmente SNR e melhoria de SNR;
- discussão sobre latência algorítmica, tempo de processamento por quadro e fator de tempo real;
- justificativa para escolhas experimentais, em vez de apenas listar ferramentas.

Essa densidade deve ser usada para dar profundidade ao relatório, não para alongar artificialmente o texto. Evite demonstrações longas, deduções desnecessárias e blocos matemáticos que não sejam conectados à metodologia.

## Referências bibliográficas orientadoras

Inclua uma seção de referências coerente com o novo escopo. Não use bibliografia decorativa: cada referência deve cumprir uma função clara no relatório. Sempre que possível, verifique dados bibliográficos, DOI, ano e veículo antes de finalizar.

Use como núcleo inicial:

- **Fourier, STFT e processamento digital de sinais:** Oppenheim e Schafer; Proakis e Manolakis; textos de processamento digital de sinais que sustentem amostragem, janelamento, FFT, espectrograma e reconstrução.
- **Realce de fala e métodos espectrais clássicos:** Boll (1979), sobre subtração espectral; Ephraim e Malah (1984), sobre estimador MMSE-STSA; Loizou, *Speech Enhancement: Theory and Practice*, para organizar técnicas, métricas e trade-offs perceptuais.
- **Wavelets e ondaletas:** Morettin, *Ondas e Ondaletas*, como base em português para amadurecimento conceitual; Mallat, *A Wavelet Tour of Signal Processing*; Daubechies, *Ten Lectures on Wavelets*; Donoho (1995), sobre denoising por soft-thresholding; Donoho e Johnstone (1994/1995), sobre wavelet shrinkage e limiarização.
- **Métricas de avaliação de voz:** Taal et al. (2011), para STOI; recomendação ITU-T P.862, para PESQ, observando restrições e adequação; métricas simples como SNR, melhoria de SNR, MSE e SI-SDR para avaliação reprodutível.
- **Bases e protocolos experimentais:** VoiceBank-DEMAND, DEMAND, LibriSpeech ou outras bases públicas adequadas, quando fizer sentido. Priorize bases abertas ou bem documentadas para evitar dependência de coleta própria de voz.
- **Estado atual do campo:** mencione que técnicas modernas de aprendizado profundo existem e dominam muitos benchmarks recentes de speech enhancement, mas deixe claro que elas entram como contexto, não como foco principal desta etapa. O centro do segundo relatório deve ser comparação Fourier/STFT versus Wavelet e viabilidade futura de embarcados.

Ao escrever o resumo das referências, explique como cada uma sustenta uma decisão do projeto. Exemplo: Boll justifica o baseline espectral; Donoho justifica limiarização wavelet; Morettin e Mallat sustentam a leitura conceitual de ondaletas; Taal e ITU-T sustentam a discussão de métricas.

## Estrutura sugerida para o segundo relatório

Uma estrutura robusta para o relatório pode ser:

1. Identificação do projeto.
2. Contextualização da reformulação do escopo.
3. Resumo do projeto reformulado.
4. Problema de pesquisa e hipótese de trabalho.
5. Objetivo geral e objetivos específicos.
6. Fundamentação teórica: voz ruidosa, Fourier/STFT e Wavelet.
7. Metodologia experimental proposta.
8. Métricas e critérios de comparação.
9. Referências bibliográficas e papel de cada referência.
10. Atividades realizadas e resultados obtidos nesta fase.
11. Avaliação do andamento e justificativa dos desvios.
12. Questionário extensionista refinado.
13. Cronograma detalhado para o segundo semestre.
14. Considerações finais.

Se o limite de páginas for apertado, preserve a densidade nas seções de fundamentação, metodologia, métricas e cronograma, e reduza repetições narrativas.

## Questionário extensionista

Refine o questionário reformulado para que ele tenha foco em voz humana e comunicação em tempo real. O questionário deve ajudar a decidir requisitos técnicos, e não apenas confirmar ideias óbvias.

Preserve perguntas úteis sobre:

- situações em que ruído prejudica comunicação por voz;
- tipos de ruído mais relevantes;
- tolerância a latência;
- preferência entre remoção agressiva de ruído e naturalidade da voz;
- importância de funcionamento offline;
- privacidade no processamento de voz;
- barreiras de acesso, custo e simplicidade;
- consumo energético;
- uma pergunta aberta realmente útil.

Remova ou reescreva perguntas que sejam:

- retóricas;
- previsíveis demais;
- moralmente óbvias;
- desconectadas de uma decisão técnica;
- repetitivas;
- amplas demais para o novo escopo.

Para cada pergunta mantida ou proposta, explique brevemente como a resposta será usada no projeto. Exemplo: escolha de ruídos de teste, definição de latência-alvo, seleção de métricas, justificativa para processamento local, priorização de hardware ou ajuste de parâmetros de supressão.

## Tom e estilo

Use linguagem acadêmica natural, sem exagerar no marketing tecnológico. O relatório deve soar como continuidade madura do anteprojeto, reconhecendo que houve ajuste de escopo a partir de crítica construtiva.

Evite:

- linguagem de PIBITI ou edital;
- promessas de protótipo completo antes da hora;
- termos grandiosos sem sustentação;
- perguntas de pesquisa amplas demais;
- afirmações de que TinyML/IA será necessariamente melhor;
- afirmar resultados experimentais ainda não obtidos.

Prefira:

- "comparar", "avaliar", "medir", "verificar viabilidade", "identificar trade-offs";
- "ambiente computacional convencional" para a primeira etapa;
- "integração embarcada no próximo semestre";
- "Raspberry Pi como plataforma inicial de validação embarcada";
- "ESP32 como etapa posterior, dependente da complexidade final do pipeline";
- "Arduino Uno R3 como trabalho futuro ou limitação".

## Saída desejada

Entregue:

1. Uma versão completa do texto do segundo relatório, com seções bem organizadas.
2. Uma proposta de título atualizado.
3. Uma versão refinada do questionário extensionista, com perguntas e uso esperado das respostas.
4. Um cronograma detalhado para o segundo semestre.
5. Uma seção curta explicando os desvios em relação ao cronograma anterior e justificando a reformulação do escopo.
6. Uma seção de fundamentação matemática e científica, com referências pertinentes e conectadas à metodologia.
7. Um protocolo experimental claro para comparação Fourier/STFT versus Wavelet.

Se estiver trabalhando diretamente no repositório LaTeX, crie uma nova versão baseada em `entrega2.tex`, por exemplo `entrega3.tex`, preservando a formatação existente, mas atualizando o conteúdo para o novo escopo.

Antes de finalizar, revise se:

- o relatório responde explicitamente ao feedback do professor;
- o escopo está concentrado em voz humana;
- PIBITI foi removido como compromisso;
- Fourier/STFT e Wavelet aparecem como comparação central desta etapa;
- hardware aparece como continuidade planejada, não como promessa já realizada;
- o questionário gera dados realmente acionáveis;
- o cronograma do segundo semestre é realista e progressivo.
- as referências não estão apenas listadas, mas realmente sustentam as escolhas técnicas;
- há densidade matemática suficiente para diferenciar STFT/Fourier e Wavelet de forma rigorosa;
- a metodologia experimental permite reproduzir e comparar resultados, e não apenas descrever intenções.
