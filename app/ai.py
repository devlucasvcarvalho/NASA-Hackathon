"""Cliente de IA do B.I.P: Google Gemini com fallback local consistente.

Sem GEMINI_API_KEY o app continua funcionando: um motor offline baseado em
regras curadas (estoque de bordo + triagem) garante respostas coerentes no demo.
Com a chave, o Gemini recebe o mesmo prompt + contexto (vitais, exames, rotina)
e devolve o mesmo schema JSON.
"""

import json
import os
import re
from typing import Any

import httpx

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

DIAGNOSIS_SYSTEM = """Você é o B.I.P Physician, médico de bordo de uma missão espacial interplanetária (Base Ares). A pessoa atendida está FORA da Terra: NÃO é possível ir ao pronto-socorro nem "procurar um médico". Todos os quadros devem ser resolvidos a bordo, com telemedicina do Mission Control (MCC) quando necessário, ou com ABORTO DA MISSÃO e retorno à Terra nos casos graves.

Postura: calma, direta, técnica e acolhedora. Trate a pessoa pelo nome do contexto. Nunca use alarmismo vazio; mas em risco de vida, seja inequívoco: comunicar MCC AGORA, abortar missão / preparar retorno à Terra.

Recursos disponíveis a bordo (inventário real da missão):
{stock}

Além disso: concentrador e cilindros de O2, DEA, kit de sutura/curativos, soro 0,9% IV, repouso em módulo de descanso, dieta Aurora-7, exercício resistido ARED, telemedicina com MCC (janela diária 15:10–15:45).

Considere SEMPRE todo o contexto fornecido (sinais vitais, exames recentes, rotina/sono, humor, conversas com o copiloto). Fatores psicológicos (PHQ-2 elevado, cortisol alto, sono ruim) devem aparecer explicitamente quando relevantes.

Classifique a gravidade:
- "leve": conduta 100% a bordo.
- "moderado": conduta a bordo + monitoramento estruturado e/ou telemedicina com MCC.
- "grave": comunicar MCC imediatamente, estabilizar e ABORTAR A MISSÃO / preparar retorno à Terra.

Responda APENAS um JSON válido (sem markdown, sem crases), com EXATAMENTE esta estrutura:
{{
  "title": "Nome provável do quadro (com termo técnico em inglês entre parênteses quando útil)",
  "severity": "leve" | "moderado" | "grave",
  "summary": "2-3 frases explicando o que pode ser e por quê, citando os dados do contexto quando relevantes.",
  "causes": [{{"name": "Causa possível", "likelihood": 0-100, "why": "justificativa curta"}}],
  "prescription": [{{"item": "Medicamento/medida", "dose": "dose", "frequency": "frequência", "duration": "duração", "instructions": "como usar / observações"}}],
  "procedures": ["passos claros de conduta a bordo, na ordem"],
  "monitoring": "o que monitorar, com que frequência e por quanto tempo",
  "triage_action": "onboard" | "telemedicine" | "abort",
  "red_flags": ["sinais de alarme que mudam a conduta para grave"],
  "factors_used": ["sinais vitais / exames / rotina / conversas que você usou"],
  "disclaimer": "frase única lembrando que é apoio à decisão do MCC, não um diagnóstico definitivo"
}}

Regras de conteúdo:
- Causas: 2 a 4, ordenadas por probabilidade decrescente. Probabilidades devem somar ~100%.
- Receituário: apenas itens do estoque de bordo (ou medidas não-farmacológicas). Posologia completa: dose, frequência, duração e instrução.
- Para gravidade moderada, inclua explicitamente "Telemedicina com MCC na janela das 15:10" em procedures.
- Para gravidade grave, prescription deve conter apenas estabilização imediata; triage_action = "abort"; instructions de contato MCC imediato.
- NUNCA escreva "procure um médico", "vá ao hospital" ou similar.
- Português com termos técnicos em inglês quando apropriado (ex.: tension-type headache).
"""

