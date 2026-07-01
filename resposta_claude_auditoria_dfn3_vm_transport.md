O plano de auditoria está completo. Vou apresentar diretamente a análise, já que `ExitPlanMode` não está disponível como ferramenta neste contexto.

---

## Auditoria técnica — DFN3 VM transport 48 kHz

### Achados fortes

**1. Integridade funcional é válida e robusta.**
6000/6000 blocos, perda zero, CRC zero, hash SHA-256 determinístico idêntico em 20+ rodadas TCP. Pode ser afirmado sem ressalvas.

**2. `consumer_interval_max = 1508 ms` está sendo ignorado nas conclusões locais.**
O `scheduler_probe_max` emparelha: 1507 ms nas mesmas rodadas. Isso é parada completa do ambiente, não jitter de transporte. A análise local foca em `receive_max ≤ 154 ms` e subestima gravemente a severidade.

**3. Underflow rate de 7–13,5 % é incompatível com áudio contínuo.**
Referência para áudio interativo: < 0,01 %. A linguagem "drops/recoveries explícitos" minimiza: **1 em cada 8 blocos foi silêncio** no pior caso.

**4. `header_wait_max (~241 ms) > receive_max (~154 ms)` — contradição não investigada.**
Esses máximos vêm de sequências diferentes. O TCP do guest bufferia múltiplos blocos e os entrega em burst (*batch delivery* involuntário). O bloco com `header_wait=241 ms` foi seguido de um bloco chegando quase imediatamente, tornando o `receive_interval` daquele par menor que 241 ms. Isso é uma classe de evento sem diagnóstico próprio no analisador.

**5. Rodada host-only eliminou `unaccounted_receive_or_nat` completamente.**
Evidência direta: NAT contribui stalls em rodadas com rota NAT. O único stall restante na rodada host-only foi `guest_scheduler_correlated`. Isso isola as duas causas como **independentes e aditivas** — dado mais forte que as conclusões locais reconhecem.

**6. Gate `check` por construção para ring buffer.**
`analyze_dfn48_vm_transport.py` tem `warn(False, "ring_buffer_diagnostic_not_realtime_gate", warnings)` — toda rodada com ring buffer é `check` por design, independentemente das métricas. As 4 rodadas recentes não são `check` por falha; são `check` por construção.

---

### Possíveis falhas na interpretação

| Afirmação local | Problema |
|---|---|
| "Afinidade melhorou o pior stall" | N=1 por config; variação Run1→Run2 (76→69 ms) está dentro do ruído run-to-run |
| "`unaccounted_receive_or_nat` é classe diagnóstica" | É bucket de falha de classificação; batch delivery TCP não tem classe própria |
| "Host-only não estabilizou baixa latência" | Correto, mas perde o dado importante: NAT **desapareceu**, sobrando apenas scheduler — as causas são separáveis |
| Playout p99 ~119 ms como métrica de transporte | 80 ms são prebuffer estrutural obrigatório (`ring_prebuffer_blocks=8`); latência de transporte real é ~39 ms p99 |
| Smoke tests com waitable_timer mostrando boas métricas | Esses resultados estão em `tmp/dfn48_ring_local_smoke`, fora dos artefatos auditáveis de `resultados/` — não podem ser citados em relatório |

---

### Experimentos que ainda valem na VM

1. **Sink=memory sem consumer thread** — medir `receive_interval` puro, sem ring. Se `receive_max` cair, stalls eram do consumer scheduler, não do transporte.
2. **`FIONREAD` antes de cada recv** — confirmar batch delivery TCP do guest stack. Se em eventos com `header_wait > 30 ms` e `receive_interval ≈ 10 ms` o FIONREAD mostrar > 960 bytes, confirma.
3. **Host-only isolado** (sem afinidade, sem prioridades extras) — confirmar que a ausência de `unaccounted_receive_or_nat` não foi artefato das outras otimizações simultâneas.

---

### Experimentos fora da VM / Windows nativo

| Experimento | Impacto de decisão |
|---|---|
| **Loopback TCP no host Windows (sem VM)** | CRÍTICO — se passar (`receive_max < 20 ms`, drops ≈ 0), fase VM pode ser encerrada com fundamento; se falhar, há bug no código |
| **DFN3 inline no receptor loopback** | Define budget de latência antes de integrar SYSVAD (~2–5 ms esperados) |
| **10 repetições de loopback** | Estabelece baseline estatístico citável no relatório acadêmico |

---

### Decisão recomendada

**Encerrar fase VM como "integridade funcional validada; tempo real descartado por limitação estrutural do ambiente VirtualBox/NEM."**

Razões: (1) `consumer_interval_max = 1508 ms` demonstra pausas que nenhuma config elimina; (2) underflow 7–13,5 % é incompatível com áudio; (3) causas identificadas são de ambiente, não de código; (4) o único experimento que muda a decisão (loopback nativo) ainda não foi feito.

Não promover nenhuma configuração como "validada para tempo real". Prosseguir para loopback nativo.

---

### Riscos para documentação acadêmica

1. N=1 por configuração — comparações entre configs são exploratórias, não controladas.
2. Rodada host-only tinha outras otimizações simultâneas ativas — não isola puramente NAT vs sem NAT.
3. Sem baseline loopback nativo, não é possível distinguir "problema de VM" de "problema de código em qualquer ambiente".
4. Smoke tests úteis estão em `tmp/`, fora dos artefatos auditáveis — não citáveis sem migrar para `resultados/`.
5. Gate `check` por construção para ring buffer deve ser declarado explicitamente para não parecer que as rodadas falharam nos critérios.

---

O texto sugerido para documentação acadêmica e os detalhes técnicos completos (incluindo trechos de código da lógica de classificação) estão no plano em `C:\Users\augus\.claude\plans\pedido-de-auditoria-eventual-parasol.md`.
