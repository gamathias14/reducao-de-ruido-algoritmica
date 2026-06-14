# Estado objetivo do projeto no Checkpoint 46-R

Data: 2026-06-14.

## Estagio

O projeto esta em **prototipo academico integrado**, nao em produto pronto.

Concluido:

- benchmark publico amplo e reproduzivel;
- comparacao com sistemas da literatura;
- avaliacao perceptual privada pre-ponte;
- RNNoise escolhido como candidato principal;
- RNNoise persistente aprovado no host com custo inferior a 20 ms por bloco;
- transporte host-convidado deterministico aprovado;
- driver SYSVAD modificado, endpoint virtual e PCM v1 funcionais;
- interface de controle e fluxo causal por blocos existentes;
- instrumentacao temporal ponta a ponta e automacao de VM maduras.

Bloqueador:

- a captura do endpoint virtual no VirtualBox/NEM sofre pausas esparsas;
- todas as estrategias permitidas ainda produzem perdas ou underruns;
- o problema ocorre depois do DSP e nao invalida a escolha do RNNoise;
- escuta ponta a ponta permanece metodologicamente bloqueada.

## O que falta

Para fechar o prototipo academico:

1. congelar RNNoise como candidato, sem torna-lo default operacional;
2. atualizar relatorio, arquitetura e apresentacao com a separacao entre
   qualidade do DSP e limitacao temporal da VM;
3. definir demonstracao segura usando host/pre-bridge ou arquivos, sem
   afirmar continuidade do endpoint virtual;
4. consolidar comandos, hashes, testes e artefatos reproduziveis.

Para transformar em produto:

1. obter pacote de driver com assinatura adequada para Windows nativo;
2. validar em maquina fisica ou ambiente nativo descartavel;
3. exigir zero perda e zero underrun em ensaios repetidos e prolongados;
4. medir latencia fisica ponta a ponta;
5. executar escuta cega do endpoint somente depois do gate temporal;
6. concluir instalador, atualizacao, recuperacao e suporte.

## Decisao operacional

Nao executar novos boots exploratorios da VM para sintonia de scheduler,
espera, afinidade, prioridade ou produtor. Um novo ensaio de endpoint so se
justifica com mudanca de ambiente de virtualizacao ou alvo Windows nativo.

## Contrafactual HDA na mesma VM

O gate compartilhado orientado a evento comparou o SYSVAD modificado com o
endpoint `Microfone (High Definition Audio Device)` do VirtualBox no mesmo
boot, em ordem ABBA e sem produtor ou audio persistido.

O HDA tambem apresentou atrasos tardios repetidos nas duas pernas:

- HDA A: 22 sinais tardios, maximo de `7.554,401 ms`;
- HDA B: 23 sinais tardios, maximo de `834,825 ms`;
- SYSVAD A: 21 sinais tardios, maximo de `2.302,083 ms`;
- SYSVAD B: 48 sinais tardios, maximo de `437,176 ms`.

Classificacao predefinida:
`virtualbox_event_timing_supported`.

Isso reforca uma limitacao global do VirtualBox/NEM ou do agendamento do
convidado. Nao prova que o driver SYSVAD esteja correto, pois ambos os
endpoints tiveram descontinuidades e parte dos atrasos nao coincidiu com o
probe geral de scheduler.