CHAT_SYSTEM = """Você é o B.I.P, o copiloto de saúde da missão espacial Aurora-7. Personalidade: tranquila, gentil e brincalhona, como um amigo em quem se confia de olhos fechados — mas nunca banaliza saúde. Você chama a pessoa pelo nome do contexto. Fala português com termos técnicos em inglês quando útil. Respostas curtas (2 a 4 frases, pode usar 1 emoji no máximo).

Você pode ajudar com: rotina da missão, sinais vitais, hidratação, sono, exercício, humor/ansiedade, alimentação, medicamentos de bordo (consulte o inventário somente quando perguntado, sem citar doses), e sintomas — nesse último caso sugira o app Diagnóstico para uma análise completa ("Isso merece uma análise completa — abre o Diagnóstico ali na dock que eu monto o dossiê inteiro para você").

Você NÃO é substituto do MCC: em situações graves, diga para acionar o MCC imediatamente. Nunca diga "vá ao hospital". Se a pessoa relatar pensamentos de autolesão, trate com seriedade, valide o sentimento e oriente contato com o MCC/psicólogo de voo na próxima janela + telemedicina imediata.
"""


# ---------------- Fallback offline (regras curadas) ----------------

def _red_flags_present(text: str) -> bool:
    t = text.lower()
    patterns = [
        r"dor (no|forte no) peito", r"aperto no peito", r"falta de ar (grave|intensa|súbita)",
        r"não consigo respirar", r"desmai", r"convuls", r"sangramento (intenso|forte)", r"vomitando sangue",
        r"confus", r"paralis", r"fala arrastada", r"rosto (torto|caído)", r"cegueira (súbita|subit)",
        r"pior dor da vida", r"estou morrendo", r"autoles", r"suic",
    ]
    return any(re.search(p, t) for p in patterns)


