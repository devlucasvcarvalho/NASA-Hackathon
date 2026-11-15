/* B.I.P — English (single-language build) */
'use strict';

const BIP_I18N_EN = {
    'met.title': 'Mission Elapsed Time — since launch (June 11, 2026)',
    'home.greet_default': 'Good morning, Elena',
    'home.mood_calm': 'Mood: balanced · keep the pace',
    'home.mood_happy': 'Mood: radiant — all good here',
    'home.mood_worried': 'Mood: uneasy — there are pending tasks in the air',
    'home.mood_cry': 'Mood: crying — nothing done yet, shall we start?',
    'home.personalize': 'Personalize',
    'home.foot': 'Smart-Tex connected · continuous biosignal streaming',
    'dash.title': 'Mission dashboard',
    'dash.subtitle': 'Expedition AURORA-7 · Elena Ricci · continuous signals via Smart-Tex',
    'dash.tz_label': 'Choose timezone',
    'clock.mars': 'Base Ares · Mean Sol',
    'strip.met_label': 'MET · DAYS',
    'strip.remaining_label': 'DAYS REMAINING',
    'strip.moon_label': 'MOON',
    'strip.sol_label': 'CURRENT SOL',
    'vital.hr': 'Heart Rate', 'vital.spo2': 'O₂ Saturation', 'vital.hyd': 'Hydration',
    'vital.rad': 'Radiation · Dosimetry', 'vital.bp': 'Blood Pressure', 'vital.temp': 'Body Temperature',
    'vital.delta_hr': '+2 bpm vs yesterday', 'vital.delta_spo2': 'stable', 'vital.delta_hyd': 'goal 2.5 L/day',
    'vital.delta_rad': 'TEPC 1-min · CAD weekly · passive 6-mo', 'vital.delta_bp': 'sitting · left arm', 'vital.delta_temp': 'range 35.8–37.3',
    'vital.status.normal': 'Normal', 'vital.status.watch': 'Monitoring', 'vital.status.ok': 'OK',
    'vital.rad_of_limit': 'of mission limit',
    'rotina.title': 'Daily routines',
    'rotina.ring_title': 'Day progress',
    'rotina.tasks': 'tasks today',
    'rotina.streak': 'day streak',
    'rotina.pending': 'pending now',
    'rotina.achieve_title': 'Mission achievements',
    'rotina.achieve_sub': 'Check your routines on time to unlock consistency medals',
    'rotina.callout_calm': 'Your avatar reacts to your rhythm — complete routines to see him smile.',
    'rotina.callout_worried': 'Psst… pending tasks are piling up. Knock one out now and the avatar will smile again.',
    'rotina.callout_cry': 'Nothing checked off yet. Start with the 06:30 check-in — the avatar will dry his tears instantly.',
    'rotina.callout_happy': 'All good, commander! B.I.P is on cloud nine (and exercise regimen on point).',
    'rotina.all_calm': 'All quiet so far. If anything slips, I will flag it before you forget.',
    'rotina.all_done': 'All clear here! Come back tomorrow to keep the streak.',
    'rotina.some_late': 'Psst… pending tasks are piling up. Knock one out now and the avatar will smile again.',
    'rotina.nothing_done': 'Nothing done yet… I am here, but I am worried about you. Shall we start with the check-in?',
    'rotina.late_tag': 'Late',
    'dx.title': 'Tell me what you are feeling',
    'dx.subtitle': 'Text, image (wound, rash, at-home exam) or both. B.I.P crosses everything: vitals, recent exams, routine, sleep and chats — then returns hypotheses + an on-board plan.',
    'dx.placeholder': 'e.g.: Tight headache since yesterday afternoon, worse at night. Slept poorly, lots of EVA tasks planned…',
    'dx.s1': 'Tight headache', 'dx.s2': 'Nausea on waking', 'dx.s3': 'Dizzy on standing', 'dx.s4': 'Racing mind / bad sleep', 'dx.s5': 'Skin rash',
    'dx.s1t': 'Tight headache since yesterday afternoon. Worse at night and with effort.',
    'dx.s2t': 'Strong nausea and queasiness on waking, no vomiting. Started 2 days ago.',
    'dx.s3t': 'Woke up dizzy; vision went blurry for a few seconds when getting out of bed.',
    'dx.s4t': 'Since the MCC call I cannot shut my mind off: racing thoughts, poor sleep for 4 nights.',
    'dx.s5t': 'Itchy red spots on my hands since yesterday, after handling the air filter.',
    'dx.attach_strong': 'Attach image',
    'dx.attach_small': 'drag or click · wounds, rashes, exams',
    'dx.analyze': 'Analyze symptoms',
    'dx.history': 'Previous results',
    'dx.kit_title': 'On-board medical kit',
    'dx.kit_sub': 'Real Aurora-7 mission inventory — diagnoses only prescribe what exists on board.',
    'dx.kit_note': 'Severe cases follow spaceflight protocol: stabilization +',
    'dx.kit_note_b': 'mission abort and return to Earth',
    'dx.kit_note_end': '. MCC telemedicine every day, 15:10–15:45.',
    'dx.loading_title': 'One moment, analyzing…',
    'dx.step0': 'Collecting real-time vital signs…',
    'dx.step1': 'Cross-checking CBC, dosimetry and exams…',
    'dx.step2': 'Checking on-board medical kit inventory…',
    'dx.step3': 'Checking chats with your copilot (psychological factor)…',
    'dx.step4': 'Building hypotheses and conduct plan…',
    'dx.analyzed_at': 'Analysis',
    'dx.image_attached': 'with attached image',
    'dx.causes_title': 'Possible causes',
    'dx.factors_title': 'Data B.I.P used',
    'dx.rx_title': 'On-board prescription',
    'dx.steps_title': 'Step-by-step conduct',
    'dx.monitoring_title': 'Monitoring',
    'dx.flags_title': 'Red flags — when to escalate to MCC',
    'dx.new': 'New consultation',
    'dx.see_history': 'View previous results',
    'dx.history_back': '← Back',
    'dx.history_title': 'Previous results',
    'dx.empty': 'No analyses yet.<br>Run your first consultation with B.I.P.',
    'dx.attached': 'attached to this diagnosis',
    'dx.describe_first': 'Describe what you are feeling (or attach an image).',
    'dx.fail': 'Could not complete the analysis. Check your connection and try again.',
    'dx.context_exam': 'attached — describe what you are feeling.',
    'rx.dose': 'Dose:', 'rx.freq': 'Frequency:', 'rx.dur': 'Duration:',
    'rx.disclaimer_default': 'Decision support — the final word belongs to the MCC flight surgeon.',
    'rx.disclaimer_engine': 'Decision support based on on-board data — the final word belongs to the MCC flight surgeon.',
    'triage.leve_title': 'Manage onboard', 'triage.leve_detail': 'Stable picture — manageable with mission resources and calm monitoring.',
    'triage.mod_title': 'MCC telemedicine', 'triage.mod_detail': 'On-board conduct + review with the flight surgeon in the 15:10–15:45 window (priority link).',
    'triage.grave_title': 'ABORT MISSION — RETURN TO EARTH', 'triage.grave_detail': 'Off-Earth emergency: stabilize NOW, contact MCC via emergency link and prepare return.',
    'exams.title': 'Exams',
    'exams.sub': 'Complete dossier of exams performed on other mission equipment',
    'exams.search': 'Search exams, results…',
    'exams.all': 'All',
    'exams.empty': 'No exams found.',
    'exams.concluido': 'Completed', 'exams.agendado': 'Scheduled', 'exams.pendente': 'Pending',
    'exams.flag_normal': 'normal', 'exams.flag_atencao': 'attention', 'exams.flag_alto': 'high', 'exams.flag_baixo': 'low',
    'exams.tbl_param': 'Parameter', 'exams.tbl_result': 'Result', 'exams.tbl_ref': 'Ref.', 'exams.tbl_flag': 'Flag',
    'exams.no_report': 'No report yet — exam scheduled.',
    'exams.send': 'Send to diagnosis',
    'exams.sent': 'Exam attached — describe what you are feeling.',
    'chat.sub': 'your friend in the mission · Aurora-7',
    'chat.close': 'Close chat',
    'chat.input': 'Write to B.I.P…',
    'chat.send': 'Send message',
    'chat.q1': "Today's pending", 'chat.q2': 'I have a headache', 'chat.q3': 'Bad sleep', 'chat.q4': 'Water goal',
    'chat.offline': 'Ops… weak signal with MCC. Try again in a moment?',
    'chat.open': 'Open chat with B.I.P', 'chat.title_aria': 'Chat with B.I.P', 'chat.bubble': 'Psst… need something?',
    'chat.q_joke': 'Tell me a joke', 'chat.q_today': 'Which routines are pending today?', 'chat.q_headache': 'I have had a headache since yesterday.', 'chat.q_sleep': "I haven't been able to sleep properly for 4 days.", 'chat.q_water': 'How much water can I drink today?',
    'chat.greeting_late': 'Hey, Elena! I see you have {n} pending {pend} in today’s routine. No drama — shall we start with one?',
    'chat.greeting_pend_one': 'task', 'chat.greeting_pend_many': 'tasks',
    'chat.greeting_fresh': "Hey, Elena! I'm B.I.P, your friend up here. Ask me anything — jokes, the mission, life… or just vent. How are you really doing?",
    'dock.home': 'Home', 'dock.routine': 'Routines', 'dock.diagnosis': 'Diagnosis', 'dock.exams': 'Exams',
    'greet.dawn': 'Early morning', 'greet.morning': 'Good morning', 'greet.afternoon': 'Good afternoon', 'greet.night': 'Good evening',
    'moon.new': 'New Moon', 'moon.waxcres': 'Waxing Crescent', 'moon.waxq': 'First Quarter', 'moon.waxgib': 'Waxing Gibbous',
    'moon.full': 'Full Moon', 'moon.waningib': 'Waning Gibbous', 'moon.waningq': 'Last Quarter', 'moon.waningc': 'Waning Crescent',
    'toast.achievement': '🏆 Achievement unlocked: ',
    'toast.reset': 'Avatar restored to Aurora defaults.',
    'lang.label': 'Language',
    'avatar.aria': 'Astronaut avatar — tap to play',
    'panel.title': 'Make the avatar your face',
    'panel.outfit': 'Outfit', 'panel.skin': 'Skin tone', 'panel.hairstyle': 'Hairstyle', 'panel.haircolor': 'Hair color',
    'panel.beard': 'Facial hair', 'panel.eyes': 'Eye color', 'panel.freckles': 'Freckles', 'panel.show_freckles': 'show freckles',
    'panel.reset': 'Restore defaults',
    'outfit.astronaut': 'Astronaut', 'outfit.casual': 'Casual', 'outfit.voo': 'Flight', 'outfit.cargo': 'Cargo',
    'hairstyle.bald': 'Bald', 'hairstyle.crop': 'Crop', 'hairstyle.sweep': 'Quiff', 'hairstyle.curly': 'Curly', 'hairstyle.ponytail': 'Ponytail', 'hairstyle.bob': 'Bob', 'hairstyle.bun': 'Bun',
    'beard.none': 'None', 'beard.beard': 'Beard', 'beard.mustache': 'Mustache', 'beard.goatee': 'Goatee',
    'skin.clara': 'Light', 'skin.medio': 'Medium-light', 'skin.media': 'Medium', 'skin.bronze': 'Tan', 'skin.escura': 'Dark', 'skin.profunda': 'Deep',
    'hairc.preto': 'Black', 'hairc.escuro': 'Dark brown', 'hairc.castanho': 'Brown', 'hairc.ruivo': 'Auburn', 'hairc.loiro': 'Blonde', 'hairc.grisalho': 'Gray', 'hairc.violeta': 'Fantasy violet',
    'eye.castanho': 'Brown', 'eye.avela': 'Hazel', 'eye.verde': 'Green', 'eye.azul': 'Blue', 'eye.cinza': 'Gray',
    'react.hi': 'Hey, crew member!', 'react.allgood': 'Houston, all good here!', 'react.lol': 'Haha! Love it!', 'react.hail': 'Greetings from Aurora Station!', 'react.eureka': 'Eureka! Shall we check the routines?',
};

const BIP_I18N = { en: BIP_I18N_EN };
const LOCALES = { en: 'en-US' };

let BIP_LANG = 'en';
window.BIP_LANG = 'en';

const t = (key, vars) => {
  let s = BIP_I18N_EN[key] ?? key;
  if (vars) Object.entries(vars).forEach(([k, v]) => { s = s.replace(`{${k}}`, v); });
  return s;
};
window.t = t;
window.LOCALES = LOCALES;

function bipSetLang(lang) { // kept for compatibility; single-language build
  if (lang !== 'en') return;
  BIP_LANG = 'en';
  window.BIP_LANG = 'en';
  applyLang();
}
window.bipSetLang = bipSetLang;

function applyLang() {
  document.documentElement.setAttribute('lang', 'en');
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.setAttribute('placeholder', t(el.dataset.i18nPh)); });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  document.querySelectorAll('[data-i18n-title]').forEach(el => { el.setAttribute('title', t(el.dataset.i18nTitle)); });
  document.querySelectorAll('.lang-pill').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.lang === 'en')));
}
