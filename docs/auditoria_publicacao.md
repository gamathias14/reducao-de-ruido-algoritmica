# Auditoria de publicação

Data: 14 de junho de 2026.

## Inventário

Na abertura do fechamento havia aproximadamente 597 MiB de arquivos não
rastreados. Cerca de 494 MiB pertenciam ao diretório
`resultados/sysvad_checkpoint46_reopened`.

Também foram identificados:

- WAVs públicos e privados;
- ZIPs de resultados e dependências;
- dumps de falha do Windows;
- executáveis, DLLs, drivers, catálogos e certificados;
- traces CSV/JSON volumosos;
- logs com caminhos locais e nomes de arquivos temporários de credencial;
- PDFs administrativos e materiais fora do escopo do repositório.

## Classificação

### Publicável

- código-fonte próprio;
- testes automatizados;
- vetores WAV curtos, inteiramente sintéticos e determinísticos, usados nos
  testes de processamento por blocos;
- documentação acadêmica e técnica;
- scripts de build que não incorporam código ou binários de terceiros;
- resumos JSON/CSV pequenos;
- hashes, versões e referências aos projetos oficiais;
- PDFs finais do relatório e da apresentação.

### Não publicável

- áudio privado ou bruto;
- datasets e ZIPs DEMAND;
- diretórios `dados/private` e equivalentes;
- credenciais e arquivos de runtime da VM;
- certificados privados ou chaves;
- dumps de falha;
- executáveis, DLLs, drivers e pacotes assinados;
- resultados brutos volumosos que podem ser regenerados;
- logs que expõem caminhos pessoais ou nomes de arquivos temporários de
  credencial;
- materiais administrativos e históricos de conversa.

## Curadoria dos resultados

Os resultados brutos permanecem locais. O repositório publica somente
`resultados/publicaveis/fechamento_20260614`, contendo:

- resumo consolidado das métricas;
- classificação do contrafactual;
- hashes dos artefatos de autoridade;
- indicação explícita de que áudio e binários não foram incluídos.

## Licenças

- RNNoise: código e modelo obtidos do projeto oficial; não redistribuídos.
- WebRTC: código oficial sob BSD-3-Clause; não redistribuído.
- DeepFilterNet: componentes sob MIT ou Apache-2.0; não redistribuídos.
- DEMAND: dados sob CC BY-SA 3.0; arquivos brutos não redistribuídos.
- SYSVAD e ferramentas Microsoft: fontes e binários externos não são copiados
  para este repositório.

O repositório ainda não possui uma licença geral. A publicação não deve ser
interpretada como concessão automática de direitos de reutilização.

## Controles antes do push

Controles concluídos em 14 de junho de 2026:

- `python -m pytest -q`: 191 testes e 11 subtestes aprovados;
- `compileall`: aprovado para `benchmark_audio`, `realtime_audio` e
  `scripts/audio`;
- parser PowerShell: 26 arquivos aprovados;
- relatório: duas passagens de `pdflatex`, 40 páginas;
- apresentação: duas passagens de `pdflatex`, 11 slides;
- inspeção visual: todas as páginas revisadas por folhas de contato, com
  ampliação das páginas novas e dos slides densos;
- `git diff --check`: sem erro de whitespace;
- busca de segredos de alta confiança e caminhos pessoais: nenhum achado;
- extensões proibidas entre os candidatos: nenhuma;
- volume candidato antes do staging: menos de 3,5 MiB, sem arquivo acima de
  1 MiB; a cópia PNG redundante do logotipo foi excluída;
- histórico local anterior reconstruído antes do push para remover 15 WAVs de
  DEMAND, refinamento e exemplos que não deveriam permanecer como blobs;
- remoto atualizado por `git fetch`; antes da reconstrução, `main` estava 26
  commits à frente e zero commit atrás de `origin/main`; o histórico
  publicável foi então recomposto em commits temáticos.

O conjunto staged deve ser novamente inspecionado antes de cada commit e o
push só deve ocorrer se os arquivos públicos permanecerem separados dos
resultados brutos locais.
