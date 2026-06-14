# Roteiro da apresentacao - Entrega 2

Apresentacao em 06/05/2026. Tempo maximo total: 5 minutos.

Divisao sugerida:

- Augusto: slides 1 a 5, cerca de 2min25s.
- Gabriel: slides 6 a 9, cerca de 2min25s.
- Slide 10, se existir como mapa de duvidas: deixar para perguntas ou passar em 5s no encerramento.
- Margem: 10s para troca entre apresentadores.

Ideia central da apresentacao:

"Nosso projeto nao e apenas listar tecnicas de reducao de ruido. A proposta e organizar a literatura de forma comparavel, conectando metodos, requisitos, limitacoes, metricas e contexto real de aplicacao."

## Roteiro do Augusto - slides 1 a 5

### Slide 1 - Capa

Tempo alvo: 15 a 20 segundos.

Fala-base:

"Bom dia. Eu sou o Augusto, e apresento junto com o Gabriel o nosso anteprojeto de formatura, orientado pelo professor Juan Luis Poletti Soto. O tema do trabalho e uma revisao sistematica da literatura sobre reducao de ruido em sinais unidimensionais no tempo. Nesta primeira parte, eu vou contextualizar o problema, os objetivos e a metodologia da revisao; depois o Gabriel apresenta o cronograma, as atividades realizadas, a atividade extensionista e os proximos passos."

Intencao do slide:

Abrir de forma objetiva, sem gastar tempo lendo todos os nomes. Ja deixar claro que a apresentacao tem duas partes.

### Slide 2 - Escopo e problema

Tempo alvo: 35 a 40 segundos.

Fala-base:

"O escopo do projeto esta em processamento de sinais, com foco em sinais temporais unidimensionais. Isso inclui, por exemplo, voz, audio, telemetria, sinais de sensores, vibracao, instrumentacao e sinais biomedicos. O problema pratico e que, em ambientes reais, esses sinais quase sempre chegam contaminados por ruido. Isso pode prejudicar inteligibilidade, medicao, classificacao automatica ou interpretacao humana. Entao, a pergunta de fundo nao e apenas 'como remover ruido', mas como escolher uma tecnica adequada para cada contexto, levando em conta tipo de ruido, dados disponiveis, custo computacional, operacao em tempo real e preservacao da informacao util."

Ritmo:

Use o grafico como apoio visual: "o sinal medido contem tanto a componente util quanto perturbacoes". Nao explique o grafico matematicamente.

### Slide 3 - Objetivos e questoes norteadoras

Tempo alvo: 35 a 40 segundos.

Fala-base:

"A partir desse problema, o objetivo geral do trabalho e revisar a literatura e propor uma taxonomia critica das principais familias de metodos. A ideia e comparar nao so desempenho, mas tambem requisitos, limitacoes, metricas, custo computacional e contexto de aplicacao. As perguntas que guiam a revisao sao: quais familias aparecem com mais frequencia, quando cada uma tende a ser adequada, quais metricas sao usadas em aplicacoes reais e que limitacoes aparecem na pratica. Tambem incorporamos requisitos sociais, eticos, de acessibilidade e sustentabilidade, porque a escolha tecnica pode afetar custo, privacidade, inclusao e viabilidade de uso."

Intencao do slide:

Mostrar que o trabalho tem criterio. Evite ler todas as perguntas uma por uma; agrupe-as em uma frase.

### Slide 4 - Metodologia da revisao sistematica

Tempo alvo: 45 a 50 segundos.

Fala-base:

"A metodologia foi pensada como uma revisao sistematica, inspirada em diretrizes como PRISMA e Kitchenham. O fluxo tem quatro etapas: busca, triagem, extracao e sintese. Na busca, usamos bases como IEEE, ACM, ScienceDirect, SpringerLink, Scopus, Web of Science, Google Scholar e arXiv. Depois, na triagem, aplicamos criterios de inclusao e exclusao para manter trabalhos realmente ligados a sinais temporais unidimensionais. Na etapa de extracao, registramos metodo, tipo de sinal, tipo de ruido, metricas, dados usados, custo e limitacoes. Por fim, a sintese organiza isso em uma taxonomia e uma matriz comparativa. O ponto importante e garantir rastreabilidade: conseguir explicar como os estudos foram encontrados, selecionados e comparados."

Ritmo:

Passe pelo diagrama da esquerda para a direita. Esse slide e o mais tecnico da sua parte, entao fale em blocos curtos.

### Slide 5 - Referencias e familias de metodos

Tempo alvo: 35 a 40 segundos.

Fala-base:

"As referencias iniciais foram escolhidas para cobrir tanto metodos classicos quanto abordagens modernas. Temos metodos espectrais e estatisticos, como subtracao espectral e estimadores MMSE, que sao importantes em voz e tem baixo custo. Temos wavelets e representacoes multiescala, uteis para sinais nao estacionarios. Tambem entram decomposicoes adaptativas, como EMD e VMD, e metodos de aprendizado profundo, que podem ter alto desempenho, mas dependem mais de dados e custo computacional. Por fim, as referencias de revisao sistematica dao a base metodologica. Com isso, a revisao fica organizada por familias de metodos, nao por uma lista solta de artigos."

Transicao para Gabriel:

"Com essa base de escopo, objetivos, metodo e referencias, o Gabriel continua mostrando como organizamos o cronograma, o que ja foi feito nesta fase e quais sao os proximos passos do projeto."

## Roteiro do Gabriel - slides 6 em diante

### Slide 6 - Cronograma do 1o semestre

