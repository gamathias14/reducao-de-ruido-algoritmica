# DFN3 local inline user-mode baseline

Rodada nativa no Windows host, em user-mode, sem VM, sem driver, sem SYSVAD,
sem ponte PCM v1 e sem alteracao de BIOS/Secure Boot/Hyper-V.

Objetivo: medir o custo real do DeepFilterNet3 C API persistente em um desenho
compativel com tempo real, separando a inferencia do callback de audio por um
worker e ring buffer.

Artefatos:

```text
tmp\dfn_native\wasapi_worker_bench\results\b3_mixed_60s_worker\
```

Comando reproduzido em 2026-07-01:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tmp\dfn_native\wasapi_worker_bench\run_b3_pre_vm.ps1
```

## R12 - DFN3 worker/ring 60 s - 2026-07-01

Input:

```text
tmp\dfn_native\wasapi_worker_bench\b3_inputs\mixed_60s_capi_input48.wav
```

Parametros principais:

- DeepFilterNet3 C API via `tmp\t_release\x86_64-pc-windows-msvc\release\df.dll`;
- modelo `tmp\dfn_native\DeepFilterNet3_onnx.tar.gz`;
- frame DFN3 de `480` amostras, isto e, `10 ms` a 48 kHz;
- `post_filter_beta=1.0`;
- `atten_lim=100.0`;
- worker thread com MMCSS;
- render callback com MMCSS;
- ring com capacidade de `32` frames DFN;
- prebuffer de `12` frames DFN;
- render mudo.

Resultado bruto:

- status `PASS`;
- duracao `60 s`;
- frames processados `6000`;
- endpoint/callback em `48000 Hz`, 2 canais, float32;
- WASAPI shared buffer `4800` frames (`100 ms`);
- `timeBeginPeriod_ok=true`;
- `render_mmcss_ok=true`;
- `worker_mmcss_ok=true`;
- worker mean `0,982 ms`;
- worker p95 `1,801 ms`;
- worker p99 `2,189 ms`;
- worker p999 `2,617 ms`;
- worker max `5,168 ms`;
- worker acima de `4/8/10 ms`: `1/0/0`;
- callback p99 `0,043 ms`;
- callback p999 `0,087 ms`;
- callback max `0,155 ms`;
- underflow `0`;
- ring minimo antes do callback `480` amostras.

Resultado estavel B3, ignorando apenas o primeiro frame de worker como criterio
historico da bancada:

- status estavel `PASS`;
- frames no gate estavel `5999`;
- worker p99 `2,188 ms`;
- worker p999 `2,598 ms`;
- worker max `3,957 ms`;
- worker acima de `4/8/10 ms`: `0/0/0`;
- callback p99 `0,043 ms`;
- callback p999 `0,087 ms`;
- callback max `0,155 ms`;
- underflow `0`;
- ring minimo antes do callback `480` amostras.

## Interpretacao

O host Windows sustenta o DeepFilterNet3 C API persistente com ampla folga no
desenho worker/ring. O processamento p99 ficou em aproximadamente `2,2 ms` para
um bloco de `10 ms`, sem underflow e com callback muito abaixo de `1 ms`.

Combinado com o baseline `dfn3_local_loopback`, o estado atual fica:

- transporte/receptor local nativo: aprovado;
- ring diagnostico local nativo: aprovado;
- DFN3 C API persistente em worker/ring: aprovado;
- VM VirtualBox/NEM: integridade funcional aprovada, mas baixa latencia nao
  confiavel por scheduler/rede do ambiente.

## Decisao

Esta rodada confirma que o proximo bloqueio tecnico nao e o custo basico do
DeepFilterNet3 no host. O retorno a SYSVAD/ponte PCM v1 ainda deve ser feito
com cautela, mas agora com a fase nativa user-mode validada.
