"""Dados estáticos da missão AURORA-7 (base do protótipo B.I.P)."""

LAUNCH_UTC = "2026-06-11T14:32:00Z"
MISSION_NAME = "Expedition AURORA-7"
CREW_MEMBER = {"name": "Elena Ricci", "role": "Flight Engineer · SpEx-47", "callsign": "Aurora-1"}

# Estoque médico de bordo (Kit Médico da missão — inventário simplificado)
MISSION_STOCK = [
    {"name": "Paracetamol 500 mg", "for": "febre, dor leve a moderada", "qty": 120},
    {"name": "Dipirona 500 mg", "for": "febre, dor", "qty": 80},
    {"name": "Ibuprofeno 400 mg", "for": "dor inflamatória, cefaleia, dor muscular", "qty": 90},
    {"name": "Omeprazol 20 mg", "for": "refluxo, proteção gástrica", "qty": 60},
    {"name": "Ondansetrona 4 mg", "for": "náusea, vômito, enjoo de movimento", "qty": 40},
    {"name": "Loperamida 2 mg", "for": "diarreia", "qty": 30},
    {"name": "Loratadina 10 mg", "for": "alergia, rinite, urticária", "qty": 40},
    {"name": "Bromoprida 10 mg", "for": "náusea, refluxo, empachamento", "qty": 30},
    {"name": "Melatonina 3 mg", "for": "insônia e ajuste de ritmo circadiano", "qty": 60},
    {"name": "Cafeína 100 mg", "for": "fadiga aguda, alerta cognitivo", "qty": 50},
    {"name": "Amoxicilina 500 mg", "for": "infecção bacteriana (uso com orientação MCC)", "qty": 28},
    {"name": "Azitromicina 500 mg", "for": "infecção respiratória bacteriana (uso com orientação MCC)", "qty": 15},
    {"name": "Ciprofloxacino 500 mg", "for": "infecção urinária/gastrointestinal (uso com orientação MCC)", "qty": 14},
    {"name": "Dexametasona 4 mg", "for": "reação inflamatória grave, crise alérgica (emergência)", "qty": 10},
    {"name": "Bisfosfonato (semanal)", "for": "perda óssea em microgravidade (profilaxia)", "qty": 24},
    {"name": "Vitamina D3 2000 UI", "for": "saúde óssea e imune em ambiente sem UV natural", "qty": 180},
    {"name": "Soro fisiológico 0,9% (bolsa 500 mL)", "for": "reidratação IV, suporte de procedimento", "qty": 10},
    {"name": "Oxigênio (concentrador + cilindros)", "for": "hipoxemia e suporte a procedimentos", "qty": None},
    {"name": "Desfibrilador semiautomático (DEA)", "for": "PCR e arritmias graves", "qty": 1},
    {"name": "Kit sutura + curativos + cola cirúrgica", "for": "ferimentos, lacerações", "qty": None},
]

# Rotinas diárias: períodos e tarefas com horários (hora local selecionada)
ROUTINE_TEMPLATE = [
    {
        "period": "manha",
        "label": "Manhã",
        "icon": "sunrise",
        "window": "06:30 – 12:00",
        "tasks": [
            {"id": "m1", "title": "Acordar + check-in de sinais vitais", "time": "06:30", "hint": "HR, SpO2, PA e temperatura registrados pelo Smart-Tex"},
            {"id": "m2", "title": "Café da manhã reidratado", "time": "07:00", "hint": "Cardápio Aurora-7 · ~820 kcal"},
            {"id": "m3", "title": "Exercício resistido — 35 min", "time": "07:30", "hint": "ARED: 2 séries de agachamento, remada e rosca"},
            {"id": "m4", "title": "Hidratação — 500 mL", "time": "08:15", "hint": "Isotônico com eletrólitos a bordo"},
            {"id": "m5", "title": "Vitamina D3 + bisfosfonato (seg/qui)", "time": "09:00", "hint": "Saúde óssea em microgravidade"},
            {"id": "m6", "title": "Inspeção dos sistemas de suporte de vida", "time": "10:30", "hint": "O2, CO2 e pressão da cabine — log no tablet"},
        ],
    },
    {
        "period": "tarde",
        "label": "Tarde",
        "icon": "sun",
        "window": "12:00 – 19:00",
        "tasks": [
            {"id": "t1", "title": "Almoço", "time": "12:30", "hint": "~780 kcal · proteína 32 g"},
            {"id": "t2", "title": "Hidratação — 500 mL", "time": "14:00", "hint": "Lembrete automático do B.I.P"},
            {"id": "t3", "title": "Atividade operacional da missão", "time": "15:00", "hint": "Janela de contato com MCC: 15:10–15:45"},
            {"id": "t4", "title": "Respiração guiada — 5 min", "time": "17:30", "hint": "Protocolo de coesão: 4-7-8 · reduz cortisol"},
            {"id": "t5", "title": "Diário de humor (PHQ-2 rápido)", "time": "18:15", "hint": "2 perguntas · usado pelo B.I.P para alertas psicológicos"},
        ],
    },
    {
        "period": "noite","label": "Noite",
        "icon": "moon",
        "window": "19:00 – 23:00",
        "tasks": [
            {"id": "n1", "title": "Jantar", "time": "19:30", "hint": "~750 kcal · evitar cafeína após as 14h"},
            {"id": "n2", "title": "Hidratação — 300 mL", "time": "20:30", "hint": "Última hidratação do dia"},
            {"id": "n3", "title": "Higiene + alongamento leve", "time": "21:15", "hint": "Foco em coluna e ombros (carga da EVA)"},
            {"id": "n4", "title": "Melatonina 3 mg (se necessário)", "time": "22:00", "hint": "Somente se latência de sono > 30 min por 3 noites"},
            {"id": "n5", "title": "Registro de sono (Sleep-Smart)", "time": "22:30", "hint": "Sincroniza HR noturno e despertares com o B.I.P"},
        ],
    },
]