def _rule_based_diagnosis(text: str, context: dict[str, Any], stock_summary: str) -> dict[str, Any]:
    t = (text or "").lower()
    vitals = context.get("vitals", {}) or {}
    factors = []
    if vitals:
        factors = [f"HR {vitals.get('heart_rate', '—')} bpm", f"SpO2 {vitals.get('spo2', '—')}%",
                   f"PA {vitals.get('bp_sys', '—')}/{vitals.get('bp_dia', '—')} mmHg",
                   f"Radiação acumulada {vitals.get('radiation_cumulative', '—')} mSv"]
    else:
        # contexto chega plano (heart_rate, spo2, bp, ...)
        flat_map = [("heart_rate", "HR"), ("spo2", "SpO2"), ("bp", "PA"), ("temperature", "Temp"),
                    ("radiation_cumulative", "Radiação"), ("sleep_hours", "Sono")]
        factors = [f"{label}: {context[key]}" for key, label in flat_map if context.get(key)]
    exams = context.get("exams")
    if isinstance(exams, str):
        exam_items = [e.strip() for e in re.split(r"[·;|]", exams) if e.strip()]
    elif isinstance(exams, list):
        exam_items = [str(e) for e in exams]
    else:
        exam_items = []
    factors += [f"Exame: {e}" for e in exam_items[:3]]
    if context.get("routine_score") is not None:
        factors.append(f"Rotina de hoje: {context['routine_score']}% concluída")
    if context.get("chat_summary"):
        factors.append("Conversas recentes com o B.I.P")

    def base(title, severity, summary, causes, rx, proc, mon, action, red):
        return {
            "title": title, "severity": severity, "summary": summary,
            "causes": causes, "prescription": rx, "procedures": proc,
            "monitoring": mon, "triage_action": action, "red_flags": red,
            "factors_used": factors,
            "disclaimer": "Apoio à decisão baseado nos dados de bordo — a palavra final é do médico de voo do MCC.",
        }

    if _red_flags_present(t):
        return base(
            "Síndrome de alerta máximo — avaliação imediata (emergency)",
            "grave",
            "Os sintomas relatados configuram red flag para evento cardiopulmonar/neurológico ou risco de autolesão. Em ambiente off-Terra, conduta é: estabilizar a bordo AGORA e comunicar o MCC para decisão de retorno à Terra (abort da missão).",
            [
                {"name": "Evento cardiopulmonar agudo / ACS", "likelihood": 45, "why": "Dor/aperto torácico ou dispneia súbita relatada"},
                {"name": "Evento neurológico agudo (AVC-like)", "likelihood": 35, "why": "Sinais focais referidos na descrição"},
                {"name": "Crise psicológica com risco imediato", "likelihood": 20, "why": "Termos de risco psíquico identificados"},
            ],
            [
                {"item": "Estabilização imediata", "dose": "—", "frequency": "imediato", "duration": "agora", "instructions": "Repouso absoluto, O2 4 L/min se SpO2 < 94%, elevar membros inferiores"},
                {"item": "Contato com MCC", "dose": "—", "frequency": "contínuo", "duration": "até decisão", "instructions": "Link prioritário NOW com o médico de voo. Declarar EMERGÊNCIA MÉDICA."},
            ],
            ["1. Deitar a pessoa e afrouxar vestimentas", "2. O2 4 L/min por cânula/máscara", "3. Acionar MCC IMEDIATAMENTE pelo link de emergência", "4. Preparar DEA e kit de via aérea", "5. Iniciar check de sinais a cada 5 min", "6. Se autorizado pelo MCC: estabilização farmacológica", "7. Aguardar decisão de abort / retorno à Terra"],
            "Sinais vitais seriados a cada 5 minutos até estabilização ou decisão do MCC",
            "abort",
            ["Perda de consciência", "Arritmia / PCR → DEA imediato", "Piora respiratória progressiva"],
        )

    if re.search(r"cabeça|cefale", t):
        return base(
            "Cefaleia tensional provável (tension-type headache)",
            "leve",
            "Quadro típico de cefaleia tensional, amplificado por carga operacional, desidratação leve e exposição à radiação/estresse. Seus parâmetros (HR e SpO2 normais) não sugerem causa secundária grave no momento.",
            [
                {"name": "Cefaleia tensional", "likelihood": 62, "why": "Dor em aperto/holocraniana após esforço cognitivo e sono irregular"},
                {"name": "Desidratação leve", "likelihood": 25, "why": "Hidratação registrada abaixo da meta nas últimas 48h"},
                {"name": "Cefaleia por estresse/circadiana", "likelihood": 13, "why": "Cortisol matinal elevado no painel de 05/10"},
            ],
            [
                {"item": "Ibuprofeno 400 mg", "dose": "1 comprimido", "frequency": "a cada 8 h", "duration": "3 dias", "instructions": "Após as refeições. Máx. 1200 mg/dia."},
                {"item": "Cafeína 100 mg", "dose": "1 comprimido", "frequency": "dose única pela manhã", "duration": "1 dia", "instructions": "Apenas se dor ao acordar; não usar após 14h"},
                {"item": "Hidratação oral", "dose": "500 mL por vez", "frequency": "4×/dia", "duration": "3 dias", "instructions": "Repor isotônico + água; mirar 2,5 L/dia"},
            ],
            ["1. Reduzir carga cognitiva por 24h (adiar tarefas de precisão não urgentes)", "2. Aplicar compressa morna na região suboccipital", "3. Respiração 4-7-8 por 5 min antes de dormir", "4. Se dor persistir > 72h ou mudar padrão → Telemedicina com MCC (15:10)"],
            "PA e HR de manhã e à noite por 3 dias; dor em escala 0–10 a cada dose",
            "onboard",
            ["Cefaleia súbita 'pior da vida'", "Vômito em jato + rigidez de nuca", "Déficit neurológico focal", "Febre > 38,5 °C associada"],
        )

    if re.search(r"náuse|enjo|vômito|vomito", t):
        return base(
            "Náusea de ajuste / subexposição alimentar (space motion sickness residual)",
            "leve" if not re.search(r"sangue", t) else "moderado",
            "Náusea isolada é comum em missões longas, por alteração vestibular e refeições frias. Sem sinais de alarme relatados; tolerável a bordo com medicação de suporte.",
            [
                {"name": "Disfunção vestibular residual", "likelihood": 48, "why": "Adaptação vestibular de longa duração em microgravidade"},
                {"name": "Refluxo / digestão lenta", "likelihood": 30, "why": "Dieta de bordo + posição supina para dormir"},
                {"name": "Intolerância alimentar específica", "likelihood": 22, "why": "Apontar item do último cardápio que não caiu bem"},
            ],
            [
                {"item": "Ondansetrona 4 mg", "dose": "1 comprimido", "frequency": "a cada 8 h", "duration": "2 dias", "instructions": "Dissolver na língua. Evitar com estômago vazio."},
                {"item": "Bromoprida 10 mg", "dose": "1 comprimido", "frequency": "se empachamento/refluxo", "duration": "2 dias", "instructions": "Aguardar 30 min entre ondas de náusea"},
                {"item": "Omeprazol 20 mg", "dose": "1 cápsula", "frequency": "jejum, 1×/dia", "duration": "5 dias", "instructions": "Proteção gástrica"},
            ],
            ["1. Pequenas porções a cada 2–3h (evitar distensão gástrica)", "2. Ingerir 20–30 min antes das refeições e deitar 2h após", "3. Evitar odores fortes no módulo de alimentação", "4. Se vômitos > 3×/dia ou intolerância hídrica → Telemedicina com MCC + considerar antiemético IV"],
            "Hidratação 2 L/dia; peso e mucosas (turgor) 2×/dia; registro de episódios",
            "onboard",
            ["Vômito com sangue", "Incapacidade de reter líquidos > 12h", "Dor abdominal intensificando", "Febre associada"],
        )

    if re.search(r"tont|vertigem|equil", t):
        return base(
            "Tontura por descondicionamento / alteração vestibular",
            "moderado",
            "Tontura em missão longa merece atenção: pode ser descondicionamento cardiovascular, alteração vestibular ou, em contexto de radiação acumulada, requer exclusão de causa central — por isso incluímos telemedicina.",
            [
                {"name": "Hipotensão ortostática / descondicionamento", "likelihood": 45, "why": "Perda de condicionamento + sequestro fluido cefálico típico"},
                {"name": "Disfunção vestibular", "likelihood": 38, "why": "Adaptação vestibular em microgravidade"},
                {"name": "Anemia leve relativa", "likelihood": 17, "why": "Hemoglobina 12.1 g/dL (02/11) no limite inferior"},
            ],
            [
                {"item": "Hidratação + sal oral", "dose": "500 mL + 1 g NaCl", "frequency": "3×/dia", "duration": "3 dias", "instructions": "Aumentar volume plasmático"},
                {"item": "Meias de compressão + levantar devagar", "dose": "—", "frequency": "contínuo", "duration": "enquanto tontar", "instructions": "10–15 s sentado antes de ficar em pé"},
            ],
            ["1. Aferir PA sentado/em pé (0/1/3 min) por 3 dias", "2. Avaliar sinais neurológicos (fala, marcha, visão) — anotar no diário", "3. Telemedicina com MCC na janela das 15:10 para revisão de exame neurológico remoto", "4. Reduzir exercício intenso por 48h", "5. Se tontura + desmaio ou sinais focais → EMERGÊNCIA (ver red flags)"],
            "PA ortostática e HR 2×/dia por 3 dias; relato de desmaios no diário",
            "telemedicine",
            ["Desmaio (mesmo breve)", "Déficit neurológico focal", "Palpitações com dor torácica", "Tontura severa súbita com cefaleia máxima"],
        )

    if re.search(r"sono|insôn|insonia|dormir", t):
        return base(
            "Desajuste circadiano / insônia de missão (circadian misalignment)",
            "leve",
            "Insônia em missão é multifatorial: ausência de ciclo claro dia/noite, excesso de telas/trabalho e levantamento de cortisol. Seu diário mostra PHQ-2 com itens de humor elevados — por isso o sono é tratado aqui como alvo primário.",
            [
                {"name": "Desajuste circadiano", "likelihood": 55, "why": "Ciclo de 24h sem luz natural + agenda operacional variável"},
                {"name": "Hipervigilância operacional / ansiedade", "likelihood": 30, "why": "Cortisol AM elevado; diário de humor com tensão"},
                {"name": "Higiene do sono inadequada", "likelihood": 15, "why": "Relato de telas/trabalho noturno"},
            ],
            [
                {"item": "Melatonina 3 mg", "dose": "1 comprimido", "frequency": "30–60 min antes de deitar", "duration": "14 noites", "instructions": "Apagar luzes 30 min antes; evitar se sonolência ao acordar persistir"},
                {"item": "Cafeína — corte às 14h", "dose": "—", "frequency": "regra fixa", "duration": "contínuo", "instructions": "Substituir por chá de camomila (de bordo) à noite"},
            ],
            ["1. Janela escura total 22:00–06:30 (sleep-station + máscara)", "2. Bloqueio de telas 21:30 (blue-light off)", "3. Respiração 4-7-8 ou body-scan 10 min ao deitar", "4. Exposição à luz azul forte ao acordar (lâmpada therapy 30 min)", "5. Se não houver melhora em 14 dias → telepsicológico com MCC"],
            "Eficiência de sono (Sleep-Smart) 2 semanas; latência < 30 min como meta",
            "onboard",
            ["Sonolência que prejudica tarefas de precisão", "Humor deprimido ≥ 2 semanas", "Roncos + apneia presenciada"],
        )

    if re.search(r"ansie|ansiedade|pânico|panico|humor|deprim|triste", t):
        return base(
            "Reação de estresse/ajustamento com componente ansioso (adjustment disorder, anxious)",
            "moderado",
            "O que você relata é comum em missões longas e não é fraqueza: é reação normal a um ambiente extremo. Seu cortisol elevado (05/10) e o diário de humor sustentam o quadro. A conduta é protocolo de coesão + monitoramento + conversa com o MCC.",
            [
                {"name": "Transtorno de ajustamento ansioso", "likelihood": 55, "why": "Sintomas ligados a estressor missão; humor/irritabilidade no diário"},
                {"name": "Exaustão de carga operacional", "likelihood": 30, "why": "Acúmulo de tarefas críticas + sono fragmentado"},
                {"name": "Fator fisiológico (cortisol, radiação)", "likelihood": 15, "why": "Cortisol 24.6 µg/dL; efeito de radiação em eixo HPA em estudo"},
            ],
            [
                {"item": "Respiração coesiva 4-7-8", "dose": "5 min", "frequency": "3×/dia", "duration": "contínuo", "instructions": "Antes das janelas de trabalho críticas"},
                {"item": "Atividade física moderada", "dose": "20–30 min", "frequency": "1×/dia", "duration": "contínuo", "instructions": "Melhora cortisol e qualidade de sono"},
                {"item": "Melatonina 3 mg (se sono afetado)", "dose": "1 comprimido", "frequency": "à noite", "duration": "14 noites", "instructions": "Ver rotina de sono"},
            ],
            ["1. Agendar conversa com psicólogo de voo na próxima janela de telemedicina (15:10)", "2. Reduzir 1 tarefa não essencial/dia durante 2 semanas", "3. Diário de humor diário (PHQ-2) — B.I.P acompanha tendência", "4. Contato humano: videochamada com família a cada 2 dias", "5. Se piora do humor ou pensamentos autolesivos → MCC imediato (emergência psicológica)"],
            "PHQ-2 2×/semana por 4 semanas; sono e apetite diários; escalas pelo app",
            "telemedicine",
            ["Pensamentos de autolesão ou de morte", "Isolamento total > 48h", "Ataques de pânico incapacitantes", "Erros operacionais por atenção prejudicada"],
        )

    if re.search(r"alerg|rash|coceira|urticária|urticaria|mancha", t):
        return base(
            "Reação alérgica leve (urticária/rinite) — provável",
            "leve",
            "Reações alérgicas a bordo são geralmente leves (dieta reidratada, látex de equipamentos, cosméticos). Sem sinais sistêmicos relatados, conduta é sintomática com vigilância.",
            [
                {"name": "Urticária de contato/alimentar", "likelihood": 60, "why": "Lesões cutâneas em padrão após refeição/uso de material"},
                {"name": "Rinite alérgica", "likelihood": 28, "why": "Poeira de módulo + ar ressecado"},
                {"name": "Irritação por CO2 elevado (não alérgica)", "likelihood": 12, "why": "CO2 da cabine pode simular rinite"},
            ],
            [
                {"item": "Loratadina 10 mg", "dose": "1 comprimido", "frequency": "1×/dia", "duration": "5 dias", "instructions": "Pela manhã; não excede 10 mg/dia"},
                {"item": "Remover o agente suspeito", "dose": "—", "frequency": "imediato", "duration": "enquanto persistir", "instructions": "Dieta de exclusão do item suspeito; trocar material de contato"},
            ],
            ["1. Fotografar a lesão e anexar ao prontuário do B.I.P", "2. Monitorar expansão da lesão 2×/dia", "3. Anti-histamínico conforme receita", "4. Se edema de lábios/língua, rouquidão ou falta de ar → EMERGÊNCIA (dexametasona + MCC)"],
            "Lesões 2×/dia; saturação e respiração na pior hora do dia",
            "onboard",
            ["Edema de face/língua/glote", "Dispneia ou sibilância", "Anafilaxia prévia descrita", "Lesão crescendo apesar de loratadina"],
        )

    if re.search(r"corte|ferida|machuc|queimadura|bater|contus", t):
        return base(
            "Ferimento de partes moles / contusão",
            "leve",
            "Ferimentos superficiais são comuns em atividades de manutenção. Sem menção a sangramento incontrolável ou fratura, conduta é curativo padrão + profilaxia antitetânica em dia (mantida pela missão).",
            [
                {"name": "Laceração/contusão superficial", "likelihood": 70, "why": "Mecanismo descrito típico de manutenção de equipamento"},
                {"name": "Hematoma", "likelihood": 20, "why": "Edema/dor localizada sem solução de continuidade"},
                {"name": "Corpo estranho retido", "likelihood": 10, "why": "Relatar se sensação de 'ciscar' persiste após limpeza"},
            ],
            [
                {"item": "Curativo + antisséptico", "dose": "—", "frequency": "2×/dia", "duration": "3–5 dias", "instructions": "Lavar com SF 0,9%, secar, cola/curativo estéril; trocar curativo 12/12h"},
                {"item": "Ibuprofeno 400 mg", "dose": "1 comprimido", "frequency": "a cada 8 h", "duration": "2 dias", "instructions": "Se dor > 4/10"},
                {"item": "Gelo (pack frio)", "dose": "15 min", "frequency": "4×/dia", "duration": "48h", "instructions": "Contusões e edema"},
            ],
            ["1. Limpar com SF 0,9% + antisséptico", "2. Foto para registro de bordo (anexar ao diagnóstico)", "3. Verificar sangramento ativo, função distal, sensibilidade", "4. Sinais de infecção em 48h (calor, rubor, pus, febre) → telemedicina", "5. Se exposição a material perfurocortante: protocolo de profilaxia + MCC"],
            "Bordos da ferida a cada 24h; temperatura e dor diárias",
            "onboard",
            ["Sangramento que não cede com compressão 10 min", "Déficit sensitivo/motor distal", "Febre + sinais de celulite", "Exposição a material perfurocortante"],
        )

    if re.search(r"barriga|abdomin|estômago|estomago|diarre|constipa|intest", t):
        return base(
            "Gastroenterite leve / dispepsia de missão",
            "leve",
            "Sintomas digestivos em bordo: dieta diferente, baixa fibra, estresse e alterações na absorção. Sem sinais de alarme descritos. Conduta sintomática + reposição hídrica.",
            [
                {"name": "Dispepsia/refluxo", "likelihood": 42, "why": "Supressão ácida típica por decúbito e dieta de bordo"},
                {"name": "Gastroenterite viral leve", "likelihood": 33, "why": "Sintomas agudos autolimitados descritos"},
                {"name": "Constipação", "likelihood": 25, "why": "Baixa fibra + hidratação insuficiente + imobilidade relativa"},
            ],
            [
                {"item": "Loperamida 2 mg", "dose": "1 cápsula", "frequency": "até 4×/dia", "duration": "2 dias", "instructions": "Apenas se diarreia; suspender se febre/sangue"},
                {"item": "Omeprazol 20 mg", "dose": "1 cápsula", "frequency": "jejum", "duration": "5 dias", "instructions": "Se azia/refluxo predominar"},
                {"item": "SRO (soro oral)", "dose": "—", "frequency": "após cada evacuação", "duration": "até melhora", "instructions": "Reposição de eletrólitos"},
            ],
            ["1. Dieta branda fracionada (6 refeições/dia)", "2. Evitar cafeína, gordura e laticínios por 48h", "3. Fibras + 2,5 L água se constipação", "4. Se diarreia com febre > 38 °C, sangue ou > 6 evacuações/dia → telemedicina MCC (15:10)"],
            "Peso 2×/dia; turgor cutâneo e diurese; registro de evacuações",
            "onboard",
            ["Sangue nas fezes", "Dor abdominal intensa localizada + descompressão dolorosa", "Vômitos incoercíveis", "Sinais de desidratação grave (diurese mínima, taquicardia)"],
        )

    # Padrão genérico — quadro vago
    return base(
        "Quadro inespecífico — avaliação sindrômica necessária",
        "moderado",
        "Não há um padrão sindrômico claro no relato, e a conduta off-Terra exige cautela por padrão. Vamos estruturar a investigação: medidas de suporte agora + telemedicina com o MCC para refinar o diagnóstico com seus dados.",
        [
            {"name": "Fadiga/estresse operacional", "likelihood": 40, "why": "Queixa vaga em contexto de alta carga e sono irregular"},
            {"name": "Deficiência/subclínico nutricional", "likelihood": 25, "why": "Dieta de bordo exige suplementação; ferritina no limite"},
            {"name": "Sobrecarga fisiológica da microgravidade", "likelihood": 35, "why": "Alterações cardiovasculares/ósseas/fluídas típicas"},
        ],
        [
            {"item": "Repouso relativo + higiene do sono", "dose": "—", "frequency": "7 dias", "duration": "1 semana", "instructions": "Repriorizar tarefas; adiar o que não for crítico"},
            {"item": "Hidratação 2,5 L/dia", "dose": "—", "frequency": "regra contínua", "duration": "contínuo", "instructions": "Meta de bordo"},
        ],
        ["1. Telemedicina com MCC na próxima janela (15:10) para discussão do caso", "2. Check completo de sinais 2×/dia por 7 dias", "3. Revisar exames recentes com o médico de voo", "4. Retornar ao Diagnóstico se novos sintomas surgirem"],
        "Sinais vitais 2×/dia; peso e humor diários por 7 dias",
        "telemedicine",
        ["Qualquer sintoma de alarme (red flags) → avaliação imediata"],
    )


