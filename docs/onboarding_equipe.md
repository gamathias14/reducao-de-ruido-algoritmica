# Onboarding da equipe

## Para que serve este documento

Este é o ponto de entrada para Augusto, Lucas e Gabriel entenderem o projeto sem
precisar reconstruir sua história a partir do relatório, dos checkpoints e dos
arquivos técnicos. Ele registra o problema estudado, as decisões já tomadas, o
estado atual, as limitações e o que cada integrante precisa fazer a seguir.

Após a leitura, todos devem conseguir explicar:

- qual problema o projeto procura resolver;
- por que comparamos STFT/Fourier e Wavelet;
- por que causalidade, custo computacional e latência importam;
- o que os resultados atuais permitem ou não concluir;
- o que falta para concluir a etapa com vozes autorais.

## Visão geral

O projeto tem como tema:

**Redução de Ruído Local em Tempo Real para Voz Humana: Comparação entre STFT e
Wavelet com Avaliação de Viabilidade Embarcada.**

O objetivo é investigar técnicas de redução de ruído para voz em aplicações de
comunicação, executadas localmente e com baixa latência. O processamento local
favorece privacidade e reduz a dependência de serviços externos. Também interessa
saber se os métodos poderão, futuramente, ser transferidos para uma plataforma
embarcada com recursos limitados.

O escopo inicial era mais amplo e tratava redução de ruído em sinais
unidimensionais em geral. Após as orientações recebidas, ele foi delimitado para:

- voz humana;
- ruído acústico aditivo;
- comunicação em tempo real;
- processamento local;
- comparação entre métodos baseados em STFT e Wavelet;
- análise de qualidade, tempo de processamento, estado interno e viabilidade de
  uma futura implementação embarcada.

Não estamos prometendo eliminar perfeitamente todo ruído nem entregar, nesta
etapa, um produto embarcado pronto. A meta é construir uma base experimental
reprodutível no PC, comparar alternativas e justificar tecnicamente qual caminho
deve avançar para o hardware.

## Pergunta de pesquisa

Sob restrições de baixa latência e capacidade computacional moderada, quais são
os compromissos práticos de qualidade e custo ao usar métodos de redução de ruído
baseados em STFT/Fourier ou Wavelet para voz humana?

O modelo experimental básico é:

```text
y[n] = x[n] + r[n]
```

em que `x[n]` é a voz limpa, `r[n]` é o ruído e `y[n]` é o sinal observado. O
sistema produz uma estimativa `x_hat[n]` da voz limpa.

## Métodos comparados

O pipeline contém quatro referências:

1. **Bypass ou sinal ruidoso:** não aplica redução de ruído e serve de controle.
2. **Subtração espectral por STFT:** estima o espectro do ruído e o subtrai do
   sinal observado, respeitando um piso para reduzir artefatos.
3. **Ganho inspirado em Wiener por STFT:** atenua regiões espectrais conforme uma
   estimativa da relação entre sinal e ruído.
4. **Wavelet DWT com limiarização:** decompõe o sinal em escalas e reduz
   coeficientes associados ao ruído.
5. **Wavelet Packet + Wiener adaptativo (próxima trilha):** decompõe baixas e
   altas frequências em subbandas, acompanha ruído no tempo e aplica ganho suave.

A Wavelet continua no trabalho porque é parte central da comparação proposta,
mas a interpretação foi refinada: o que apresentou desempenho inferior até agora
foi a DWT com limiarização universal/MAD. A próxima pergunta experimental é se
uma formulação Wavelet mais adaptativa, baseada em WPT + rastreamento de ruído +
Wiener, consegue competir melhor.

## Dados utilizados

Até o momento, o projeto usa:

- **FSDD:** gravações públicas curtas de fala;
- **ruídos sintéticos:** usados nos primeiros testes controlados;
- **DEMAND:** ruídos ambientais reais, incluindo cozinha, escritório, cafeteria
  e tráfego;
- **vozes autorais:** próxima etapa, com gravações de Augusto, Lucas e Gabriel.

Os áudios brutos, preparados e autorais não são versionados no Git. O repositório
mantém código, documentação, manifestos-modelo e resultados leves. Dados autorais
ficam em área privada e só podem ser usados conforme o consentimento de cada
participante.

## Métricas

As principais medidas são:

