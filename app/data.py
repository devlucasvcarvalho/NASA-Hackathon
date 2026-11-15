"""Dados estáticos da missão AURORA-7 — em PT / EN / ES."""

LANGS = ("pt", "en", "es")

LAUNCH_UTC = "2026-06-11T14:32:00Z"
MISSION_NAME = "Expedition AURORA-7"
CREW_MEMBER = {"name": "Elena Ricci", "role": "Flight Engineer · SpEx-47", "callsign": "Aurora-1"}

# Estoque médico de bordo (kit da missão) — "for" traduzido por idioma
_STOCK_PT = [
    ("Paracetamol 500 mg", "febre, dor leve a moderada", 120),
    ("Dipirona 500 mg", "febre, dor", 80),
    ("Ibuprofeno 400 mg", "dor inflamatória, cefaleia, dor muscular", 90),
    ("Omeprazol 20 mg", "refluxo, proteção gástrica", 60),
    ("Ondansetrona 4 mg", "náusea, vômito, enjoo de movimento", 40),
    ("Loperamida 2 mg", "diarreia", 30),
    ("Loratadina 10 mg", "alergia, rinite, urticária", 40),
    ("Bromoprida 10 mg", "náusea, refluxo, empachamento", 30),
    ("Melatonina 3 mg", "insônia e ajuste de ritmo circadiano", 60),
    ("Cafeína 100 mg", "fadiga aguda, alerta cognitivo", 50),
    ("Amoxicilina 500 mg", "infecção bacteriana (uso com orientação MCC)", 28),
    ("Azitromicina 500 mg", "infecção respiratória bacteriana (uso com orientação MCC)", 15),
    ("Ciprofloxacino 500 mg", "infecção urinária/gastrointestinal (uso com orientação MCC)", 14),
    ("Dexametasona 4 mg", "reação inflamatória grave, crise alérgica (emergência)", 10),
    ("Bisfosfonato (semanal)", "perda óssea em microgravidade (profilaxia)", 24),
    ("Vitamina D3 2000 UI", "saúde óssea e imune em ambiente sem UV natural", 180),
    ("Soro fisiológico 0,9% (bolsa 500 mL)", "reidratação IV, suporte de procedimento", 10),
    ("Oxigênio (concentrador + cilindros)", "hipoxemia e suporte a procedimentos", None),
    ("Desfibrilador semiautomático (DEA)", "PCR e arritmias graves", 1),
    ("Kit sutura + curativos + cola cirúrgica", "ferimentos, lacerações", None),
]
_STOCK_EN = [
    ("Paracetamol 500 mg", "fever, mild to moderate pain", 120),
    ("Dipyrone 500 mg", "fever, pain", 80),
    ("Ibuprofen 400 mg", "inflammatory pain, headache, muscle soreness", 90),
    ("Omeprazole 20 mg", "reflux, gastric protection", 60),
    ("Ondansetron 4 mg", "nausea, vomiting, motion sickness", 40),
    ("Loperamide 2 mg", "diarrhea", 30),
    ("Loratadine 10 mg", "allergy, rhinitis, hives", 40),
    ("Bromopride 10 mg", "nausea, reflux, indigestion", 30),
    ("Melatonin 3 mg", "insomnia and circadian rhythm adjustment", 60),
    ("Caffeine 100 mg", "acute fatigue, cognitive alertness", 50),
    ("Amoxicillin 500 mg", "bacterial infection (MCC guidance required)", 28),
    ("Azithromycin 500 mg", "bacterial respiratory infection (MCC guidance required)", 15),
    ("Ciprofloxacin 500 mg", "urinary/gastrointestinal infection (MCC guidance required)", 14),
    ("Dexamethasone 4 mg", "severe inflammatory reaction, allergic crisis (emergency)", 10),
    ("Bisphosphonate (weekly)", "bone loss in microgravity (prophylaxis)", 24),
    ("Vitamin D3 2000 IU", "bone and immune health in no-UV environment", 180),
    ("Saline 0.9% (500 mL bag)", "IV rehydration, procedure support", 10),
    ("Oxygen (concentrator + cylinders)", "hypoxemia and procedure support", None),
    ("Automated external defibrillator (AED)", "cardiac arrest and severe arrhythmias", 1),
    ("Suture kit + dressings + surgical glue", "wounds, lacerations", None),
]
_STOCK_ES = [
    ("Paracetamol 500 mg", "fiebre, dolor leve a moderado", 120),
    ("Dipirona 500 mg", "fiebre, dolor", 80),
    ("Ibuprofeno 400 mg", "dolor inflamatorio, cefalea, dolor muscular", 90),
    ("Omeprazol 20 mg", "reflujo, protección gástrica", 60),
    ("Ondansetrón 4 mg", "náuseas, vómito, mareo por movimiento", 40),
    ("Loperamida 2 mg", "diarrea", 30),
    ("Loratadina 10 mg", "alergia, rinitis, urticaria", 40),
    ("Bromoprida 10 mg", "náuseas, reflujo, empacho", 30),
    ("Melatonina 3 mg", "insomnio y ajuste del ritmo circadiano", 60),
    ("Cafeína 100 mg", "fatiga aguda, alerta cognitiva", 50),
    ("Amoxicilina 500 mg", "infección bacteriana (con orientación del MCC)", 28),
    ("Azitromicina 500 mg", "infección respiratoria bacteriana (con orientación del MCC)", 15),
    ("Ciprofloxacino 500 mg", "infección urinaria/gastrointestinal (con orientación del MCC)", 14),
    ("Dexametasona 4 mg", "reacción inflamatoria grave, crisis alérgica (emergencia)", 10),
    ("Bifosfonato (semanal)", "pérdida ósea en microgravedad (profilaxis)", 24),
    ("Vitamina D3 2000 UI", "salud ósea e inmune en ambiente sin UV natural", 180),
    ("Suero fisiológico 0,9% (bolsa 500 mL)", "rehidratación IV, soporte de procedimientos", 10),
    ("Oxígeno (concentrador + cilindros)", "hipoxemia y soporte de procedimientos", None),
    ("Desfibrilador semiautomático (DEA)", "parada cardiorrespiratoria y arritmias graves", 1),
    ("Kit sutura + apósitos + cola quirúrgica", "heridas, laceraciones", None),
]
MISSION_STOCK = {
    lang: [{"name": n, "for": f, "qty": q} for n, f, q in rows]
    for lang, rows in (("pt", _STOCK_PT), ("en", _STOCK_EN), ("es", _STOCK_ES))
}

