# Escuta perceptual W261 · Voice Control / PTC 3528

Instrumento interno de pesquisa exploratória para Augusto, Gabriel e Lucas, com identidade visual oficial do Voice Control. Foi desenvolvido para integrar o site do repositório de Gabriel, `gamathias14/reducao-de-ruido-algoritmica`, hospedado em GitHub Pages (`main/docs`).

**Estado atual:** interface construída, ensaio de navegador aprovado e prévia no ASUS. **NÃO PUBLICADO**. Não enviar o link público até que existam áudios privados acessíveis por convite e persistência com recibo em backend isolado.

## Estrutura

- `index.html`: instruções, consentimento, seletor de participante, formulário e finalização.
- `assets/voice-control.svg`: SVG oficial colorido reaproveitado do projeto.
- `styles.css`: identidade própria, controles de áudio, barra de progresso e scrollbars personalizados.
- `config.js`: contrato do instrumento, três cenas, quatro escolhas por cena e backend **desabilitado**.
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

O áudio está **exclusivamente no ASUS**, em `AUDICAO_LOCAL`, e o manifesto de nomes em `MANIFESTO_CEGO_PRIVADO.json`. A política de produção prevista é armazená-lo em bucket **privado**, em um projeto Supabase **dedicado**, com URLs assinadas temporárias emitidas somente após validar o convite individual. O servidor de pesquisa **não está criado/deployado**.

## Prévia local no ASUS

`http://127.0.0.1:8767/teste-perceptual/`

Servidor Python: `project/continuacao_tcc_20261117/validacao_w261_20261117/captura_20261117_165235/servidor_previa_local.py` (bind 127.0.0.1; não acessível via internet). Mapeia os nove arquivos privados para os nomes opacos esperados pelo site sem copiá-los para o Git. Não usar o servidor local como backend público.

## Publicação segura futura

1. Selecionar a organização Supabase onde será criado um novo projeto dedicado, com custo cotado e aprovado se não for zero. Não reutilizar as bases `circuitos-curadoria` ou `legal-finance-origination-radar`.
2. Criar projeto; aplicar `backend_supabase/setup.sql`; verificar RLS, ausência de políticas anônimas, bucket privado e tabelas sem grants para `anon`/`authenticated`.
3. Enviar os nove WAVs ao bucket privado nos nomes opacos `media/c0X_s0Y.wav` (sem expor `MANIFESTO_CEGO_PRIVADO.json`).
4. Emitir três códigos de convite criptograficamente aleatórios, um por pessoa. Guardar **somente os SHA-256** na tabela `vc_w261_invites`; entregar links com código privadamente. Não colocar convites ou chave `service_role` em GitHub.
5. Implantar Edge Function `ptc3528-perceptual` usando o arquivo privado `edge_function.ts`, `verify_jwt=false` apenas por ter autenticação própria forte de convites. Configurar `SUPABASE_URL` e credencial de servidor no ambiente do Edge Function.
6. Verificar: token inválido = 401; origem não permitida = 403; token de outro participante não aceita nome trocado; três WAVs por cena acessíveis via URL assinada; POST válido retorna **recibo real**; repetição idêntica é idempotente; alteração depois de submetido retorna 409; SELECT direto com `anon` é negado. Não usar dados reais para testes que gerem entradas falsificadas em produção.
7. Só depois mudar `config.js` para `backend.enabled=true` e `backend.url=<URL_VERIFICADA>`; testar fim a fim no domínio `gamathias14.github.io`.
8. Fazer commit de **arquivos explicitamente selecionados**, inspecionar `git diff --cached`, publicar `main` com a conta que possua push, verificar deploy GitHub Pages, e enviar links privados individuais.

**Não enviar os WAVs para `docs/` no repo, releases do GitHub ou outro servidor público.** O GitHub Pages é público independentemente de os links não serem divulgados.

## QA já realizado em 17/11/2026

- Chrome 157 headless, resposta simulada do participante Augusto.
- Todos os nove WAVs reproduziram; três cenas preenchidas; validações de escolhas A/B/C e contextos aceitas.
- Ao recarregar após a primeira cena, a sessão foi retomada automaticamente na segunda.
- A conclusão exibiu três cenas completas e salvamento local; envio remoto corretamente desabilitado, sem falso recibo.
- Sem exceções JavaScript. Arquivos WAV ficaram fora do repositório.
- Backend TypeScript passou por `deno lint` e `deno check` locais; ainda sem implantação nem teste em banco real.

## Privacidade e integridade científica

As respostas são nominativas somente porque os três membros da equipe serão os avaliadores definidos. O conteúdo pode conter observações pessoais; não inserir nos assets públicos. Antes da coleta, garantir que todos consentem em ouvir a gravação e que eventuais vozes de terceiros não sejam expostas. Os resultados são exploratórios e não permitem generalizar para usuários externos, afirmar causalidade acústica ou substituir ensaios com referência limpa.

Para análise local posterior, consultar `project/continuacao_tcc_20261117/validacao_w261_20261117/captura_20261117_165235/analisar_respostas_w261.py`, que traduz A/B/C conforme manifesto privado e computa somente contagens descritivas; não executar antes de receber arquivos realmente preenchidos.