Tempo alvo: 35 a 40 segundos.

Fala-base:

"Dando continuidade, o cronograma do primeiro semestre foi organizado em funcao dos marcos da disciplina. Em abril, fechamos tema, orientador, grupo e escopo. No fim de abril e inicio de maio, consolidamos o primeiro relatorio, os objetivos, as referencias iniciais e o questionario extensionista. Agora, em maio, estamos na etapa da apresentacao, revisao do questionario a partir de feedback e inicio da busca sistematica. Para junho, a meta e fazer a triagem dos estudos e iniciar a matriz comparativa. No inicio de julho, queremos chegar com resultados parciais, analise inicial das respostas e uma visao mais clara das lacunas encontradas."

Intencao do slide:

Mostrar que ha planejamento e que o grupo sabe exatamente onde esta no processo.

### Slide 7 - Atividades realizadas nesta fase

Tempo alvo: 35 a 40 segundos.

Fala-base:

"Nesta fase, o principal resultado foi transformar um tema amplo em um protocolo de trabalho. Ja definimos o tema, o titulo, o orientador e o grupo; delimitamos o foco em sinais temporais 1D; levantamos familias de tecnicas; selecionamos referencias fundamentais; definimos questoes de pesquisa e campos de extracao; e elaboramos o questionario extensionista. Ou seja, ainda nao estamos na etapa de conclusoes tecnicas finais, mas ja estruturamos o caminho para que a revisao seja comparavel, rastreavel e orientada por aplicacoes reais."

Ritmo:

Nao leia todos os itens como checklist. Agrupe-os em "definicao", "levantamento" e "instrumento extensionista".

### Slide 8 - Atividade extensionista

Tempo alvo: 45 a 50 segundos.

Fala-base:

"A atividade extensionista foi planejada por meio de um formulario eletronico, voluntario e sem coleta obrigatoria de dados sensiveis. O publico-alvo inclui estudantes, pesquisadores, profissionais de engenharia e tecnologia, alem de usuarios afetados por sinais ruidosos em contextos como chamadas de voz, sensores, telemetria e medicoes. O questionario tem 16 perguntas e foi organizado em quatro eixos: beneficio social, acessibilidade e inclusao, sustentabilidade, e etica e privacidade. A ideia nao e fazer uma pesquisa estatistica ampla neste momento, mas usar as respostas agregadas para ajustar os criterios da revisao e entender quais requisitos reais aparecem fora da literatura puramente tecnica."

Intencao do slide:

Conectar extensao ao projeto tecnico. Evite parecer que o questionario e um anexo burocratico.

### Slide 9 - Atividades previstas para o 2o semestre

Tempo alvo: 40 a 45 segundos.

Fala-base:

"Para o segundo semestre, a continuidade natural e concluir a selecao dos estudos, documentar o fluxo de inclusao e exclusao e finalizar a matriz comparativa das tecnicas. Tambem pretendemos aprofundar os metodos mais promissores para voz, telemetria e sensores, considerando desempenho, custo, dados disponiveis, interpretabilidade e restricoes de uso. Quando for viavel, podemos implementar ou adaptar experimentos de referencia para comparar metodos representativos. Ao final, a entrega esperada e uma sintese tecnica organizada e reprodutivel, que ajude na escolha de tecnicas de reducao de ruido para aplicacoes reais, incorporando tambem os aspectos sociais e eticos levantados pelo questionario."

Fechamento:

"Em resumo, esta entrega consolida o anteprojeto como uma revisao sistematica estruturada, com escopo tecnico definido, metodologia rastreavel, atividade extensionista planejada e proximos passos claros para a continuidade do trabalho. Obrigado."

### Slide 10 - Mapa para duvidas, se for apresentado

Tempo alvo: 5 a 10 segundos.

Fala-base:

"Deixamos este mapa apenas para orientar eventuais duvidas da banca, caso queiram voltar a algum ponto especifico da apresentacao."

## Dicas de apresentacao

- Nao tentem falar tudo que esta no slide. Cada slide deve ter uma mensagem principal.
- Evitem comecar frases com "nesse slide". Melhor entrar direto na ideia.
- Usem conectores: "a partir disso", "com esse escopo", "na pratica", "por fim".
- Se o tempo apertar, cortem exemplos, nao cortem a logica.
- A apresentacao deve soar como uma historia: problema, objetivo, metodo, base bibliografica, andamento, extensao e proximos passos.
- Treinem uma vez mirando 4min30s. Assim sobra margem para troca de apresentador e pequenas pausas.

## Versao ultracurta para memorizar

Augusto:

"O projeto trata de reducao de ruido em sinais temporais 1D. O problema e escolher tecnicas adequadas para contextos diferentes, considerando ruido, dados, custo e preservacao da informacao. Nosso objetivo e fazer uma revisao sistematica e propor uma taxonomia critica. A metodologia segue busca, triagem, extracao e sintese, com criterios rastreaveis. As referencias cobrem metodos classicos, wavelets, decomposicoes adaptativas, aprendizado profundo e protocolo de revisao."

Gabriel:

"O cronograma parte da definicao do projeto em abril, passa pela apresentacao e questionario em maio, triagem e matriz em junho, e resultados parciais em julho. Nesta fase, estruturamos escopo, referencias, questoes de pesquisa e campos de extracao. A atividade extensionista usa um formulario voluntario para captar demandas reais ligadas a beneficio social, acessibilidade, sustentabilidade e etica. No segundo semestre, vamos consolidar a selecao dos estudos, finalizar a matriz comparativa e preparar a sintese tecnica final."
