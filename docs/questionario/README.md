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

## Atualizar dashboard de respostas

A analise das respostas tambem fica no mesmo Apps Script, sem bibliotecas
externas. Depois de novas respostas chegarem na planilha, abra o projeto em
<https://script.google.com/> e execute manualmente:

```js
rebuildDashboard()
```

A funcao le `responses_raw` como fonte canonica e recria/atualiza as abas:

- `dashboard_metrics`: tabela longa com metricas por bloco, pergunta,
  alternativa/nota, `N`, contagem, percentual, media, mediana e ranking quando
  aplicavel.
- `dashboard`: resumo visual com data/hora de atualizacao, `questionnaireId`,
  `schemaVersion`, total de respostas, observacao de privacidade e graficos
  nativos do Google Sheets.
- `coded_open_answers`: respostas abertas preparadas para codificacao manual,
  preservando colunas manuais ja preenchidas quando o dashboard for reconstruido.

A reconstrucao nao apaga `responses_raw`, nao sobrescreve respostas existentes e
nao altera o receptor `doPost`. Se uma pergunta nova for adicionada no futuro,
o script tenta aproveitar `questionSnapshot` e `answers` para manter
compatibilidade com schemas antigos.

As respostas abertas nao recebem conclusoes automaticas. A aba
`coded_open_answers` apenas organiza o texto para codificacao manual com
categorias como ruido de fundo, eco, voz abafada, privacidade, latencia,
travamento, dificuldade de configuracao, clareza da voz, uso em chamadas e
outro.

A analise registra explicitamente que os audios dos usuarios nao sao coletados,
enviados ou armazenados pelo questionario.

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

A versao `2026-06-30.1` do questionario usa tres exemplos publicos em MP3,
gerados a partir da mesma amostra ruidosa de referencia:

- `amostra_noisy_reference.mp3`: referencia ruidosa;
- `amostra_rnnoise.mp3`: RNNoise com normalizacao de loudness e equalizacao leve
  de presenca;
- `amostra_dfn3_default.mp3`: DeepFilterNet3 default offline com normalizacao de
  loudness.

Os exemplos OM-LSA/IMCRA, STFT e Wavelet permanecem no diretorio como historico,
mas nao fazem parte do manifesto ativo nem aparecem na comparacao atual.

O arquivo `amostra_rnnoise.mp3` foi atualizado a partir da variante escolhida na
avaliacao local `rnnoise_presence_eq_loudnorm`. A base continua sendo o RNNoise
com `startup_preroll_ms = 200`, mas a amostra publicada inclui normalizacao de
loudness e um EQ leve de presenca para reduzir a percepcao de voz apagada/abafada
sem alterar o nucleo do metodo de reducao de ruido.

O arquivo `amostra_dfn3_default.mp3` veio da avaliacao offline
`questionario_amostra_deepfilternet_loudnorm`. Ele representa o candidato
DeepFilterNet3 default aprovado perceptualmente como comparacao exploratoria,
mas ainda nao prova tempo real, baixa latencia nem integracao com o microfone
virtual Windows.

Comando de referencia para reproduzir as variantes RNNoise:

```powershell
python scripts\audio\prepare_rnnoise_variants_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name questionario_amostra `
  --output-dir tmp\rnnoise_variants_eval `
  --target-i -16 `
  --eq-gain-db 2.0
```

A variante publicada corresponde a:

```text
tmp\rnnoise_variants_eval\questionario_amostra\mp3\questionario_amostra_rnnoise_presence_eq_loudnorm.mp3
```

O hash SHA-256 registrado no manifesto para essa versao do RNNoise e:

```text
cb9ed5a5481186f6e8c7e657aa99c33b09dad943d1cc5e398a8981afaa3f85f9
```

Comando de referencia para reproduzir a amostra DFN3 publicada:

```powershell
tmp\.venv_deepfilternet\Scripts\python.exe scripts\audio\prepare_deepfilternet_eval.py `
  --input tmp\questionario_audio_work\amostra_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name questionario_amostra
```

A variante publicada corresponde a:

```text
tmp\deepfilternet_eval\questionario_amostra\mp3\questionario_amostra_deepfilternet_loudnorm.mp3
```

O hash SHA-256 registrado no manifesto para essa versao do DFN3 e:

```text
410e8867b6a47303da8ed455cb3a154f41ece567f28a86f6bbd160ffd2a8a7b1
```

## Experimento local com audio proprio

A area experimental permite gravar ou carregar um audio curto somente no
navegador. A versao atual nao envia esse arquivo no payload e ainda nao carrega
processadores RNNoise/STFT em WebAssembly/JavaScript. Quando esses modulos forem
incluidos, o fluxo deve continuar local, sem upload de voz para servidor.
