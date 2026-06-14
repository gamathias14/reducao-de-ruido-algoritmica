# Estimador causal de ruido

## Escopo

O nucleo causal da etapa PC-1 fica em `benchmark_audio/causal.py`. Ele e
independente de dispositivo e expoe a mesma API por blocos para a captura
Windows e para o futuro processador de WAV:

```python
processor = CausalSTFTProcessor(config)
output, diagnostics = processor.process_block(input_block)
processor.reset()
```

O processador aceita blocos de qualquer comprimento, preserva o comprimento da
saida e mantem todo o estado explicitamente no objeto. Nao usa semente aleatoria
nem consulta amostras posteriores ao bloco recebido. O espectro observado no
bloco atual atualiza o estimador somente para os blocos seguintes.

## Modos avaliados

`calibration`

- acumula a potencia espectral dos primeiros 250 ms;
- libera o sinal sem supressao durante a calibracao;
- congela a media depois da calibracao;
- serve como baseline causal que ainda depende de um inicio representativo do
  ruido.

`adaptive`

- aquece por 250 ms sem exigir silencio;
- mantem uma janela causal de espectros passados;
- calcula um quantil por bin e um quantil da energia global;
- usa EMA rapida em quadros de baixa energia;
- usa EMA lenta durante fala provavel;
- continua adaptando-se a mudancas persistentes de ruido sem incorporar
  rapidamente a fala ao perfil de ruido.

O alias de CLI `rolling` e mantido por compatibilidade e mapeia para
`adaptive`.

## Parametros congelados da PC-1

| Parametro | Valor |
|---|---:|
| taxa de amostragem | 16 kHz |
| FFT | 512 amostras |
| hop | 160 amostras, 10 ms |
| bloco de avaliacao | 320 amostras, 20 ms |
| aquecimento | 250 ms |
| historico causal | 500 ms, 50 quadros |
| quantil espectral | 0,22 |
| quantil de energia | 0,20 |
| limiar de fala provavel | 6 dB sobre o piso de energia |
| EMA em baixa energia | 0,30 |
| EMA durante fala provavel | 0,005 |
| subtracao espectral | alpha 1,5; piso 0,02 |
| Wiener | piso 0,05 |
| protecao numerica | epsilon `1e-12` e saneamento de nao finitos |

Os parametros foram escolhidos entre 20 variantes adaptativas mais o baseline
de calibracao, usando somente os 72 casos da divisao `validation`. A regra
minimizou primeiro a fracao de degradacao de SNR e, depois, maximizou melhoria
media de SNR e SI-SDR. A divisao `final_operational` foi aberta pelo script
somente depois da selecao. Nenhuma gravacao autoral futura foi usada.

## Estado persistente

O estado inclui:

- historico circular de potencia espectral;
- historico circular de energia por quadro;
- estimativa atual de potencia de ruido;
- acumulador usado pelo modo de calibracao;
- janela Hann;
- buffer de analise para blocos menores que a FFT;
- historico de amostras para o processamento STFT;
- contadores e ultima decisao de fala/baixa energia.

Na configuracao congelada, o maior estado medido pelo script foi 60.900 bytes,
aproximadamente 59,5 KiB. O valor inclui arrays NumPy do algoritmo, mas nao o
overhead do interpretador Python nem temporarios internos de FFT/STFT.

## Resultados resumidos

Na divisao operacional existente:

| Metodo | Melhoria SNR | Melhoria SI-SDR | Degradacao |
|---|---:|---:|---:|
| bypass | 0,00 dB | 0,00 dB | 0,0% |
| subtracao, calibracao causal | 0,96 dB | -2,38 dB | 33,3% |
| subtracao, inicial antiga | 1,82 dB | -0,16 dB | 33,3% |
| subtracao, adaptativa causal | 3,76 dB | 2,65 dB | 0,0% |
| subtracao, baixa energia offline | 4,85 dB | 3,72 dB | 0,0% |
| Wiener adaptativo causal | 1,68 dB | 1,35 dB | 0,0% |
| Wiener, baixa energia offline | 2,92 dB | 2,25 dB | 0,0% |

A referencia offline continua sendo um limite superior operacional, nao uma
implementacao disponivel em streaming.

## Tempo e limitacoes

Na divisao operacional, a subtracao causal teve RTF medio 0,068, p99 medio de
3,08 ms por bloco e pior bloco de 13,31 ms. Na execucao longa em lote da
validacao ocorreu um pico isolado de 104,12 ms, embora o p99 medio tenha sido
3,74 ms e o RTF medio 0,078. Esse pico deve ser tratado como evidencia de
jitter do processo Python/sistema durante o benchmark, e nao como falha de
qualidade nem como validacao realtime prolongada.

O autoteste sintetico de 1 s posterior registrou media de 1,58 ms, p99 de
4,01 ms e pior bloco de 4,62 ms, sem bloco acima do orcamento de 20 ms. A
validacao fisica prolongada pertence a PC-6 e ainda nao foi executada com este
estimador.

## Reproducao

```powershell
python -m benchmark_audio.run_causal_estimator
python -m pytest -q
python -m realtime_audio.windows_realtime --self-test --method stft_subtraction --noise-mode adaptive --duration 1 --block-ms 20 --no-save
```

Tabelas e metadados ficam em
`resultados/causal_estimator/tabelas/`.

## Complemento PC-2: contrato de arquivo

`realtime_audio/process_wav_blocks.py` instancia diretamente
`CausalSTFTProcessor`; nao existe uma segunda implementacao da subtracao, do
Wiener, do aquecimento ou do estimador. A captura Windows usa o mesmo objeto
por meio de `RealtimeBlockProcessor`.

O caminho de arquivo:

- converte a entrada para float32 mono a 16 kHz sem normalizacao de pico;
- cria um processador novo por arquivo, garantindo estado reinicializado;
- envia blocos em ordem e processa o ultimo bloco com seu tamanho real;
- concatena exatamente uma saida por amostra processada;
- nao adiciona padding ao arquivo nem remove amostras para compensar latencia;
- limita valores somente na escrita PCM16 e registra a faixa excedida.

Assim, entrada convertida e saida possuem deslocamento de indice zero. A
estimativa de 32 ms para a janela STFT continua registrada como latencia
algoritmica, mas nao deve ser confundida com deslocamento do WAV, latencia de
driver, latencia de dispositivo ou round-trip fisico.

Os tamanhos de 10, 20 e 32 ms alteram apenas o particionamento externo. FFT,
hop, estimador e parametros de supressao permanecem congelados.
