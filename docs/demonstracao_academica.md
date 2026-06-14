# Demonstração acadêmica em camadas

Data-base: 14 de junho de 2026.

## Objetivo

Demonstrar o que foi efetivamente comprovado sem misturar qualidade do DSP,
integração funcional e continuidade temporal da VM.

## Camada 1 - DSP audível

Apresentar uma comparação A/B entre:

- fala ruidosa autorizada ou pública;
- a mesma fala tratada pelo RNNoise.

Regras:

- usar a mesma entrada e o mesmo corte;
- não normalizar seletivamente as saídas;
- informar que a comparação ocorre antes da ponte e do endpoint;
- não publicar nem distribuir voz privada;
- preferir material público quando a apresentação for gravada ou publicada.

Mensagem autorizada:

> O RNNoise foi o candidato preferido na escuta cega pré-ponte e apresentou
> forte supressão objetiva no corpus avaliado.

### Reproduzir com qualquer WAV

Depois de compilar a DLL, qualquer WAV mono ou estéreo pode ser convertido
para mono a 16 kHz e processado pelo mesmo RNNoise persistente:

```powershell
.\scripts\native\Build-RNNoiseAdapter.ps1
python -m realtime_audio.process_wav_rnnoise `
  --input caminho\audio_ruidoso.wav `
  --output resultados\demo_rnnoise\audio_tratado.wav
```

O JSON criado ao lado da saída registra hashes, formato, tempos por bloco, RTF
e latência algorítmica. Não há normalização seletiva.

No exemplo público local `resultados/audio/exemplo_noisy.wav`, com
`resultados/audio/exemplo_clean.wav` usado apenas como referência objetiva, o
SNR passou de 2,31 dB para 7,33 dB após alinhamento do atraso causal: melhoria
de 5,02 dB. O processamento dos 150 blocos teve RTF total 0,020 e nenhum bloco
acima do orçamento de 20 ms. Os WAVs gerados permanecem fora do Git; o comando,
o código e os resultados numéricos são reproduzíveis.

## Camada 2 - Microfone virtual funcional

Alimentar o SYSVAD com um sinal sintético conhecido e capturá-lo em um cliente
Windows.

Prova recomendada:

- tom de 440 Hz;
- PCM16 mono a 16 kHz;
- duração curta e determinística;
- captura por cliente externo;
- confirmação de duração, frequência dominante, pico e silêncio após a parada
  do produtor.

Mensagem autorizada:

> O endpoint virtual e a ponte usuário-driver são funcionalmente capazes de
> transportar e expor um sinal conhecido.

## Camada 3 - Integração técnica

Exibir um resumo dos registros:

- hash da DLL RNNoise e dos artefatos do ensaio;
- 1.000 blocos recebidos por perna;
- zero erro de sequência, CRC, enquadramento, perda ou duplicação;
- zero erro de escrita, overrun do driver ou requisição rejeitada nos gates
  aceitos;
- percentis de processamento abaixo do orçamento de 20 ms.

Mensagem autorizada:

> Processamento, transporte e escrita no driver passaram em gates separados e
> reproduzíveis.

## Slide de limite obrigatório

Apresentar o contrafactual SYSVAD versus HDA e declarar:

- ambos os endpoints tiveram sinais tardios repetidos;
- o resultado é compatível com limitação global do VirtualBox/NEM;
- o resultado não prova correção do driver;
- a continuidade temporal ponta a ponta não foi demonstrada.

## O que não fazer

- Não apresentar captura longa da VM como prova de tempo real.
- Não repetir amostras, editar WAVs ou aumentar filas para esconder lacunas.
- Não atribuir ao RNNoise perdas que aparecem depois do DSP.
- Não chamar latência estimada por componentes de medição física.
- Não usar áudio privado em repositório, transmissão pública ou material de
  divulgação.

## Ordem sugerida

1. problema e objetivo;
2. comparação A/B do DSP;
3. sinal sintético no microfone virtual;
4. logs e contadores da integração;
5. limite temporal encontrado;
6. próximo passo em Windows nativo.
