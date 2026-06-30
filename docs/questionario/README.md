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
externas. Para manter o envio rapido para o participante, o receptor apenas
marca o dashboard como pendente quando uma resposta chega. Instale uma vez o
gatilho periodico no Apps Script:

```js
installQuestionarioDashboardTrigger()
```

Com isso, `rebuildDashboardIfPending()` roda automaticamente a cada 5 minutos e
reconstroi as abas de dashboard apenas quando houver resposta nova. Para uma
reconstrucao manual, abra o projeto em <https://script.google.com/> e execute:

```js
rebuildDashboard()
```

A versao publicada do Apps Script precisa estar sincronizada com
`scripts/google_forms/receber_respostas_questionario_github_pages.gs`. Depois
de alterar esse arquivo no repositorio, copie o conteudo para o `Code.gs` do
Apps Script e implante uma nova versao do Web App antes de coletar respostas.

Durante o periodo de testes, use a funcao abaixo no Apps Script para limpar as
submissoes experimentais e reconstruir o dashboard vazio antes da coleta
oficial:

```js
resetQuestionarioTestData()
```

Ela limpa `responses_raw`, `responses_wide`, `dashboard_metrics`,
`coded_open_answers` e `errors`, preserva `schema_history` e `audit`, e registra
o reset na propria aba `audit`.

A funcao le `responses_raw` como fonte canonica e recria/atualiza as abas:

- `dashboard_metrics`: tabela longa com metricas por bloco, pergunta,
  alternativa/nota, `N`, contagem, percentual, media, mediana e ranking quando
  aplicavel.
- `dashboard`: resumo visual com data/hora de atualizacao, `questionnaireId`,
  `schemaVersion`, total de respostas, observacao de privacidade e graficos
  nativos do Google Sheets.
- `coded_open_answers`: respostas abertas preparadas para codificacao manual,
  preservando colunas manuais ja preenchidas quando o dashboard for reconstruido.

A reconstrucao nao apaga `responses_raw` nem sobrescreve respostas existentes.
Se uma pergunta nova for adicionada no futuro, o script tenta aproveitar
`questionSnapshot` e `answers` para manter compatibilidade com schemas antigos.

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

A versao `2026-06-30.4` do questionario usa tres exemplos publicos em MP3 de
aproximadamente `8,5 s`, gerados a partir da mesma amostra ruidosa de
referencia:

- `amostra_noisy_reference.mp3`: referencia ruidosa;
- `amostra_rnnoise.mp3`: RNNoise com normalizacao de loudness e equalizacao leve
  de presenca;
- `amostra_dfn3_default.mp3`: DeepFilterNet3 C API com `post_filter_beta = 1`,
  preroll de `2 s`, EQ de presenca e normalizacao de loudness.

Os exemplos OM-LSA/IMCRA, STFT e Wavelet permanecem no diretorio como historico,
mas nao fazem parte do manifesto ativo nem aparecem na comparacao atual.

O arquivo `amostra_rnnoise.mp3` foi atualizado a partir da variante escolhida na
avaliacao local `rnnoise_presence_eq_loudnorm`. A base continua sendo o RNNoise
com `startup_preroll_ms = 200`, mas a amostra publicada inclui normalizacao de
loudness e um EQ leve de presenca para reduzir a percepcao de voz apagada/abafada
sem alterar o nucleo do metodo de reducao de ruido.

O arquivo `amostra_dfn3_default.mp3` veio da cadeia DeepFilterNet3 C API
congelada perceptualmente em `tmp\dfn_native\preroll_beta100_diag`. A
configuracao usada foi:

```text
post_filter_beta = 1.0
preroll = 2 s
loop interno = crossfade de 10 ms
atraso causal descartado = 1440 samples = 30 ms
EQ de presenca = 3 kHz, Q = 1.0, +2 dB
loudnorm dois-passos = I = -16 LUFS, LRA = 7 LU, TP = -1 dBTP
```

Ele representa o candidato DeepFilterNet3 aprovado perceptualmente como
comparacao exploratoria, mas ainda nao prova integracao com o microfone virtual
Windows/SYSVAD.

Comando de referencia para reproduzir as variantes longas RNNoise/default
offline usadas como etapa anterior:

```powershell
tmp\.venv_deepfilternet\Scripts\python.exe scripts\audio\prepare_deepfilternet_eval.py `
  --input tmp\non_rnnoise_candidates_eval\teste_audio_augusto\wav\teste_audio_augusto_noisy_reference.wav `
  --clean-reference resultados\audio\exemplo_clean.wav `
  --name dfn3_default `
  --output-dir tmp\dfn_aug
```

As variantes publicadas correspondem a:

```text
tmp\dfn_aug\dfn3_default\mp3\dfn3_default_noisy_reference_loudnorm.mp3
tmp\dfn_aug\dfn3_default\mp3\dfn3_default_rnnoise_presence_eq_loudnorm.mp3
tmp\dfn_native\preroll_beta100_diag\capi_loop2s_xfade10_beta100_presence_eq_loudnorm.wav
```

Os hashes SHA-256 registrados no manifesto sao:

```text
amostra_noisy_reference.mp3  0635dcde09f32a05cc7745fb990c6ed2b0b326259fb8ad0a9da419e2bf34f1d9
amostra_rnnoise.mp3          335705fad15d09ba3677d48fb171a0495879ab838419f581d2906ccff22f6304
amostra_dfn3_default.mp3     70337fd055add5fc9dde4f15ebdd6ce7546182290b911a7298b751ca8c48da3d
```

## Experimento local com audio proprio

A area experimental permite gravar ou carregar um audio curto somente no
navegador. A versao atual nao envia esse arquivo no payload e ainda nao carrega
processadores RNNoise/STFT em WebAssembly/JavaScript. Quando esses modulos forem
incluidos, o fluxo deve continuar local, sem upload de voz para servidor.
