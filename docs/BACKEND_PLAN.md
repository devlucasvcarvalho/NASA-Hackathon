# Plano do Backend + ML — B.I.P

Branch: `back_ml` · Stack: FastAPI + SQLite + scikit-learn · Dono: Eng. ML/Dados

## 1. Princípios

1. **Não quebrar o front.** Endpoints atuais (`/api/vitals`, `/routines`, `/exams`, `/stock`, `/achievements`, `/chat`, `/diagnose`, `/health`) mantêm o contrato. Só **adicionamos campos e rotas novas**.
2. **O servidor é a fonte da verdade.** Status, deltas, tendências, conquistas e contexto clínico passam a ser calculados no backend (hoje estão fixos/fake no JS).
3. **Funciona offline.** Sem Gemini e sem rede o demo roda completo (já é assim; mantemos).
4. **Dados defensáveis.** Faixas de referência e perfis baseados em fontes NASA (HRP Evidence Reports, OSDR, ISS medical standards), citadas no README.

## 2. Estrutura de pastas

```
app/
  main.py              # só cria o app, monta routers e static
  config.py            # env vars (GEMINI_*, DB_PATH, SEED, SIM_SPEED)
  db.py                # conexão SQLite + criação de tabelas + seed
  schemas.py           # modelos Pydantic (entrada/saída, resposta da IA)
  routers/
    vitals.py          # /api/vitals, /history, /status
    routines.py        # /api/routines + completar + histórico
    achievements.py    # /api/achievements (calculado no servidor)
    exams.py           # /api/exams, /trends
    stock.py           # /api/stock + baixa de estoque
    diagnose.py        # /api/diagnose, /diagnoses (histórico)
    chat.py            # /api/chat, histórico
    mood.py            # /api/mood (PHQ-2)
    health.py
  services/
    simulator.py       # gerador de série temporal fisiológica
    anomaly.py         # detecção de anomalia + status por vital
    risk.py            # score de risco da tripulante
    context.py         # monta contexto clínico p/ IA (vitais+exames+rotina+sono+humor)
    gamification.py    # streak, dias perfeitos, conquistas
  ai.py                # Gemini + fallback (existente, refatorar p/ validar JSON)
  data.py              # dados estáticos (kit, rotinas, exames, conquistas)
data/
  bip.db               # SQLite (gitignored)
  reference_ranges.json
ml/
  notebooks/           # exploração
  train_anomaly.py     # treina/salva modelo
  models/              # .joblib
tests/
```

## 3. Banco (SQLAlchemy: SQLite local, Postgres/Neon em produção)

Escolha: **`DATABASE_URL`** define o banco. Sem ela, SQLite local (`data/bip.db`); na Vercel, Neon Postgres.
O SQLite em arquivo **não persiste na Vercel** (disco efêmero), por isso Postgres lá.
**Vitais e sono não são gravados**: o simulador é determinístico (`seed + timestamp`) e o histórico é recalculado.
Só o estado do usuário vai ao banco (tabelas abaixo, exceto `vitals`/`sleep`, que viram cálculo).

| Tabela | Colunas principais |
|---|---|
| `vitals` | ts, heart_rate, spo2, hydration, bp_sys, bp_dia, temperature, hrv, radiation_rate |
| `sleep` | date, hours, latency_min, awakenings, deep_pct, rem_pct, night_hr |
| `routine_log` | date, task_id, done_at |
| `mood` | ts, phq2_q1, phq2_q2, score |
| `diagnoses` | id, ts, query, image_attached, result_json |
| `chat` | id, ts, role, text |
| `stock_moves` | ts, item, delta, reason |
| `achievements_unlocked` | id, ts |
| `anomalies` | ts, metric, value, score, level |

Vitais e sono são gerados/ingeridos; o resto é escrito pelo usuário via API.

## 4. Endpoints

### Existentes (manter contrato, enriquecer)
- `GET /api/vitals` → mesmos campos **+** `status` e `delta` por métrica (`{"heart_rate": {"value":69,"status":"normal","delta":"+2 vs ontem"}}` em campo novo `metrics`, sem remover os antigos).
- `GET /api/achievements` → lista + `progress` e `unlocked` calculados.
- `POST /api/diagnose` → contexto montado no servidor; resposta validada por schema.
- `POST /api/chat` → grava histórico.

### Novos
| Método | Rota | Função |
|---|---|---|
| GET | `/api/vitals/history?metric=&hours=` | série temporal real (substitui sparkline fake) |
| GET | `/api/vitals/status` | status e score de anomalia por vital |
| GET | `/api/risk` | risco global (0–100) + fatores |
| GET | `/api/sleep?days=` | histórico de sono |
| GET/POST | `/api/routines/today`, `/routines/{id}/complete` | estado e conclusão de tarefas |
| GET | `/api/routines/history?days=` | dias perfeitos, streak |
| GET/POST | `/api/mood` | diário PHQ-2 |
| GET | `/api/exams/trends?name=` | evolução (cortisol, DMO…) |
| GET | `/api/diagnoses` | histórico persistido |
| POST | `/api/stock/consume` | baixa de estoque após prescrição |
| GET | `/api/context` | contexto clínico que a IA enxerga (debug/demo) |

