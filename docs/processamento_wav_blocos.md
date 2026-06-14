# Processamento de WAV em blocos

## Objetivo

A etapa PC-2 fornece um caminho reproduzivel, sem microfone, para executar o
mesmo nucleo causal usado pela captura Windows. O ponto de entrada e:

```powershell
python -m realtime_audio.process_wav_blocks `
  --input entrada.wav `
  --output saida.wav `
  --method stft_subtraction `
  --noise-mode adaptive `
  --block-ms 20 `
  --metrics-json resultados/file_blocks/run.json `
  --blocks-csv resultados/file_blocks/run.csv
```

O modulo importa diretamente:

```python
from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor
```

E/S, reamostragem, escrita PCM, hashes e relatorios ficam fora do nucleo DSP.

## Contrato da CLI

- metodos: `bypass`, `stft_subtraction`, `stft_wiener`;
- modos de ruido: `adaptive` e `calibration`;
- blocos: 10, 20 ou 32 ms;
- taxa processada: 16 kHz;
- saida: mono PCM16;
- sobrescrita: recusada, salvo `--overwrite`;
- erro de entrada ou caminho invalido: codigo de retorno 2;
- dependencia de `sounddevice`: nenhuma.

`adaptive` e o modo operacional principal. `calibration` permanece apenas como
baseline que depende de um inicio representativo do ruido.

## E/S, comprimento e alinhamento

1. O WAV e lido com SciPy.
2. Canais estereo sao reduzidos pela media aritmetica.
3. Inteiros PCM sao convertidos para float32.
4. Taxas diferentes sao reamostradas com `resample_poly`.
5. Nenhuma normalizacao de pico e aplicada.
6. O ultimo bloco usa apenas as amostras existentes.
7. A concatenacao preserva o numero de amostras depois da conversao.
8. O arquivo de saida nao recebe silencio ou padding de compensacao.

O alinhamento de arquivo e, portanto, por indice de amostra, com deslocamento
zero entre a entrada convertida e a saida. Para STFT, o JSON registra 32 ms
como estimativa de latencia algoritmica de janela. Esse valor nao representa
latencia de driver, dispositivo ou round-trip, e nao e convertido em atraso
artificial no WAV.

O bypass e exato em float32 antes da escrita. Na escrita PCM16, valores fora de
`[-1, 1]` sao limitados e contados. Picos e contagens antes da escrita ficam no
JSON.

## Saidas

O CSV por bloco contem:

- indice e intervalo de amostras;
- tamanho real do bloco;
- tempo e RTF;
- picos de entrada e saida;
- aquecimento e prontidao do estimador;
- fala provavel e baixa energia;
- atualizacoes do estimador;
- potencia media estimada do ruido;
- memoria do estado.

O JSON por execucao contem:

- caminhos e SHA-256;
- taxa, canais, dtype e bits originais;
- taxa e formato de saida;
- duracao e amostras processadas;
- configuracao causal completa;
- media, desvio, p50, p95, p99 e pior caso;
- RTF total e medio por bloco;
- blocos acima do orcamento;
- memoria maxima;
- picos, clipping e nao finitos;
- latencia algoritmica estimada;
- Python, plataforma, NumPy e SciPy;
- timestamp e argumentos.

Tempos de arquivo medem custo computacional offline por blocos. Eles nao
validam estabilidade de stream nem latencia fisica.

## Matriz PC-2

Reproducao:

```powershell
python -m benchmark_audio.run_file_blocks_experiment
```

Dados:

- fala publica preparada: `speech_george.wav`, FSDD;
- ruido: `pcafeter_ch01_seg01.wav`, DEMAND;
- SNRs: -5 e 5 dB;
- blocos: 10, 20 e 32 ms;
- causal: bypass, subtracao e Wiener adaptativos;
- referencia: baixa energia offline, quantil 0,35.

Resultados agregados:

| Metodo | Bloco | Delta SNR | Delta SI-SDR | RTF total | P99 por bloco |
|---|---:|---:|---:|---:|---:|
| subtracao causal | 10 ms | 3,36 dB | 1,22 dB | 0,111 | 2,12 ms |
| subtracao causal | 20 ms | 3,27 dB | 1,27 dB | 0,081 | 2,76 ms |
| subtracao causal | 32 ms | 3,25 dB | 1,35 dB | 0,068 | 3,41 ms |
| Wiener causal | 10 ms | 1,54 dB | 0,74 dB | 0,107 | 2,49 ms |
| Wiener causal | 20 ms | 1,33 dB | 0,67 dB | 0,078 | 2,40 ms |
| Wiener causal | 32 ms | 1,27 dB | 0,68 dB | 0,069 | 3,66 ms |

As referencias offline obtiveram 4,31 dB/2,14 dB para subtracao e
2,85 dB/1,68 dB para Wiener. Todos os comprimentos foram preservados, o
deslocamento registrado foi zero, nenhum bloco excedeu seu orcamento e o estado
causal maximo foi 60.900 bytes.

Nesta amostra pequena, 10 ms teve leve vantagem de SNR, enquanto 32 ms reduziu
o RTF e teve leve vantagem de SI-SDR na subtracao. Isso e uma observacao
operacional, nao uma nova selecao de parametros.

## Vetores de teste

Geracao:

```powershell
python -m realtime_audio.generate_test_vectors
```

Arquivos em `test_vectors/file_blocks/`:

- `noisy_input.wav`;
- `expected_bypass.wav`;
- `expected_causal_subtraction.wav`;
- `config.json`;
- `manifest.json`.

Os sinais sao sinteticos, usam semente 3527 e nao contem voz privada. O
manifesto registra SHA-256 e tolerancias float32/PCM16. A execucao CLI
versionada em `resultados/file_blocks/example/` reproduziu exatamente o SHA-256
do vetor causal esperado.

## Testes e limites

A suite cobre bypass, comprimento multiplo e nao multiplo, ultimo bloco curto,
determinismo, equivalencia com chamada direta, 10/20/32 ms, estereo/8 kHz,
entradas ausentes/vazias/truncadas, sobrescrita, finitude de CSV/JSON, reset e
hashes.

Limitacoes:

- matriz com uma fala, um trecho de ruido e duas SNRs;
- tempos medidos em um unico PC e sujeitos a jitter;
- referencia offline examina o arquivo completo;
- sem escuta perceptual;
- sem captura fisica ou validacao prolongada nesta etapa.
