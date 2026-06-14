# Protocolo futuro de validação em Windows nativo

Este protocolo registra o próximo passo técnico. Ele não deve ser executado no
computador principal nem durante o fechamento acadêmico.

## Escopo da migração

A arquitetura não será reescrita para o Windows nativo. RNNoise, blocos de
20 ms, PCM v1, ponte Python-driver, SYSVAD modificado, UI e analisadores serão
reutilizados. As adaptações esperadas são de compilação, assinatura,
instalação, enumeração de dispositivos, backend de captura, automação local e
medição física.

A primeira rodada deve preservar a configuração congelada da VM. Polling,
profundidades de fila, política de descarte e protocolo só podem ser ajustados
depois do baseline comparável. A matriz completa e a interpretação dos
resultados estão em `docs/migracao_windows_nativo.md`.

## Ambiente recomendado

- computador secundário ou SSD descartável;
- Windows 11 Pro limpo;
- imagem completa ou reinstalação garantida;
- chave de recuperação do BitLocker preservada;
- Secure Boot desabilitado somente na bancada;
- `TESTSIGNING` habilitado;
- certificado de teste instalado em `LocalMachine\Root` e
  `LocalMachine\TrustedPublisher`;
- WinRE, modo de segurança, `pnputil` e restauração de imagem disponíveis.

Thumbprint do certificado usado no pacote experimental:

```text
7ABED3D56ECAFD8B95C7B98451237673A53F899B
```

O certificado privado e qualquer chave associada não integram o repositório.

## Aviso de segurança

Um driver de teste pode causar falha de inicialização, perda de acesso ao
sistema ou tela azul. A bancada deve ser isolada e recuperável. O protocolo não
promete risco zero.

## Sequência experimental

### 1. Baseline nativo

- registrar versão do Windows, hardware e drivers;
- medir HDA ou microfone físico sem SYSVAD;
- executar captura orientada a evento e registrar períodos, sinais tardios,
  descontinuidades e latência;
- preservar um snapshot lógico dos estados de segurança e boot.

Esse baseline deve usar os mesmos critérios de sinal tardio e continuidade da
VM, para permitir comparação direta sem atribuir antecipadamente a falha ao
VirtualBox/NEM ou ao SYSVAD.

### 2. Instalação controlada

- verificar hash e assinatura do pacote;
- instalar o certificado de teste;
- habilitar `TESTSIGNING`;
- instalar o SYSVAD com `pnputil`;
- confirmar serviço, dispositivo, endpoint e estado após reinicialização.

### 3. Sinal determinístico

- alimentar o PCM v1 com tom conhecido;
- capturar o endpoint por cliente independente;
- confirmar formato, duração, frequência dominante e retorno a silêncio;
- exigir zero erro de sequência, escrita, overrun e rejeição.

### 4. Transporte e continuidade

- executar matriz pareada com bypass e RNNoise;
- usar a mesma entrada, duração e ordem balanceada;
- começar com parâmetros congelados da VM, sem retuning;
- exigir zero perda, zero descarte e zero underrun em todas as pernas;
- repetir o gate em sessões independentes.

Se o baseline físico for contínuo e somente o SYSVAD falhar, investigar
WaveRT/PortCls, consumo do ring buffer e captura do endpoint. Se ambos
falharem, investigar scheduler, DPC/ISR, energia, backend e drivers do host.

### 5. Latência física

- medir latência por loopback físico ou método equivalente;
- separar entrada, algoritmo, fila, endpoint e saída;
- reportar distribuição, p95, p99 e pior caso;
- não substituir medição por valores reportados pelo driver.

### 6. Fala controlada

Somente após os gates anteriores:

- capturar ou reproduzir fala autorizada;
- comparar bypass e RNNoise em condições pareadas;
- executar escuta cega;
- registrar inteligibilidade, naturalidade, ruído residual, artefatos e
  preferência.

## Critério de aprovação

O protótipo só pode avançar para alegação de continuidade nativa quando houver:

- zero perda e zero underrun em repetições prolongadas;
- integridade de sequência e formato;
- latência física medida;
- estabilidade após reinicialização;
- reversão documentada e testada;
- avaliação perceptual sem edição para mascarar falhas.

## Reversão

1. interromper o produtor e clientes;
2. remover o dispositivo e o pacote com `pnputil`;
3. remover o certificado de teste;
4. desabilitar `TESTSIGNING`;
5. reiniciar;
6. confirmar ausência de serviço, dispositivo, endpoint e certificado;
7. restaurar a imagem se a remoção não produzir estado conhecido.
