---
title: B.I.P — Biomedical Intelligent Partner
emoji: 🫀
colorFrom: teal
colorTo: orange
sdk: docker
pinned: false
---

# B.I.P · Biomedical Intelligent Partner

**Copiloto de saúde para tripulações em missões espaciais.** Sistema web interativo construído para a **NASA Space Apps Challenge**, com estética Y2K / Frutiger Aero e leitura de missão inspirada em fição científica operacional.

O B.I.P acompanha o tripulante **fora da Terra** — por isso nenhuma conduta remete a pronto-socorro: tudo é resolvido com o **kit médico de bordo**, **telemedicina com o Mission Control (MCC)** ou, em caso grave, **aborto da missão e retorno à Terra**.

## O que o B.I.P faz

| Tela | Função |
| --- | --- |
| **Início** | Avatar do tripulante **humano e editável** (traje, tom de pele, corte/cor de cabelo, pelos faciais, cor dos olhos, sardas) com emoções reativas, sinais vitais (FC, SpO₂, hidratação, dosimetria de radiação, PA, temperatura) em dashboard, relógio compacto no canto direito (Houston / Greenwich / Tóquio / **Sol médio de Marte**) com **céu celeste real** (sol, dourado, **fase da lua calculada** ou sol marciano) e o **B.I.P**, robô mascote conversacional |
| **Rotinas** | Checklist gamificado por períodos (manhã/tarde/noite) com horários, streak, anel de progresso do dia, 9 **conquistas** e avatar que **muda de expressão**: feliz (tudo feito), aflito (pendências atrasadas), choroso (nada feito) |
| **Diagnóstico** | Entrada por **texto e/ou imagem** (ferida, exantema, exame). A IA cruza **vitais + exames + rotina + sono + conversas com o B.I.P**, devolve hipóteses com probabilidade, **receituário de bordo** (dose, frequência, duração, instrução), conduta passo a passo, monitoramento, red flags e triagem: **a bordo → telemedicina MCC → aborto/retorno à Terra**. Histórico de resultados anteriores |
| **Exames** | Dossiê completo dos exames feitos em outros equipamentos (hemograma, ECG, DXA, dosimetria…), com valores, flags (alto/baixo/atenção), busca, filtro por categoria e **"Enviar para o diagnóstico"** |

Barra inferior estilo **macOS Dock** (com magnificação no hover) + **badge de alerta** sobre o ícone de Rotinas quando há pendências atrasadas.

## Idioma / Language / Idioma

O B.I.P é **trilíngue (Português · English · Español)**, com detecção automática do idioma do navegador na primeira visita (PT/ES/EN, fallback `en`) e seletor manual no topo (PT · EN · ES) persistido em `localStorage`. Cobre toda a UI, conteúdo da missão (rotinas, exames, conquistas, kit de bordo), respostas da IA (Gemini no idioma escolhido) e até o motor offline. Chaves centralizadas em `static/js/i18n.js` + conteúdo servido pelo backend por `?lang=` / campo `lang`.

## IA — como funciona

- **Com `GEMINI_API_KEY`**: respostas reais via Google Gemini (`gemini-2.5-flash` por padrão), com system prompt estrito: off-Terra, kit de bordo, sem "procure um médico", JSON estruturado.
- **Sem a chave** (ex.: demo offline): motor local curado e consistente (red-flags, 10 síndromes, fallback) garante a experiência completa sem custo nem rede.
- Em ambos os casos o diagnóstico devolve o **mesmo schema JSON** (severity, causes, prescription, procedures, monitoring, red_flags, factors_used…).

> ⚠️ **Disclaimer médico**: o B.I.P é uma ferramenta de apoio à decisão para contexto de missão (e protótipo de hackathon). Não substitui o médico de voo do MCC. Em emergência real, o único protocolo é: MCC agora + estabilização a bordo.

## Rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860
```

Abra http://127.0.0.1:7860

Para IA real (opcional):

```bash
set GEMINI_API_KEY=sua_chave_aqui   # Windows · export no macOS/Linux
# opcional: set GEMINI_MODEL=gemini-2.5-flash
uvicorn app.main:app --port 7860
```

A chave gratuita do Gemini sai em https://aistudio.google.com/apikey

## Deploy grátis — Hugging Face Spaces (recomendado)

1. Crie um Space em https://huggingface.co/new-space → SDK **Docker**.
2. Suba este repositório (o `README.md` já tem o front matter `sdk: docker` e o `Dockerfile` expõe a porta 7860):

```bash
git remote add space https://huggingface.co/spaces/SEU_USUARIO/bip-health
git push space main
```

3. Em **Settings → Variables and secrets**, adicione `GEMINI_API_KEY` (secret). Sem ela o app funciona com o motor local.
4. Pronto: `https://huggingface.co/spaces/SEU_USUARIO/bip-health`

