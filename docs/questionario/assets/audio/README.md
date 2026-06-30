# Audios do questionario

Coloque aqui apenas audios curtos, publicos ou autorizados, usados na comparacao
perceptual do questionario.

Formatos recomendados:

- `.mp3` para compatibilidade ampla;
- `.ogg` como alternativa aberta.

Depois de adicionar os arquivos, atualize `../../questionario.config.js` nos
campos `src` e `sha256` de cada item de `audioComparison.items`.

Manifesto ativo em `2026-06-30.1` com audios de aproximadamente `8,5 s`:

- `amostra_noisy_reference.mp3`
- `amostra_rnnoise.mp3`
- `amostra_dfn3_default.mp3`

Os demais MP3s no diretorio sao historico de comparacoes anteriores e nao
aparecem no questionario enquanto nao estiverem listados em
`audioComparison.items`.
