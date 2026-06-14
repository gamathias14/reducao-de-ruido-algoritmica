# Plano Wavelet Packet + Wiener adaptativo

## Decisao tecnica

A rodada Wavelet existente continua valida, mas passa a ser interpretada de
forma mais especifica: ela avaliou DWT com shrinkage por limiarizacao
hard/soft, usando MAD e limiar universal escalado. Esse resultado nao deve ser
lido como evidencia contra toda a familia Wavelet.

A nova hipotese experimental e implementar uma alternativa baseada em:

- Wavelet Packet Transform (WPT), para decompor tambem as subbandas de baixa
  frequencia;
- rastreamento temporal de ruido por subbanda, inspirado em MCRA/IMCRA;
- ganho suave do tipo Wiener, em vez de zerar ou encolher coeficientes por
  limiar hard/soft.

Essa trilha deve ser comparada contra as STFTs ja consolidadas, especialmente a
subtracao causal e o limite offline de baixa energia.

## Motivacao

A DWT atual preserva os coeficientes de aproximacao e aplica limiarizacao apenas
aos detalhes. Em ruidos ambientais como cafeteria e trafego, parte importante do
ruido vive em baixas frequencias e nao e tratada diretamente. Alem disso, o MAD
global ou por escala nao acompanha mudancas temporais do ruido, e a limiarizacao
pode introduzir distorcao ou simplesmente escolher um limiar tao baixo que quase
nada acontece.

A WPT corrige a primeira limitacao ao produzir uma arvore de subbandas mais
uniforme. O rastreamento temporal corrige a segunda ao estimar energia de ruido
ao longo do tempo. O ganho Wiener corrige a terceira ao aplicar atenuacao suave:
coeficientes com SNR estimada alta passam quase intactos; coeficientes dominados
por ruido sao reduzidos sem descontinuidades bruscas.

## Escopo proposto

1. Manter `wavelet_soft` como baseline historico DWT.
2. Criar um novo metodo, por exemplo `wavelet_packet_wiener`, sem substituir os
   resultados anteriores.
3. Implementar primeiro uma versao offline auditavel:
   - WPT em janelas ou blocos com tamanho fixo;
   - energia por subbanda;
   - estimativa de ruido por quadros de baixa energia ou minimo controlado;
   - ganho Wiener por subbanda/coeciente;
   - reconstrucao por inverse WPT.
4. Depois implementar uma versao causal:
   - estado explicito por subbanda;
   - atualizacao rapida quando energia baixa sugere ausencia de fala;
   - atualizacao lenta durante fala provavel;
   - protecoes numericas, piso de ganho e limite de agressividade.
5. Rodar a mesma divisao validation/final ja usada em DEMAND.
6. Comparar SNR, SI-SDR, fracao de degradacao, RTF, memoria de estado e escuta
   critica.

## Criterios de aceitacao

- O bypass continua com melhoria zero.
- O novo metodo preserva comprimento e finitude numerica.
- A versao offline deve superar claramente a DWT limiarizada em SNR ou SI-SDR,
  sem aumentar a fracao de degradacao.
- A versao causal deve ser comparada contra `stft_subtraction` causal; nao basta
  vencer a DWT antiga.
- Se o ganho objetivo for pequeno, a trilha ainda pode ser mantida se houver
  vantagem perceptual clara ou custo muito menor.
- Se houver ganho somente com alta distorcao perceptual, a trilha deve ser
  classificada como exploratoria, nao como candidata principal.

## Mudanca de narrativa

Formula antiga, agora insuficiente:

> A Wavelet refinada permanece neutra e deve ficar como baseline leve.

Formula revisada:

> A DWT com limiarizacao universal/MAD permaneceu neutra. Por isso, a proxima
> investigacao Wavelet deve abandonar shrinkage global estatico e testar WPT com
> rastreamento temporal de ruido e ganho Wiener adaptativo.

## Status da primeira implementacao

- Data: 2026-06-07.
- Metodo criado: `wavelet_packet_wiener`.
- Escopo: versao offline por arquivo, ainda nao causal.
- Local dos resultados: `resultados/wpt_refinement/`.
- Comando:

```powershell
python -m benchmark_audio.run_refinement `
  --include-wpt `
  --results-dir resultados/wpt_refinement
```

Resultado resumido da melhor configuracao WPT escolhida na validacao
(`wpt_wiener_sym4_l3_rolling_q0.2_w31_f0.1`):

