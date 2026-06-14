# Plano de ensaio RNNoise na VM

## Objetivo

Validar a integracao RNNoise no pipeline existente sem promove-la diretamente
a padrao e sem alterar driver, endpoint ou protocolo PCM v1.

## Pre-condicoes

- Reverter a VM ao snapshot funcional anterior ao ensaio.
- Confirmar nenhuma VM em execucao antes da preparacao.
- Copiar somente o bundle Python necessario e a DLL RNNoise.
- Verificar no guest:
  - executavel offline SHA-256
    `6D35F2465B5A8C1E1E87F0F54418BFDF3F84D0105067E6204748987989ECF7CB`;
  - DLL SHA-256
    `593D387801A7D0464D2F11449E43E466811DEAEB66C39E367085E28DAAB0F84C`.

## Etapas

1. Rodar `--self-test --method rnnoise` por 60 s, sem captura e sem ponte.
2. Rodar input-only por 60 s, sem abrir a ponte.
3. Rodar `--virtual-mic --method rnnoise` com fonte diagnostica deterministica,
   profundidade 2, fila local 4, polling 2 ms e trace habilitado.
4. Capturar o endpoint por cliente externo e comparar indices enviados,
   descartados e recuperados.
5. Somente se as etapas anteriores passarem, executar uma tomada curta com o
   microfone fisico e escuta controlada.

## Gates

- zero erro de callback ou escrita;
- zero valor nao finito;
- p99 de processamento abaixo de 20 ms;
- framing constante de 320 amostras;
- ausencia de nova descontinuidade pre-ponte;
- nenhum agravamento de drops, underruns ou lacunas contra o controle;
- atraso total registrado com os `21,3125 ms` algoritmicos;
- encerramento limpo e hash da DLL inalterado.

## Parada e rollback

- Parar em erro nativo, callback acima do orcamento recorrente, hash divergente
  ou aumento de falhas de transporte.
- Nao alterar defaults apos uma unica rodada.
- Preservar logs, desligar a VM e reverter ao snapshot inicial ao final.
