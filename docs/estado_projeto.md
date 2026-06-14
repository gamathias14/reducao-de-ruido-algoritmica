# Estado do projeto

Data de consolidação: 14 de junho de 2026.

## Classificação

O trabalho está no estágio de **protótipo acadêmico integrado**. Ele não é um
produto comercial pronto e não possui validação de baixa latência física ponta
a ponta.

## Evidências consolidadas

### Qualidade algorítmica

- O baseline STFT causal foi construído, refinado e usado como referência.
- DWT e WPT foram avaliadas; a WPT causal passou em métricas instrumentais, mas
  foi rejeitada na escuta privada contra o baseline.
- O benchmark de literatura comparou OM-LSA/IMCRA, RNNoise, WebRTC APM NS e
  DeepFilterNet3 sob um harness comum.
- RNNoise e OM-LSA/IMCRA formaram a fronteira final pública.
- A escuta cega pré-ponte classificou RNNoise em primeiro, OM-LSA/IMCRA em
  segundo e o baseline STFT em terceiro.

### Processamento e transporte

- RNNoise persistente usa estado contínuo, buffers fixos e dois quadros nativos
  por bloco externo de 20 ms.
- No host, 30.000 blocos tiveram p99 de 1,951 ms, pior caso de 18,249 ms e zero
  estouro do orçamento de 20 ms.
- No self-test isolado da VM, 3.000 blocos tiveram p99 de 2,021 ms, pior caso
  de 10,691 ms e zero estouro.
- O canal host-convidado entregou 1.000 blocos por perna, sem erro de sequência,
  CRC, enquadramento, perda ou duplicação.

### Microfone virtual

- O SYSVAD modificado expõe um endpoint virtual de captura.
- A interface de dispositivo usa PCM v1, blocos de 320 amostras, PCM16 mono a
  16 kHz e fila não paginada no driver.
- Um sinal sintético de 440 Hz foi escrito no driver e capturado por cliente
  Windows em WAV de 12 s com formato e frequência dominante corretos.
- A interface de controle, a exclusividade do produtor, a reconexão e os
  contadores de erro foram exercitados.

## Limite temporal da VM

O VirtualBox/NEM não sustentou continuidade temporal confiável no endpoint.
Foram observados atrasos e lacunas após o DSP, mesmo quando processamento,
transporte e escrita no driver permaneceram corretos.

O contrafactual final comparou SYSVAD e HDA no mesmo boot, em ordem ABBA, com
WASAPI compartilhado orientado a evento:

| Perna | Sinais tardios | Períodos perdidos equivalentes | Máximo |
|---|---:|---:|---:|
| SYSVAD A | 21 | 381 | 230,21 períodos |
| HDA A | 22 | 1.121 | 743,64 períodos |
| HDA B | 23 | 248 | 82,18 períodos |
| SYSVAD B | 48 | 304 | 43,72 períodos |

Classificação predefinida:
`virtualbox_event_timing_supported`.

O HDA não foi um controle limpo. O resultado reforça uma limitação global do
VirtualBox/NEM ou do agendamento do convidado, mas não demonstra que o driver
SYSVAD esteja correto.

## Decisões

- RNNoise permanece candidato principal, sem promoção automática a padrão de
  produto.
- OM-LSA/IMCRA permanece como reserva perceptual.
- Driver, PCM v1 e profundidades de fila não devem ser alterados para mascarar
  lacunas.
- Não executar novos testes exploratórios na VM para sintonia de scheduler,
  afinidade, prioridade ou espera.
- Não liberar escuta ponta a ponta baseada em WAVs com lacunas.
- A próxima validação temporal deve ocorrer em Windows nativo, em bancada
  isolada e recuperável.

## Entregáveis acadêmicos

- relatório e apresentação atualizados;
- código e testes dos algoritmos, transporte e analisadores;
- documentação de arquitetura, demonstração e validação futura;
- resumos públicos com hashes e métricas;
- dados privados, binários e rastros volumosos mantidos fora do Git.