- validacao: +0,878 dB SNR, +0,200 dB SI-SDR, 25,0% degradacoes;
- final operacional: +0,366 dB SNR, -0,248 dB SI-SDR, 25,0% degradacoes.

Leitura atual: a primeira WPT + Wiener melhora SNR em relacao a DWT
limiarizada, mas ainda nao compete com STFT e traz degradacao perceptualmente
suspeita pelo SI-SDR negativo no final. A trilha permanece exploratoria.

## Status apos benchmark pesado

- Data: 2026-06-07.
- Rodada completa: `resultados/wavelet_heavy_refinement/`.
- Script: `benchmark_audio/run_wavelet_heavy_refinement.py`.
- Perfil: `focused`.
- Triagem: 2556 candidatos, separados em DWT, WPT por coeficiente e WPT em
  quadros.

Resultado principal:

- DWT limiarizada ampliada continuou praticamente neutra.
- WPT por coeficiente continuou limitada.
- WPT em quadros com overlap mudou a conclusao:
  - configuracao robusta:
    `wpt_frame_sym6_l3_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - final operacional: +3,210 dB SNR, +1,753 dB SI-SDR, 0,0% degradacoes;
  - configuracao de maior SNR:
    `wpt_frame_coif3_l3_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - final operacional: +3,524 dB SNR, +1,785 dB SI-SDR, 4,2% degradacoes.

Leitura revisada: a trilha Wavelet nao deve ser encerrada. A candidata Wavelet
mais promissora nao e a DWT nem a WPT por coeficiente, mas WPT em quadros com
estimativa temporal por subbanda. Ainda assim, a configuracao vencedora e
offline, usa quantil global por subbanda e continua abaixo da subtracao STFT em
SI-SDR. O proximo passo natural, se a equipe quiser insistir, e uma WPT em
quadros causal/rolante com escuta critica.

## Status apos perfil max completo

- Data: 2026-06-08.
- Rodada completa: `resultados/wavelet_heavy_max_refinement_full/`.
- Perfil: `max`.
- Triagem: 8784 candidatos.
- Validacao completa: 113 candidatos.
- Comparacao final: 12 candidatos.

Resultado principal:

- DWT limiarizada continuou praticamente neutra.
- WPT por coeficiente continuou limitada.
- WPT em quadros melhorou em relacao ao perfil `focused`:
  - configuracao robusta:
    `wpt_frame_haar_l4_n1024_h512_global_quantile_q0.2_w31_f0.2_sm0`;
  - final operacional: +3,212 dB SNR, +1,922 dB SI-SDR, 0,0% degradacoes;
  - configuracao de maior SNR:
    `wpt_frame_db6_l4_n1024_h512_global_quantile_q0.35_w31_f0.2_sm0`;
  - final operacional: +3,613 dB SNR, +2,099 dB SI-SDR, 0,0% degradacoes;
  - ressalva: a configuracao `db6` teve 4,2% degradacoes na validacao.

Leitura atualizada: o perfil `max` encontrou WPT em quadros melhor que o
`focused`, entao a trilha Wavelet tem um resultado offline forte. Mesmo assim,
ela nao passa a ser candidata PC principal: a subtracao STFT causal adaptativa
continua mais madura para tempo real e tem SI-SDR final maior. A proxima etapa
Wavelet, se priorizada, deve ser uma formulacao em quadros causal/rolante com
estado explicito e escuta critica, nao a promocao direta da versao offline.

## Status apos Checkpoint 24

- Data: 2026-06-08.
- Decisao PC: subtracao STFT causal adaptativa.
- Validacao PC: STFT causal congelada validada no Windows por 600 s em
  self-test sintetico e 600 s em captura fisica `input-only`, sem blocos acima
  de 20 ms.
- Papel da WPT em quadros: achado Wavelet offline forte, nao implementacao PC.
- Papel da voz autoral: validacao complementar futura, sem bloquear a decisao
  tecnica.

Conclusao de narrativa: a trilha Wavelet foi refinada e valorizada, mas nao
muda o caminho PC atual. Uma WPT causal/rolante pode ser proposta como pesquisa
futura; ela nao e requisito para a consolidacao da STFT causal no relatorio ou
na defesa. A validacao Windows prolongada nao mede playback nem `round-trip`, e
uma rodada full-duplex cabeada deve ser tratada como experimento separado.
