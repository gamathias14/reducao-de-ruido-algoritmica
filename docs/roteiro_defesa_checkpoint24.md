# Roteiro de defesa apos Checkpoint 24

Data: 2026-06-08

## Mensagem central

A decisao tecnica da plataforma PC esta consolidada: a implementacao principal
e a subtracao STFT causal adaptativa, com parametros congelados e estado causal
explicito. Ela nao depende de silencio inicial fixo e ja foi exercitada no
Windows por 10 min em self-test, 10 min em captura fisica `input-only` e
10 min em full-duplex cabeado, sem blocos acima do orcamento externo de 20 ms.

## Sequencia sugerida

1. Problema: reducao de ruido local para voz humana, com foco em comunicacao em
   tempo real e futura portabilidade embarcada.
2. Comparacao: STFT/Fourier contra Wavelet, sempre separando benchmark offline,
   processamento causal por blocos e captura fisica.
3. Resultado offline: a STFT de baixa energia e o limite superior operacional;
   a versao causal adaptativa recupera boa parte desse ganho.
4. Decisao PC: STFT causal adaptativa como caminho principal; Wiener causal como
   alternativa menos agressiva; Wavelet/WPT como achado complementar offline.
5. Validacao Windows: self-test de 600 s com 30.000 blocos, pior bloco 4,127 ms
   e RTF medio 0,049; input-only de 600 s com 29.998 blocos, pior bloco
   6,799 ms e RTF medio 0,064.
6. Full-duplex cabeado: STFT por 600 s com 29.998 blocos, pior bloco 7,301 ms,
   RTF medio 0,063 e `status_counts` vazio.
7. Ressalva de latencia: o JSON fisico input-only registra 72 ms como 32 ms
   algoritmicos + 40 ms de entrada; no duplex cabeado MME, o JSON registra
   272 ms por causa dos 200 ms de saida reportados pelo driver. Nenhum dos dois
   e medicao fisica de `round-trip`.
8. Proximos passos: voz autoral e escuta critica como validacao complementar;
   investigar driver/loopback apenas se a equipe quiser afirmar baixa latencia
   fisica; Raspberry Pi como primeira plataforma de continuidade.

## Numeros para citar

| Evidencia | Resultado |
|---|---:|
| STFT causal adaptativa, conjunto final operacional | +3,76 dB SNR, +2,65 dB SI-SDR |
| Estado causal maximo observado | 60.900 bytes |
| Self-test Windows, 600 s | 30.000 blocos, pior 4,127 ms |
| Input-only Windows, 600 s | 29.998 blocos, pior 6,799 ms |
| Full-duplex cabeado Windows, 600 s | 29.998 blocos, pior 7,301 ms |
| Blocos acima de 20 ms nas rodadas longas | 0 |
| `status_counts` nas rodadas longas | vazio |
| Latencia input-only estimada no JSON | 72 ms, nao `round-trip` |
| Latencia duplex cabeada estimada no JSON | 272 ms, nao `round-trip` |

## Evitar afirmar

- Nao dizer que Bluetooth comprovou baixa latencia.
- Nao dizer que os 72 ms ou 272 ms sao latencia fisica ponta a ponta.
- Nao dizer que WPT e causal ou substituiu a STFT PC.
- Nao dizer que ha resultados de voz autoral ou avaliacao perceptual formal.
- Nao generalizar a matriz PC-2 como benchmark amplo de ambientes e falantes.

## Frase curta de fechamento

O resultado principal nao e que o prototipo final esta pronto para uso comercial;
e que a escolha tecnica em PC esta justificada, reproduzivel e operacionalmente
estavel por blocos no Windows, inclusive em full-duplex cabeado, com as
limitacoes de latencia fisica declaradas.