EXAMS = [
    {
        "id": "hemograma-2026-11-02",
        "name": "Hemograma completo",
        "category": "Sangue",
        "date": "2026-11-02",
        "lab": "Lab-Sonde 9000 · módulo de laboratório",
        "status": "concluido",
        "summary": "Leve queda de hemoglobina, dentro da expectativa para 5 meses de missão. Sem sinais de infecção.",
        "values": [
            {"name": "Hemoglobina", "value": "12.1", "unit": "g/dL", "ref": "12.0–16.0", "flag": "normal"},
            {"name": "Hematócrito", "value": "36.8", "unit": "%", "ref": "36–46", "flag": "normal"},
            {"name": "Leucócitos", "value": "6.4", "unit": "×10³/µL", "ref": "4.0–11.0", "flag": "normal"},
            {"name": "Plaquetas", "value": "218", "unit": "×10³/µL", "ref": "150–450", "flag": "normal"},
            {"name": "Neutrófilos", "value": "58", "unit": "%", "ref": "40–70", "flag": "normal"},
            {"name": "Ferritina", "value": "38", "unit": "ng/mL", "ref": "15–150", "flag": "normal"},
        ],
    },
    {
        "id": "ecg-2026-10-21",
        "name": "ECG de repouso (12 derivações)",
        "category": "Cardíaco",
        "date": "2026-10-21",
        "lab": "Cardiu-Sat · módulo médico",
        "status": "concluido",
        "summary": "Ritmo sinusal normal, 68 bpm. Sem ectopia. Intervalo QT normal.",
        "values": [
            {"name": "FC", "value": "68", "unit": "bpm", "ref": "60–100", "flag": "normal"},
            {"name": "Eixo", "value": "+45°", "unit": "", "ref": "-30 a +90°", "flag": "normal"},
            {"name": "QTc", "value": "412", "unit": "ms", "ref": "< 450", "flag": "normal"},
            {"name": "PR", "value": "156", "unit": "ms", "ref": "120–200", "flag": "normal"},
        ],
    },
    {
        "id": "dosimetria-2026-11-10",
        "name": "Dosimetria acumulada (radiação)",
        "category": "Radiação",
        "date": "2026-11-10",
        "lab": "Rad-Mon · dosímetro pessoal",
        "status": "concluido",
        "summary": "Dose acumulada desde o lançamento dentro do limite para EVA e cabine. Tendência estável.",
        "values": [
            {"name": "Dose acumulada", "value": "32.4", "unit": "mSv", "ref": "< 180 mSv/missão", "flag": "normal"},
            {"name": "Taxa diária média", "value": "0.21", "unit": "mSv/dia", "ref": "< 1.0 mSv/dia", "flag": "normal"},
            {"name": "Dose EVA (percurso)", "value": "1.8", "unit": "µSv", "ref": "registro", "flag": "normal"},
        ],
    },
    {
        "id": "densitometria-2026-09-30",
        "name": "Densitometria óssea (DXA)",
        "category": "Imagem",
        "date": "2026-09-30",
        "lab": "DXA-Orbital · módulo médico",
        "status": "concluido",
        "summary": "Perda de 1.8% de DMO no colo do fêmur, dentro da faixa esperada. Profilaxia com bisfosfonato mantida.",
        "values": [
            {"name": "DMO colo fêmur", "value": "0.94", "unit": "g/cm²", "ref": "perda esperada < 2%/6m", "flag": "atencao"},
            {"name": "DMO coluna lombar", "value": "1.02", "unit": "g/cm²", "ref": "perda esperada < 2%/6m", "flag": "normal"},
            {"name": "T-score", "value": "-0.6", "unit": "", "ref": "> -1.0", "flag": "normal"},
        ],
    },
    {
        "id": "cortisol-2026-10-05",
        "name": "Painel hormonal (cortisol AM/PM + testosterona)",
        "category": "Sangue",
        "date": "2026-10-05",
        "lab": "Lab-Sonde 9000 · módulo de laboratório",
        "status": "concluido",
        "summary": "Cortisol matinal levemente elevado; padrão compatível com estresse operacional. Reavaliar em 30 dias.",
        "values": [
            {"name": "Cortisol AM", "value": "24.6", "unit": "µg/dL", "ref": "6.2–19.4", "flag": "alto"},
            {"name": "Cortisol PM", "value": "5.1", "unit": "µg/dL", "ref": "< 7.0", "flag": "normal"},
            {"name": "Testosterona total", "value": "512", "unit": "ng/dL", "ref": "300–1000", "flag": "normal"},
        ],
    },
    {
        "id": "rx-torax-2026-08-15",
        "name": "Radiografia de tórax",
        "category": "Imagem",
        "date": "2026-08-15",
        "lab": "Rad-Scan · módulo médico",
        "status": "concluido",
        "summary": "Campos pulmonares limpos, seios costofrênicos livres. Silhueta cardíaca normal.",
        "values": [
            {"name": "Campos pulmonares", "value": "Limpos", "unit": "", "ref": "—", "flag": "normal"},
            {"name": "Área cardíaca", "value": "Normal", "unit": "", "ref": "índice < 0.5", "flag": "normal"},
        ],
    },
    {
        "id": "hemograma-seguimento",
        "name": "Hemograma de seguimento",
        "category": "Sangue",
        "date": "2026-11-25",
        "lab": "Lab-Sonde 9000 · módulo de laboratório",
        "status": "agendado",
        "summary": "Coleta agendada para acompanhar a hemoglobina após ajuste dietético.",
        "values": [],
    },
    {
        "id": "ecg-esforco",
        "name": "ECG de esforço",
        "category": "Cardíaco",
        "date": "2026-12-02",
        "lab": "Cardiu-Sat · módulo médico",
        "status": "agendado",
        "summary": "Teste ergométrico agendado após 6 semanas do último ajuste de carga no ARED.",
        "values": [],
    },
]

