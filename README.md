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

## Arquitetura

```
app/
  main.py   → FastAPI: serve o frontend + /api/vitals (drift fisiológico simulado),
              /api/routines, /api/exams, /api/stock, /api/achievements,
              /api/chat (B.I.P), /api/diagnose (Gemini | fallback offline)
  ai.py     → cliente Gemini + prompt médico espacial + motor offline curado
  data.py   → missão AURORA-7: tripulante, kit médico de bordo, rotinas, exames, conquistas
static/
  index.html → 4 telas + dock + chat (sem framework, SVG inline)
  css/styles.css → design system Frutiger Aero × terracota/azul-petróleo
  js/app.js → relógio/fusos/céu + fase da lua, vitais, rotinas+conquistas,
              diagnóstico, exames, chat, personalização do avatar, dock magnética
```

- **Sem banco de dados**: estado do usuário (rotinas do dia, histórico, conquistas, conversas, diagnósticos) em `localStorage`; vitais simulados server-side com deriva suave.
- **Avatar/B.I.P**: SVG vetorial animado (corpo inteiro sobre **palco**, respiração, piscar, lágrimas). O avatar é **interativo ao toque** (acenar, pular, rir, balão de fala) e **customizável** (roupa: astronauta/casual/voo/cargo · pele · cabelo · pelos faciais · olhos · sardas).

## Créditos / próximos passos

- Dados de missão fictícios: Expedition AURORA-7, Base Ares (Mare Acidalium). MET desde 11/jun/2026.
- Fase da lua: algoritmo sinódico simplificado a partir da lua nova de 06/jan/2000.
- Ideias de evolução: integração real com wearables (HR/SpO₂), exames via FHIR/HL7, cenário 3D (Three.js), modo EVA, registro de sintomas por voz, modelo de dosimetria real (NASA OLTARIS), multiplayer de tripulação.
