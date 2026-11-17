# Escuta perceptual W261 · Voice Control / PTC 3528

Instrumento interno de pesquisa exploratória para Augusto, Gabriel e Lucas, com identidade visual oficial do Voice Control. Foi desenvolvido para integrar o site do repositório de Gabriel, `gamathias14/reducao-de-ruido-algoritmica`, hospedado em GitHub Pages (`main/docs`).

**Estado atual (17/11/2026):** interface e backend implantados em projeto Supabase dedicado, três convites individuais registrados somente por hash e nove áudios em bucket privado. QA remota verificou acesso restrito, recuperação dos nove áudios com SHA-256 idêntico e fluxo completo no Chrome sem salvar votos sintéticos. A gravação de uma **resposta humana real com recibo** ainda não foi efetuada; não afirmar recebimento antecipadamente.

## Estrutura

- `index.html`: instruções, consentimento, seletor de participante, formulário e finalização.
- `assets/voice-control.svg`: SVG oficial colorido reaproveitado do projeto.
- `styles.css`: identidade própria, controles de áudio, barra de progresso e scrollbars personalizados.
- `config.js`: contrato do instrumento, três cenas, quatro escolhas por cena e backend **habilitado** no projeto exclusivo do TCC.
- `app.js`: reprodução A/B/C, ordem balanceada para três avaliadores, validação, salvamento local, exportação JSON e envio remoto com confirmação estrita.
- `testes/e2e-browser.mjs`: teste automatizado com respostas SIMULADAS em perfil isolado do Chrome.

### Perguntas por trecho

Após ouvir A, B e C, selecionar a melhor opção para (1) inteligibilidade percebida, (2) naturalidade vocal, (3) menor interferência sonora durante a fala, e (4) preferência global para uma reunião. Para cada uma, A/B/C/Empate/Não avaliável são válidos. Registrar ainda se há fala inteligível, ruído concomitante e motocicleta reconhecível (sim/não/incerto), além de observação livre opcional.

O participante não vê os nomes dos processamentos. A ordem das fontes usa quadrado latino fixo por participante e cena. **Os três áudios de cada cena têm exatamente o mesmo intervalo temporal**, após correção aproximada dos atrasos observados no OBS; os trechos originais de 16s foram derivados de uma captura espontânea e não representam eventos de motocicleta previamente confirmados.

Os trechos são **38–54s, 150–166s, 356–372s** na gravação original de 17/11/2026. A escolha foi heurística por energia grave; não deve ser rotulada automaticamente como motocicleta.

### Ganho e escuta

Os WAVs privados foram pré-processados para aproximação do nível de faixa vocal sem clipping; a janela 2 tem pareamento incompleto porque elevar os sinais além do nível de pico seguro não seria aceitável. Isso limita a comparação. Não chamar as escolhas de teste controlado de SNR, STOI, PESQ ou latência física. Evitar conclusões estatísticas com três colegas do próprio projeto.

## Armazenamento: três camadas explícitas

1. **Rascunho:** `localStorage` por participante e por versão do instrumento. Preserva navegação e permite retomar no mesmo navegador, mas não é um backup confiável a longo prazo.
2. **Cópia exportável:** botão `Baixar cópia JSON` fornece resposta individual, verificável e independente do servidor.
3. **Servidor de produção:** o botão `Enviar e confirmar gravação` só é habilitado quando `backend.enabled=true` e `backend.url` aponta a um serviço real. O frontend exige HTTP 2xx **e** JSON `{ok:true,receiptId,receivedAt}`, e nunca declara sucesso após uma requisição `no-cors` ou sem recibo.

O backend Supabase Edge Function, a migração SQL e os manifestos contendo nomes de processamentos estão **fora do repositório público**, no diretório de pesquisa do ASUS:

`project/continuacao_tcc_20261117/validacao_w261_20261117/captura_20261117_165235/backend_supabase/`

O arquivo MKV original e as cópias locais dos trechos permanecem no ASUS, em `AUDICAO_LOCAL`. Os nove WAVs também estão em bucket **privado** no projeto Supabase exclusivo `voice-control-ptc3528-perceptual` (região `sa-east-1`); suas cópias remotas foram validadas por SHA-256. O manifesto que relaciona os métodos aos nomes opacos permanece exclusivamente no ASUS. URLs de áudio assinadas com prazo de uma hora são emitidas após validação do convite individual. O servidor de convites e respostas está implantado; a rota temporária de upload devolve HTTP 410.

