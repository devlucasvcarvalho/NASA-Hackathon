"""Cliente de IA do B.I.P: Google Gemini com fallback local consistente.

Sem GEMINI_API_KEY o app continua funcionando: um motor offline baseado em
regras curadas (estoque de bordo + triagem) garante respostas coerentes no demo,
PT/EN/ES. Com a chave, o Gemini recebe o mesmo prompt + contexto
(vitais, exames, rotina) e devolve o mesmo schema JSON — também no idioma escolhido.
"""

import json
import os
import re
from typing import Any

import httpx

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

LANG_NAMES = {"pt": "português (Brasil)", "en": "English", "es": "español"}
LANGS = ("pt", "en", "es")


def _norm(lang: str | None) -> str:
    code = (lang or "").lower().split("-")[0]
    return code if code in LANGS else "pt"


DIAGNOSIS_SYSTEM = """Você é o B.I.P Physician, médico de bordo de uma missão espacial interplanetária (Base Ares). A pessoa atendida está FORA da Terra: NÃO é possível ir ao pronto-socorro nem "procurar um médico". Todos os quadros devem ser resolvidos a bordo, com telemedicina do Mission Control (MCC) quando necessário, ou com ABORTO DA MISSÃO e retorno à Terra nos casos graves.

Postura: calma, direta, técnica e acolhedora. Trate a pessoa pelo nome do contexto. Nunca use alarmismo vazio; mas em risco de vida, seja inequívoco: comunicar MCC AGORA, abortar missão / preparar retorno à Terra.

IDIOMA DA RESPOSTA: {lang_name}. Escreva TUDO em {lang_name}.

Recursos disponíveis a bordo (inventário real da missão):
{stock}

Além disso: concentrador e cilindros de O2, DEA, kit de sutura/curativos, soro 0,9% IV, repouso em módulo de descanso, dieta Aurora-7, exercício resistido ARED, telemedicina com MCC (janela diária 15:10–15:45).

Considere SEMPRE todo o contexto fornecido (sinais vitais, exames recentes, rotina/sono, humor, conversas com o copiloto). Fatores psicológicos (PHQ-2 elevado, cortisol alto, sono ruim) devem aparecer explicitamente quando relevantes.

Classifique a gravidade:
- "leve" / "mild" / "leve": conduta 100% a bordo.
- "moderado" / "moderate" / "moderado": conduta a bordo + monitoramento estruturado e/ou telemedicina com MCC.
- "grave" / "severe" / "grave": comunicar MCC imediatamente, estabilizar e ABORTAR A MISSÃO / preparar retorno à Terra.

Responda APENAS um JSON válido (sem markdown, sem crases), com EXATAMENTE esta estrutura (valores de gravidade e triagem EM INGLÊS: "mild" | "moderate" | "severe"; triage_action: "onboard" | "telemedicine" | "abort"):
{{
  "title": "Nome provável do quadro (termo técnico em inglês entre parênteses quando útil)",
  "severity": "mild" | "moderate" | "severe",
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
- Para gravidade moderada, inclua explicitamente "Telemedicina com MCC na janela das 15:10" / "MCC telemedicine at 15:10" / "Telemedicina con MCC a las 15:10" em procedures.
- Para gravidade grave, prescription deve conter apenas estabilização imediata; triage_action = "abort"; instructions de contato MCC imediato.
- NUNCA escreva "procure um médico", "vá ao hospital" ou similar — em nenhum idioma.
- Seja consistente: mesmas doses, mesmas recomendações, mesmas ressalvas, independente do idioma escolhido.
"""

CHAT_SYSTEM = """Você é o B.I.P, o copiloto de saúde da missão espacial Aurora-7. Personalidade: tranquila, gentil e brincalhona, como um amigo em quem se confia de olhos fechados — mas nunca banaliza saúde. Você chama a pessoa pelo nome do contexto. Fala de forma natural, em {lang_name}. Respostas curtas (2 a 4 frases, pode usar 1 emoji no máximo).

Você pode ajudar com: rotina da missão, sinais vitais, hidratação, sono, exercício, humor/ansiedade, alimentação, medicamentos de bordo (consulte o inventário somente quando perguntado, sem citar doses), e sintomas — nesse último caso sugira o app Diagnóstico para uma análise completa (ex.: "isso merece uma análise completa — abre o Diagnóstico ali na dock que eu monto o dossiê inteiro para você").

Você NÃO é substituto do MCC: em situações graves, diga para acionar o MCC imediatamente. Nunca diga "vá ao hospital" nem "procure um médico" em nenhum idioma. Se a pessoa relatar pensamentos de autolesão, trate com seriedade, valide o sentimento e oriente contato com o MCC/psicólogo de voo na próxima janela + telemedicina imediata.
"""


# ---------------- Fatores do contexto (rótulos por idioma) ----------------
_FACTOR_LABELS = {
    "pt": {"sleep": "Sono", "rad": "Radiação", "routine": "Rotina de hoje", "chats": "Conversas recentes com o B.I.P", "exam": "Exame", "vitals_none": []},
    "en": {"sleep": "Sleep", "rad": "Radiation", "routine": "Today's routine", "chats": "Recent chats with B.I.P", "exam": "Exam"},
    "es": {"sleep": "Sueño", "rad": "Radiación", "routine": "Rutina de hoy", "chats": "Conversaciones recientes con B.I.P", "exam": "Examen"},
}


def _context_factors(context: dict[str, Any], lang: str) -> list[str]:
    L = _FACTOR_LABELS.get(lang, _FACTOR_LABELS["pt"])
    factors = []
    vitals = (context or {}).get("vitals") or {}
    if vitals:
        factors = [
            f"HR {vitals.get('heart_rate', '—')} bpm",
            f"SpO2 {vitals.get('spo2', '—')}%",
            f"BP {vitals.get('bp_sys', '—')}/{vitals.get('bp_dia', '—')}",
            f"{L['rad']}: {vitals.get('radiation_cumulative', '—')} mSv",
        ]
    else:
        if context.get("heart_rate"): factors.append(f"HR: {context['heart_rate']}")
        if context.get("spo2"): factors.append(f"SpO2: {context['spo2']}")
        if context.get("bp"): factors.append(f"BP/PA: {context['bp']}")
        if context.get("temperature"): factors.append(f"Temp: {context['temperature']}")
        if context.get("radiation_cumulative"): factors.append(f"{L['rad']}: {context['radiation_cumulative']}")
        if context.get("sleep_hours"): factors.append(f"{L['sleep']}: {context['sleep_hours']}")
    exams = (context or {}).get("exams")
    if isinstance(exams, str):
        items = [e.strip() for e in re.split(r"[·|]", exams) if e.strip()]
    elif isinstance(exams, list):
        items = [str(e) for e in exams]
    else:
        items = []
    factors += [f"{L['exam']}: {e}" for e in items[:3]]
    if context.get("routine_score") is not None:
        factors.append(f"{L['routine']} — {context['routine_score']}%")
    if context.get("chat_summary"):
        factors.append(L["chats"])
    return factors


def _red_flags_present(text: str) -> bool:
    t = text.lower()
    patterns = [
        r"dor (no|forte no) peito", r"aperto no peito", r"chest pain", r"chest pressure", r"dolor (en el|opresivo en el) pecho", r"opresión en el pecho",
        r"falta de ar (grave|intensa|súbita)", r"severe (shortness of breath|difficulty breathing)", r"no consigo respirar", r"can't breathe", r"dificultad para respirar",
        r"desmai", r"faint|syncope", r"desmay", r"convuls", r"seizure",
        r"sangramento (intenso|forte)", r"heavy bleeding", r"sangrado (intenso|abundante)", r"vomitando sangue", r"vomiting blood", r"vómitos con sangre",
        r"confus", r"confusion", r"confusión", r"paralis", r"paralys", r"parális",
        r"fala arrastada", r"slurred speech", r"habla arrastrada", r"rosto (torto|caído)", r"face droop", r"cara (torcida|caída)",
        r"cegueira (súbita|subit)", r"sudden (blindness|vision loss)", r"ceguera súbita",
        r"pior dor da vida", r"worst (pain|headache) (of|in) my life", r"peor dolor de mi vida",
        r"estou morrendo", r"i('m| am) dying", r"me estoy muriendo", r"autoles", r"self-harm", r"autolesión", r"suic",
    ]
    return any(re.search(p, t) for p in patterns)


