# Avaliacao objetiva e perceptual com voz autoral

## Escopo

Este documento prepara a etapa posterior a ingestao das gravacoes dos tres
autores. Ele nao substitui o protocolo de gravacao em
`docs/protocolo_voz_autoral.md` e nao autoriza publicar audio por si so.

A avaliacao deve usar os parametros congelados da PC-1/PC-2:

- subtracao espectral causal adaptativa como candidata principal;
- Wiener causal adaptativo como alternativa;
- estimador offline de baixa energia apenas como referencia nao causal;
- Wavelet refinada apenas como baseline leve;
- bypass como controle.

Nao ha nova busca de parametros nesta etapa. Se a Sessao B revelar problema e
for necessario alterar parametro, a rodada deve ser declarada como nova
iteracao, sem tratar os valores anteriores como confirmacao final.

## Entrada esperada

Antes de rodar a avaliacao:

1. coletar autorizacao dos participantes;
2. gravar `raw_quiet`, `raw_noise` e `raw_live_noisy`;
3. preencher o manifesto privado;
4. executar `benchmark_audio.prepare_authored_voice`;
5. revisar erros e avisos do relatorio de qualidade.

Exemplo de ingestao:

```powershell
python -m benchmark_audio.prepare_authored_voice `
  --manifest dados/private/authored_voice/manifests/session_b_raw_manifest.csv `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --quality-report resultados/authored_voice/ingestion/session_b_quality_report.json
```

Por padrao, a avaliacao autoral recusa arquivos com `prepared_with_warnings`.
Use `--allow-warnings` somente depois de registrar por que os avisos sao
aceitaveis para aquela rodada.

## Avaliacao objetiva

Rodada final prevista:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --session session_b `
  --results-dir resultados/authored_voice/evaluation/session_b_final
```

Para depuracao antes da confirmacao final, use `session_a`:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_a_prepared_manifest.csv `
  --session session_a `
  --results-dir resultados/authored_voice/evaluation/session_a_dev
```

Saidas:

- `controlled_metrics.csv`: uma linha por condicao pareada e metodo;
- `controlled_summary.csv`: agregacao por metodo e SNR;
- `controlled_by_speaker_noise.csv`: agregacao por falante e ruido;
- `operational_live_noisy_metrics.csv`: estatisticas de fala naturalmente
  ruidosa, sem metricas pareadas;
- `metadata_authored_evaluation.json`: manifestos, parametros, politicas e
  contagens.

As metricas SNR, SI-SDR e MSE sao calculadas somente em misturas controladas
`raw_quiet + raw_noise` ou `raw_quiet + ruido conhecido`. Para
`raw_live_noisy`, a CLI registra apenas comprimento, picos, RMS, tempo, RTF,
percentis e memoria. Nao fabricar SNR nem SI-SDR sem referencia limpa
sincronizada.

## Matriz pequena recomendada

A CLI limita por padrao a tres trechos `raw_quiet` por falante e dois ruidos,
com SNRs -5, 0, 5 e 10 dB. Esses limites mantem a rodada auditavel e podem ser
ajustados:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --session session_b `
  --max-clean-per-speaker 3 `
  --max-noises 2 `
  --snrs -5 0 5 10
```

Use `--max-clean-per-speaker 0` ou `--max-noises 0` apenas se a equipe decidir
processar todos os arquivos preparados. Registre essa decisao no diario.

## Escuta critica

A escuta deve ser estruturada antes de abrir resultados da Sessao B:

- ordem aleatoria;
- identificadores cegos;
- volume constante;
- avaliadores registrados como autores do projeto;
- criterios separados para inteligibilidade, naturalidade, ruido residual,
  artefatos e preferencia;
- nenhum reajuste apos a rodada final sem declarar nova iteracao.

Modelo de formulario:

```text
dados/templates/authored_voice/perceptual_rating_template.csv
```

Campos principais:

- `listener_id`;
- `trial_id`;
- `blind_label`;
- `intelligibility_1_5`;
- `naturalness_1_5`;
- `residual_noise_1_5`;
- `artifacts_1_5`;
- `preference_rank`;
- `notes`.

O arquivo de chave cega, quando existir, deve ficar em area privada se apontar
para WAVs autorais. O relatorio final deve publicar somente agregados e
exemplos explicitamente autorizados.

## Criterios de auditoria

Antes de atualizar `entrega3.tex`, conferir:

- todos os CSVs sem `NaN` ou infinito;
- bypass com melhoria media de SNR igual a zero nas misturas controladas;
- Sessao B ausente de qualquer ajuste de parametros;
- raw_live_noisy sem SNR/SI-SDR pareadas;
- autorizacao e nivel de compartilhamento documentados;
- nenhum WAV privado versionado;
- limitacoes registradas para tres falantes e avaliadores autores.
