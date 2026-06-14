# Revisao do codigo Wavelet para Gabriel

Este guia concentra os arquivos e comandos necessarios para revisar a parte de
Wavelets do projeto sem precisar navegar pelo repositorio inteiro.

## Leitura rapida

1. Implementacao principal:
   - `benchmark_audio/denoise.py`
   - Comecar por:
     - `DenoiseConfig`, campos `wavelet`, `wavelet_level`,
       `wavelet_mode`, `wavelet_threshold_strategy` e
       `wavelet_threshold_scale`;
     - `wavelet_denoise`;
     - `process_method`.
2. Busca de parametros e comparacao:
   - `benchmark_audio/run_refinement.py`
   - Comecar por:
     - `wavelet_candidates`;
     - `evaluate_candidate`;
     - `select_candidates`;
     - `comparison_candidates`;
     - `evaluate_comparison`.
3. Testes minimos relacionados:
   - `tests/test_denoise.py`;
   - `tests/test_refinement.py`.
4. Resultados que explicam a conclusao atual:
   - `resultados/demand_refinement/tabelas/validation_candidates.csv`;
   - `resultados/demand_refinement/tabelas/selected_configs.csv`;
   - `resultados/demand_refinement/tabelas/comparison_overall.csv`;
   - `resultados/demand_refinement/tabelas/comparison_summary.csv`;
   - `resultados/demand_refinement/tabelas/comparison_metrics.csv`.

## Dependencias

As dependencias estao em `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
```

Para a revisao estatica da Wavelet, as dependencias centrais sao:

- `numpy`;
- `scipy`;
- `pandas`;
- `PyWavelets`.

`sounddevice` so e necessario para os testes de captura em tempo real, nao para
revisar ou reproduzir o benchmark offline de Wavelets.

## Implementacao Wavelet

Arquivo: `benchmark_audio/denoise.py`.

O metodo registrado no pipeline se chama `wavelet_soft`, mas esse nome e legado:
a funcao usa o modo configurado em `DenoiseConfig.wavelet_mode`. Portanto uma
configuracao com `wavelet_mode="hard"` realmente aplica limiarizacao hard.

Fluxo da funcao `wavelet_denoise`:

1. Calcula o nivel maximo permitido por `pywt.dwt_max_level`.
2. Usa `pywt.wavedec` com borda `symmetric`.
3. Mantem os coeficientes de aproximacao sem limiarizacao.
4. Estima o ruido por MAD:
   - estrategia `global`: usa o detalhe mais fino para todas as escalas;
   - estrategia `per_scale`: estima sigma em cada escala.
5. Calcula limiar universal escalado:
   - `threshold_scale * sigma * sqrt(2 log(N))`.
6. Aplica `pywt.threshold` em cada detalhe com modo `soft` ou `hard`.
7. Reconstrui com `pywt.waverec` e preserva o comprimento original.

Pontos importantes para revisar:

- se o uso de MAD no detalhe mais fino e adequado para fala com ruido DEMAND;
- se o limiar universal ficou agressivo ou conservador demais;
- se manter a aproximacao sem limiarizacao esta coerente com o objetivo;
- se o modo de borda `symmetric` introduz artefatos relevantes;
- se faria sentido testar limiares dependentes de banda de fala ou uma regra
  tipo SURE/BayesShrink em vez da regra universal escalada.

## Grade de parametros testada

Arquivo: `benchmark_audio/run_refinement.py`.

A funcao `wavelet_candidates` avaliou 72 configuracoes:

- familias: `db4`, `sym4`, `coif1`;
- niveis: `3`, `5`;
- modos: `soft`, `hard`;
- estrategias: `global`, `per_scale`;
- fatores de limiar: `0.50`, `0.75`, `1.00`.

A selecao foi feita apenas na validacao. O conjunto final operacional foi usado
depois para comparacao.

Divisoes:

- validacao: falantes `jackson`, `nicolas`, `theo` e ruidos `DKITCHEN`,
  `OOFFICE`;
- final operacional: falantes `george`, `lucas`, `yweweler` e ruidos
  `PCAFETER`, `STRAFFIC`.

## Comandos uteis

Rodar testes rapidos:

```powershell
python -m unittest tests.test_denoise tests.test_refinement
```

Reexecutar o refinamento, usando os dados locais ja preparados:

```powershell
python -m benchmark_audio.run_refinement --results-dir resultados/demand_refinement_revisao_gabriel
```

Se os arquivos de fala preparados nao existirem no computador, usar:

```powershell
python -m benchmark_audio.run_refinement --prepare-speech --results-dir resultados/demand_refinement_revisao_gabriel
```

Esse comando ainda espera que os ruidos DEMAND preparados existam em
`dados/demo/noise_demand/`. Os arquivos brutos grandes do DEMAND ficam fora do
Git; para reproduzir a preparacao, ver `README_benchmark.md` e
`benchmark_audio/prepare_environmental_noise.py`.

## Consultas rapidas em CSV

Top 15 configuracoes Wavelet na validacao:

```powershell
@'
import pandas as pd
df = pd.read_csv("resultados/demand_refinement/tabelas/validation_candidates.csv")
cols = [
    "candidate_id",
    "snr_improvement_mean_db",
    "snr_improvement_min_db",
    "snr_degradation_fraction",
    "si_sdr_improvement_mean_db",
    "wavelet",
    "wavelet_level",
    "wavelet_mode",
    "wavelet_threshold_strategy",
    "wavelet_threshold_scale",
]
print(
    df[df.family == "wavelet"]
    .sort_values(["snr_improvement_mean_db", "si_sdr_improvement_mean_db"], ascending=False)
    .head(15)[cols]
    .to_string(index=False)
)
'@ | python -
```