ACHIEVEMENTS = [
    {"id": "first-day", "title": "Dia perfeito", "desc": "Completou 100% das rotinas do dia", "tier": 1, "metric": "perfect_days", "target": 1},
    {"id": "streak-3", "title": "Constância orbital", "desc": "3 dias seguidos com rotina completa", "tier": 2, "metric": "streak", "target": 3},
    {"id": "streak-7", "title": "Semana estelar", "desc": "7 dias seguidos com rotina completa", "tier": 3, "metric": "streak", "target": 7},
    {"id": "streak-14", "title": "Lenda da Base Ares", "desc": "14 dias seguidos com rotina completa", "tier": 4, "metric": "streak", "target": 14},
    {"id": "hydration-7", "title": "Mestre da hidratação", "desc": "7 registros de hidratação no tempo certo", "tier": 2, "metric": "hydration_logs", "target": 7},
    {"id": "mornings-5", "title": "Madrugador orbital", "desc": "5 manhãs completas antes do meio-dia", "tier": 2, "metric": "mornings_full", "target": 5},
    {"id": "nights-7", "title": "Guardião do sono", "desc": "7 rotinas noturnas completas", "tier": 2, "metric": "nights_full", "target": 7},
    {"id": "first-dx", "title": "Consulta astuta", "desc": "Primeiro diagnóstico realizado com o B.I.P", "tier": 1, "metric": "diagnoses", "target": 1},
    {"id": "first-upload", "title": "Olhos de águia", "desc": "Enviou uma imagem para análise", "tier": 1, "metric": "image_diagnoses", "target": 1},
]