- **melhoria de SNR:** quanto a relação sinal-ruído aumentou;
- **melhoria de SI-SDR:** quanto a reconstrução se aproximou da voz de referência;
- **MSE:** erro quadrático, mantido principalmente por continuidade histórica;
- **fração de degradação:** proporção de casos em que o método piorou o sinal;
- **RTF:** tempo de processamento dividido pela duração do áudio; abaixo de `1`
  significa que o processamento foi mais rápido que o tempo real;
- **tempos por bloco:** média, percentis `p50`, `p95`, `p99` e pior caso;
- **memória/estado interno:** aproximação do custo para execução contínua;
- **avaliação perceptual:** será adicionada para verificar o que ouvintes percebem,
  pois métricas numéricas não capturam sozinhas todos os artefatos.

## Evolução e resultados

### Benchmark preliminar

Nos testes iniciais com ruído sintético, a subtração espectral apresentou o
melhor resultado médio, o método inspirado em Wiener ficou em segundo lugar e a
Wavelet foi inconsistente.

### Ruído ambiental

Nos primeiros experimentos com DEMAND, a subtração espectral obteve melhoria
média de SNR entre aproximadamente `6,21` e `7,69 dB`, dependendo do SNR de
entrada. O Wiener ficou entre `4,07` e `4,62 dB`, enquanto a Wavelet permaneceu
próxima de zero ou negativa.

Esses números não podiam ser lidos isoladamente: parte dos áudios tinha silêncio
inicial, o que facilitava artificialmente a estimativa de ruído dos métodos
STFT. O experimento foi então refinado para não depender desse silêncio.

### Referência offline refinada

Na avaliação final da referência offline:

| Método | Melhoria de SNR | Melhoria de SI-SDR | Degradação |
|---|---:|---:|---:|
| Subtração espectral | `+4,85 dB` | `+3,72 dB` | `0%` |
| Wiener | `+2,92 dB` | `+2,25 dB` | `0%` |
| Wavelet refinada | `+0,03 dB` | `+0,01 dB` | `11,1%` |

Essa referência identifica trechos de baixa energia olhando o arquivo inteiro.
Portanto, ela não é causal e não pode ser usada diretamente em uma aplicação ao
vivo. Seu papel é fornecer uma referência operacional superior para comparação.

A linha Wavelet será reaberta em outro nível metodológico. A DWT limiarizada
fica como baseline histórico; a nova candidata deve seguir o plano em
`docs/plano_wavelet_packet_wiener.md`.

### Estimador causal

Para o funcionamento em tempo real, foi criado um estimador que usa somente
amostras passadas. Ele combina histórico espectral, quantis de energia e
atualizações rápidas ou lentas conforme a probabilidade de fala.

Os parâmetros foram congelados em `16 kHz`, FFT de `512` amostras, salto de `160`
amostras, aquecimento de `250 ms` e histórico de `500 ms`, além dos parâmetros
documentados em `docs/estimador_causal.md`.

Resultados operacionais:

| Método causal | Melhoria de SNR | Melhoria de SI-SDR | Degradação |
|---|---:|---:|---:|
| Subtração espectral | `+3,76 dB` | `+2,65 dB` | `0%` |
| Wiener | `+1,68 dB` | `+1,35 dB` | `0%` |

O maior estado interno medido foi de `60.900 bytes`, cerca de `59,5 KiB`. Houve
um pico isolado de tempo de `104,12 ms` em uma execução em lote. Isso exige
investigação, mas não equivale por si só a uma falha contínua de tempo real.

### Processamento de WAV em blocos

O Checkpoint 21 validou o mesmo núcleo causal usado pelo protótipo Windows em
arquivos WAV processados como blocos de `10`, `20` e `32 ms`. O comprimento e o
alinhamento foram preservados, e os resultados são exportados em CSV e JSON.

Na matriz com uma voz FSDD, ruído de cafeteria e SNRs de `-5` e `5 dB`, todos os
casos tiveram `RTF < 1`. Para subtração espectral, a melhoria média de SNR ficou
em aproximadamente `+3,36`, `+3,27` e `+3,25 dB` para blocos de `10`, `20` e
`32 ms`, respectivamente. Esses testes demonstram reprodutibilidade em blocos no
PC, mas não medem toda a latência física de microfone, sistema operacional,
driver e dispositivo de saída.

## O que já foi concluído

- pipeline reprodutível de mistura, processamento e métricas;
- comparação preliminar e refinada entre STFT e Wavelet;
- preparação e uso de ruídos ambientais DEMAND;
- estimador de ruído causal com parâmetros congelados;
- núcleo causal compartilhado entre processamento de arquivo e captura Windows;
- processamento WAV por blocos com relatórios CSV e JSON;
- testes automatizados: `39` testes e `9` subtestes na última verificação;
- protocolo, autorização, roteiro e ferramenta de ingestão para vozes autorais;
- estrutura privada para armazenar consentimentos, gravações e manifestos.