Comparacao final agregada:

```powershell
@'
import pandas as pd
df = pd.read_csv("resultados/demand_refinement/tabelas/comparison_overall.csv")
cols = [
    "split",
    "candidate_id",
    "family",
    "snr_improvement_mean_db",
    "snr_improvement_min_db",
    "snr_degradation_fraction",
    "si_sdr_improvement_mean_db",
    "rtf_mean",
]
print(df[df.split == "final"][cols].to_string(index=False))
'@ | python -
```

Piores e melhores condicoes da Wavelet refinada no final:

```powershell
@'
import pandas as pd
df = pd.read_csv("resultados/demand_refinement/tabelas/comparison_metrics.csv")
w = df[
    (df.split == "final")
    & (df.candidate_id == "wavelet_sym4_l3_hard_global_s0.5")
]
cols = [
    "speaker",
    "noise",
    "noise_group",
    "snr_target_db",
    "input_snr_db",
    "output_snr_db",
    "snr_improvement_db",
    "si_sdr_improvement_db",
]
print("Piores:")
print(w.sort_values("snr_improvement_db").head(10)[cols].to_string(index=False))
print("\nMelhores:")
print(w.sort_values("snr_improvement_db", ascending=False).head(10)[cols].to_string(index=False))
'@ | python -
```

## Resultado atual a conferir

Na validacao, a melhor configuracao Wavelet foi:

- `wavelet_sym4_l3_hard_global_s0.5`;
- melhoria media de SNR: aproximadamente `+0.137 dB`;
- melhoria media de SI-SDR: aproximadamente `+0.054 dB`;
- fracao de degradacao: aproximadamente `45.8%`.

No conjunto final operacional, essa configuracao ficou praticamente neutra:

- melhoria media de SNR: aproximadamente `+0.026 dB`;
- melhoria media de SI-SDR: aproximadamente `+0.008 dB`;
- fracao de degradacao: aproximadamente `11.1%`.

Interpretacao atual: o refinamento reduziu dano em relacao ao baseline
`db4`, nivel 5, soft, mas nao demonstrou supressao relevante de ruido no
protocolo atual.

## Decisao apos discussao com Gabriel

A conclusao acima deve ser lida com precisao: ela vale para a implementacao DWT
com limiarizacao hard/soft, MAD e limiar universal escalado. Ela nao encerra a
linha Wavelet como familia de metodos.

A proxima hipotese aceita para investigacao e abandonar shrinkage global
estatico e testar uma arquitetura mais adaptativa:

- `Wavelet Packet Transform` para decompor tambem as subbandas de baixa
  frequencia;
- rastreamento temporal de ruido por subbanda, inspirado em MCRA/IMCRA;
- ganho Wiener suave por subbanda/coeciente, em vez de threshold hard/soft.

Essa nova trilha deve entrar como metodo separado, por exemplo
`wavelet_packet_wiener`, mantendo `wavelet_soft` como baseline historico. O
plano de implementacao esta em `docs/plano_wavelet_packet_wiener.md`.

## Arquivos de audio para escuta

Ha exemplos salvos em:

- `resultados/demand_refinement/audio/`.

Arquivos relevantes:

- `final_pcafeter_ch01_seg01_0db_clean.wav`;
- `final_pcafeter_ch01_seg01_0db_noisy.wav`;
- `final_pcafeter_ch01_seg01_0db_wavelet_default_db4_l5_soft.wav`;
- `final_pcafeter_ch01_seg01_0db_wavelet_sym4_l3_hard_global_s0.5.wav`;
- saidas STFT equivalentes para comparacao auditiva.

Esses WAVs sao exemplos diagnosticos. A conclusao numerica vem dos CSVs, nao de
uma unica escuta.

## Pontos de atencao para a revisao

- O nome `wavelet_soft` pode induzir erro de leitura, pois o modo hard tambem
  passa por esse caminho.
- A DWT atual nao estima um perfil explicito de ruido; ela aplica shrinkage por
  coeficientes.
- A proxima revisao nao deve insistir apenas em mais fatores de limiar; a
  mudanca relevante e testar WPT + tracking temporal de ruido + ganho Wiener.
- A comparacao refinada removeu o silencio inicial garantido, o que torna a
  avaliacao mais justa para STFT, mas a melhor STFT ainda usa um estimador
  offline por baixa energia.
- A versao causal posterior do projeto foi feita para STFT, nao para Wavelet.
- A avaliacao ainda usa SNR e SI-SDR; uma revisao perceptual pode encontrar
  diferencas que essas metricas nao capturam.
- Houve warning numerico do PyWavelets em uma rodada realtime antiga; os CSVs
  daquele teste nao tinham `NaN` ou infinito, mas vale manter no radar se a
  Wavelet voltar a ser testada em streaming.

## Onde a conclusao aparece no texto

- `docs/auditoria_resultados.md`, secao "Refinamento Wavelet";
- `docs/checkpoints.md`, Checkpoint 18;
- `entrega3.tex`, trechos da tabela de refinamento e conclusao.
