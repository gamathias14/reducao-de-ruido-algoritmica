# Migracao do laboratorio da VM para Windows nativo

Data-base: 14 de junho de 2026.

## Objetivo

Registrar o que pode ser reutilizado, o que depende do novo ambiente e como a
validacao nativa deve esclarecer o limite temporal observado no
VirtualBox/NEM. A migracao nao e uma reimplementacao da arquitetura: e uma
etapa de implantacao controlada, reproducao dos gates e diagnostico comparavel.

## Matriz de reutilizacao

| Componente | Decisao inicial no Windows nativo |
|---|---|
| RNNoise persistente e resampling causal | Reutilizar sem alterar algoritmo, estado ou framing. |
| Blocos PCM16 mono, 16 kHz e 20 ms | Reutilizar como contrato congelado. |
| Protocolo PCM v1 e IOCTLs | Reutilizar sem alterar versao ou layout. |
| Ring buffer nao paginado e politica de underrun | Reutilizar no primeiro gate. |
| Ponte Python-driver e telemetria | Reutilizar, atualizando apenas caminhos e enumeracao de dispositivos. |
| SYSVAD modificado | Recompilar e empacotar para o WDK/Windows da bancada; validar assinatura e instalacao. |
| UI e scripts de diagnostico | Reutilizar, reenumerando microfone, endpoint e backend de captura. |
| Polling, periodos e profundidades de fila | Manter os valores congelados na primeira repeticao; recalibrar somente depois da comparacao. |
| Automacao especifica do VirtualBox | Substituir por scripts locais de instalacao, captura, coleta e reversao. |

## Regra de comparacao

A primeira execucao nativa deve preservar RNNoise, PCM v1, bloco de 20 ms,
profundidades de fila, politica de descarte e criterios de analise usados na
VM. Alterar esses parametros antes do baseline impediria distinguir melhoria
ambiental de melhoria causada por retuning.

Depois do baseline comparavel:

1. se HDA/microfone fisico e SYSVAD mantiverem cadencia continua, a hipotese de
   limitacao do VirtualBox/NEM ganha forca;
2. se o baseline fisico for continuo, mas o SYSVAD apresentar pausas, a
   investigacao deve se concentrar em WaveRT, PortCls, timer/callback, consumo
   do ring buffer e captura do endpoint;
3. se ambos apresentarem pausas, devem ser investigados backend de audio,
   drivers do hardware, energia, scheduler, DPC/ISR e configuracao do Windows;
4. se somente o caminho com RNNoise falhar, devem ser comparados bypass e
   RNNoise com os mesmos blocos, timestamps e contadores antes de atribuir o
   problema ao DSP.

Nenhuma fila deve ser aumentada apenas para ocultar underruns. Mudancas
posteriores precisam ser isoladas, pareadas e registradas.

## Adaptacoes esperadas

- preparar bancada secundaria ou SSD restauravel;
- conferir versoes de Windows, Visual Studio, SDK e WDK;
- recompilar, assinar em modo de teste e instalar o pacote SYSVAD;
- registrar certificado, hashes, estado de boot e procedimento de reversao;
- enumerar novamente dispositivos de captura e selecionar o backend nativo;
- validar formato mono PCM16 a 16 kHz em produtor, endpoint e cliente;
- trocar caminhos e indices especificos da VM por configuracao da bancada;
- medir latencia fisica por loopback ou instrumentacao externa.

## Estimativa de trabalho

O trabalho esperado e moderado e se concentra em implantacao, seguranca e
validacao. O nucleo DSP, o contrato PCM, a ponte, o driver modificado e os
analisadores ja existem. Uma reimplementacao so se justificaria se o Windows
nativo revelar incompatibilidade real no driver ou se os gates isolarem uma
falha arquitetural que nao apareceu na VM.

## Evidencias a preservar

- configuracao exata e hashes do pacote;
- baseline anterior a instalacao;
- logs pareados de bypass e RNNoise;
- sequencias, perdas, descartes, underruns e profundidades;
- distribuicao dos intervalos de callback e sinais tardios;
- medicao fisica de latencia;
- resultado de reinicializacao e reversao.

O protocolo executavel e os criterios de aprovacao estao em
`docs/validacao_windows_nativo.md`.