## Limitações que todos devem conhecer

- o conjunto ambiental ainda é pequeno e contém amostras correlacionadas;
- a divisão operacional final não foi historicamente totalmente cega;
- ainda não existem resultados com as vozes autorais;
- ainda não há avaliação perceptual formal;
- a validação Windows prolongada de dez minutos já existe para self-test e
  captura física `input-only`, mas ainda não mede playback nem `round-trip`;
- o teste Bluetooth anterior funcionou, mas a latência foi dominada pelo próprio
  Bluetooth e não comprova baixa latência;
- processamento em blocos de arquivo não é igual a latência física ponta a ponta;
- ainda não existe implementação para Raspberry Pi.

Esses pontos não invalidam o trabalho. Eles definem corretamente o alcance das
conclusões atuais e orientam os próximos experimentos.

## Estado atual e proximo checkpoint

A decisao tecnica PC esta fechada: a implementacao principal e a subtracao STFT
causal adaptativa, com parametros congelados, estado causal explicito e
processamento reproduzivel por blocos de WAV. A WPT em quadros virou o achado
Wavelet mais importante, mas continua offline e deve ser apresentada como
frente cientifica/futura versao causal, nao como caminho PC atual.

O protocolo de voz autoral, os termos, o roteiro, a ingestao e a avaliacao
objetiva estao preparados. Ainda nao ha consentimentos nem gravacoes reais no
conjunto privado. Isso nao bloqueia a decisao PC: a voz autoral entra depois
como validacao complementar, usando parametros congelados e sem ajuste
oportunista.

O Checkpoint 24 foi concluido no Windows com a STFT causal congelada:

1. self-test sintetico de 600 s, 30.000 blocos, pior bloco 4,127 ms e zero
   blocos acima de 20 ms;
2. captura fisica `input-only` de 600 s com `Microfone (USB Audio Device), MME`,
   29.998 blocos, pior bloco 6,799 ms, RTF medio 0,064 e zero blocos acima de
   20 ms;
3. `status_counts` vazio nas duas rodadas longas, sem underflow/overflow
   reportado pela CLI;
4. latencia de 72 ms no JSON fisico deve ser lida apenas como 32 ms
   algoritmicos + 40 ms de entrada reportada, nao como `round-trip`.

O proximo marco e consolidar a narrativa no relatorio/defesa. Uma rodada
full-duplex cabeada pode ser planejada separadamente se a equipe quiser medir
caminho de saida ou `round-trip` fisico; Bluetooth nao deve ser usado como prova
de baixa latencia. Em paralelo, a equipe pode planejar a coleta autoral e uma
futura WPT causal/rolante, mas nenhuma dessas frentes reabre a decisao PC.

## Responsabilidades da equipe

### Augusto (`spk01`)

- coordenar o repositório, o pipeline e os checkpoints;
- receber e ingerir os arquivos autorais na área privada;
- auditar nomes, formatos, clipping, duração e manifestos;
- executar os experimentos congelados e consolidar os resultados;
- comunicar bloqueios e manter a documentação sincronizada.

### Lucas (`spk02`)

- ler este onboarding e os documentos essenciais indicados abaixo;
- definir e registrar seu consentimento;
- informar o equipamento e o ambiente de gravação disponíveis;
- realizar as Sessões A e B conforme o roteiro;
- revisar a qualidade e a rastreabilidade do conjunto de gravações;
- participar da escuta comparativa e da interpretação dos resultados.

### Gabriel (`spk03`)

- ler este onboarding e os documentos essenciais indicados abaixo;
- definir e registrar seu consentimento;
- informar o equipamento e o ambiente de gravação disponíveis;
- realizar as Sessões A e B conforme o roteiro;
- apoiar a organização da avaliação perceptual e da validação operacional;
- participar da escuta comparativa e da interpretação dos resultados.

Essa divisão é uma proposta inicial de propriedade das tarefas, não uma
restrição. O importante é que Lucas e Gabriel participem das decisões e análises,
e não apenas como fontes de gravação.

### Responsabilidade compartilhada

Todos devem:

