# Checklist de release PC

Data-base: 2026-06-08

Este checklist congela a superficie operacional da plataforma PC atual. Ele nao
declara produto comercial pronto, driver proprio, baixa latencia fisica
ponta a ponta ou resultado de voz autoral. O release PC e a demonstracao
Windows da STFT causal adaptativa por blocos.

## Escopo do release

- Implementacao principal: `stft_subtraction` com estimador causal adaptativo.
- Taxa de amostragem: 16 kHz.
- Bloco externo: 20 ms.
- STFT: `n_fft=512`, `hop_length=160`.
- Parametros de supressao: `spectral_alpha=1.5`, `spectral_floor=0.02`.
- Estimador causal: aquecimento de 250 ms e historico passado de 500 ms.
- Estado causal maximo observado: 60.900 bytes.
- Presets oficiais da CLI:
  - `self-test`;
  - `input-only`;
  - `wired`.

## Comandos oficiais

Verificacao automatizada:

```powershell
python -m pytest
```

Smoke sem dispositivo fisico:

```powershell
python -m realtime_audio.windows_realtime --pc-demo self-test --duration 1
```

Validacao prolongada sem dispositivo fisico:

```powershell
python -m realtime_audio.windows_realtime --pc-demo self-test --duration 600
```

Validacao fisica de entrada, sem reproducao:

```powershell
python -m realtime_audio.windows_realtime --pc-demo input-only --duration 600
```

Demo full-duplex cabeada no PC validado:

```powershell
python -m realtime_audio.windows_realtime --pc-demo wired --duration 600
```

Antes de usar `wired`, confirmar fone cabeado, volume baixo e indices de
dispositivo. Se o Windows reorganizar dispositivos, rodar:

```powershell
python -m realtime_audio.windows_realtime --list-devices
```

e usar o comando expandido com indices atualizados.

## Artefatos esperados

- `resultados/windows_realtime_longrun/*_metrics.json`: metricas de self-test e
  input-only.
- `resultados/windows_realtime_longrun/*_blocks.csv`: metricas por bloco.
- `resultados/windows_realtime_wired/*_metrics.json`: metricas full-duplex
  cabeadas.
- `resultados/windows_realtime_wired/*_blocks.csv`: blocos da demonstracao
  cabeada.
- `resultados/tabelas/realtime_windows_wired.csv`: resumo consolidado da rodada
  cabeada.
- Nenhum WAV e salvo nos presets oficiais, pois todos aplicam `--no-save`.

## Evidencias de estabilidade

- `python -m pytest`: 50 testes passaram em 2026-06-08.
- `--pc-demo self-test --duration 1`: 50 blocos, pior bloco 1,612 ms,
  RTF medio 0,049, zero blocos acima de 20 ms e `status_counts` vazio em
  `synthetic_stft_subtraction_20ms_20260608_114451_metrics.json`.
- Self-test Windows de 600 s: 30.000 blocos, media 0,987 ms, p95 1,271 ms,
  p99 1,594 ms, pior bloco 4,127 ms, RTF medio 0,049, zero blocos acima de
  20 ms e `status_counts` vazio.
- Captura fisica input-only de 600 s: 29.998 blocos, media 1,280 ms,
  p95 2,205 ms, p99 3,904 ms, pior bloco 6,799 ms, RTF medio 0,064,
  zero blocos acima de 20 ms e `status_counts` vazio.
- Full-duplex cabeado de 600 s: 29.998 blocos, media 1,259 ms, p95 1,965 ms,
  p99 3,283 ms, pior bloco 7,301 ms, RTF medio 0,063, zero blocos acima de
  20 ms e `status_counts` vazio.

## Demonstracao segura

1. Comecar sempre por `--pc-demo self-test --duration 1`.
2. Para demonstracao fisica sem risco de realimentacao, usar primeiro
   `--pc-demo input-only --duration 30`.
3. Para `wired`, conectar fone cabeado ou saida controlada, usar volume baixo
   e evitar alto-falante aberto perto do microfone.
4. Fazer smoke curto antes de uma rodada longa:

```powershell
python -m realtime_audio.windows_realtime --pc-demo wired --duration 30
```

5. Encerrar a demonstracao se houver desconforto, eco forte ou volume inseguro.
6. Registrar no diario o comando, arquivo JSON gerado, pior bloco, blocos acima
   de 20 ms, `status_counts` e qualquer observacao subjetiva relevante.

## Limitacoes que devem aparecer na narrativa

- O release comprova estabilidade computacional por bloco no Windows, nao baixa
  latencia fisica ponta a ponta.
- A latencia input-only de 72 ms no JSON e estimativa de 32 ms algoritmicos
  mais 40 ms de entrada; nao e round-trip.
- A latencia do duplex cabeado MME de 272 ms no JSON inclui 200 ms de saida
  reportada pelo driver; nao e medicao fisica de loopback.
- Os presets `input-only` e `wired` assumem indices do PC atual: entrada 2 e,
  para `wired`, saida 8.
- WPT em quadros e achado Wavelet offline; nao e implementacao causal PC.
- Voz autoral ainda nao tem resultados reais e permanece validacao futura.
- Bluetooth nao deve ser usado como evidencia de baixa latencia.

## Fora do release PC

- Driver de microfone virtual proprio.
- Distribuicao comercial ou instalador assinado.
- Medicao fisica de round-trip por loopback.
- Avaliacao perceptual formal.
- Resultados de voz autoral.
- WPT causal em tempo real.

## Criterio de aprovacao

O release PC esta aprovado para defesa tecnica quando:

- `python -m pytest` passa;
- `--pc-demo self-test --duration 1` conclui;
- os documentos preservam as limitacoes acima;
- qualquer demo com saida fisica e feita apenas com fone/saida controlada;
- a apresentacao usa a frase "estavel por blocos" em vez de "baixa latencia
  ponta a ponta".
