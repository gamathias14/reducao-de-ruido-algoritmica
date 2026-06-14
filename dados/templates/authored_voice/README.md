# Modelos para voz autoral

Estes arquivos são modelos versionáveis. Os manifestos preenchidos, termos
assinados, WAVs brutos e derivados devem permanecer nas pastas privadas ou
ignoradas pelo Git.

Arquivos:

- `raw_manifest_template.csv`: uma linha por WAV bruto;
- `session_sheet_template.csv`: uma linha por sessão de gravação;
- `authorization_registry_template.csv`: registro codificado da autorização,
  sem nome ou assinatura;
- `perceptual_rating_template.csv`: formulario de escuta critica com
  identificadores cegos.

Fluxo:

1. Copie os modelos para `dados/private/authored_voice/`.
2. Preencha somente códigos neutros.
3. Coloque os WAVs em `dados/raw/authored_voice/`.
4. Execute `python -m benchmark_audio.prepare_authored_voice --manifest ...`.
5. Para a escuta, copie `perceptual_rating_template.csv` e preencha uma linha
   por avaliador e trecho cego.

O termo assinado deve seguir `docs/autorizacao_voz_autoral.md` e ficar em
`dados/private/authored_voice/consent/`.
