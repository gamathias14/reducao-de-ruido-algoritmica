# Checkpoint 46-R - Benchmark de algoritmos consolidados

Data de pre-registro: 2026-06-13

## Motivo

O ensaio causal STFT de seis bracos terminou em
`stop_no_public_candidate`. Esta fase e um protocolo novo: ela compara
familias consolidadas da literatura em vez de continuar ajustando o baseline
por tentativa e erro.

A rejeicao perceptual da WPT causal continua valida. Nenhum audio privado,
endpoint, driver, ponte ou VM participa desta etapa.

## Corpus e unidade de comparacao

- corpus publico DEMAND/FSDD ja preparado e congelado;
- mesmas 72 misturas de validacao para todos os sistemas;
- mistura canonica mono `float32`, 16 kHz, com hash SHA-256 dos bytes little
  endian;
- saida convertida de volta para 16 kHz e mesmo comprimento antes das
  metricas;
- nenhum WAV e salvo por padrao;
- split final operacional bloqueado ate congelar no maximo dois finalistas.

Sistemas de 48 kHz recebem resampling deterministico
`16 kHz -> 48 kHz -> 16 kHz`. O custo do resampling integra RTF e memoria
end-to-end; o custo interno do algoritmo deve ser reportado separadamente
quando a API permitir.

## Contrato dos adaptadores

Cada adaptador deve declarar:

- implementacao, versao e revisao imutavel;
- licenca do codigo e dos pesos;
- taxa nativa, bloco da API, janela/hop de analise, lookahead e latencia
  algoritmica;
- causalidade e estado persistente;
- backend e comando reproduzivel;
- hashes de binario, modelo e configuracao quando aplicavel.

O adaptador deve preservar comprimento, produzir `float32` finito e ser
deterministico no mesmo host. Sistemas externos serao executados em processo
isolado para medir pico de working set; memoria de estado interno sera mantida
como medida adicional, nao substituta.

## Metricas

Medidas comuns:

- SNR e SI-SDR pareados;
- STOI quando a dependencia estiver instalada;
- densidade de picos tonais e spectral flatness;
- distancia log-espectral;
- correlacao de envelope;
- preservacao das bandas 2-4 kHz e 4-8 kHz;
- latencia algoritmica, atraso por impulso, RTF e memoria.

Nenhuma metrica isolada decide promocao. DNSMOS pode ser acrescentado como
evidencia secundaria, com versao e modelo fixados, sem substituir escuta.

## Sistemas e ordem

1. Baseline STFT causal congelado `E0-S02`.
2. OM-LSA + IMCRA, implementado a partir das equacoes e parametros publicados.
3. RNNoise 0.2, API C nativa a 48 kHz.
4. WebRTC APM com somente Noise Suppression habilitado.
5. DeepFilterNet 0.5.6 a 48 kHz, sem compensar atraso durante a medicao.

SpeexDSP fica como reserva caso um adaptador nativo bloqueie a matriz.

GTCRN passou a triagem inicial: repositorio oficial MIT, checkpoints
publicados e implementacao streaming disponivel. Ele permanece fora da
primeira bateria para evitar expansao de escopo antes da conclusao dos cinco
sistemas principais.

## Viabilidade Windows verificada

- Python 3.11, NumPy, SciPy, pandas, PyWavelets, PyTorch, ONNX Runtime e
  `psutil` disponiveis;
- Visual Studio Community 2026 com MSVC x64 e CMake instalado;
- Rust nao esta instalado;
- `pystoi` 0.4.1 foi fixado para a execucao oficial; antes da instalacao, STOI
  apareceu como ausente, nunca como zero;
- RNNoise e WebRTC exigem build nativo;
- DeepFilterNet oferece caminho Windows, mas o binario/tag e os pesos ainda
  precisam ser instalados e hashados.

## Licencas e revisoes iniciais

- RNNoise: BSD-3-Clause, tag `v0.2`,
  `c9137adac37fe21ede831f8a0aa31c17560c01e7`;
- WebRTC: licenca BSD, pin inicial
  `eb79ac6e330baa0a6d26c53d522f9ed57495edb7`;
- DeepFilterNet: MIT ou Apache-2.0, tag `v0.5.6`,
  `978576aa8400552a4ce9730838c635aa30db5e61`;
- GTCRN: MIT, checkpoint e pasta streaming presentes; fora da primeira fase.

Antes da execucao oficial, cada pin deve ser clonado em cache externo ao
repositorio e acompanhado de hash dos artefatos usados.

## Selecao

- executar primeiro apenas validacao;
- excluir falha de causalidade, nao determinismo, comprimento, finitude ou
  reproducao;
- comparar cada sistema com o baseline por condicao e por grupo de ruido;
- considerar fronteira de Pareto, degradacoes e estabilidade, sem soma
  arbitraria em um unico escore;
- congelar no maximo dois finalistas;
- so entao executar o split final operacional;
- gerar escuta privada pre-ponte apenas se ainda houver candidato;
- integrar na VM somente apos aprovacao perceptual.

## Estado deste incremento

- harness comum e manifestos hashados implementados;
- adaptador do baseline implementado;
- OM-LSA/IMCRA, RNNoise, WebRTC APM e DeepFilterNet implementados e medidos
  nas 72 condicoes de validacao;
- WebRTC APM foi rejeitado na configuracao oficial padrao `moderate`;
- DeepFilterNet foi rejeitado depois da comparacao multicriterio;
- finalistas congelados: RNNoise e OM-LSA/IMCRA;
- baseline mantido como referencia;
- nenhuma VM ou fonte privada utilizada;
- revisao independente com `claude --chrome` tentada, mas indisponivel por
  limite de sessao da conta ate 17h de 2026-06-13.