# ---------------- Conteúdo médico de bordo por idioma ----------------
# Chaves: rf (red flag), head (cefaleia), nausea, dizzy, sleep, mood, allergy, wound, gut, generic
_DISCLAMER = {
    "pt": "Apoio à decisão baseado nos dados de bordo — a palavra final é do médico de voo do MCC.",
    "en": "Decision support based on on-board data — the final word belongs to the MCC flight surgeon.",
    "es": "Apoyo a la decisión basado en los datos de a bordo — la palabra final la tiene el médico de vuelo del MCC.",
}

_TOPIC_CONTENT: dict[str, dict[str, Any]] = {
    "pt": {
        "rf": {"t": "Síndrome de alerta máximo — avaliação imediata (emergency)", "s": "grave",
               "sum": "Os sintomas relatados configuram red flag para evento cardiopulmonar/neurológico ou risco de autolesão. Off-Terra, a conduta é: estabilizar AGORA e comunicar o MCC para decisão de retorno à Terra.",
               "c": [("Evento cardiopulmonar agudo / ACS", 45, "Dor/aperto torácico ou dispneia súbita relatada"),
                     ("Evento neurológico agudo (AVC-like)", 35, "Sinais focais referidos na descrição"),
                     ("Crise psicológica com risco imediato", 20, "Termos de risco psíquico identificados")],
               "rx": [("Estabilização imediata", "—", "imediato", "agora", "Repouso absoluto, O2 4 L/min se SpO2 < 94%, elevar membros inferiores"),
                      ("Contato com MCC", "—", "contínuo", "até decisão", "Link prioritário NOW com o médico de voo. Declarar EMERGÊNCIA MÉDICA.")],
               "p": ["1. Deitar a pessoa e afrouxar vestimentas", "2. O2 4 L/min por cânula/máscara", "3. Acionar MCC IMEDIATAMENTE pelo link de emergência", "4. Preparar DEA e kit de via aérea", "5. Sinais vitais a cada 5 min", "6. Estabilização farmacológica apenas autorizada pelo MCC", "7. Aguardar decisão de abort / retorno à Terra"],
               "m": "Sinais vitais seriados a cada 5 minutos até estabilização ou decisão do MCC", "a": "abort",
               "r": ["Perda de consciência", "Arritmia / PCR → DEA imediato", "Piora respiratória progressiva"]},
        "head": {"t": "Cefaleia tensional provável (tension-type headache)", "s": "leve",
                 "sum": "Quadro típico de cefaleia tensional, amplificado por carga operacional, desidratação leve e exposição à radiação/estresse. Seus parâmetros (HR e SpO2 normais) não sugerem causa secundária grave.",
                 "c": [("Cefaleia tensional", 62, "Dor em aperto/holocraniana após esforço cognitivo e sono irregular"),
                       ("Desidratação leve", 25, "Hidratação registrada abaixo da meta nas últimas 48h"),
                       ("Cefaleia por estresse/circadiana", 13, "Cortisol matinal elevado no painel de 05/10")],
                 "rx": [("Ibuprofeno 400 mg", "1 comprimido", "a cada 8 h", "3 dias", "Após as refeições. Máx. 1200 mg/dia."),
                        ("Cafeína 100 mg", "1 comprimido", "dose única pela manhã", "1 dia", "Apenas se dor ao acordar; não usar após 14h"),
                        ("Hidratação oral", "500 mL por vez", "4×/dia", "3 dias", "Repor isotônico + água; mirar 2,5 L/dia")],
                 "p": ["1. Reduzir carga cognitiva por 24h (adiar tarefas de precisão não urgentes)", "2. Compressa morna na região suboccipital", "3. Respiração 4-7-8 por 5 min antes de dormir", "4. Se dor persistir > 72h ou mudar padrão → Telemedicina com MCC (15:10)"],
                 "m": "PA e FC de manhã e à noite por 3 dias; dor em escala 0–10 a cada dose", "a": "onboard",
                 "r": ["Cefaleia súbita 'pior da vida'", "Vômito em jato + rigidez de nuca", "Déficit neurológico focal", "Febre > 38,5 °C associada"]},
        "nausea": {"t": "Náusea de ajuste / enjoo de missão (space motion sickness residual)", "s": "leve",
                   "sum": "Náusea isolada é comum em missões longas, por alteração vestibular e refeições frias. Sem sinais de alarme; tolerável a bordo com medicação de suporte.",
                   "c": [("Disfunção vestibular residual", 48, "Adaptação vestibular de longa duração em microgravidade"),
                         ("Refluxo / digestão lenta", 30, "Dieta de bordo + posição supina para dormir"),
                         ("Intolerância alimentar específica", 22, "Apontar item do último cardápio que não caiu bem")],
                   "rx": [("Ondansetrona 4 mg", "1 comprimido", "a cada 8 h", "2 dias", "Dissolver na língua. Evitar com estômago vazio."),
                          ("Bromoprida 10 mg", "1 comprimido", "se empachamento/refluxo", "2 dias", "Aguardar 30 min entre ondas de náusea"),
                          ("Omeprazol 20 mg", "1 cápsula", "jejum, 1×/dia", "5 dias", "Proteção gástrica")],
                   "p": ["1. Pequenas porções a cada 2–3h (evitar distensão)", "2. 20–30 min antes das refeições, deitar 2h após", "3. Evitar odores fortes no módulo de alimentação", "4. Vômitos > 3×/dia ou intolerância hídrica → Telemedicina com MCC + antiemético IV"],
                   "m": "Hidratação 2 L/dia; peso e turgor cutâneo 2×/dia; registro de episódios", "a": "onboard",
                   "r": ["Vômito com sangue", "Incapacidade de reter líquidos > 12h", "Dor abdominal intensificando", "Febre associada"]},
        "dizzy": {"t": "Tontura por descondicionamento / alteração vestibular", "s": "moderado",
                  "sum": "Tontura em missão longa merece atenção: pode ser descondicionamento cardiovascular, alteração vestibular ou, com radiação acumulada, requer exclusão de causa central — por isso incluímos telemedicina.",
                  "c": [("Hipotensão ortostática / descondicionamento", 45, "Sequestro fluido cefálico + perda de condicionamento"),
                        ("Disfunção vestibular", 38, "Adaptação vestibular em microgravidade"),
                        ("Anemia leve relativa", 17, "Hemoglobina 12.1 g/dL (02/11) no limite inferior")],
                  "rx": [("Hidratação + sal oral", "500 mL + 1 g NaCl", "3×/dia", "3 dias", "Aumentar volume plasmático"),
                         ("Meias de compressão + levantar devagar", "—", "contínuo", "enquanto tontar", "10–15 s sentado antes de ficar em pé")],
                  "p": ["1. PA sentado/em pé (0/1/3 min) por 3 dias", "2. Anotar sinais neurológicos (fala, marcha, visão) no diário", "3. Telemedicina com MCC (15:10) para revisão neurológica remota", "4. Reduzir exercício intenso por 48h", "5. Tontura + desmaio ou sinais focais → EMERGÊNCIA (red flags)"],
                  "m": "PA ortostática e FC 2×/dia por 3 dias; relato de desmaios no diário", "a": "telemedicine",
                  "r": ["Desmaio (mesmo breve)", "Déficit neurológico focal", "Palpitações com dor torácica", "Tontura súbita com cefaleia máxima"]},
        "sleep": {"t": "Desajuste circadiano / insônia de missão", "s": "leve",
                  "sum": "Insônia em missão é multifatorial: ausência de ciclo dia/noite claro, excesso de telas e cortisol elevado. Seu diário mostra PHQ-2 com itens de humor elevados — o sono é o alvo primário.",
                  "c": [("Desajuste circadiano", 55, "Ciclo de 24h sem luz natural + agenda variável"),
                        ("Hipervigilância operacional / ansiedade", 30, "Cortisol AM elevado; diário com tensão"),
                        ("Higiene do sono inadequada", 15, "Relato de telas/trabalho noturno")],
                  "rx": [("Melatonina 3 mg", "1 comprimido", "30–60 min antes de deitar", "14 noites", "Apagar luzes 30 min antes; evitar se sonolência persistir"),
                         ("Cafeína — corte às 14h", "—", "regra fixa", "contínuo", "Substituir por chá de camomila à noite")],
                  "p": ["1. Janela escura total 22:00–06:30 (sleep-station + máscara)", "2. Bloqueio de telas 21:30 (blue-light off)", "3. Respiração 4-7-8 ou body-scan ao deitar", "4. Luz azul forte ao acordar (terapia 30 min)", "5. Sem melhora em 14 dias → telepsicológico com MCC"],
                  "m": "Eficiência de sono (Sleep-Smart) por 2 semanas; latência < 30 min como meta", "a": "onboard",
                  "r": ["Sonolência que prejudica tarefas de precisão", "Humor deprimido ≥ 2 semanas", "Roncos + apneia presenciada"]},
        "mood": {"t": "Reação de estresse/ajustamento ansioso (adjustment disorder)", "s": "moderado",
                 "sum": "É reação normal a um ambiente extremo — não é fraqueza. Seu cortisol elevado (05/10) e o diário sustentam o quadro. Conduta: protocolo de coesão + monitoramento + conversa com o MCC.",
                 "c": [("Transtorno de ajustamento ansioso", 55, "Sintomas ligados a estressor de missão; tensão no diário"),
                       ("Exaustão de carga operacional", 30, "Acúmulo de tarefas críticas + sono fragmentado"),
                       ("Fator fisiológico (cortisol, radiação)", 15, "Cortisol 24.6 µg/dL; eixo HPA em estudo")],
                  "rx": [("Respiração coesiva 4-7-8", "5 min", "3×/dia", "contínuo", "Antes das janelas de trabalho críticas"),
                         ("Atividade física moderada", "20–30 min", "1×/dia", "contínuo", "Melhora cortisol e qualidade do sono"),
                         ("Melatonina 3 mg (se sono afetado)", "1 comprimido", "à noite", "14 noites", "Ver rotina de sono")],
                  "p": ["1. Psicólogo de voo na próxima janela (15:10)", "2. Reduzir 1 tarefa não essencial/dia por 2 semanas", "3. Diário de humor diário (PHQ-2) — B.I.P acompanha tendência", "4. Videochamada com família a cada 2 dias", "5. Piora do humor ou pensamentos autolesivos → MCC imediato"],
                  "m": "PHQ-2 2×/semana por 4 semanas; sono e apetite diários; escalas no app", "a": "telemedicine",
                  "r": ["Pensamentos de autolesão ou de morte", "Isolamento total > 48h", "Ataques de pânico incapacitantes", "Erros operacionais por atenção prejudicada"]},
        "allergy": {"t": "Reação alérgica leve (urticária/rinite)", "s": "leve",
                    "sum": "Reações alérgicas a bordo são geralmente leves (dieta reidratada, látex, cosméticos). Sem sinais sistêmicos relatados; conduta sintomática com vigilância.",
                    "c": [("Urticária de contato/alimentar", 60, "Lesões após refeição/manuseio de material"),
                          ("Rinite alérgica", 28, "Poeira de módulo + ar ressecado"),
                          ("Irritação por CO2 (não alérgica)", 12, "CO2 da cabine pode simular rinite")],
                    "rx": [("Loratadina 10 mg", "1 comprimido", "1×/dia", "5 dias", "Pela manhã; não exceder 10 mg/dia"),
                           ("Remover o agente suspeito", "—", "imediato", "enquanto persistir", "Dieta de exclusão; trocar material de contato")],
                    "p": ["1. Fotografar a lesão e anexar ao prontuário do B.I.P", "2. Monitorar expansão da lesão 2×/dia", "3. Anti-histamínico conforme receita", "4. Edema de lábios/língua, rouquidão ou falta de ar → EMERGÊNCIA (dexametasona + MCC)"],
                    "m": "Lesões 2×/dia; saturação e respiração na pior hora do dia", "a": "onboard",
                    "r": ["Edema de face/língua/glote", "Dispneia ou sibilância", "Anafilaxia prévia descrita", "Lesão crescendo apesar de loratadina"]},
        "wound": {"t": "Ferimento de partes moles / contusão", "s": "leve",
                  "sum": "Ferimentos superficiais são comuns em atividades de manutenção. Sem menção a sangramento incontrolável ou fratura; conduta é curativo padrão.",
                  "c": [("Laceração/contusão superficial", 70, "Mecanismo típico de manutenção de equipamento"),
                        ("Hematoma", 20, "Edema/dor localizada sem solução de continuidade"),
                        ("Corpo estranho retido", 10, "Relatar se sensação de 'ciscar' persiste após limpeza")],
                  "rx": [("Curativo + antisséptico", "—", "2×/dia", "3–5 dias", "SF 0,9%, secar, cola/curativo; trocar 12/12h"),
                         ("Ibuprofeno 400 mg", "1 comprimido", "a cada 8 h", "2 dias", "Se dor > 4/10"),
                         ("Gelo (pack frio)", "15 min", "4×/dia", "48h", "Contusões e edema")],
                  "p": ["1. Limpar com SF 0,9% + antisséptico", "2. Foto para registro de bordo (anexar ao diagnóstico)", "3. Verificar sangramento, função distal e sensibilidade", "4. Sinais de infecção em 48h (calor, pus, febre) → telemedicina", "5. Perfurocortante → protocolo de profilaxia + MCC"],
                  "m": "Bordos da ferida a cada 24h; temperatura e dor diárias", "a": "onboard",
                  "r": ["Sangramento que não cede com compressão de 10 min", "Déficit sensitivo/motor distal", "Febre + sinais de celulite", "Exposição a perfurocortante"]},
        "gut": {"t": "Gastroenterite leve / dispepsia de missão", "s": "leve",
                "sum": "Sintomas digestivos em bordo: dieta diferente, baixa fibra, estresse. Sem sinais de alarme descritos. Conduta sintomática + reposição hídrica.",
                "c": [("Dispepsia/refluxo", 42, "Decúbito + dieta de bordo"),
                      ("Gastroenterite viral leve", 33, "Sintomas agudos autolimitados descritos"),
                      ("Constipação", 25, "Baixa fibra + hidratação insuficiente")],
                "rx": [("Loperamida 2 mg", "1 cápsula", "até 4×/dia", "2 dias", "Só se diarreia; suspender se febre/sangue"),
                       ("Omeprazol 20 mg", "1 cápsula", "jejum", "5 dias", "Se azia/refluxo predominar"),
                       ("SRO (soro oral)", "—", "após cada evacuação", "até melhora", "Reposição de eletrólitos")],
                "p": ["1. Dieta branda fracionada (6 refeições/dia)", "2. Evitar cafeína, gordura e laticínios por 48h", "3. Fibras + 2,5 L água se constipação", "4. Febre > 38 °C, sangue ou > 6 evacuações/dia → telemedicina MCC (15:10)"],
                "m": "Peso 2×/dia; turgor cutâneo e diurese; registro de evacuações", "a": "onboard",
                "r": ["Sangue nas fezes", "Dor abdominal intensa + descompressão dolorosa", "Vômitos incoercíveis", "Sinais de desidratação grave"]},
        "generic": {"t": "Quadro inespecífico — avaliação sindrômica necessária", "s": "moderado",
                    "sum": "Não há um padrão sindrômico claro no relato, e a conduta off-Terra exige cautela por padrão. Vamos estruturar: suporte agora + telemedicina com o MCC.",
                    "c": [("Fadiga/estresse operacional", 40, "Queixa vaga em contexto de alta carga e sono irregular"),
                          ("Deficiência/subclínico nutricional", 25, "Dieta de bordo exige suplementação; ferritina no limite"),
                          ("Sobrecarga fisiológica da microgravidade", 35, "Alterações cardiovasculares/ósseas/fluidas típicas")],
                    "rx": [("Repouso relativo + higiene do sono", "—", "7 dias", "1 semana", "Repriorizar tarefas; adiar o que não for crítico"),
                           ("Hidratação 2,5 L/dia", "—", "regra contínua", "contínuo", "Meta de bordo")],
                    "p": ["1. Telemedicina com MCC (15:10) para discussão do caso", "2. Check completo de sinais 2×/dia por 7 dias", "3. Revisar exames recentes com o médico de voo", "4. Retornar ao Diagnóstico se novos sintomas surgirem"],
                    "m": "Sinais vitais 2×/dia; peso e humor diários por 7 dias", "a": "telemedicine",
                    "r": ["Qualquer sintoma de alarme (red flags) → avaliação imediata"]},
    },
    "en": {
        "rf": {"t": "Maximum-alert syndrome — immediate evaluation (emergency)", "s": "severe",
               "sum": "The reported symptoms are red flags for a cardiopulmonary/neurologic event or risk of self-harm. Off-Earth, the conduct is: stabilize NOW and contact MCC to decide on return to Earth.",
               "c": [("Acute cardiopulmonary event / ACS", 45, "Reported chest pain/tightness or sudden dyspnea"),
                     ("Acute neurologic event (stroke-like)", 35, "Focal signs referred in the description"),
                     ("Psychological crisis with immediate risk", 20, "Mental-health risk terms identified")],
               "rx": [("Immediate stabilization", "—", "immediately", "now", "Absolute rest, O2 4 L/min if SpO2 < 94%, elevate legs"),
                      ("Contact MCC", "—", "continuous", "until decision", "Priority NOW link with the flight surgeon. Declare MEDICAL EMERGENCY.")],
               "p": ["1. Lay the person down and loosen clothing", "2. O2 4 L/min via cannula/mask", "3. Contact MCC IMMEDIATELY via emergency link", "4. Prepare AED and airway kit", "5. Vital signs every 5 min", "6. Pharmacologic stabilization only with MCC authorization", "7. Await abort / return-to-Earth decision"],
               "m": "Serial vital signs every 5 minutes until stabilization or MCC decision", "a": "abort",
               "r": ["Loss of consciousness", "Arrhythmia / cardiac arrest → AED immediately", "Progressive respiratory deterioration"]},
        "head": {"t": "Probable tension-type headache", "s": "mild",
                 "sum": "Classic tension-type headache, amplified by operational workload, mild dehydration and radiation/stress exposure. Your parameters (normal HR and SpO2) do not suggest a serious secondary cause.",
                 "c": [("Tension-type headache", 62, "Squeezing/holocranial pain after cognitive effort and irregular sleep"),
                       ("Mild dehydration", 25, "Hydration logged below target over the last 48h"),
                       ("Stress/circadian headache", 13, "Morning cortisol elevated in the Oct 5th panel")],
                 "rx": [("Ibuprofen 400 mg", "1 tablet", "every 8 h", "3 days", "After meals. Max 1200 mg/day."),
                        ("Caffeine 100 mg", "1 tablet", "single morning dose", "1 day", "Only if waking with pain; none after 2 PM"),
                        ("Oral hydration", "500 mL at a time", "4×/day", "3 days", "Replenish isotonic + water; target 2.5 L/day")],
                 "p": ["1. Reduce cognitive load for 24h (postpone non-urgent precision tasks)", "2. Warm compress on the suboccipital region", "3. 4-7-8 breathing for 5 min before sleep", "4. Pain persisting > 72h or pattern change → MCC telemedicine (15:10)"],
                 "m": "BP and HR morning and night for 3 days; 0–10 pain score each dose", "a": "onboard",
                 "r": ["Sudden 'worst of my life' headache", "Projectile vomiting + neck stiffness", "Focal neurologic deficit", "Associated fever > 38.5 °C"]},
        "nausea": {"t": "Adjustment nausea / space motion sickness residual", "s": "mild",
                   "sum": "Isolated nausea is common on long missions, from vestibular change and cold meals. No alarm signs; manageable onboard with supportive medication.",
                   "c": [("Residual vestibular dysfunction", 48, "Long-duration vestibular adaptation in microgravity"),
                         ("Reflux / slow digestion", 30, "Onboard diet + supine sleep position"),
                         ("Specific food intolerance", 22, "Note which item from the last menu did not sit well")],
                   "rx": [("Ondansetron 4 mg", "1 tablet", "every 8 h", "2 days", "Dissolve on tongue. Avoid on empty stomach."),
                          ("Bromopride 10 mg", "1 tablet", "if fullness/reflux", "2 days", "Wait 30 min between waves of nausea"),
                          ("Omeprazole 20 mg", "1 capsule", "fasting, 1×/day", "5 days", "Gastric protection")],
                   "p": ["1. Small portions every 2–3h (avoid distension)", "2. Eat 20–30 min before meals, lie down 2h after", "3. Avoid strong odors in the galley module", "4. Vomiting > 3×/day or fluid intolerance → MCC telemedicine + IV antiemetic"],
                   "m": "Hydration 2 L/day; weight and skin turgor 2×/day; episode log", "a": "onboard",
                   "r": ["Vomiting blood", "Inability to keep fluids > 12h", "Intensifying abdominal pain", "Associated fever"]},
        "dizzy": {"t": "Deconditioning / vestibular dizziness", "s": "moderate",
                  "sum": "Dizziness on a long mission deserves attention: could be cardiovascular deconditioning, vestibular change, or — with cumulative radiation — central causes must be excluded, which is why telemedicine is included.",
                  "c": [("Orthostatic hypotension / deconditioning", 45, "Cephalic fluid shift + loss of conditioning"),
                        ("Vestibular dysfunction", 38, "Vestibular adaptation in microgravity"),
                        ("Relative mild anemia", 17, "Hemoglobin 12.1 g/dL (Nov 2) at lower limit")],
                  "rx": [("Hydration + oral salt", "500 mL + 1 g NaCl", "3×/day", "3 days", "Increase plasma volume"),
                         ("Compression stockings + rise slowly", "—", "continuous", "while dizzy", "Sit 10–15 s before standing")],
                  "p": ["1. BP sitting/standing (0/1/3 min) for 3 days", "2. Log neuro signs (speech, gait, vision) in diary", "3. MCC telemedicine (15:10) for remote neuro review", "4. Reduce intense exercise for 48h", "5. Dizziness + faint or focal signs → EMERGENCY (red flags)"],
                  "m": "Orthostatic BP and HR 2×/day for 3 days; fainting noted in diary", "a": "telemedicine",
                  "r": ["Fainting (even brief)", "Focal neurologic deficit", "Palpitations with chest pain", "Sudden dizziness with maximal headache"]},
        "sleep": {"t": "Circadian misalignment / mission insomnia", "s": "mild",
                  "sum": "Insomnia on mission is multifactorial: no clear day/night cycle, screen excess and elevated cortisol. Your diary shows PHQ-2 with elevated mood items — sleep is the primary target.",
                  "c": [("Circadian misalignment", 55, "24h cycle without natural light + variable schedule"),
                        ("Operational hypervigilance / anxiety", 30, "Morning cortisol elevated; tense diary"),
                        ("Poor sleep hygiene", 15, "Report of screens/night work")],
                  "rx": [("Melatonin 3 mg", "1 tablet", "30–60 min before bed", "14 nights", "Lights out 30 min prior; skip if morning sleepiness persists"),
                         ("Caffeine — 2 PM cutoff", "—", "fixed rule", "continuous", "Swap for chamomile tea at night")],
                  "p": ["1. Full dark window 22:00–06:30 (sleep-station + mask)", "2. Screen block at 21:30 (blue-light off)", "3. 4-7-8 breathing or body scan at bedtime", "4. Bright blue light on waking (therapy 30 min)", "5. No improvement in 14 days → MCC telemental health"],
                  "m": "Sleep efficiency (Sleep-Smart) for 2 weeks; latency < 30 min as target", "a": "onboard",
                  "r": ["Sleepiness impairing precision tasks", "Depressed mood ≥ 2 weeks", "Snoring + witnessed apnea"]},
        "mood": {"t": "Stress/adjustment reaction with anxious component", "s": "moderate",
                 "sum": "This is a normal reaction to an extreme environment — not weakness. Your elevated cortisol (Oct 5) and diary support the picture. Conduct: cohesion protocol + monitoring + MCC conversation.",
                 "c": [("Adjustment disorder, anxious", 55, "Symptoms tied to mission stressor; tension in diary"),
                       ("Operational workload exhaustion", 30, "Critical task buildup + fragmented sleep"),
                       ("Physiological factor (cortisol, radiation)", 15, "Cortisol 24.6 µg/dL; HPA axis under study")],
                  "rx": [("Coherent breathing 4-7-8", "5 min", "3×/day", "continuous", "Before critical work windows"),
                         ("Moderate physical activity", "20–30 min", "1×/day", "continuous", "Improves cortisol and sleep quality"),
                         ("Melatonin 3 mg (if sleep affected)", "1 tablet", "at night", "14 nights", "See sleep routine")],
                  "p": ["1. Flight psychologist at next window (15:10)", "2. Drop 1 non-essential task/day for 2 weeks", "3. Daily mood diary (PHQ-2) — B.I.P tracks trend", "4. Family video call every 2 days", "5. Worsening mood or self-harm thoughts → MCC immediately"],
                  "m": "PHQ-2 twice weekly for 4 weeks; daily sleep and appetite; app scales", "a": "telemedicine",
                  "r": ["Self-harm or suicidal thoughts", "Total isolation > 48h", "Incapacitating panic attacks", "Operational errors from impaired attention"]},
        "allergy": {"t": "Mild allergic reaction (urticaria/rhinitis)", "s": "mild",
                    "sum": "Allergic reactions onboard are usually mild (rehydrated diet, latex, cosmetics). No systemic signs reported; symptomatic care with vigilance.",
                    "c": [("Contact/food urticaria", 60, "Lesions after meals/material handling"),
                          ("Allergic rhinitis", 28, "Module dust + dry air"),
                          ("CO2 irritation (non-allergic)", 12, "Cabin CO2 can mimic rhinitis")],
                    "rx": [("Loratadine 10 mg", "1 tablet", "1×/day", "5 days", "In the morning; do not exceed 10 mg/day"),
                           ("Remove the suspected agent", "—", "immediately", "while persists", "Elimination diet; swap contact material")],
                    "p": ["1. Photograph the lesion and attach to B.I.P record", "2. Monitor lesion spread 2×/day", "3. Antihistamine as prescribed", "4. Lip/tongue swelling, hoarseness or dyspnea → EMERGENCY (dexamethasone + MCC)"],
                    "m": "Lesions 2×/day; saturation and breathing at worst hour", "a": "onboard",
                    "r": ["Face/tongue/laryngeal edema", "Dyspnea or wheezing", "Previous anaphylaxis described", "Lesion growing despite loratadine"]},
        "wound": {"t": "Soft-tissue injury / contusion", "s": "mild",
                  "sum": "Superficial injuries are common in maintenance work. No mention of uncontrolled bleeding or fracture; standard dressing protocol applies.",
                  "c": [("Superficial laceration/contusion", 70, "Typical mechanism of equipment maintenance"),
                        ("Hematoma", 20, "Localized edema/pain without skin break"),
                        ("Retained foreign body", 10, "Report if 'gritty' sensation persists after cleaning")],
                  "rx": [("Dressing + antiseptic", "—", "2×/day", "3–5 days", "Saline 0.9%, dry, glue/dressing; change 12/12h"),
                         ("Ibuprofen 400 mg", "1 tablet", "every 8 h", "2 days", "If pain > 4/10"),
                         ("Ice pack", "15 min", "4×/day", "48h", "Contusions and edema")],
                  "p": ["1. Clean with saline 0.9% + antiseptic", "2. Photo for onboard record (attach to diagnosis)", "3. Check bleeding, distal function and sensation", "4. Infection signs in 48h (warmth, pus, fever) → telemedicine", "5. Needle-stick exposure → prophylaxis protocol + MCC"],
                  "m": "Wound edges every 24h; temperature and pain daily", "a": "onboard",
                  "r": ["Bleeding that does not stop with 10 min compression", "Distal sensory/motor deficit", "Fever + cellulitis signs", "Needle-stick exposure"]},
        "gut": {"t": "Mild gastroenteritis / mission dyspepsia", "s": "mild",
                "sum": "Digestive symptoms onboard: different diet, low fiber, stress. No alarm signs described. Symptomatic care + fluid replacement.",
                "c": [("Dyspepsia/reflux", 42, "Supine position + onboard diet"),
                      ("Mild viral gastroenteritis", 33, "Self-limited acute symptoms described"),
                      ("Constipation", 25, "Low fiber + insufficient hydration")],
                "rx": [("Loperamide 2 mg", "1 capsule", "up to 4×/day", "2 days", "Only if diarrhea; stop if fever/blood"),
                       ("Omeprazole 20 mg", "1 capsule", "fasting", "5 days", "If heartburn/reflux predominates"),
                       ("ORS (oral rehydration salts)", "—", "after each bowel movement", "until improvement", "Electrolyte replacement")],
                "p": ["1. Small frequent meals (6 meals/day)", "2. Avoid caffeine, fat and dairy for 48h", "3. Fiber + 2.5 L water if constipated", "4. Fever > 38 °C, blood or > 6 stools/day → MCC telemedicine (15:10)"],
                "m": "Weight 2×/day; skin turgor and diuresis; bowel log", "a": "onboard",
                "r": ["Blood in stools", "Intense localized abdominal pain + rebound", "Incoercible vomiting", "Signs of severe dehydration"]},
        "generic": {"t": "Nonspecific picture — syndromic assessment required", "s": "moderate",
                    "sum": "No clear syndromic pattern in the report, and off-Earth conduct demands caution by default. We will structure: support measures now + MCC telemedicine to refine.",
                    "c": [("Fatigue/operational stress", 40, "Vague complaint in high-load, irregular-sleep context"),
                          ("Subclinical nutritional gap", 25, "Onboard diet needs supplementation; ferritin at limit"),
                          ("Microgravity physiological load", 35, "Typical cardiovascular/bone/fluid changes")],
                    "rx": [("Relative rest + sleep hygiene", "—", "7 days", "1 week", "Reprioritize tasks; postpone non-critical ones"),
                           ("Hydration 2.5 L/day", "—", "continuous rule", "continuous", "Onboard target")],
                    "p": ["1. MCC telemedicine (15:10) to discuss the case", "2. Full vitals check 2×/day for 7 days", "3. Review recent exams with the flight surgeon", "4. Return to Diagnostics if new symptoms appear"],
                    "m": "Vital signs 2×/day; weight and mood daily for 7 days", "a": "telemedicine",
                    "r": ["Any alarm symptom (red flags) → immediate evaluation"]},
    },
    "es": {
        "rf": {"t": "Síndrome de alerta máxima — evaluación inmediata (emergencia)", "s": "grave",
               "sum": "Los síntomas relatados configuran red flag para evento cardiopulmonar/neurológico o riesgo de autolesión. Fuera de la Tierra, la conducta es: estabilizar AHORA y comunicar al MCC para decidir el retorno a la Tierra.",
               "c": [("Evento cardiopulmonar agudo / ACS", 45, "Dolor/opresión torácica o disnea súbita relatada"),
                     ("Evento neurológico agudo (AVC-like)", 35, "Signos focales referidos en la descripción"),
                     ("Crisis psicológica con riesgo inmediato", 20, "Términos de riesgo psíquico identificados")],
               "rx": [("Estabilización inmediata", "—", "inmediato", "ahora", "Reposo absoluto, O2 4 L/min si SpO2 < 94%, elevar miembros inferiores"),
                      ("Contacto con MCC", "—", "continuo", "hasta decisión", "Enlace prioritario NOW con el médico de vuelo. Declarar EMERGENCIA MÉDICA.")],
               "p": ["1. Acostar a la persona y aflojar vestimenta", "2. O2 4 L/min por cánula/máscara", "3. Llamar al MCC INMEDIATAMENTE por el enlace de emergencia", "4. Preparar DEA y kit de vía aérea", "5. Signos vitales cada 5 min", "6. Estabilización farmacológica solo con autorización del MCC", "7. Esperar decisión de aborto / retorno a la Tierra"],
               "m": "Signos vitales seriados cada 5 minutos hasta estabilización o decisión del MCC", "a": "abort",
               "r": ["Pérdida de consciencia", "Arritmia / PCR → DEA inmediato", "Deterioro respiratorio progresivo"]},
        "head": {"t": "Cefalea tensional probable (tension-type headache)", "s": "leve",
                 "sum": "Cuadro típico de cefalea tensional, amplificado por carga operativa, deshidratación leve y exposición a radiación/estrés. Tus parámetros (FC y SpO2 normales) no sugieren causa secundaria grave.",
                 "c": [("Cefalea tensional", 62, "Dolor opresivo/holocranial tras esfuerzo cognitivo y sueño irregular"),
                       ("Deshidratación leve", 25, "Hidratación registrada por debajo de la meta en las últimas 48h"),
                       ("Cefalea por estrés/circadiana", 13, "Cortisol matinal elevado en el panel del 05/10")],
                 "rx": [("Ibuprofeno 400 mg", "1 comprimido", "cada 8 h", "3 días", "Después de las comidas. Máx. 1200 mg/día."),
                        ("Cafeína 100 mg", "1 comprimido", "dosis única por la mañana", "1 día", "Solo si despierta con dolor; nada después de las 14h"),
                        ("Hidratación oral", "500 mL por vez", "4×/día", "3 días", "Reponer isotónico + agua; apuntar a 2,5 L/día")],
                 "p": ["1. Reducir carga cognitiva por 24h (posponer tareas de precisión no urgentes)", "2. Compresa tibia en la región suboccipital", "3. Respiración 4-7-8 por 5 min antes de dormir", "4. Dolor persistente > 72h o cambio de patrón → Telemedicina con MCC (15:10)"],
                 "m": "PA y FC de mañana y noche por 3 días; dolor en escala 0–10 en cada dosis", "a": "onboard",
                 "r": ["Cefalea súbita 'peor de mi vida'", "Vómito en chorro + rigidez de nuca", "Déficit neurológico focal", "Fiebre > 38,5 °C asociada"]},
        "nausea": {"t": "Náuseas de ajuste / cinetosis espacial residual", "s": "leve",
                   "sum": "Las náuseas aisladas son comunes en misiones largas, por alteración vestibular y comidas frías. Sin signos de alarma; manejable a bordo con medicación de soporte.",
                   "c": [("Disfunción vestibular residual", 48, "Adaptación vestibular de larga duración en microgravedad"),
                         ("Reflujo / digestión lenta", 30, "Dieta de a bordo + posición supina para dormir"),
                         ("Intolerancia alimentaria específica", 22, "Apuntar qué ítem del último menú no cayó bien")],
                   "rx": [("Ondansetrón 4 mg", "1 comprimido", "cada 8 h", "2 días", "Disolver en la lengua. Evitar con el estómago vacío."),
                          ("Bromoprida 10 mg", "1 comprimido", "si empacho/reflujo", "2 días", "Esperar 30 min entre oleadas de náuseas"),
                          ("Omeprazol 20 mg", "1 cápsula", "ayunas, 1×/día", "5 días", "Protección gástrica")],
                   "p": ["1. Porciones pequeñas cada 2–3h (evitar distensión)", "2. 20–30 min antes de comer, acostarse 2h después", "3. Evitar olores fuertes en el módulo de alimentación", "4. Vómitos > 3×/día o intolerancia hídrica → Telemedicina con MCC + antiemético IV"],
                   "m": "Hidratación 2 L/día; peso y turgor cutáneo 2×/día; registro de episodios", "a": "onboard",
                   "r": ["Vómito con sangre", "Incapacidad de retener líquidos > 12h", "Dolor abdominal intensificándose", "Fiebre asociada"]},
        "dizzy": {"t": "Mareo por desacondicionamiento / alteración vestibular", "s": "moderado",
                  "sum": "El mareo en misión larga merece atención: puede ser desacondicionamiento cardiovascular, alteración vestibular o, con radiación acumulada, requiere excluir causa central — por eso incluimos telemedicina.",
                  "c": [("Hipotensión ortostática / desacondicionamiento", 45, "Secuestro de fluido cefálico + pérdida de condición"),
                        ("Disfunción vestibular", 38, "Adaptación vestibular en microgravedad"),
                        ("Anemia leve relativa", 17, "Hemoglobina 12.1 g/dL (02/11) en el límite inferior")],
                  "rx": [("Hidratación + sal oral", "500 mL + 1 g NaCl", "3×/día", "3 días", "Aumentar volumen plasmático"),
                         ("Medias de compresión + levantarse lento", "—", "continuo", "mientras haya mareo", "10–15 s sentado antes de ponerse de pie")],
                  "p": ["1. PA sentado/de pie (0/1/3 min) por 3 días", "2. Anotar signos neurológicos (habla, marcha, visión) en el diario", "3. Telemedicina con MCC (15:10) para revisión neurológica remota", "4. Reducir ejercicio intenso por 48h", "5. Mareo + desmayo o signos focales → EMERGENCIA (red flags)"],
                  "m": "PA ortostática y FC 2×/día por 3 días; registros de desmayos en el diario", "a": "telemedicine",
                  "r": ["Desmayo (aunque sea breve)", "Déficit neurológico focal", "Palpitaciones con dolor torácico", "Mareo súbito con cefalea máxima"]},
        "sleep": {"t": "Desajuste circadiano / insomnio de misión", "s": "leve",
                  "sum": "El insomnio en misión es multifactorial: ausencia de ciclo día/noche claro, exceso de pantallas y cortisol elevado. Tu diario muestra PHQ-2 con ítems de humor elevados — el sueño es el objetivo primario.",
                  "c": [("Desajuste circadiano", 55, "Ciclo de 24h sin luz natural + agenda variable"),
                        ("Hipervigilancia operativa / ansiedad", 30, "Cortisol AM elevado; diario con tensión"),
                        ("Higiene del sueño inadecuada", 15, "Relato de pantallas/trabajo nocturno")],
                  "rx": [("Melatonina 3 mg", "1 comprimido", "30–60 min antes de acostarse", "14 noches", "Apagar luces 30 min antes; evitar si la somnolencia persiste"),
                         ("Cafeína — corte a las 14h", "—", "regla fija", "continuo", "Sustituir por manzanilla por la noche")],
                  "p": ["1. Ventana oscura total 22:00–06:30 (sleep-station + antifaz)", "2. Bloqueo de pantallas 21:30 (blue-light off)", "3. Respiración 4-7-8 o body-scan al acostarse", "4. Luz azul fuerte al despertar (terapia 30 min)", "5. Sin mejora en 14 días → telepsicológico con MCC"],
                  "m": "Eficiencia de sueño (Sleep-Smart) por 2 semanas; latencia < 30 min como meta", "a": "onboard",
                  "r": ["Somnolencia que perjudica tareas de precisión", "Ánimo deprimido ≥ 2 semanas", "Ronquidos + apnea presenciada"]},
        "mood": {"t": "Reacción de estrés/ajuste con componente ansioso", "s": "moderado",
                 "sum": "Es una reacción normal a un ambiente extremo — no es debilidad. Tu cortisol elevado (05/10) y el diario lo sostienen. Conducta: protocolo de cohesión + monitoreo + conversación con el MCC.",
                 "c": [("Trastorno de adaptación ansioso", 55, "Síntomas ligados a estresor de misión; tensión en el diario"),
                       ("Agotamiento por carga operativa", 30, "Acumulación de tareas críticas + sueño fragmentado"),
                       ("Factor fisiológico (cortisol, radiación)", 15, "Cortisol 24.6 µg/dL; eje HPA en estudio")],
                  "rx": [("Respiración de coherencia 4-7-8", "5 min", "3×/día", "continuo", "Antes de las ventanas de trabajo críticas"),
                         ("Actividad física moderada", "20–30 min", "1×/día", "continuo", "Mejora cortisol y calidad de sueño"),
                         ("Melatonina 3 mg (si el sueño está afectado)", "1 comprimido", "por la noche", "14 noches", "Ver rutina de sueño")],
                  "p": ["1. Psicólogo de vuelo en la próxima ventana (15:10)", "2. Reducir 1 tarea no esencial/día por 2 semanas", "3. Diario de humor diario (PHQ-2) — B.I.P sigue la tendencia", "4. Videollamada con la familia cada 2 días", "5. Empeoramiento del ánimo o pensamientos de autolesión → MCC inmediato"],
                  "m": "PHQ-2 2×/semana por 4 semanas; sueño y apetito diarios; escalas en la app", "a": "telemedicine",
                  "r": ["Pensamientos de autolesión o de muerte", "Aislamiento total > 48h", "Ataques de pánico incapacitantes", "Errores operativos por atención deteriorada"]},
        "allergy": {"t": "Reacción alérgica leve (urticaria/rinitis)", "s": "leve",
                    "sum": "Las reacciones alérgicas a bordo suelen ser leves (dieta rehidratada, látex, cosméticos). Sin signos sistémicos relatados; conducta sintomática con vigilancia.",
                    "c": [("Urticaria de contacto/alimentaria", 60, "Lesiones tras comidas/manipulación de material"),
                          ("Rinitis alérgica", 28, "Polvo de módulo + aire seco"),
                          ("Irritación por CO2 (no alérgica)", 12, "El CO2 de cabina puede simular rinitis")],
                    "rx": [("Loratadina 10 mg", "1 comprimido", "1×/día", "5 días", "Por la mañana; no exceder 10 mg/día"),
                           ("Retirar el agente sospechoso", "—", "inmediato", "mientras persista", "Dieta de exclusión; cambiar material de contacto")],
                    "p": ["1. Fotografiar la lesión y adjuntarla al prontuario de B.I.P", "2. Monitorear expansión de la lesión 2×/día", "3. Antihistamínico según receta", "4. Edema de labios/lengua, ronquera o disnea → EMERGENCIA (dexametasona + MCC)"],
                    "m": "Lesiones 2×/día; saturación y respiración en la peor hora", "a": "onboard",
                    "r": ["Edema de cara/lengua/glotis", "Disnea o sibilancias", "Anafilaxia previa descrita", "Lesión que crece pese a loratadina"]},
        "wound": {"t": "Herida de partes blandas / contusión", "s": "leve",
                  "sum": "Las heridas superficiales son comunes en actividades de mantenimiento. Sin mención de sangrado incontrolable ni fractura; conducta estándar de curación.",
                  "c": [("Laceración/contusión superficial", 70, "Mecanismo típico de mantenimiento de equipos"),
                        ("Hematoma", 20, "Edema/dolor localizado sin solución de continuidad"),
                        ("Cuerpo extraño retenido", 10, "Reportar si persiste sensación de 'arenilla' tras la limpieza")],
                  "rx": [("Apósito + antiséptico", "—", "2×/día", "3–5 días", "SF 0,9%, secar, cola/apósito; cambiar 12/12h"),
                         ("Ibuprofeno 400 mg", "1 comprimido", "cada 8 h", "2 días", "Si dolor > 4/10"),
                         ("Hielo (pack frío)", "15 min", "4×/día", "48h", "Contusiones y edema")],
                  "p": ["1. Limpiar con SF 0,9% + antiséptico", "2. Foto para registro de a bordo (adjuntar al diagnóstico)", "3. Verificar sangrado, función distal y sensibilidad", "4. Signos de infección en 48h (calor, pus, fiebre) → telemedicina", "5. Pinchazo con material punzante → protocolo de profilaxis + MCC"],
                  "m": "Bordes de la herida cada 24h; temperatura y dolor diarios", "a": "onboard",
                  "r": ["Sangrado que no cede con compresión de 10 min", "Déficit sensitivo/motor distal", "Fiebre + signos de celulitis", "Exposición a material punzante"]},
        "gut": {"t": "Gastroenteritis leve / dispepsia de misión", "s": "leve",
                "sum": "Síntomas digestivos a bordo: dieta diferente, baja fibra, estrés. Sin signos de alarma descritos. Conducta sintomática + reposición hídrica.",
                "c": [("Dispepsia/reflujo", 42, "Decúbito + dieta de a bordo"),
                      ("Gastroenteritis viral leve", 33, "Síntomas agudos autolimitados descritos"),
                      ("Estreñimiento", 25, "Baja fibra + hidratación insuficiente")],
                "rx": [("Loperamida 2 mg", "1 cápsula", "hasta 4×/día", "2 días", "Solo si diarrea; suspender si fiebre/sangre"),
                       ("Omeprazol 20 mg", "1 cápsula", "ayunas", "5 días", "Si predomina acidez/reflujo"),
                       ("SRO (suero oral)", "—", "tras cada deposición", "hasta mejora", "Reposición de electrolitos")],
                "p": ["1. Dieta blanda fraccionada (6 comidas/día)", "2. Evitar cafeína, grasa y lácteos por 48h", "3. Fibra + 2,5 L agua si estreñimiento", "4. Fiebre > 38 °C, sangre o > 6 deposiciones/día → telemedicina MCC (15:10)"],
                "m": "Peso 2×/día; turgor cutáneo y diuresis; registro de deposiciones", "a": "onboard",
                "r": ["Sangre en heces", "Dolor abdominal intenso + descompresión dolorosa", "Vómitos incoercibles", "Signos de deshidratación grave"]},
        "generic": {"t": "Cuadro inespecífico — requiere valoración sindrómica", "s": "moderado",
                    "sum": "No hay un patrón sindrómico claro en el relato, y la conducta fuera de la Tierra exige cautela por defecto. Estructuramos: medidas de soporte ahora + telemedicina con el MCC.",
                    "c": [("Fatiga/estrés operativo", 40, "Queja vaga en contexto de alta carga y sueño irregular"),
                          ("Déficit/subclínico nutricional", 25, "La dieta de a bordo exige suplementación; ferritina en el límite"),
                          ("Sobrecarga fisiológica de la microgravedad", 35, "Cambios cardiovasculares/óseos/fluidos típicos")],
                    "rx": [("Reposo relativo + higiene del sueño", "—", "7 días", "1 semana", "Repriorizar tareas; posponer lo no crítico"),
                           ("Hidratación 2,5 L/día", "—", "regla continua", "continuo", "Meta de a bordo")],
                    "p": ["1. Telemedicina con MCC (15:10) para discutir el caso", "2. Chequeo completo de signos 2×/día por 7 días", "3. Revisar exámenes recientes con el médico de vuelo", "4. Volver a Diagnóstico si surgen nuevos síntomas"],
                    "m": "Signos vitales 2×/día; peso y ánimo diarios por 7 días", "a": "telemedicine",
                    "r": ["Cualquier síntoma de alarma (red flags) → evaluación inmediata"]},
    },
}