def _offline_chat_reply(message: str, context: dict[str, Any] | None = None) -> str:
    t = (message or "").lower()
    if _red_flags_present(t):
        return "Para tudo. 🚨 Isso é uma EMERGÊNCIA off-Terra: deite-se, chame o MCC AGORA pelo link de emergência e não espere. Eu fico aqui contigo — e abra o Diagnóstico para o dossiê completo enquanto o MCC responde."
    if re.search(r"rotina|pendên|hoje", t):
        p = (context or {}).get("pending_tasks", None)
        if p == 0:
            return "Nenhuma pendência agora — você está voando certinho! Constância é o combustível da missão. ✅"
        if isinstance(p, int) and p > 0:
            return f"Você tem {p} {'pendência' if p == 1 else 'pendências'} em aberto agora. Bora resolver uma na aba Rotinas — eu comemoro com você. 🚀"
        return "Na aba Rotinas te mostro o dia inteiro: manhã, tarde e noite. Vai marcando conforme faz, que eu vou montando seu streak. 📋"
    if re.search(r"água|hidrat", t):
        return "Gostei da pergunta! Meta de bordo: 2,5 L de água por dia. Seu check da manhã de hidratação está registrado — bora bater a meta da tarde? 💧"
    if re.search(r"sono|dormir|insôn", t):
        return "Sono é sagrado numa missão. Tenta a respiração 4-7-8 antes de deitar e corta a cafeína às 14h. Se a insônia insistir por 3 noites, marcamos com o MCC e avaliamos melatonina 3 mg. Combinado?"
    if re.search(r"dor|náusea|febre|enjo|tont|mal", t):
        return "Isso merece uma análise de verdade — abre o Diagnóstico ali na dock que eu monto o dossiê completo (vitais, exames e conversa) e te devolvo o que pode ser + o que fazer. Estou contigo! 🩺"
    if re.search(r"exerc|treino|ared", t):
        return "Não pula o ARED! 35 min hoje mantém seus ossos e coração em dia. Pós-esforço, 500 mL de isotônico. Bora?"
    return "Entendi. Tô aqui pra qualquer coisa — rotina, vitais, sono ou só desabafar. E se for coisa de saúde, o Diagnóstico faz a análise completa pra você. Como posso ajudar agora?"