- preservar a privacidade dos participantes;
- não enviar áudios ou consentimentos para o Git;
- registrar alterações de equipamento, ambiente ou roteiro;
- evitar ajustar o algoritmo depois de olhar os resultados finais autorais;
- saber apresentar o problema, os métodos, os resultados e as limitações;
- revisar as conclusões antes de incorporá-las ao relatório.

## O que está congelado e o que continua aberto

**Congelado para a plataforma PC e avaliacao autoral:**

- métodos principais;
- parâmetros do estimador causal;
- métricas objetivas;
- estrutura das Sessões A e B;
- regras de armazenamento e ingestão.

**Ainda aberto:**

- logística e datas das gravações;
- equipamentos efetivamente usados;
- execução final do protocolo perceptual;
- testes prolongados no Windows;
- eventual WPT em quadros causal/rolante;
- interpretação conjunta e redação final;
- estratégia futura de implementação no Raspberry Pi.

## Mapa do repositório

| Local | Finalidade |
|---|---|
| `entrega3.tex` / `entrega3.pdf` | relatório acadêmico principal |
| `benchmark_audio/denoise.py` | DSP offline, mistura e métricas |
| `benchmark_audio/causal.py` | núcleo causal compartilhado |
| `benchmark_audio/run_benchmark.py` | benchmark preliminar |
| `benchmark_audio/prepare_environmental_noise.py` | preparação do DEMAND |
| `benchmark_audio/run_refinement.py` | refinamento e seleção offline |
| `benchmark_audio/run_causal_estimator.py` | seleção e avaliação causal |
| `benchmark_audio/run_file_blocks_experiment.py` | matriz WAV em blocos |
| `benchmark_audio/prepare_authored_voice.py` | ingestão de voz autoral |
| `realtime_audio/process_wav_blocks.py` | CLI de processamento em blocos |
| `realtime_audio/windows_realtime.py` | protótipo de captura no Windows |
| `tests/` | testes automatizados |
| `resultados/` | resultados leves versionados |
| `dados/raw`, `dados/prepared`, `dados/private` | dados locais não versionados |
| `docs/checkpoints.md` | histórico detalhado dos checkpoints |

## Ordem de leitura recomendada

1. Este documento.
2. `docs/processamento_wav_blocos.md`.
3. `docs/estimador_causal.md`.
4. `docs/protocolo_voz_autoral.md`.
5. `docs/autorizacao_voz_autoral.md`.
6. `docs/roteiro_voz_autoral.md`.
7. Introdução, objetivos, método, resultados e conclusões de `entrega3.pdf`.
8. `docs/checkpoints.md` somente para consultar a evolução e decisões passadas.

Não é necessário ler todos os arquivos Markdown em ordem cronológica antes de
começar a colaborar.

## Glossário rápido

- **STFT:** análise do conteúdo de frequência em janelas sucessivas.
- **FFT:** algoritmo usado para calcular a representação em frequência.
- **Hop:** avanço entre janelas consecutivas da STFT.
- **Bloco:** quantidade de áudio entregue ao processador em cada chamada.
- **Causal:** usa somente o presente e o passado, requisito para operação ao vivo.
- **Offline:** pode usar o arquivo completo, inclusive informações futuras.
- **SNR:** relação entre potência da voz e do ruído.
- **SI-SDR:** medida de fidelidade da reconstrução da fonte.
- **RTF:** razão entre tempo de processamento e duração do áudio.
- **Warmup:** período inicial para formar a primeira estimativa de ruído.
- **Clipping:** saturação da gravação por amplitude excessiva.
- **Bypass:** sinal que passa sem redução de ruído.
- **Validação/final:** conjuntos separados para reduzir ajustes oportunistas.

## Primeira conversa de alinhamento

Uma reunião de 30 a 45 minutos deve cobrir:

1. apresentação deste resumo e esclarecimento de dúvidas;
2. demonstração curta do pipeline e de uma amostra processada;
3. escolha individual do nível de consentimento;
4. levantamento dos equipamentos e ambientes disponíveis;
5. combinação das datas das Sessões A e B;
6. confirmação das responsabilidades e do canal para registrar problemas.

## Mensagem curta para compartilhar

> Pessoal, consolidamos em `docs/onboarding_equipe.md` o contexto completo do
> projeto: problema, métodos, decisões, resultados, limitações, estado atual e
> tarefas de cada integrante. A leitura desse documento é o primeiro passo para
> alinharmos a equipe. Depois faremos uma conversa curta para tirar dúvidas,
> definir consentimento e equipamento e agendar as Sessões A e B de gravação.
> Nenhum áudio ou termo de consentimento será colocado no Git.