_ROUTINE_PT = [
    {"period": "manha", "label": "Manhã", "icon": "sunrise", "window": "06:30 – 12:00",
     "tasks": [
         {"id": "m1", "title": "Acordar + check-in de sinais vitais", "time": "06:30", "hint": "HR, SpO2, PA e temperatura registrados pelo Smart-Tex"},
         {"id": "m2", "title": "Café da manhã reidratado", "time": "07:00", "hint": "Cardápio Aurora-7 · ~820 kcal"},
         {"id": "m3", "title": "Exercício resistido — 35 min", "time": "07:30", "hint": "ARED: 2 séries de agachamento, remada e rosca"},
         {"id": "m4", "title": "Hidratação — 500 mL", "time": "08:15", "hint": "Isotônico com eletrólitos a bordo"},
         {"id": "m5", "title": "Vitamina D3 + bisfosfonato (seg/qui)", "time": "09:00", "hint": "Saúde óssea em microgravidade"},
         {"id": "m6", "title": "Inspeção dos sistemas de suporte de vida", "time": "10:30", "hint": "O2, CO2 e pressão da cabine — log no tablet"},
     ]},
    {"period": "tarde", "label": "Tarde", "icon": "sun", "window": "12:00 – 19:00",
     "tasks": [
         {"id": "t1", "title": "Almoço", "time": "12:30", "hint": "~780 kcal · proteína 32 g"},
         {"id": "t2", "title": "Hidratação — 500 mL", "time": "14:00", "hint": "Lembrete automático do B.I.P"},
         {"id": "t3", "title": "Atividade operacional da missão", "time": "15:00", "hint": "Janela de contato com MCC: 15:10–15:45"},
         {"id": "t4", "title": "Respiração guiada — 5 min", "time": "17:30", "hint": "Protocolo de coesão: 4-7-8 · reduz cortisol"},
         {"id": "t5", "title": "Diário de humor (PHQ-2 rápido)", "time": "18:15", "hint": "2 perguntas · usado pelo B.I.P para alertas psicológicos"},
     ]},
    {"period": "noite", "label": "Noite", "icon": "moon", "window": "19:00 – 23:00",
     "tasks": [
         {"id": "n1", "title": "Jantar", "time": "19:30", "hint": "~750 kcal · evitar cafeína após as 14h"},
         {"id": "n2", "title": "Hidratação — 300 mL", "time": "20:30", "hint": "Última hidratação do dia"},
         {"id": "n3", "title": "Higiene + alongamento leve", "time": "21:15", "hint": "Foco em coluna e ombros (carga da EVA)"},
         {"id": "n4", "title": "Melatonina 3 mg (se necessário)", "time": "22:00", "hint": "Somente se latência de sono > 30 min por 3 noites"},
         {"id": "n5", "title": "Registro de sono (Sleep-Smart)", "time": "22:30", "hint": "Sincroniza HR noturno e despertares com o B.I.P"},
     ]},
]
_ROUTINE_EN = [
    {"period": "manha", "label": "Morning", "icon": "sunrise", "window": "06:30 – 12:00",
     "tasks": [
         {"id": "m1", "title": "Wake up + vitals check-in", "time": "06:30", "hint": "HR, SpO2, BP and temperature logged by Smart-Tex"},
         {"id": "m2", "title": "Rehydrated breakfast", "time": "07:00", "hint": "Aurora-7 menu · ~820 kcal"},
         {"id": "m3", "title": "Resistance exercise — 35 min", "time": "07:30", "hint": "ARED: 2 sets of squats, rows and curls"},
         {"id": "m4", "title": "Hydration — 500 mL", "time": "08:15", "hint": "Isotonic electrolyte drink onboard"},
         {"id": "m5", "title": "Vitamin D3 + bisphosphonate (Mon/Thu)", "time": "09:00", "hint": "Bone health in microgravity"},
         {"id": "m6", "title": "Life-support systems inspection", "time": "10:30", "hint": "O2, CO2 and cabin pressure — tablet log"},
     ]},
    {"period": "tarde", "label": "Afternoon", "icon": "sun", "window": "12:00 – 19:00",
     "tasks": [
         {"id": "t1", "title": "Lunch", "time": "12:30", "hint": "~780 kcal · 32 g protein"},
         {"id": "t2", "title": "Hydration — 500 mL", "time": "14:00", "hint": "Automatic B.I.P reminder"},
         {"id": "t3", "title": "Mission operations task", "time": "15:00", "hint": "MCC contact window: 15:10–15:45"},
         {"id": "t4", "title": "Guided breathing — 5 min", "time": "17:30", "hint": "Coherence protocol: 4-7-8 · lowers cortisol"},
         {"id": "t5", "title": "Mood diary (quick PHQ-2)", "time": "18:15", "hint": "2 questions · used by B.I.P for psychological alerts"},
     ]},
    {"period": "noite", "label": "Night", "icon": "moon", "window": "19:00 – 23:00",
     "tasks": [
         {"id": "n1", "title": "Dinner", "time": "19:30", "hint": "~750 kcal · avoid caffeine after 2 PM"},
         {"id": "n2", "title": "Hydration — 300 mL", "time": "20:30", "hint": "Last hydration of the day"},
         {"id": "n3", "title": "Hygiene + light stretching", "time": "21:15", "hint": "Focus on spine and shoulders (EVA load)"},
         {"id": "n4", "title": "Melatonin 3 mg (if needed)", "time": "22:00", "hint": "Only if sleep onset > 30 min for 3 nights"},
         {"id": "n5", "title": "Sleep log (Sleep-Smart)", "time": "22:30", "hint": "Syncs nocturnal HR and awakenings to B.I.P"},
     ]},
]
_ROUTINE_ES = [
    {"period": "manha", "label": "Mañana", "icon": "sunrise", "window": "06:30 – 12:00",
     "tasks": [
         {"id": "m1", "title": "Despertar + check de vitales", "time": "06:30", "hint": "FC, SpO2, PA y temperatura registradas por Smart-Tex"},
         {"id": "m2", "title": "Desayuno rehidratado", "time": "07:00", "hint": "Menú Aurora-7 · ~820 kcal"},
         {"id": "m3", "title": "Ejercicio de resistencia — 35 min", "time": "07:30", "hint": "ARED: 2 series de sentadillas, remo y curl"},
         {"id": "m4", "title": "Hidratación — 500 mL", "time": "08:15", "hint": "Isotónica con electrolitos a bordo"},
         {"id": "m5", "title": "Vitamina D3 + bisfosfonato (lun/jue)", "time": "09:00", "hint": "Salud ósea en microgravedad"},
         {"id": "m6", "title": "Inspección de soporte vital", "time": "10:30", "hint": "O2, CO2 y presión de cabina — registro en tablet"},
     ]},
    {"period": "tarde", "label": "Tarde", "icon": "sun", "window": "12:00 – 19:00",
     "tasks": [
         {"id": "t1", "title": "Almuerzo", "time": "12:30", "hint": "~780 kcal · 32 g proteína"},
         {"id": "t2", "title": "Hidratación — 500 mL", "time": "14:00", "hint": "Recordatorio automático de B.I.P"},
         {"id": "t3", "title": "Tarea operativa de la misión", "time": "15:00", "hint": "Ventana de contacto con MCC: 15:10–15:45"},
         {"id": "t4", "title": "Respiración guiada — 5 min", "time": "17:30", "hint": "Protocolo de coherencia: 4-7-8 · reduce cortisol"},
         {"id": "t5", "title": "Diario de humor (PHQ-2 rápido)", "time": "18:15", "hint": "2 preguntas · usadas por B.I.P para alertas psicológicas"},
     ]},
    {"period": "noite", "label": "Noche", "icon": "moon", "window": "19:00 – 23:00",
     "tasks": [
         {"id": "n1", "title": "Cena", "time": "19:30", "hint": "~750 kcal · evitar cafeína después de las 14h"},
         {"id": "n2", "title": "Hidratación — 300 mL", "time": "20:30", "hint": "Última hidratación del día"},
         {"id": "n3", "title": "Higiene + estiramiento ligero", "time": "21:15", "hint": "Foco en columna y hombros (carga de EVA)"},
         {"id": "n4", "title": "Melatonina 3 mg (si es necesario)", "time": "22:00", "hint": "Solo si latencia de sueño > 30 min por 3 noches"},
         {"id": "n5", "title": "Registro de sueño (Sleep-Smart)", "time": "22:30", "hint": "Sincroniza FC nocturna y despertares con B.I.P"},
     ]},
]
ROUTINE_TEMPLATE = {"pt": _ROUTINE_PT, "en": _ROUTINE_EN, "es": _ROUTINE_ES}