## 5. Parte de ML / dados

### 5.1 Simulador de vitais (`services/simulator.py`)
- Modelo base: ritmo circadiano + ruído + resposta a eventos (exercício ARED às 07:30, sono, EVA, estresse).
- Perfil de missão: **adaptação à microgravidade** (FC de repouso, PA, perda óssea, deslocamento de fluidos) com parâmetros de literatura NASA.
- **Injeção de cenários** para a demo: `?scenario=infection|dehydration|stress|spe` altera as curvas de forma coerente e dispara o ML.
- Persistência: pré-gera 30 dias no seed e continua em tempo real.

### 5.2 Detecção de anomalia (`services/anomaly.py`, `ml/train_anomaly.py`)
1. **Camada regra/estatística** (baseline, sempre ativa): z-score em janela móvel + limites clínicos de `reference_ranges.json` → `normal | vigilancia | alerta`.
2. **Camada ML**: `IsolationForest` multivariado (FC, SpO₂, temp, PA, HRV, sono) treinado nos primeiros dias "saudáveis" da tripulante → `anomaly_score`.
3. Saída por vital: `status`, `delta` vs ontem, `trend` (slope), `score`.

### 5.3 Score de risco (`services/risk.py`)
Combina anomalias + sono + radiação acumulada + humor + aderência à rotina + exames flagados em 0–100 com **fatores explicáveis** ("cortisol AM alto", "sono < 6h por 3 noites"). Alimenta o `/diagnose` e a tela Início.

### 5.4 Contexto para a IA (`services/context.py`)
Monta texto estruturado: vitais atuais + tendências + anomalias + sono + humor + exames alterados + rotina atrasada. Substitui a string hardcoded do front e é o diferencial técnico (IA ancorada em dados).

### 5.5 Dados reais / referências
- NASA HRP Evidence Reports e Human Research Roadmap (riscos e faixas).
- NASA OSDR/GeneLab e LSDA (perfis biomédicos de voo, quando aplicável).
- Dose de radiação: valores típicos ISS/Mars transit (RAD/MSL) e OLTARIS como referência.
- Registrar fonte e ano em `data/reference_ranges.json` e no README.

## 6. IA (Gemini) — endurecimento
- Validar a resposta com Pydantic (`DiagnosisOut`); se inválida → 1 retry → fallback offline.
- Timeout 15 s, tratamento de erro/quota, logging.
- Prompt recebe o **contexto do servidor** (5.4).
- Guardrails: sempre off-Terra (kit → MCC → abortar), sem "procure médico".

## 7. Gamificação no servidor
`services/gamification.py` calcula `perfect_days`, `streak`, `hydration_logs`, `mornings_full`, `nights_full`, `diagnoses`, `image_diagnoses` a partir de `routine_log` e `diagnoses`; destrava conquistas e grava em `achievements_unlocked`.

## 8. Fases e prioridade

| Fase | Entrega | Valor |
|---|---|---|
| **0** | Refatorar em routers/services, `config.py`, SQLite + seed. Contrato antigo intacto | base |
| **1** | Simulador + `/vitals/history` + `status/delta` no `/vitals` | tira sparkline/status fake |
| **2** | Anomalia (z-score + IsolationForest) + `/risk` | **núcleo ML da demo** |
| **3** | `context.py` + `/diagnose` validado + histórico | IA ancorada em dados |
| **4** | Rotinas/humor/estoque/conquistas persistidos | estado fora do `localStorage` |
| **5** | Cenários de demo, testes (pytest), README, deploy HF Spaces | pronto p/ apresentar |

Se o tempo apertar: **0 → 1 → 2 → 3** é o mínimo para mostrar ML de verdade.

## 9. Acordos com o front
- Nenhum campo existente é removido ou renomeado.
- Campos novos são opcionais; o front adota quando quiser (`metrics`, `history`, `risk`).
- Mudanças de contrato são avisadas antes do merge em `develop`.
- Tarefa de front que sai disso: trocar sparkline/status/delta fixos pelos dados da API e ler rotinas/diagnósticos do backend.

## 10. Testes e qualidade
- `pytest` + `httpx` TestClient: contrato dos endpoints, schema da IA, streak, anomalia em cenário injetado.
- `GET /api/health` expõe: IA pronta, DB ok, modelo ML carregado.
- CI opcional: rodar pytest no PR.

## 11. Riscos
| Risco | Mitigação |
|---|---|
| Quebrar o front ao refatorar | Fase 0 só move código; testes de contrato antes |
| Sem dataset real | Simulador parametrizado por literatura + disclaimer honesto |
| Gemini fora do ar na demo | Fallback offline já existente + retry |
| SQLite no HF Spaces é efêmero | Seed recriado a cada start; aceitável para demo |
| ML "caixa-preta" | Fatores explicáveis no risco; baseline estatístico visível |
