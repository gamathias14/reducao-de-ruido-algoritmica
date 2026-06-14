# Protocolo de gravação de voz autoral

## Escopo

Este protocolo prepara gravações dos três autores do projeto, identificados
somente como `spk01`, `spk02` e `spk03`. As gravações complementam FSDD e
DEMAND; elas não substituem as bases públicas nem justificam alegações de
generalização populacional.

Cada participante deve realizar duas sessões:

- `session_a`: desenvolvimento, conferência da ingestão e níveis seguros;
- `session_b`: confirmação final, sem uso na escolha de parâmetros.

Os parâmetros causais foram congelados antes da coleta. A Sessão B não pode ser
usada para reajustá-los sem declarar uma nova rodada experimental.

## Privacidade e autorização

Antes de gravar:

1. preencher e assinar localmente `docs/autorizacao_voz_autoral.md`;
2. escolher um nível de compartilhamento;
3. criar um identificador de consentimento, por exemplo
   `consent_spk01_v1`;
4. guardar o documento assinado em
   `dados/private/authored_voice/consent/`;
5. registrar no manifesto somente o código, nunca o nome real.

Níveis:

- `local_only`: processamento local pela equipe; sem envio de áudio;
- `advisor_board`: permite compartilhar exemplos necessários com
  orientador e banca;
- `public_excerpt`: permite publicar somente trechos explicitamente aprovados.

Na ausência de autorização documentada, não grave nem execute a ingestão. Uma
autorização mais ampla não obriga a publicação. Revogação de publicação deve
ser respeitada sem apagar resultados agregados que não permitam reidentificar
o participante, quando isso tiver sido acordado no termo.

## Configuração recomendada

- formato: WAV PCM, nunca MP3;
- taxa preferencial: 48 kHz;
- resolução preferencial: 24 bits; 16 bits é aceitável;
- canais: mono; estéreo é aceito se registrado;
- distância: aproximadamente 15 a 20 cm;
- posição e ganho fixos dentro de cada sessão;
- picos desejados: aproximadamente -12 a -6 dBFS;
- microfone fora de contato com a mesa, quando possível;
- ambiente sem conversas de terceiros.

Desative, quando possível:

- supressão de ruído;
- cancelamento de eco;
- controle automático de ganho;
- isolamento de voz;
- normalização;
- aprimoramentos do Windows ou do fabricante;
- filtros de aplicativos de chamada.

Qualquer processamento que não possa ser desativado deve aparecer em
`capture_processing`.

## Estrutura local

Os WAVs brutos devem ser colocados assim:

```text
dados/raw/authored_voice/
  spk01/
    session_a/
      quiet/
      noise/
      live_noisy/
    session_b/
      quiet/
      noise/
      live_noisy/
  spk02/
  spk03/
```

Os derivados serão criados automaticamente em:

```text
dados/prepared/authored_voice/
```

Ambas as árvores são ignoradas pelo Git.

Use nomes sem dados pessoais:

```text
spk01_session_a_quiet_q01.wav
spk01_session_a_noise_n01.wav
spk01_session_a_live_l01.wav
```

## Conteúdo por sessão

### Voz em ambiente silencioso

- 15 enunciados do roteiro;
- pausas naturais no início e no fim;
- dois trechos espontâneos de 20 a 30 s;
- uma frase por arquivo, preferencialmente;
- repetir a frase apenas se houver erro evidente, registrando a tomada usada.

Esses arquivos recebem `recording_type=raw_quiet`. Eles são referências limpas
aproximadas, não gravações matematicamente livres de ruído.

### Ruído do ambiente

- 30 a 60 s sem fala;
- mesma posição, ganho e equipamento;
- ninguém deve conversar no ambiente;
- não mover o microfone durante a gravação.

Esses arquivos recebem `recording_type=raw_noise`.

### Fala naturalmente ruidosa

- três a cinco trechos de 10 a 20 s;
- ruído real seguro, constante ou variável;
- não captar conversas de terceiros;
- não tentar sincronizar uma referência limpa.

Esses arquivos recebem `recording_type=raw_live_noisy`. Não serão calculadas
SNR ou SI-SDR pareadas sem referência correspondente.

## Sequência da sessão

1. Confirmar autorização e código do falante.
2. Preencher uma linha da folha de sessão.
3. Fixar dispositivo, distância e ganho.
4. Fazer teste curto e conferir pico.
5. Gravar `raw_quiet`.
6. Gravar `raw_noise` sem alterar ganho ou posição.
7. Gravar `raw_live_noisy`, se seguro e autorizado.
8. Não editar, normalizar ou denoisar os WAVs brutos.
9. Preencher o manifesto bruto.
10. Executar a ingestão e revisar avisos.

## Manifesto e ingestão

Copie os modelos de `dados/templates/authored_voice/` para uma pasta local de
trabalho. Não coloque nome real nos CSVs.

Exemplo:

```powershell
python -m benchmark_audio.prepare_authored_voice `
  --manifest dados/private/authored_voice/manifests/session_a_raw_manifest.csv
```

Saídas padrão:

- derivados: `dados/prepared/authored_voice/`;
- manifesto preparado:
  `resultados/authored_voice/ingestion/prepared_manifest.csv`;
- relatório:
  `resultados/authored_voice/ingestion/quality_report.json`.

A CLI:

- exige `consent_record_id`;
- valida WAV PCM, taxa, canais e profundidade;
- detecta vazio, truncamento, silêncio e clipping;
- compara metadados esperados e medidos;
- preserva o bruto;
- converte para mono a 16 kHz;
- remove somente o componente DC;
- não aplica denoising, gate, equalização, compressão ou normalização;
- recusa sobrescrita sem `--overwrite`;
- gera SHA-256 do bruto e do derivado.

Avisos não devem ser apagados. Um arquivo com clipping pode ser mantido para
auditoria, mas deve ser repetido antes da avaliação final quando possível.

## Avaliacao apos a ingestao

Depois da revisao do manifesto preparado, a rodada objetiva deve ser executada
com os parametros ja congelados:

```powershell
python -m benchmark_audio.run_authored_evaluation `
  --prepared-manifest resultados/authored_voice/ingestion/session_b_prepared_manifest.csv `
  --session session_b `
  --results-dir resultados/authored_voice/evaluation/session_b_final
```

A Sessao A pode ser usada para depurar ingestao e comandos. A Sessao B deve
confirmar o algoritmo sem nova busca de parametros. A CLI calcula metricas
pareadas somente para misturas `raw_quiet + raw_noise`; `raw_live_noisy` nao
recebe SNR ou SI-SDR sem referencia limpa sincronizada.

O protocolo detalhado da avaliacao e o modelo de formulario perceptual ficam em
`docs/avaliacao_autoral.md` e
`dados/templates/authored_voice/perceptual_rating_template.csv`.

## Critérios para liberar a Sessão B

- autorização dos três participantes registrada;
- Sessão A ingerida sem erros não explicados;
- equipamento e processamento conhecidos;
- picos dentro da faixa planejada ou desvios documentados;
- nenhum arquivo silencioso por engano;
- nenhum clipping não tratado;
- manifesto sem nomes reais;
- parâmetros do algoritmo mantidos congelados.

## Fronteiras metodológicas

- `raw_quiet` pode ser misturado com ruído conhecido para métricas pareadas;
- `raw_noise` pode ser usado como fonte conhecida de mistura;
- `raw_live_noisy` recebe análise operacional e perceptual, sem métricas
  pareadas fabricadas;
- nenhuma gravação será publicada apenas porque foi processada;
- escuta e playback exigem confirmação humana em etapa posterior.
