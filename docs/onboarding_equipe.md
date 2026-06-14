# Onboarding da equipe

Data-base: 14 de junho de 2026.

## Visao geral

O projeto atual e:

**Prototipo de Reducao de Ruido Local para Voz Humana no Windows: Avaliacao
Algoritmica, RNNoise e Microfone Virtual.**

O objetivo e processar voz localmente, selecionar um metodo de reducao de ruido
por criterios objetivos e perceptuais e disponibilizar o sinal tratado a
aplicativos Windows por meio de um endpoint virtual de captura.

O trabalho nao comprova baixa latencia fisica ponta a ponta nem constitui
produto comercial. O estado correto e **prototipo academico integrado**.

## Pergunta central

Como construir e avaliar, no Windows, um fluxo local de reducao de ruido para
voz humana que combine:

- qualidade perceptual;
- processamento causal por blocos;
- custo compativel com operacao continua;
- transporte PCM integro;
- integracao com aplicativos por um microfone virtual;
- continuidade temporal verificavel?

## Evolucao tecnica

1. STFT e Wavelet foram comparadas como ponto de partida.
2. A STFT causal adaptativa tornou-se o baseline operacional.
3. DWT e WPT foram refinadas; a WPT causal passou gates instrumentais, mas foi
   rejeitada na escuta pre-ponte.
4. O harness de literatura comparou OM-LSA/IMCRA, RNNoise, WebRTC APM NS e
   DeepFilterNet3.
5. RNNoise foi selecionado como candidato principal; OM-LSA/IMCRA ficou como
   reserva perceptual.
6. O RNNoise persistente foi integrado por DLL, com estado continuo e
   resampling causal.
7. A saida foi transportada por PCM v1 ate um SYSVAD modificado que expoe um
   endpoint virtual.
8. O endpoint funcionou com sinal sintetico, mas a continuidade prolongada
   ficou limitada no VirtualBox/NEM.

## Arquitetura

```text
fonte ou replay
  -> DSP causal em espaco de usuario
  -> PCM16 mono, 16 kHz, blocos de 20 ms
  -> ponte PCM v1 por IOCTL
  -> ring buffer nao paginado no SYSVAD
  -> endpoint virtual de captura
  -> cliente Windows
```

O DSP e o transporte nao devem ser confundidos com o comportamento temporal do
endpoint.

## Evidencias consolidadas

### DSP

- RNNoise ficou em primeiro na escuta cega pre-ponte.
- Latencia algoritmica medida: aproximadamente `21,3 ms`.
- No host, 30.000 blocos tiveram p99 de `1,951 ms` e zero estouro do bloco de
  20 ms.
- Na VM isolada, 3.000 blocos tiveram p99 de `2,021 ms` e zero estouro.

### Transporte

- Quatro pernas host-convidado entregaram 1.000 blocos cada.
- Nao houve erro de sequencia, CRC, framing, perda ou duplicacao.

### Microfone virtual

- O protocolo PCM v1 usa blocos de 320 amostras.
- O SYSVAD modificado capturou corretamente um tom de 440 Hz.
- Interface de controle, exclusividade do produtor, reconexao e contadores
  foram exercitados.

### Limite temporal

- O VirtualBox/NEM nao sustentou cadencia confiavel no endpoint.
- SYSVAD e HDA apresentaram notificacoes tardias no contrafactual orientado a
  evento.
- O resultado e compativel com limitacao global da VM, mas nao prova que o
  driver SYSVAD esteja correto.

## Demonstracao recomendada

1. A/B entre fala ruidosa e a mesma fala tratada pelo RNNoise, antes da ponte.
2. Tom sintetico alimentando o SYSVAD e capturado por cliente Windows.
3. Logs, hashes e contadores de DSP, transporte e escrita no driver.
4. Slide explicito sobre o limite temporal da VM.

Para processar qualquer WAV:

```powershell
python -m realtime_audio.process_wav_rnnoise `
  --input caminho\audio_ruidoso.wav `
  --output resultados\demo_rnnoise\audio_tratado.wav
```

## Proximo gate

A proxima validacao deve ocorrer em Windows nativo, em bancada isolada e
recuperavel:

1. medir baseline fisico antes do SYSVAD;
2. instalar o pacote de forma controlada;
3. repetir a configuracao congelada da VM, sem retuning;
4. validar tom, IOCTLs, PCM v1 e captura;
5. executar matriz pareada bypass/RNNoise;
6. exigir zero perda e zero underrun;
7. medir latencia fisica;
8. somente entao executar fala controlada e escuta cega do endpoint.

Detalhes:

- `docs/migracao_windows_nativo.md`;
- `docs/validacao_windows_nativo.md`.

## Privacidade e publicacao

- Nao versionar voz privada, consentimentos, datasets brutos ou binarios de
  terceiros.
- Nao publicar capturas da VM com lacunas como demonstracao de qualidade.
- Nao editar ou repetir amostras para esconder falhas.
- Preservar hashes, configuracoes, metricas e limitacoes.

## Mapa essencial do repositorio

| Local | Finalidade |
|---|---|
| `entrega3.tex` / `entrega3.pdf` | relatorio final |
| `apresentacao_fechamento.tex` / `.pdf` | apresentacao final |
| `benchmark_audio/` | benchmarks, metodos e harness de literatura |
| `realtime_audio/` | processamento causal, RNNoise, ponte e UI |
| `scripts/native/` | adaptadores nativos |
| `scripts/vm/` | automacao e diagnosticos historicos da VM |
| `tests/` | testes automatizados |
| `docs/estado_projeto.md` | estado consolidado |
| `docs/checkpoints.md` | historico completo |
| `docs/demonstracao_academica.md` | roteiro de demonstracao |

## Ordem de leitura

1. `README.md`;
2. `docs/estado_projeto.md`;
3. `docs/demonstracao_academica.md`;
4. `docs/migracao_windows_nativo.md`;
5. `docs/validacao_windows_nativo.md`;
6. `entrega3.pdf`;
7. `docs/checkpoints.md`, apenas para detalhes historicos.