_TOPIC_PATTERNS = [
    ("rf", r"dor (no|forte no) peito|aperto no peito|chest (pain|pressure)|dolor (en el|opresivo en el) pecho|opresión en el pecho|falta de ar (grave|intensa|súbita)|severe (shortness of breath|difficulty breathing)|no consigo respirar|can't breathe|dificultad (para|de) respirar|desmai|fainting|syncope|desmay|convuls|seizure|sangramento (intenso|forte)|heavy bleeding|sangrado (intenso|abundante)|vomitando sangue|vomiting blood|vómitos? con sangre|confus|confusion|confusión|paralis|paralys|parális|fala arrastada|slurred speech|habla arrastrada|rosto (torto|caído)|face droop|cara (torcida|caída)|cegueira (súbita|subit)|sudden (blindness|vision loss)|ceguera súbita|pior dor da vida|worst (pain|headache) (of|in) my life|peor dolor de mi vida|estou morrendo|i('m| am) dying|me estoy muriendo|autoles|self-harm|autolesión|suic"),
    ("head", r"cabeça|cefale|headache|migraine|migraine headache|dolor de cabeza|cefalea|migraña"),
    ("nausea", r"náuse|enjo|vômito|vomito|nausea|vomit|feel (sick|queasy)|mareo por movimiento|vómito|antojo de vomitar|sick to (my|the) stomach"),
    ("dizzy", r"tont|vertigem|equil|dizz|vertigo|balance|marea|vértigo|equil"),
    ("sleep", r"sono|insôn|insonia|dormir|sleep|insomnia|can't sleep|sueño|no puedo dormir|no duermo"),
    ("mood", r"ansie|ansiedade|pânico|panico|humor|deprim|triste|anxi|panic|mood|depress|sad|ansiedad|ánimo|deprim|triste"),
    ("allergy", r"alerg|rash|coceira|urticár|urticaria|mancha|spots|itch|hives|allerg|erupc|roncha|sarpullido"),
    ("wound", r"corte|ferida|machuc|queimadura|bater|contus|cut|wound|burn|bruis|herida|quemadura|golpe"),
    ("gut", r"barriga|abdomin|estômago|estomago|diarre|constipa|intest|stomach|diarrhea|constip|intestin|diarrea|estreñim|vientre"),
]


