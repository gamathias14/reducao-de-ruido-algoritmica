# Modelo de autorização para uso de voz

Este é um modelo operacional do projeto acadêmico, não um parecer jurídico.
O formulário assinado deve permanecer local e fora do Git.

## Identificação privada

- Nome do participante: _________________________________________________
- Código público no projeto: `spk____`
- Data: ____/____/________
- Identificador do registro: `consent_spk____v____`

## Finalidade

Autorizo a gravação e o processamento da minha voz para o projeto de redução
de ruído em comunicação por voz. Entendo que a voz é dado pessoal e pode ter
características biométricas.

Os arquivos poderão ser usados para:

- validar ingestão, conversão e processamento local;
- criar misturas controladas quando houver referência adequada;
- comparar bypass, subtração espectral causal, Wiener causal e referências
  offline;
- medir custo computacional e estabilidade;
- realizar avaliação perceptual separada.

## Nível autorizado

Marcar somente uma opção:

- [ ] `local_only`: uso apenas nos computadores da equipe, sem envio de áudio.
- [ ] `advisor_board`: uso local e compartilhamento de exemplos necessários
  com orientador e banca, sem publicação aberta.
- [ ] `public_excerpt`: itens anteriores e publicação apenas de trechos curtos
  aprovados explicitamente por mim.

O nível escolhido é: _________________________________________________

## Condições

1. Meu nome real não será usado nos nomes dos WAVs nem nos manifestos
   versionados.
2. Os WAVs brutos e derivados privados ficarão fora do Git.
3. Publicação aberta exige `public_excerpt` e aprovação do trecho específico.
4. Conversas de terceiros e informações pessoais não devem ser gravadas.
5. Posso solicitar a interrupção de novos usos ou a remoção de trechos
   publicados.
6. Resultados agregados já incorporados ao relatório podem ser preservados
   quando não contiverem áudio nem identificação direta, conforme acordado com
   a equipe.
7. A Sessão B será usada para confirmação, não para escolher novos parâmetros.

## Publicação de trechos

Preencher somente para `public_excerpt`:

- [ ] Nenhum trecho está aprovado neste momento.
- [ ] Os trechos aprovados serão listados em anexo com hash SHA-256.

## Assinaturas

- Participante: _________________________________________________________
- Responsável pelo registro na equipe: __________________________________
- Data: ____/____/________

Guardar como, por exemplo:

```text
dados/private/authored_voice/consent/consent_spk01_v1.pdf
```

No manifesto versionável, registrar somente `consent_spk01_v1` e o nível
autorizado.
