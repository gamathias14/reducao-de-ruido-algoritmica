# Questionario extensionista em GitHub Pages

Esta pasta contem uma pagina estatica para aplicar o questionario extensionista
do projeto. Ela foi pensada para funcionar no GitHub Pages sem etapa de build.

## Arquivos principais

- `index.html`: estrutura da pagina.
- `styles.css`: estilo visual e responsividade.
- `app.js`: renderizacao das perguntas, validacao, audio, experimento local e envio.
- `questionario.config.js`: textos, perguntas, audios e endpoint de envio.
- `assets/audio/`: audios curtos e publicos usados na comparacao perceptual.
- `assets/img/ptc_virtual_mic.svg`: icone oficial do projeto.
- `assets/img/logopoli.svg` e `assets/img/logousp.svg`: marcas institucionais usadas no cabecalho e no rodape.

## Publicacao no GitHub Pages

1. Commitar esta pasta no repositorio.
2. No GitHub, abrir `Settings > Pages`.
3. Em `Build and deployment`, escolher `Deploy from a branch`.
4. Selecionar a branch desejada e a pasta `/docs`.
5. A pagina ficara disponivel em:

```text
https://<usuario-ou-org>.github.io/<repositorio>/questionario/
```

## Configurar respostas no Google Sheets

1. Abrir <https://script.google.com/> e criar um projeto.
2. Copiar o conteudo de
   `scripts/google_forms/receber_respostas_questionario_github_pages.gs`
   para o Apps Script.
3. Executar `setupQuestionarioReceiver()` uma vez e autorizar o script.
4. Publicar como Web App:
   - Execute as: `Me`
   - Who has access: `Anyone`
5. Copiar a URL do Web App.
6. Em `questionario.config.js`, preencher:

```js
submission: {
  endpoint: "URL_DO_WEB_APP",
  enabled: true,
}
```

O envio usa `POST` em modo `no-cors`, adequado para GitHub Pages. A pagina nao
consegue ler a resposta detalhada do endpoint, mas o Apps Script registra o
envio na planilha.

## Modelo de auditoria

O Apps Script cria ou reutiliza uma planilha com as abas:

- `responses_raw`: payload completo em JSON, preservando respostas antigas mesmo
  se o questionario mudar.
- `responses_wide`: tabela larga com colunas dinamicas por pergunta.
- `schema_history`: historico de versoes de schema e manifesto de audio.
- `audit`: eventos de recebimento.
- `errors`: payloads rejeitados ou com erro de validacao.

Ao alterar perguntas:

- mantenha o `id` de uma pergunta se ela continuar medindo a mesma coisa;
- crie um `id` novo quando a pergunta mudar de sentido;
- incremente `schemaVersion`;
- nao reutilize IDs removidos para novas perguntas.

## Audios preparados

O Google Forms nao e usado aqui porque a pagina consegue usar players nativos de
audio. Para publicar exemplos:

1. Gerar arquivos curtos em `.mp3` ou `.ogg`.
2. Salvar em `docs/questionario/assets/audio/`.
3. Preencher o campo `src` em `questionario.config.js`, por exemplo:

```js
src: "assets/audio/amostra_rnnoise.mp3"
```

4. Preencher `sha256` com o hash do arquivo, se disponivel.

Os audios devem ser publicos ou autorizados. Nao publicar fala privada, datasets
restritos ou trechos com dados pessoais.

### Manifesto atual de audio

A versao `2026-06-28.4` do questionario usa seis exemplos publicos em MP3,
gerados a partir da mesma amostra ruidosa de referencia:

- `amostra_noisy_reference.mp3`: referencia ruidosa;
- `amostra_rnnoise.mp3`: RNNoise v0.2;
- `amostra_omlsa_imcra.mp3`: OM-LSA/IMCRA;
- `amostra_stft_causal.mp3`: STFT causal adaptativa;
- `amostra_stft_wiener.mp3`: STFT Wiener;
- `amostra_wavelet_soft.mp3`: Wavelet soft.

O arquivo `amostra_rnnoise.mp3` foi regenerado com `startup_preroll_ms = 200`
no pipeline `realtime_audio/process_wav_rnnoise.py`. Esse pre-roll processa os
primeiros 200 ms reais do proprio audio para aquecer o estado do RNNoise e
descarta essa primeira saida antes do passe principal. O comprimento final do
audio e preservado. A decisao foi tomada porque a versao sem pre-roll gerava um
transiente curto perceptivel antes do inicio da fala de teste.

Comandos de referencia para reproduzir essa amostra:

```powershell
python -m realtime_audio.process_wav_rnnoise `
  --input resultados\audio\exemplo_noisy.wav `
  --output tmp\questionario_audio_work\amostra_rnnoise_preroll_real.wav `
  --metrics-json tmp\questionario_audio_work\amostra_rnnoise_preroll_real.json `
  --startup-preroll-ms 200 `
  --overwrite

ffmpeg -y `
  -i tmp\questionario_audio_work\amostra_rnnoise_preroll_real.wav `
  -codec:a libmp3lame -b:a 96k -ar 16000 -ac 1 `
  docs\questionario\assets\audio\amostra_rnnoise.mp3
```

O hash SHA-256 registrado no manifesto para essa versao do RNNoise e:

```text
9c91587755d8410d7273798026580f0db0d1720659eee105a31845cc7fa2ee4c
```

## Experimento local com audio proprio

A area experimental permite gravar ou carregar um audio curto somente no
navegador. A versao atual nao envia esse arquivo no payload e ainda nao carrega
processadores RNNoise/STFT em WebAssembly/JavaScript. Quando esses modulos forem
incluidos, o fluxo deve continuar local, sem upload de voz para servidor.