def _rule_based_diagnosis(text: str, context: dict[str, Any], stock_summary: str, lang: str = "pt") -> dict[str, Any]:
    lang = _norm(lang)
    content = _TOPIC_CONTENT[lang]
    t = (text or "").lower()
    topic = "generic"
    if _red_flags_present(t):
        topic = "rf"
    else:
        for key, pattern in _TOPIC_PATTERNS:
            if re.search(pattern, t):
                topic = key
                break
    d = content[topic]
    factors = _context_factors(context, lang)
    return {
        "title": d["t"],
        # classes internas sempre em PT (front/está histórico dependem delas); o TEXTO permanece no idioma escolhido
        "severity": d["s"],
        "summary": d["sum"],
        "causes": [{"name": n, "likelihood": p, "why": w} for n, p, w in d["c"]],
        "prescription": [{"item": i, "dose": ds, "frequency": f, "duration": du, "instructions": ins} for i, ds, f, du, ins in d["rx"]],
        "procedures": d["p"],
        "monitoring": d["m"],
        "triage_action": d["a"],
        "red_flags": d["r"],
        "factors_used": factors,
        "disclaimer": _DISCLAMER[lang],
    }


def _offline_chat_reply(message: str, context: dict[str, Any] | None = None, lang: str = "pt") -> str:
    lang = _norm(lang)
    t = (message or "").lower()
    if _red_flags_present(t):
        return {
            "pt": "Para tudo. 🚨 Isso é uma EMERGÊNCIA off-Terra: deite-se, chame o MCC AGORA pelo link de emergência e não espere. Eu fico aqui contigo — e abra o Diagnóstico para o dossiê completo enquanto o MCC responde.",
            "en": "Stop everything. 🚨 This is an off-Earth EMERGENCY: lie down, call MCC NOW via the emergency link and do not wait. I'm right here with you — open Diagnosis for the full dossier while MCC responds.",
            "es": "Para todo. 🚨 Esto es una EMERGENCIA fuera de la Tierra: túmbate, llama al MCC AHORA por el enlace de emergencia y no esperes. Yo me quedo aquí contigo — abre Diagnóstico para el expediente completo mientras responde el MCC.",
        }[lang]
    if re.search(r"rotina|pendên|hoje|routine|pending|today|rutina|pendiente|hoy", t):
        p = (context or {}).get("pending_tasks", None)
        if p == 0:
            return {"pt": "Nenhuma pendência agora — você está voando certinho! Constância é o combustível da missão. ✅",
                    "en": "Nothing pending right now — you nailed it! Consistency is the fuel of the mission. ✅",
                    "es": "Nada pendiente ahora — ¡lo estás haciendo genial! La constancia es el combustible de la misión. ✅"}[lang]
        if isinstance(p, int) and p > 0:
            return {"pt": f"Você tem {p} {'pendência' if p == 1 else 'pendências'} em aberto agora. Bora resolver uma na aba Rotinas — eu comemoro com você. 🚀",
                    "en": f"You have {p} open {'task' if p == 1 else 'tasks'} right now. Let's knock one out in Routines — I'll celebrate with you. 🚀",
                    "es": f"Tienes {p} {'tarea pendiente' if p == 1 else 'tareas pendientes'} ahora. Resolvamos una en Rutinas — celebraré contigo. 🚀"}[lang]
        return {"pt": "Na aba Rotinas te mostro o dia inteiro: manhã, tarde e noite. Vai marcando conforme faz, que eu vou montando seu streak. 📋",
                "en": "Routines has your whole day: morning, afternoon, night. Check things off as you go and I'll build your streak. 📋",
                "es": "En Rutinas te muestro el día completo: mañana, tarde y noche. Ve marcando y yo monto tu racha. 📋"}[lang]
    if re.search(r"água|hidrat|water|agua", t):
        return {"pt": "Gostei da pergunta! Meta de bordo: 2,5 L de água por dia. Seu check da manhã de hidratação está registrado — bora bater a meta da tarde? 💧",
                "en": "Love that question! Onboard target: 2.5 L of water a day. Your morning hydration check is logged — let's hit the afternoon goal. 💧",
                "es": "¡Me gusta la pregunta! Meta de a bordo: 2,5 L de agua al día. Tu check matutino de hidratación está registrado — ¿vamos por el objetivo de la tarde? 💧"}[lang]
    if re.search(r"sono|dormir|insôn|sleep|insomnia|sueño|dormir", t):
        return {"pt": "Sono é sagrado numa missão. Tenta a respiração 4-7-8 antes de deitar e corta a cafeína às 14h. Se a insônia insistir por 3 noites, marcamos com o MCC e avaliamos melatonina 3 mg. Combinado?",
                "en": "Sleep is sacred on a mission. Try 4-7-8 breathing before bed and cut caffeine at 2 PM. If insomnia persists for 3 nights, we loop in MCC and consider melatonin 3 mg. Deal?",
                "es": "El sueño es sagrado en una misión. Prueba la respiración 4-7-8 antes de acostarte y corta la cafeína a las 14h. Si el insomnio persiste 3 noches, avisamos al MCC y valoramos melatonina 3 mg. ¿Trato?"}[lang]
    if re.search(r"dor|náuse|febre|enjo|tont|mal|pain|ache|headache|hurt|nause|fever|dizzy|dolor|náusea|fiebre|mareo|duele|duelen|cabeza", t):
        return {"pt": "Isso merece uma análise de verdade — abre o Diagnóstico ali na dock que eu monto o dossiê completo (vitais, exames e conversa) e te devolvo o que pode ser + o que fazer. Estou contigo! 🩺",
                "en": "This deserves a real analysis — open Diagnosis in the dock and I'll build the full dossier (vitals, exams, chat) and tell you what it might be + what to do. I've got you! 🩺",
                "es": "Esto merece un análisis de verdad — abre Diagnóstico en el dock y te monto el expediente completo (vitales, exámenes y charla) con lo que puede ser y qué hacer. ¡Aquí estoy! 🩺"}[lang]
    if re.search(r"exerc|treino|ared|exercise|workout|ejercicio|entren", t):
        return {"pt": "Não pula o ARED! 35 min hoje mantém seus ossos e coração em dia. Pós-esforço, 500 mL de isotônico. Bora?",
                "en": "Don't skip ARED! 35 min today keeps your bones and heart in shape. Post-workout, 500 mL of isotonic. Let's go?",
                "es": "¡No te saltes el ARED! 35 min hoy mantienen tus huesos y tu corazón en forma. Tras el esfuerzo, 500 mL de isotónico. ¿Vamos?"}[lang]
    return {"pt": "Entendi. Tô aqui pra qualquer coisa — rotina, vitais, sono ou só desabafar. E se for coisa de saúde, o Diagnóstico faz a análise completa pra você. Como posso ajudar agora?",
            "en": "Got it. I'm here for anything — routine, vitals, sleep, or just to vent. And if it's health, Diagnosis does the full analysis for you. How can I help right now?",
            "es": "Entendido. Estoy aquí para lo que sea — rutina, vitales, sueño o solo desahogarte. Y si es cosa de salud, Diagnóstico hace el análisis completo por ti. ¿En qué te ayudo ahora?"}[lang]


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
        data_ = r.json()
        return data_["candidates"][0]["content"]["parts"][0]["text"]
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
    for item in MISSION_STOCK["pt"]:  # nomes são universais; só os usos mudam por idioma
        qty = "" if item["qty"] is None else f" (estoque: {item['qty']})"
        lines.append(f"- {item['name']}{qty} — {item['for']}")
    return "\n".join(lines)