_ACHIEVEMENTS_PT = [
    ("first-day", "Dia perfeito", "Completou 100% das rotinas do dia", 1, "perfect_days", 1),
    ("streak-3", "Constância orbital", "3 dias seguidos com rotina completa", 2, "streak", 3),
    ("streak-7", "Semana estelar", "7 dias seguidos com rotina completa", 3, "streak", 7),
    ("streak-14", "Lenda da Base Ares", "14 dias seguidos com rotina completa", 4, "streak", 14),
    ("hydration-7", "Mestre da hidratação", "7 registros de hidratação no tempo certo", 2, "hydration_logs", 7),
    ("mornings-5", "Madrugador orbital", "5 manhãs completas antes do meio-dia", 2, "mornings_full", 5),
    ("nights-7", "Guardião do sono", "7 rotinas noturnas completas", 2, "nights_full", 7),
    ("first-dx", "Consulta astuta", "Primeiro diagnóstico realizado com o B.I.P", 1, "diagnoses", 1),
    ("first-upload", "Olhos de águia", "Enviou uma imagem para análise", 1, "image_diagnoses", 1),
]
_ACHIEVEMENTS_EN = [
    ("first-day", "Perfect day", "Completed 100% of the day's routines", 1, "perfect_days", 1),
    ("streak-3", "Orbital consistency", "3 consecutive days with a complete routine", 2, "streak", 3),
    ("streak-7", "Stellar week", "7 consecutive days with a complete routine", 3, "streak", 7),
    ("streak-14", "Base Ares legend", "14 consecutive days with a complete routine", 4, "streak", 14),
    ("hydration-7", "Hydration master", "7 on-time hydration logs", 2, "hydration_logs", 7),
    ("mornings-5", "Orbital early bird", "5 full mornings before noon", 2, "mornings_full", 5),
    ("nights-7", "Sleep keeper", "7 complete night routines", 2, "nights_full", 7),
    ("first-dx", "Savvy checkup", "First diagnosis with B.I.P", 1, "diagnoses", 1),
    ("first-upload", "Eagle eyes", "Sent an image for analysis", 1, "image_diagnoses", 1),
]
_ACHIEVEMENTS_ES = [
    ("first-day", "Día perfecto", "Completó el 100% de las rutinas del día", 1, "perfect_days", 1),
    ("streak-3", "Constanza orbital", "3 días seguidos con rutina completa", 2, "streak", 3),
    ("streak-7", "Semana estelar", "7 días seguidos con rutina completa", 3, "streak", 7),
    ("streak-14", "Leyenda de Base Ares", "14 días seguidos con rutina completa", 4, "streak", 14),
    ("hydration-7", "Maestro de la hidratación", "7 registros de hidratación a tiempo", 2, "hydration_logs", 7),
    ("mornings-5", "Madrugador orbital", "5 mañanas completas antes del mediodía", 2, "mornings_full", 5),
    ("nights-7", "Guardián del sueño", "7 rutinas nocturnas completas", 2, "nights_full", 7),
    ("first-dx", "Consulta astuta", "Primer diagnóstico con B.I.P", 1, "diagnoses", 1),
    ("first-upload", "Ojos de águila", "Envió una imagen para análisis", 1, "image_diagnoses", 1),
]
ACHIEVEMENTS = {
    lang: [{"id": i, "title": t, "desc": d, "tier": tier, "metric": m, "target": tg}
           for i, t, d, tier, m, tg in rows]
    for lang, rows in (("pt", _ACHIEVEMENTS_PT), ("en", _ACHIEVEMENTS_EN), ("es", _ACHIEVEMENTS_ES))
}