### Alternativas gratuitas
- **Render** (free web service, Docker): acorde lento após inatividade (~30 s).
- **Streamlit Cloud**: exigiria portar a UI (não recomendado para esta estética).

## Backend and ML

FastAPI + SQLAlchemy (SQLite locally, Postgres in production) + numpy. Front-end API reference: [`docs/API_FRONT.md`](docs/API_FRONT.md); method and limitations: [`docs/METHOD_AND_LIMITATIONS.md`](docs/METHOD_AND_LIMITATIONS.md); plan: [`docs/BACKEND_PLAN.md`](docs/BACKEND_PLAN.md).

```
app/
  main.py            → wires routers and static files, initializes the database
  config.py, db.py   → env vars; SQLAlchemy engine (DATABASE_URL)
  models.py          → vitals, sleep, routines, mood, diagnoses, chat, stock, achievements, demo state, space-weather cache
  schemas.py         → validation and guardrails for the AI response
  ai.py              → Gemini (2 attempts) + curated offline engine (PT/EN/ES)
  exams_data.py      → exam dossier (PT/EN/ES)
  routers/           → vitals, tracking (routines/mood/stock/achievements), ai_routes, content, demo, spaceweather, health
  services/
    simulator.py     → deterministic simulated vitals/sleep (+ demo scenarios)
    history.py       → persisted history (30-day backfill + per-request catch-up)
    anomaly.py       → circadian baseline (15-min slots) + robust z + Mahalanobis
    risk.py          → 0–100 risk score with explainable factors
    context.py       → clinical context built on the server for the AI
    spaceweather.py  → real NASA DONKI: CME impacts on Mars, SEP events
    gamification.py  → streak and achievements
    demo.py          → global demo scenario
  snapshots/         → real NASA DONKI snapshot used when the API is unreachable
tests/               → pytest (contract, history, anomaly, AI, tracking, demo, space weather, i18n)
```

### Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | Postgres (e.g. Neon). Accepts `postgres://` | SQLite at `data/bip.db` (`/tmp` on Vercel) |
| `GEMINI_API_KEY` | Real AI | none: offline engine |
| `GEMINI_MODEL` / `GEMINI_TIMEOUT` | model / timeout in seconds | `gemini-2.5-flash` / `15` |
| `HISTORY_DAYS` | days of vitals history | `30` |
| `NASA_API_KEY` | NASA key (free at api.nasa.gov); without it `DEMO_KEY` is used (very small quota) | `DEMO_KEY` |
| `SPACE_WEATHER` | `off` disables the NASA call (cache/snapshot only) | `on` |
| `MAX_IMAGE_MB` | max image size for diagnosis | `5` |
| `DEMO_TOKEN` | requires `X-Demo-Token` to change the demo scenario | off |

### Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

### Demo mode

`POST /api/demo/scenario` with `{"scenario": "infection"}` (or `dehydration`, `stress`, `spe`) makes vitals, risk, context, diagnosis and space weather respond with the scenario; `{"scenario": null}` goes back to normal. Vitals and sleep are **simulated** (see the limitations doc). The `spe` scenario adds a **simulated, labelled** solar event; the rest of the space-weather data is real NASA DONKI.

### Deploying to Vercel (untested)

1. Create a Postgres database (Neon via the Vercel Marketplace) and set `DATABASE_URL`.
2. Set `NASA_API_KEY`, `GEMINI_API_KEY` (optional) and `DEMO_TOKEN`.
3. `api/index.py` exposes the app and `vercel.json` bundles `static/**` into the function. Without `DATABASE_URL` it falls back to SQLite in `/tmp` (ephemeral).

## Front-end architecture

```
static/
  index.html → 4 telas + dock + chat (sem framework, SVG inline)
  css/styles.css → design system Frutiger Aero × terracota/azul-petróleo
  js/app.js → relógio/fusos/céu + fase da lua, vitais, rotinas+conquistas,
              diagnóstico, exames, chat, personalização do avatar, dock magnética
```

- **Avatar/B.I.P**: SVG vetorial animado (corpo inteiro sobre **palco**, respiração, piscar, lágrimas). O avatar é **interativo ao toque** (acenar, pular, rir, balão de fala) e **customizável** (roupa: astronauta/casual/voo/cargo · pele · cabelo · pelos faciais · olhos · sardas).
- User state is moving from `localStorage` to the backend (see `docs/FRONT_DEMANDS.md`).

## Créditos / próximos passos

- Dados de missão fictícios: Expedition AURORA-7, Base Ares (Mare Acidalium). MET desde 11/jun/2026.
- Fase da lua: algoritmo sinódico simplificado a partir da lua nova de 06/jan/2000.
- Ideias de evolução: integração real com wearables (HR/SpO₂), exames via FHIR/HL7, cenário 3D (Three.js), modo EVA, registro de sintomas por voz, modelo de dosimetria real (NASA OLTARIS), multiplayer de tripulação.