def diagnose(text: str, context: dict[str, Any], image_data_url: str | None = None, lang: str = "pt") -> dict[str, Any]:
    lang = _norm(lang)
    stock = _stock_summary()
    ctx_lines = [f"- {k}: {v}" for k, v in (context or {}).items()]
    prompt = (
        f"RELATO DO TRIPULANTE:\n{text}\n\nCONTEXTO DA PESSOA (use tudo):\n" + "\n".join(ctx_lines)
        + ("\n\nA PESSOA ANEXOU UMA IMAGEM (ferida, exantema ou exame caseiro). Analise a imagem junto com o relato." if image_data_url else "")
    )
    system = DIAGNOSIS_SYSTEM.format(stock=stock, lang_name=LANG_NAMES[lang])
    raw = _call_gemini(prompt, image_data_url, system=system)
    parsed = _extract_json(raw) if raw else None
    if parsed and "severity" in parsed:
        # normaliza gravidade para PT para compatibilidade com o front (que entende leves/moderados/graves por classe)
        sev = (parsed.get("severity") or "mild").lower()
        parsed["severity"] = {"mild": "leve", "moderate": "moderado", "severe": "grave", "leve": "leve", "moderado": "moderado", "grave": "grave"}.get(sev, "moderado")
        return parsed
    return _rule_based_diagnosis(text, context or {}, stock, lang)


def chat_reply(message: str, history: list[dict[str, str]] | None = None, context: dict[str, Any] | None = None, lang: str = "pt") -> str:
    lang = _norm(lang)
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
        raw = _call_gemini(prompt, system=CHAT_SYSTEM.format(lang_name=LANG_NAMES[lang]))
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
    return _offline_chat_reply(message, context, lang)