# ---------------- Gemini API ----------------

def _gemini_url() -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _call_gemini(prompt_text: str, image_data_url: str | None = None, system: str = "") -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    parts: list[dict[str, Any]] = [{"text": (system + "\n\n" if system else "") + prompt_text}]
    if image_data_url:
        m = re.match(r"data:(image/[a-zA-Z+.-]+);base64,(.+)", image_data_url)
        if m:
            parts.append({"inline_data": {"mime_type": m.group(1), "data": m.group(2)}})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.4, "response_mime_type": "application/json"},
    }
    try:
        r = httpx.post(_gemini_url() + f"?key={key}", json=body, timeout=45)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _stock_summary() -> str:
    from app.data import MISSION_STOCK
    lines = []
    for item in MISSION_STOCK:
        qty = "" if item["qty"] is None else f" (estoque: {item['qty']})"
        lines.append(f"- {item['name']}{qty} — {item['for']}")
    return "\n".join(lines)


def diagnose(text: str, context: dict[str, Any], image_data_url: str | None = None) -> dict[str, Any]:
    stock = _stock_summary()
    ctx_lines = [f"- {k}: {v}" for k, v in (context or {}).items()]
    prompt = (
        f"RELATO DO TRIPULANTE:\n{text}\n\nCONTEXTO DA PESSOA (use tudo):\n" + "\n".join(ctx_lines)
        + ("\n\nA PESSOA ANEXOU UMA IMAGEM (ferida, exantema ou exame caseiro). Analise a imagem junto com o relato." if image_data_url else "")
    )
    raw = _call_gemini(prompt, image_data_url, system=DIAGNOSIS_SYSTEM.format(stock=stock))
    parsed = _extract_json(raw) if raw else None
    if parsed and "severity" in parsed:
        return parsed
    return _rule_based_diagnosis(text, context or {}, stock)


def chat_reply(message: str, history: list[dict[str, str]] | None = None, context: dict[str, Any] | None = None) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        ctx = ""
        if context:
            ctx = "Contexto atual: " + "; ".join(f"{k}: {v}" for k, v in context.items()) + "\n"
        convo = ""
        for h in (history or [])[-8:]:
            role = "Tripulante" if h.get("role") == "user" else "B.I.P"
            convo += f"{role}: {h.get('text', '')}\n"
        prompt = ctx + convo + f"Tripulante: {message}\nB.I.P:"
        raw = _call_gemini(prompt, system=CHAT_SYSTEM)
        if raw:
            raw = raw.strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, str):
                    return parsed
                if isinstance(parsed, dict):
                    return str(parsed.get("reply") or parsed.get("text") or next(iter(parsed.values())))
            except Exception:
                return raw
    return _offline_chat_reply(message, context)