## Prévia local no ASUS

`http://127.0.0.1:8767/teste-perceptual/`

Servidor Python: `project/continuacao_tcc_20261117/validacao_w261_20261117/captura_20261117_165235/servidor_previa_local.py` (bind 127.0.0.1; não acessível via internet). Mapeia os nove arquivos privados para os nomes opacos esperados pelo site sem copiá-los para o Git. Não usar o servidor local como backend público.

## Infraestrutura implantada e controles de publicação

1. **Feito:** organização `Circuitos` (Free), projeto dedicado `voice-control-ptc3528-perceptual` (`jcmceskyxupmzmgqpvvc`, `sa-east-1`, custo de criação informado US$ 0/mês). Bases alheias não foram modificadas.
2. **Feito:** migração e auditoria SQL: RLS ligada, nenhuma política pública, `anon` sem SELECT, `authenticated` sem INSERT, bucket privado.
3. **Feito:** nove WAVs no bucket privado `vc-w261-listening-private`, nomeados `media/c0X_s0Y.wav`. SHA-256 de todos os nove objetos remotos coincide com os WAVs originais locais. Upload temporário desativado (HTTP 410).
4. **Feito:** três tokens criptograficamente aleatórios, um por participante, armazenados em `INVITES_PRIVADOS_W261.json` somente no ASUS. Apenas SHA-256 no banco. Links completos em `LINKS_PRIVADOS_W261.txt` somente no ASUS. Enviar individualmente, sem publicar tokens no GitHub nem na descrição de vídeo.
5. **Feito:** Edge Function `ptc3528-perceptual` implantada com `verify_jwt=false` e verificação obrigatória de token longo SHA-256 no próprio servidor. Segredo de serviço Supabase é utilizado somente no ambiente protegido da função, nunca no JavaScript público.
6. **Verificado parcialmente:** token inválido = 401, origem não permitida = 403, troca de participante = 403, autorização dos três convites para suas próprias fontes, nove URLs assinadas e nove WAVs com hash igual. POST com dados inválidos = 400. **Pendente de validação com a primeira resposta humana real:** POST bem-sucedido com recibo, idempotência de repetição e rejeição de nova submissão diferente. Não inserir respostas sintéticas na coleta oficial.
7. **Feito na branch:** `config.js` com `backend.enabled=true` e URL HTTPS do projeto dedicado. O Chrome reproduziu os nove áudios privados e concluiu todos os passos em prévia local com servidor real, sem enviar respostas fictícias. **A confirmar após o merge:** mesma experiência no GitHub Pages público, com convite no fragmento de URL (`#convite=`).
8. A finalizar: inspecionar commit atualizado, publicar em `main` após QA, confirmar GitHub Pages e disponibilizar convites individuais por canal privado.

**Não enviar os WAVs para `docs/` no repo, releases do GitHub ou outro servidor público.** O GitHub Pages é público independentemente de os links não serem divulgados.

## QA já realizado em 17/11/2026

- Chrome 157 headless, resposta simulada do participante Augusto.
- Todos os nove WAVs reproduziram; três cenas preenchidas; validações de escolhas A/B/C e contextos aceitas.
- Ao recarregar após a primeira cena, a sessão foi retomada automaticamente na segunda.
- A conclusão exibiu três cenas completas e salvamento local; posteriormente o frontend foi ligado ao backend real. O Chrome confirmou que o botão de envio fica habilitado com convite válido, sem registrar falsos recibos.
- Sem exceções JavaScript. Arquivos WAV ficaram fora do repositório.
- Backend TypeScript passou por `deno lint` e `deno check` locais; serviço implantado e acessos de leitura testados remotamente. O primeiro POST válido com recibo aguarda avaliação real.

## Privacidade e integridade científica

As respostas são nominativas somente porque os três membros da equipe serão os avaliadores definidos. O conteúdo pode conter observações pessoais; não inserir nos assets públicos. Antes da coleta, garantir que todos consentem em ouvir a gravação e que eventuais vozes de terceiros não sejam expostas. Os resultados são exploratórios e não permitem generalizar para usuários externos, afirmar causalidade acústica ou substituir ensaios com referência limpa.

Para análise local posterior, consultar `project/continuacao_tcc_20261117/validacao_w261_20261117/captura_20261117_165235/analisar_respostas_w261.py`, que traduz A/B/C conforme manifesto privado e computa somente contagens descritivas; não executar antes de receber arquivos realmente preenchidos.
