/* ═══════════════════════════════════════════════
   B.I.P — Biomedical Intelligent Partner · front-end
   ═══════════════════════════════════════════════ */
'use strict';

const $ = (s, ctx = document) => ctx.querySelector(s);
const $$ = (s, ctx = document) => [...ctx.querySelectorAll(s)];
const store = {
  get: (k, fb) => { try { const v = localStorage.getItem(k); return v === null ? fb : JSON.parse(v); } catch { return fb; } },
  set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  del: (k) => localStorage.removeItem(k),
};
const todayKey = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const pad = (n, l = 2) => String(n).padStart(l, '0');

const LAUNCH_MS = Date.parse('2026-06-11T14:32:00Z');
const MARS_SOL_S = 88775.244;

/* ═════════ 1 · NAVEGAÇÃO / DOCK ═════════ */
const dock = $('#dock');
const dockButtons = $$('.dock-btn');
function switchScreen(id) {
  $$('.screen').forEach(s => s.classList.toggle('is-active', s.id === id));
  dockButtons.forEach(b => b.classList.toggle('is-active', b.dataset.screen === id));
  if (id === 'screen-rotina') updateRoutinesUI();
  window.scrollTo(0, 0);
}
dockButtons.forEach(b => b.addEventListener('click', () => switchScreen(b.dataset.screen)));

// Magnificação estilo macOS
const ICON_MAX = 96;
dock.addEventListener('mousemove', e => {
  dockButtons.forEach(btn => {
    const icon = $('.dock-icon', btn);
    const r = icon.getBoundingClientRect();
    const d = Math.abs(e.clientX - (r.left + r.width / 2));
    const s = 1 + Math.max(0, (ICON_MAX - d) / ICON_MAX) * 0.55;
    icon.style.transform = `scale(${s.toFixed(3)}) translateY(${(-(s - 1) * 30).toFixed(1)}px)`;
  });
});
dock.addEventListener('mouseleave', () => dockButtons.forEach(b => { $('.dock-icon', b).style.transform = ''; }));

/* ═════════ 2 · TOAST + DING ═════════ */
const toastEl = $('#toast');
let toastTimer = null;
function toast(msg, ms = 3400) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
}
function ding(freq = 880) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ac = new Ctx(); const o = ac.createOscillator(); const g = ac.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(freq, 0); o.frequency.exponentialRampToValueAtTime(freq * 1.5, 0.14);
    g.gain.setValueAtTime(0.0001, 0); g.gain.exponentialRampToValueAtTime(0.22, 0.02); g.gain.exponentialRampToValueAtTime(0.0001, 0.7);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + 0.72);
  } catch {}
}

/* ═════════ 3 · VITAIS ═════════ */
let lastVitals = null;
const spark = (seed, n = 15, base = 16, amp = 9) => {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const y = base + Math.sin(i * 1.55 + seed) * amp * 0.6 + Math.sin(i * 0.62 + seed * 2.3) * amp * 0.45;
    pts.push(`${(i * (100 / (n - 1))).toFixed(1)},${y.toFixed(1)}`);
  }
  return pts;
};
const vitalDefs = [
  { key: 'heart_rate', label: 'Frequência Cardíaca', unit: 'bpm', iconClass: '', delta: '+2 bpm vs ontem', deltaKind: 'ok', status: 'Normal', statusKind: 'ok', sparkSeed: 1.6, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20.3s-6.6-4.4-9.1-9.1C1.7 8.6 3.8 6 7 6c2.1 0 3.7 1.2 5 3 1.3-1.8 2.9-3 5-3 3.2 0 5.3 2.6 4.1 5.2-2.5 4.7-9.1 9.1-9.1 9.1Z"/></svg>' },
  { key: 'spo2', label: 'Saturação de O₂', unit: '%', iconClass: 'sky', delta: 'estável', deltaKind: 'ok', status: 'Normal', statusKind: 'ok', sparkSeed: 4.1, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c3.2 4.4 5.4 7.7 5.4 11a5.4 5.4 0 0 1-10.8 0C6.6 10.7 8.8 7.4 12 3Z"/><path d="M9.5 14.5a2.6 2.6 0 0 0 2.5 2.7"/></svg>' },
  { key: 'hydration', label: 'Hidratação', unit: '%', iconClass: 'sky', delta: 'meta 2,5 L/dia', deltaKind: 'ok', status: 'OK', statusKind: 'ok', meter: true, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h10M8.5 3 6.6 8.2a4.9 4.9 0 1 0 10.8 0L15.5 3"/><path d="M7.3 13h9.4"/></svg>' },
  { key: 'radiation', label: 'Radiação · Dosimetria', unit: 'mSv/dia', iconClass: 'gold', delta: 'limite 180 mSv/missão', deltaKind: 'warn', status: 'Vigilância', statusKind: 'watch', meter: true, meterMax: 180, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/><path d="M12 2a10 10 0 0 1 8.7 5.1l-4.4 2.5M12 22a10 10 0 0 1-8.7-5.1l4.4-2.5M22 12a10 10 0 0 1-5 8.7l-2.5-4.4M2 12a10 10 0 0 1 5-8.7l2.5 4.4"/></svg>' },
  { key: 'bp', label: 'Pressão Arterial', unit: 'mmHg', iconClass: 'terra', delta: 'sentado · braço esq.', deltaKind: 'ok', status: 'Normal', statusKind: 'ok', sparkSeed: 2.8, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4a8 8 0 0 1 8 8h-2.4"/><path d="M12 4a8 8 0 0 0-8 8h2.4"/><path d="M12 12l3.4-3.4"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/></svg>' },
  { key: 'temperature', label: 'Temperatura Corporal', unit: '°C', iconClass: '', delta: 'faixa 35.8–37.3', deltaKind: 'ok', status: 'Normal', statusKind: 'ok', sparkSeed: 5.3, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13.6V5a2 2 0 0 1 4 0v8.6a4.5 4.5 0 1 1-4 0Z"/><circle cx="12" cy="17.5" r="1.4" fill="currentColor" stroke="none"/></svg>' },
];

function renderVitals(v) {
  lastVitals = v;
  $('#vitalsGrid').innerHTML = vitalDefs.map(def => {
    let valueHtml, footExtra = '';
    if (def.key === 'bp') {
      valueHtml = `${Math.round(v.bp_sys)}<small>/</small>${Math.round(v.bp_dia)}<small> mmHg</small>`;
    } else if (def.key === 'radiation') {
      valueHtml = `${v.radiation_dose_rate.toFixed(2)}<small> mSv/dia</small>`;
      const pct = Math.min(100, (v.radiation_cumulative / 180) * 100);
      footExtra = `<div class="meter radiation" title="${v.radiation_cumulative.toFixed(1)} mSv de 180 mSv (limite de carreira da missão)"><span style="width:${pct.toFixed(1)}%"></span></div><div class="vital-delta delta-warn" style="margin-top:4px">acumulado ${v.radiation_cumulative.toFixed(1)} mSv · ${pct.toFixed(1)}% do limite</div>`;
    } else if (def.key === 'hydration') {
      valueHtml = `${Math.round(v.hydration)}<small>%</small>`;
      footExtra = `<div class="meter"><span style="width:${v.hydration}%"></span></div>`;
    } else if (def.key === 'temperature') {
      valueHtml = `${v.temperature.toFixed(1)}<small> °C</small>`;
    } else if (def.key === 'spo2') {
      valueHtml = `${v.spo2.toFixed(1)}<small>%</small>`;
    } else {
      valueHtml = `${Math.round(v.heart_rate)}<small> bpm</small>`;
    }
    const sparkSvg = def.meter ? '' : `<svg class="spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polygon points="0,30 ${spark(def.sparkSeed).join(' ')} 100,30"/><polyline points="${spark(def.sparkSeed).join(' ')}"/></svg>`;
    return `<article class="vital-card">
      <div class="vital-top"><span class="vital-icon ${def.iconClass}">${def.icon}</span><span class="vital-label">${def.label}</span></div>
      <div class="vital-value">${valueHtml}</div>
      ${sparkSvg}${footExtra}
      <div class="vital-foot"><span class="vital-delta delta-${def.deltaKind}">${def.delta}</span><span class="vital-status ${def.statusKind}">${def.status}</span></div>
    </article>`;
  }).join('');
}
async function refreshVitals() {
  try { renderVitals(await (await fetch('/api/vitals')).json()); } catch (e) { console.warn('vitals offline', e); }
}

/* ═════════ 4 · RELÓGIO + CÉU ═════════ */
const tzSelect = $('#tzSelect');
let currentTz = store.get('bip.tz', 'houston');
tzSelect.value = currentTz;

const TZ_META = {
  houston: { label: 'Mission Control — Houston', tz: 'America/Chicago' },
  utc:     { label: 'Greenwich — UTC',           tz: 'UTC' },
  tokyo:   { label: 'Tóquio — UTC+9',            tz: 'Asia/Tokyo' },
  mars:    { label: 'Base Ares — Sol médio',     tz: null },
};

function marsNow() {
  const elapsed = (Date.now() - LAUNCH_MS) / 1000;
  const marsElapsed = elapsed * (MARS_SOL_S / 86400);
  const sol = Math.floor(marsElapsed / MARS_SOL_S) + 1;
  const secToday = marsElapsed % MARS_SOL_S;
  const h = Math.floor(secToday / 3600), m = Math.floor((secToday % 3600) / 60), s = Math.floor(secToday % 60);
  return { sol, h, m, s, hhmmss: `${pad(h)}:${pad(m)}:${pad(s)}`, hour: h + m / 60 };
}
function earthNow(tz) {
  const parts = new Intl.DateTimeFormat('pt-BR', { timeZone: tz, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
  const get = t => Number(parts.find(p => p.type === t).value);
  return { h: get('hour'), m: get('minute'), s: get('second'), hour: get('hour') + get('minute') / 60,
           hhmmss: `${pad(get('hour'))}:${pad(get('minute'))}:${pad(get('second'))}` };
}
function moonPhase(date = new Date()) {
  const synodic = 29.53058867;
  const ref = Date.UTC(2000, 0, 6, 18, 14) / 86400000;
  const now = date.getTime() / 86400000;
  let p = ((now - ref) % synodic) / synodic;
  if (p < 0) p += 1;
  const illum = (1 - Math.cos(2 * Math.PI * p)) / 2;
  const names = ['Lua Nova', 'Crescente', 'Quarto Crescente', 'Gibosa Crescente', 'Lua Cheia', 'Gibosa Minguante', 'Quarto Minguante', 'Minguante'];
  const idx = Math.floor(((p + 1 / 16) % 1) * 8);
  return { p, illum, name: names[idx] };
}
function moonPhaseName(p) {
  if (p < 0.033 || p > 0.967) return 'Lua Nova';
  if (p < 0.216) return 'Crescente';
  if (p < 0.283) return 'Quarto Crescente';
  if (p < 0.466) return 'Gibosa Crescente';
  if (p < 0.534) return 'Lua Cheia';
  if (p < 0.717) return 'Gibosa Minguante';
  if (p < 0.784) return 'Quarto Minguante';
  return 'Minguante';
}

const MISSION_DAYS = 400;

function celestSvg(kind, isMars) {
  if (kind === 'night') {
    const ph = moonPhase();
    const waxing = ph.p < 0.5;
    const off = (1 - ph.illum) * 2 * 13.2 * (waxing ? -1 : 1);
    const stars = [[8, 9], [37, 7], [12, 33], [39, 28], [23, 5]].map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="${i % 2 ? 0.8 : 1.15}" fill="#fff" opacity=".9"/>`).join('');
    const clipId = waxing ? 'cmcWax' : 'cmcWan';
    return `<svg viewBox="0 0 46 46"><rect width="46" height="46" rx="12" fill="#0a2233"/>${stars}<clipPath id="${clipId}"><circle cx="23" cy="23" r="10.4"/></clipPath><circle cx="23" cy="23" r="10.4" fill="#f3ead8"/><g clip-path="url(#${clipId})"><circle cx="${(23 + off).toFixed(1)}" cy="23" r="10.4" fill="#0a2233" opacity=".92"/></g></svg>`;
  }
  if (kind === 'golden') {
    return `<svg viewBox="0 0 46 46"><rect width="46" height="46" rx="12" fill="#331d12"/><circle cx="23" cy="30" r="13" fill="#f7b36a" opacity=".85"/><circle cx="23" cy="30" r="8.4" fill="#ffe6a8"/><rect y="30" width="46" height="16" rx="12" fill="#4e2412"/></svg>`;
  }
  if (kind === 'midday') {
    return `<svg viewBox="0 0 46 46"><rect width="46" height="46" rx="12" fill="${isMars ? '#c49a6c' : '#7ec8e0'}"/><circle cx="23" cy="22" r="10.5" fill="${isMars ? '#ffdf9e' : '#ffe586'}"/><circle cx="23" cy="22" r="${isMars ? 6 : 7}" fill="#fff8d6"/><g stroke="${isMars ? '#ffedb8' : '#ffe586'}" stroke-width="1.8" stroke-linecap="round" opacity=".9"><path d="M23 2.5v4.5M23 39v4.5M2.5 22.5H7M39 22.5h4.5M8.6 8.1l3.2 3.2M34.2 33.6l3.2 3.2M37.4 8.1l-3.2 3.2M11.8 33.6l-3.2 3.2"/></g></svg>`;
  }
  // manhã: sol nascente + nuvens
  return `<svg viewBox="0 0 46 46"><rect width="46" height="46" rx="12" fill="${isMars ? '#d8ab7d' : '#a8dbe8'}"/><circle cx="15" cy="27" r="8" fill="#ffd98a"/><circle cx="15" cy="27" r="5" fill="#fff0bd"/><g fill="#ffffff" opacity=".95"><ellipse cx="30" cy="16" rx="8.6" ry="4.2"/><ellipse cx="37" cy="13.4" rx="5.4" ry="3.2"/></g></svg>`;
}

function tickClock() {
  const isMars = currentTz === 'mars';
  let hour, hhmmss, dateLabel;
  if (isMars) {
    const mn = marsNow();
    hour = mn.hour; hhmmss = mn.hhmmss;
    dateLabel = `Sol ${mn.sol} · Ares`;
    $('#stripMoon').textContent = `Sol ${mn.sol}`;
    $('#stripMoonName').textContent = 'sol atual';
  } else {
    const en = earthNow(TZ_META[currentTz].tz);
    hour = en.hour; hhmmss = en.hhmmss;
    dateLabel = new Intl.DateTimeFormat('pt-BR', { timeZone: TZ_META[currentTz].tz, weekday: 'short', day: '2-digit', month: 'short' }).format(new Date()).replaceAll('.', '');
    const ph = moonPhase();
    $('#stripMoon').textContent = `${Math.round(ph.illum * 100)}%`;
    $('#stripMoonName').textContent = moonPhaseName(ph.p);
  }
  $('#clockTime').textContent = hhmmss.slice(0, 5);
  $('#clockDate').textContent = dateLabel;
  const kind = hour >= 5 && hour < 11 ? 'morning' : hour >= 11 && hour < 16 ? 'midday' : hour >= 16 && hour < 19 ? 'golden' : 'night';
  $('#celestIcon').innerHTML = celestSvg(kind, isMars);

  const sec = Math.max(0, Math.floor((Date.now() - LAUNCH_MS) / 1000));
  const metDays = Math.floor(sec / 86400);
  $('#metClock').textContent = `${pad(metDays, 3)}:${pad(Math.floor(sec / 3600) % 24)}:${pad(Math.floor(sec / 60) % 60)}:${pad(sec % 60)}`;
  $('#stripMet').textContent = `${pad(metDays, 3)}d ${pad(Math.floor(sec / 3600) % 24)}h`;
  $('#stripRemaining').textContent = String(Math.max(0, MISSION_DAYS - metDays));

  $('#greetName').textContent = `${hour < 6 ? 'Boa madrugada' : hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'}, Elena`;
  const rd = $('#routineDate');
  if (rd) rd.textContent = isMars ? `Sol ${marsNow().sol} · Base Ares`
    : new Intl.DateTimeFormat('pt-BR', { timeZone: TZ_META[currentTz].tz, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
}
tzSelect.addEventListener('change', () => { currentTz = tzSelect.value; store.set('bip.tz', currentTz); tickClock(); });

/* ═════════ 5 · ROTINAS ═════════ */
const ROUTINE_KEY = () => `bip.routines.${todayKey()}`;
const HISTORY_KEY = 'bip.history.v1';
let routineTemplate = [];
let doneIds = store.get(ROUTINE_KEY(), []);
const HISTORY = store.get(HISTORY_KEY, {});

const PERIOD_ICONS = {
  sunrise: '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M12 3v4"/><path d="M5.6 10.6 4.2 9.2M18.4 10.6l1.4-1.4"/><path d="M3 17h18"/><path d="M8 17a4 4 0 0 1 8 0"/><path d="M7 13h10"/></svg>',
  sun: '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="4.6"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/></svg>',
  moon: '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13.5A8.5 8.5 0 0 1 10.5 4a8.5 8.5 0 1 0 9.5 9.5Z"/></svg>',
};

function minutesNow() { const d = new Date(); return d.getHours() * 60 + d.getMinutes(); }
function taskLate(task) {
  const [h, m] = task.time.split(':').map(Number);
  return minutesNow() > h * 60 + m + 15 && !doneIds.includes(task.id);
}
function allTaskIds() { return routineTemplate.flatMap(p => p.tasks.map(t => t.id)); }
function periodDone(period) { return period.tasks.every(t => doneIds.includes(t.id)); }
function routineScore() { const all = allTaskIds(); return all.length ? Math.round((doneIds.filter(id => all.includes(id)).length / all.length) * 100) : 0; }

function buildRoutines() {
  const grid = $('#periodsGrid');
  grid.innerHTML = routineTemplate.map(period => `
    <div class="period-card" data-period="${period.period}">
      <div class="period-head">
        <span class="period-icon ${period.period}">${PERIOD_ICONS[period.icon] || PERIOD_ICONS.sun}</span>
        <span><h3>${period.label}</h3><small>${period.window}</small></span>
        <span class="period-count" data-count="${period.period}">0/${period.tasks.length}</span>
      </div>
      ${period.tasks.map(t => `
        <label class="task${doneIds.includes(t.id) ? ' done' : ''}" data-id="${t.id}" data-time="${t.time}">
          <input type="checkbox" data-id="${t.id}" ${doneIds.includes(t.id) ? 'checked' : ''} aria-label="${t.title}">
          <span class="task-box"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#eafff6" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12.5l5 5L19.5 6.5"/></svg></span>
          <span><span class="task-title">${t.title}</span>
            <span class="task-meta"><span class="task-time">${t.time}</span><span class="late-tag" hidden>Atrasada</span></span>
            <span class="task-hint">${t.hint}</span>
          </span>
        </label>`).join('')}
    </div>`).join('');

  grid.addEventListener('change', e => {
    const id = e.target.dataset.id; if (!id) return;
    if (e.target.checked) { if (!doneIds.includes(id)) doneIds.push(id); }
    else doneIds = doneIds.filter(x => x !== id);
    store.set(ROUTINE_KEY(), doneIds);
    persistHistory();
    updateRoutinesUI();
  });
}

function persistHistory() {
  const all = routineTemplate.flatMap(p => p.tasks.map(t => ({ ...t, period: p.period })));
  HISTORY[todayKey()] = {
    done: [...doneIds],
    total: all.length,
    perfect: all.length > 0 && all.every(t => doneIds.includes(t.id)),
    morningsFull: all.filter(t => t.period === 'manha').every(t => doneIds.includes(t.id)),
    nightsFull: all.filter(t => t.period === 'noite').every(t => doneIds.includes(t.id)),
    hyd: doneIds.filter(id => ['m4', 't2', 'n2'].includes(id)).length,
  };
  store.set(HISTORY_KEY, HISTORY);
  evaluateAchievements();
}

function computeMetrics() {
  const days = Object.entries(HISTORY).sort(([a], [b]) => a.localeCompare(b));
  const perfectDays = days.filter(([, d]) => d.perfect).map(([k]) => k);
  let streak = 0;
  for (let i = days.length - 1; i >= 0; i--) {
    if (days[i][1].perfect) streak++; else if (days[i][0] === todayKey()) continue; else break;
  }
  return {
    perfect_days: perfectDays.length,
    streak,
    hydration_logs: days.reduce((acc, [, d]) => acc + (d.hyd || 0), 0),
    mornings_full: days.filter(([, d]) => d.morningsFull).length,
    nights_full: days.filter(([, d]) => d.nightsFull).length,
    diagnoses: (store.get('bip.diagnoses', []) || []).length,
    image_diagnoses: (store.get('bip.diagnoses', []) || []).filter(d => d.image_attached).length,
  };
}
let achievements = [];
function evaluateAchievements(silent = true) {
  const metrics = computeMetrics();
  const unlocked = new Set(store.get('bip.achievements', []));
  achievements.forEach(a => {
    if ((metrics[a.metric] || 0) >= a.target && !unlocked.has(a.id)) {
      unlocked.add(a.id);
      store.set('bip.achievements', [...unlocked]);
      toast(`🏆 Conquista desbloqueada: ${a.title}!`);
      ding(1046);
    }
  });
  renderAchievements(metrics, unlocked);
}
function renderAchievements(metrics, unlockedSet) {
  const unlocked = unlockedSet || new Set(store.get('bip.achievements', []));
  $('#achievementsRail').innerHTML = achievements.map(a => {
    const isOpen = unlocked.has(a.id);
    const prog = Math.min(1, (metrics[a.metric] || 0) / a.target);
    return `<div class="achievement ${isOpen ? 'unlocked' : 'locked'}" title="${isOpen ? a.desc : `${a.desc} — ${Math.floor(prog * 100)}%`}">
      <span class="ach-medal"><svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="5.4"/><path d="M8.8 13.4 6.5 21l5.5-3.2L17.5 21l-2.3-7.6"/></svg></span>
      <h4>${a.title}</h4><p>${a.desc}</p>
    </div>`;
  }).join('');
}

function updateRoutinesUI() {
  if (!routineTemplate.length) return;
  // estado visual
  let late = 0, total = 0, done = 0;
  $$('#periodsGrid .task').forEach(el => {
    const id = el.dataset.id;
    const cb = $('input', el);
    const isDone = doneIds.includes(id);
    el.classList.toggle('done', isDone);
    const task = routineTemplate.flatMap(p => p.tasks).find(t => t.id === id);
    const isLate = task && taskLate(task);
    el.classList.toggle('late', !!isLate);
    $('.late-tag', el).hidden = !isLate;
    cb.checked = isDone;
    total++; if (isDone) done++; if (isLate) late++;
  });
  routineTemplate.forEach(p => {
    const c = $(`[data-count="${p.period}"]`);
    const d = p.tasks.filter(t => doneIds.includes(t.id)).length;
    c.textContent = `${d}/${p.tasks.length}`;
    c.classList.toggle('all-done', d === p.tasks.length);
  });
  const pct = total ? Math.round(done / total * 100) : 0;
  $('#dayRing').style.strokeDashoffset = String(213.6 * (1 - pct / 100));
  $('#dayRingLabel').textContent = `${pct}%`;
  $('#kpiDone').textContent = `${done}/${total}`;
  $('#kpiPending').textContent = String(late);
  $('#kpiStreak').textContent = String(computeMetrics().streak);

  // humor do avatar
  const mood = pct === 100 ? 'happy' : (late > 0 && done === 0 ? 'cry' : (late > 0 ? 'worried' : 'calm'));
  $$('.avatar').forEach(a => a.setAttribute('data-mood', mood));
  const moodText = {
    happy: 'Humor: radiante — tudo certo por aqui ✨',
    calm: 'Humor: em equilíbrio · mantenha o ritmo',
    worried: 'Humor: apreensivo — tem pendência no ar',
    cry: 'Humor: chorando — nada feito ainda, vamos começar?',
  }[mood];
  $('#moodLine').textContent = moodText;
  $('#moodCallout').textContent = {
    happy: 'Tudo certo, comandante! O Bip está em êxtase (e regime de exercício em dia).',
    calm: 'Tudo tranquilo por enquanto. Se algo atrasar, eu aviso antes de te deixar esquecer.',
    worried: 'Psst… pendências acumulando. Resolve uma agora que o avatar volta a sorrir.',
    cry: 'Nada marcado hoje. Recomeça pelo check-in das 06:30 — o avatar seca as lágrimas na hora.',
  }[mood];

  // badge da dock
  const badge = $('#dockBadge');
  badge.hidden = late === 0;
  badge.textContent = String(late);
}

/* ═════════ 6 · DIAGNÓSTICO ═════════ */
const dxViews = { form: $('#dxFormView'), loading: $('#dxLoadingView'), result: $('#dxResultView'), history: $('#dxHistoryView') };
const showDxView = name => Object.entries(dxViews).forEach(([k, v]) => { v.hidden = k !== name; });
let dxImageDataUrl = null;
let pendingExamContext = null;

function applyDxContextChip() {
  const chip = $('#dxContextChip');
  if (pendingExamContext) {
    chip.hidden = false;
    chip.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 3h6v4a4 4 0 0 1-6 0Z"/><path d="M9 7H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3"/></svg><span>${pendingExamContext.label} anexado ao diagnóstico</span>`;
  } else { chip.hidden = true; }
}

$('#dxSuggestChips').addEventListener('click', e => {
  const btn = e.target.closest('.chip'); if (!btn) return;
  $('#dxText').value = btn.dataset.fill;
  $('#dxText').focus();
});
const dxImageInput = $('#dxImageInput');
dxImageInput.addEventListener('change', () => {
  const file = dxImageInput.files && dxImageInput.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    dxImageDataUrl = reader.result;
    $('#dxPreviewImg').src = dxImageDataUrl;
    $('#dxPreview').hidden = false;
  };
  reader.readAsDataURL(file);
});
$('#dxPreviewRemove').addEventListener('click', () => { dxImageDataUrl = null; dxImageInput.value = ''; $('#dxPreview').hidden = true; });

// drag & drop na dropzone
const dz = $('#dxDropzone');
['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('dz-over'); }));
['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('dz-over'); }));
dz.addEventListener('drop', e => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0]; if (!file || !file.type.startsWith('image/')) return;
  const reader = new FileReader();
  reader.onload = () => { dxImageDataUrl = reader.result; $('#dxPreviewImg').src = dxImageDataUrl; $('#dxPreview').hidden = false; };
  reader.readAsDataURL(file);
});

$('#dxAnalyzeBtn').addEventListener('click', analyzeSymptoms);

const SCAN_STEP_DELAYS = [250, 800, 1400, 2050];
function animateScanSteps() {
  const steps = $$('#scanSteps li');
  steps.forEach(s => s.classList.remove('done', 'current'));
  steps[0].classList.add('current');
  SCAN_STEP_DELAYS.forEach((delay, i) => {
    setTimeout(() => {
      steps[i].classList.replace('current', 'done');
      if (steps[i + 1]) steps[i + 1].classList.add('current');
    }, delay);
  });
}

async function analyzeSymptoms() {
  const text = $('#dxText').value.trim();
  if (text.length < 4 && !dxImageDataUrl) { toast('Descreva o que está sentindo (ou anexe uma imagem).'); return; }
  showDxView('loading');
  animateScanSteps();

  const chat = store.get('bip.chat', []);
  const chatSummary = chat.filter(m => m.role === 'user').slice(-3).map(m => m.text).join(' | ');
  const v = lastVitals || {};
  const context = {
    heart_rate: v.heart_rate ? `${Math.round(v.heart_rate)} bpm` : undefined,
    spo2: v.spo2 ? `${v.spo2}%` : undefined,
    bp: v.bp_sys ? `${Math.round(v.bp_sys)}/${Math.round(v.bp_dia)} mmHg` : undefined,
    temperature: v.temperature ? `${v.temperature} °C` : undefined,
    sleep_hours: '7.2 h (média 6 noites)',
    radiation_cumulative: v.radiation_cumulative ? `${v.radiation_cumulative.toFixed(1)} mSv` : undefined,
    routine_score: routineScore(),
    chat_summary: chatSummary || 'sem conversas recentes',
    exams: 'Cortisol AM 24.6 µg/dL ALTO (05/out) · Hemoglobina 12.1 g/dL (02/nov) · DMO colo fêmur −1.8% (30/set, atenção) · Dosimetria acumulada 32.4 mSv (10/nov) · ECG normal (21/out)',
    exam_sent: pendingExamContext ? pendingExamContext.detail : undefined,
    crew: 'Elena Ricci · Flight Engineer · SpEx-47 · Expedition AURORA-7',
  };
  Object.keys(context).forEach(k => context[k] === undefined && delete context[k]);

  let result = null;
  try {
    const res = await fetch('/api/diagnose', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text || '(imagem anexada para análise)', image: dxImageDataUrl, context }),
    });
    result = await res.json();
  } catch (e) { console.error(e); }

  await new Promise(r => setTimeout(r, Math.max(0, 2400 - 0))); // garante a animação mínima
  if (!result || !result.severity) {
    showDxView('form');
    toast('Não consegui concluir a análise. Verifique a conexão e tente de novo.');
    return;
  }
  const diagnoses = store.get('bip.diagnoses', []);
  diagnoses.push(result);
  store.set('bip.diagnoses', diagnoses.slice(-25));
  renderDiagnosisResult(result);
  $('#dxHistoryCount').textContent = String(Math.min(diagnoses.length, 25));
  pendingExamContext = null; applyDxContextChip();
  evaluateAchievements();
}

const TRIAGE_META = {
  leve:      { title: 'Conduta a bordo', detail: 'Quadro estável — manejável com os recursos da missão e monitoramento tranquilo.', action: 'onboard' },
  moderado:  { title: 'Telemedicina com o MCC', detail: 'Conduta a bordo + revisão com o médico de voo na janela das 15:10–15:45 (link prioritário).', action: 'telemedicine' },
  grave:     { title: 'ABORTAR MISSÃO — RETORNO À TERRA', detail: 'Emergência off-Terra: estabilizar AGORA, comunicar o MCC pelo link de emergência e preparar o retorno.', action: 'abort' },
};
const SEV_ICON = {
  leve: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  moderado: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v5"/><path d="M12 16.5h.01"/><circle cx="12" cy="12" r="9.2"/></svg>',
  grave: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 10v4.5M12 17.2h.01"/></svg>',
};

function renderDiagnosisResult(d) {
  showDxView('result');
  const sev = (d.severity || 'leve').toLowerCase();
  const meta = TRIAGE_META[sev] || TRIAGE_META.leve;
  const banner = $('#triageBanner');
  banner.dataset.level = sev;
  $('#triageIcon').innerHTML = SEV_ICON[sev] || SEV_ICON.leve;
  $('#triageTitle').textContent = meta.title;
  $('#triageDetail').textContent = meta.detail;

  $('#dxAnalyzedAt').textContent = `Análise ${d.analyzed_at ? new Date(d.analyzed_at).toLocaleString('pt-BR') : 'agora'}${d.image_attached ? ' · com imagem anexada' : ''}`;
  $('#dxResultTitle').textContent = d.title || 'Resultado';
  $('#dxSummary').textContent = d.summary || '';

  $('#dxCauses').innerHTML = (d.causes || []).map(c => `
    <div class="cause">
      <div class="cause-top"><span>${c.name}</span><span class="mono">${c.likelihood ?? 0}%</span></div>
      <div class="cause-bar"><span style="width:${Math.max(2, Math.min(100, c.likelihood || 0))}%"></span></div>
      <div class="cause-why">${c.why || ''}</div>
    </div>`).join('');

  $('#dxFactors').innerHTML = (d.factors_used || []).map(f => `<span class="factor-chip">${f}</span>`).join('');

  $('#dxPrescription').innerHTML = (d.prescription || []).map((p, i) => `
    <div class="rx-item"><span class="rx-num">${pad(i + 1)}</span>
      <span><h5>${p.item || '—'}</h5>
        <div class="rx-posology">
          ${p.dose ? `<span><b>Dose:</b> ${p.dose}</span>` : ''}
          ${p.frequency ? `<span><b>Frequência:</b> ${p.frequency}</span>` : ''}
          ${p.duration ? `<span><b>Duração:</b> ${p.duration}</span>` : ''}
        </div>
        ${p.instructions ? `<small>${p.instructions}</small>` : ''}
      </span>
    </div>`).join('');

  $('#dxProcedures').innerHTML = (d.procedures || []).map(p => `<li>${p}</li>`).join('');
  $('#dxMonitoring').textContent = d.monitoring || '—';
  $('#dxRedFlags').innerHTML = (d.red_flags || []).map(r => `<li>${r}</li>`).join('');
  $('#dxDisclaimer').textContent = d.disclaimer || 'Apoio à decisão — a palavra final é do médico de voo do MCC.';
  // animar barras após pintura
  requestAnimationFrame(() => $$('#dxCauses .cause-bar > span').forEach(s => { s.style.width = s.style.width; }));
}

$('#dxNewConsultBtn').addEventListener('click', () => {
  $('#dxText').value = ''; dxImageDataUrl = null; dxImageInput.value = ''; $('#dxPreview').hidden = true;
  showDxView('form'); $('#dxText').focus();
});

function renderHistory() {
  const list = $('#dxHistoryList');
  const diagnoses = [...(store.get('bip.diagnoses', []))].reverse();
  if (!diagnoses.length) {
    list.innerHTML = '<div class="history-empty">Nenhuma análise ainda.<br>Faça sua primeira consulta com o Bip. 🩺</div>';
    return;
  }
  list.innerHTML = diagnoses.map((d, i) => `
    <button class="history-item" data-idx="${diagnoses.length - 1 - i}">
      <span class="history-sev ${d.severity || 'leve'}"></span>
      <span><h4>${d.title || 'Análise'}</h4>
      <p>${d.analyzed_at ? new Date(d.analyzed_at).toLocaleString('pt-BR') : ''} · “${(d.query || '').slice(0, 90)}${(d.query || '').length > 90 ? '…' : ''}”</p></span>
    </button>`).join('');
}
$('#dxHistoryBtn').addEventListener('click', () => { renderHistory(); showDxView('history'); });
$('#dxBackHistoryBtn').addEventListener('click', () => { renderHistory(); showDxView('history'); });
$('#dxHistoryBackBtn').addEventListener('click', () => showDxView('form'));
$('#dxHistoryList').addEventListener('click', e => {
  const btn = e.target.closest('.history-item'); if (!btn) return;
  const diagnoses = store.get('bip.diagnoses', []);
  const d = diagnoses[Number(btn.dataset.idx)];
  if (d) renderDiagnosisResult(d);
});

/* ═════════ 7 · EXAMES ═════════ */
let exams = [];
let examFilter = 'Todos';
let examQuery = '';
const FLAG_LABEL = { normal: 'normal', atencao: 'atenção', alto: 'alto', baixo: 'baixo' };

async function loadExams() {
  try { exams = (await (await fetch('/api/exams')).json()).exams; } catch { exams = []; }
  const cats = ['Todos', ...new Set(exams.map(e => e.category))];
  $('#examFilters').innerHTML = cats.map(c => `<button class="filter-chip${c === examFilter ? ' is-active' : ''}" data-cat="${c}">${c}</button>`).join('');
  renderExams();
}
function renderExams() {
  const q = examQuery.trim().toLowerCase();
  const filtered = exams.filter(e => (examFilter === 'Todos' || e.category === examFilter) &&
    (!q || `${e.name} ${e.summary} ${e.date}`.toLowerCase().includes(q)));
  $('#examsGrid').innerHTML = filtered.map(e => {
    const flagged = (e.values || []).filter(v => v.flag && v.flag !== 'normal');
    return `<button class="exam-card" data-id="${e.id}">
      <div class="exam-card-top"><h3>${e.name}</h3><span class="exam-cat">${e.category}</span></div>
      <span class="exam-date mono">${new Date(e.date + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
      <p class="exam-summary">${e.summary}</p>
      ${flagged.length ? `<div class="flag-row">${flagged.map(f => `<span class="mini-flag ${f.flag}">${f.name}: ${FLAG_LABEL[f.flag] || f.flag}</span>`).join('')}</div>` : ''}
      <span class="status-badge ${e.status}">${e.status === 'concluido' ? 'Concluído' : e.status === 'agendado' ? 'Agendado' : 'Pendente'}</span>
    </button>`;
  }).join('') || '<p class="muted" style="grid-column:1/-1;text-align:center;padding:40px">Nenhum exame encontrado.</p>';
}
$('#examFilters').addEventListener('click', e => {
  const btn = e.target.closest('.filter-chip'); if (!btn) return;
  examFilter = btn.dataset.cat;
  $$('#examFilters .filter-chip').forEach(c => c.classList.toggle('is-active', c === btn));
  renderExams();
});
$('#examSearch').addEventListener('input', e => { examQuery = e.target.value; renderExams(); });

let currentExam = null;
$('#examsGrid').addEventListener('click', e => {
  const card = e.target.closest('.exam-card'); if (!card) return;
  const exam = exams.find(x => x.id === card.dataset.id); if (!exam) return;
  currentExam = exam;
  $('#edMeta').textContent = `${new Date(exam.date + 'T00:00:00').toLocaleDateString('pt-BR')} · ${exam.lab}`;
  $('#edTitle').textContent = exam.name;
  $('#edStatus').textContent = exam.status === 'concluido' ? 'Concluído' : exam.status === 'agendado' ? 'Agendado' : 'Pendente';
  $('#edStatus').className = `status-badge ${exam.status}`;
  $('#edSummary').textContent = exam.summary;
  const tbody = $('#edTable tbody');
  tbody.innerHTML = (exam.values || []).map(v => `<tr><td>${v.name}</td><td class="mono">${v.value}${v.unit ? ' ' + v.unit : ''}</td><td>${v.ref || '—'}</td><td><span class="mini-flag ${v.flag || 'normal'}">${FLAG_LABEL[v.flag] || v.flag || 'normal'}</span></td></tr>`).join('') || '<tr><td colspan="4" class="muted">Sem laudo ainda — exame agendado.</td></tr>';
  $('#examDetail').hidden = false;
});
$('#examDetailClose').addEventListener('click', () => { $('#examDetail').hidden = true; });
$('#examDetail').addEventListener('click', e => { if (e.target.id === 'examDetail') $('#examDetail').hidden = true; });
$('#edSendToDx').addEventListener('click', () => {
  if (!currentExam) return;
  pendingExamContext = {
    label: `${currentExam.name} (${new Date(currentExam.date + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })})`,
    detail: `${currentExam.name} (${currentExam.date}): ${currentExam.summary}`,
  };
  applyDxContextChip();
  $('#examDetail').hidden = true;
  switchScreen('screen-diagnostico');
  toast('Exame anexado — descreva o que está sentindo.');
});

/* ═════════ 8 · CHAT COM O BIP ═════════ */
const chatPanel = $('#chatPanel');
const chatMessages = $('#chatMessages');
let chatHistory = store.get('bip.chat', []);

function chatTimestamp() { return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }); }
function renderChat() {
  chatMessages.innerHTML = chatHistory.map(m => `
    <div class="msg ${m.role === 'user' ? 'msg-user' : 'msg-bip'}">${escapeHtml(m.text)}<div class="msg-time">${m.time || ''}</div></div>`).join('');
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function addChatMsg(role, text) {
  chatHistory.push({ role, text, time: chatTimestamp() });
  chatHistory = chatHistory.slice(-40);
  store.set('bip.chat', chatHistory);
  renderChat();
}
function showTyping() {
  const el = document.createElement('div');
  el.className = 'msg msg-bip'; el.id = 'typingMsg';
  el.innerHTML = '<span class="typing"><i></i><i></i></span>';
  chatMessages.appendChild(el); chatMessages.scrollTop = chatMessages.scrollHeight;
  return el;
}

async function sendChat(text) {
  const trimmed = text.trim(); if (!trimmed) return;
  addChatMsg('user', trimmed);
  const typing = showTyping();
  let reply = null;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: trimmed, history: chatHistory.slice(-8), context: { ...(lastVitals || {}), pending_tasks: $$('#periodsGrid .task.late').length, routine_score: routineScore() } }),
    });
    reply = (await res.json()).reply;
  } catch { reply = 'Ops… sinal fraco com o MCC. Tenta de novo em instantes? 📡'; }
  typing.remove();
  addChatMsg('bip', reply || 'Hmm, me perdi por aqui. Repete?');
}

$('#bipBotBtn').addEventListener('click', () => {
  const opening = chatPanel.hidden;
  chatPanel.hidden = !chatPanel.hidden;
  if (opening && !chatHistory.length) {
    const late = $$('#periodsGrid .task.late').length;
    addChatMsg('bip', late > 0
      ? `Oi, Elena! Vi que você tem ${late} ${late === 1 ? 'pendência' : 'pendências'} na rotina de hoje. Sem drama — quer que eu te ajude a começar por uma? 🚀`
      : 'Oi, Elena! Eu sou o Bip, seu copiloto de saúde. Vim ver como você está — pode perguntar qualquer coisa: rotina, vitais, sono, treino… Ou só desabafar. 🙂');
  }
  if (opening) { $('#chatInput').focus(); renderChat(); }
});
$('#chatCloseBtn').addEventListener('click', () => { chatPanel.hidden = true; });
$('#chatForm').addEventListener('submit', e => {
  e.preventDefault();
  const input = $('#chatInput');
  sendChat(input.value); input.value = '';
});
$('#chatQuick').addEventListener('click', e => {
  const chip = e.target.closest('.chip'); if (!chip) return;
  sendChat(chip.dataset.q);
});

/* ═════════ 9 · PERSONALIZAÇÃO DO AVATAR ═════════ */
// Variáveis CSS vivem no :root (document.documentElement): assim os gradientes
// do <symbol> compartilhado enxergam a cor escolhida em TODAS as instâncias.
const suitOptions = [{ a: '#1f6f6e', b: '#0e4e4d', n: 'Verde Aurora' }, { a: '#c4714b', b: '#8a4a28', n: 'Terracota Ares' }, { a: '#e8dcc8', b: '#b9a887', n: 'Areia Lunar' }, { a: '#5f4a9e', b: '#37285e', n: 'Violeta Cósmica' }, { a: '#2c4a3e', b: '#142a21', n: 'Esmeralda' }];
const skinOptions = [{ a: '#f6d3b3', b: '#ddb08a', n: 'Clara' }, { a: '#f2c4a0', b: '#d9a074', n: 'Médio-clara' }, { a: '#d9a97b', b: '#b87f52', n: 'Média' }, { a: '#c98e5a', b: '#a06a3d', n: 'Bronzeada' }, { a: '#8a5a33', b: '#5f3a1e', n: 'Escura' }, { a: '#5f3d24', b: '#3a2412', n: 'Profunda' }];
const hairStyleOptions = [{ id: 'bald', n: 'Calvo' }, { id: 'crop', n: 'Crop' }, { id: 'sweep', n: 'Topete' }, { id: 'curly', n: 'Cacheado' }, { id: 'ponytail', n: 'Rabo de cavalo' }, { id: 'bob', n: 'Bob' }, { id: 'bun', n: 'Coque' }];
const hairColorOptions = [{ c: '#1d1712', n: 'Preto' }, { c: '#3a2a1e', n: 'Castanho escuro' }, { c: '#6b4a2a', n: 'Castanho' }, { c: '#a8552f', n: 'Ruivo' }, { c: '#d9b36a', n: 'Loiro' }, { c: '#c9c9c9', n: 'Grisalho' }, { c: '#7a3fa0', n: 'Violeta fantasia' }];
const facialHairOptions = [{ id: 'none', n: 'Nenhum' }, { id: 'beard', n: 'Barba' }, { id: 'mustache', n: 'Bigode' }, { id: 'goatee', n: 'Cavanhaque' }];
const eyeColorOptions = [{ c: '#4a3423', n: 'Castanho' }, { c: '#6b4a2a', n: 'Avelã' }, { c: '#2e7d5b', n: 'Verde' }, { c: '#3f7fa6', n: 'Azul' }, { c: '#6b6b6b', n: 'Cinza' }];
const personalizeKey = 'bip.personalize';
const PERSONALIZE_DEFAULTS = { suit: 'Verde Aurora', skin: 'Médio-clara', hairStyle: 'sweep', hair: 'Castanho escuro', beard: 'none', eyes: 'Castanho', freckles: false };

function getPersonalize() { return { ...PERSONALIZE_DEFAULTS, ...store.get(personalizeKey, {}) }; }

function applyPersonalize() {
  const p = getPersonalize();
  const root = document.documentElement;
  const suit = suitOptions.find(s => s.n === p.suit) || suitOptions[0];
  const skin = skinOptions.find(s => s.n === p.skin) || skinOptions[1];
  const hair = hairColorOptions.find(s => s.n === p.hair) || hairColorOptions[1];
  const eyes = eyeColorOptions.find(s => s.n === p.eyes) || eyeColorOptions[0];
  root.style.setProperty('--suit-a', suit.a);
  root.style.setProperty('--suit-b', suit.b);
  root.style.setProperty('--skin-a', skin.a);
  root.style.setProperty('--skin-b', skin.b);
  root.style.setProperty('--hair', hair.c);
  root.style.setProperty('--iris', eyes.c);
  $$('.avatar').forEach(a => {
    a.setAttribute('data-hair', p.hairStyle);
    a.setAttribute('data-beard', p.beard);
    a.setAttribute('data-freckles', p.freckles ? 'on' : 'off');
  });
  const mark = (container, key, value) =>
    $$(`${container} [data-key="${key}"]`).forEach(el => el.setAttribute('aria-pressed', String((el.dataset.n || el.dataset.id) === value)));
  mark('#suitSwatches', 'suit', suit.n);
  mark('#skinSwatches', 'skin', skin.n);
  mark('#hairColors', 'hair', hair.n);
  mark('#eyeColors', 'eyes', eyes.n);
  mark('#hairStyles', 'hairStyle', p.hairStyle);
  mark('#facialHair', 'beard', p.beard);
  const ft = $('#frecklesToggle');
  if (ft) ft.checked = !!p.freckles;
}

function buildPersonalizePanel() {
  const mkSwatch = (opts, containerId, key) => {
    $(containerId).innerHTML = opts.map(o =>
      `<button class="swatch" style="background:${o.a ? `linear-gradient(150deg, ${o.a}, ${o.b})` : o.c}" data-key="${key}" data-n="${o.n}" aria-pressed="false" aria-label="${o.n}" title="${o.n}"></button>`
    ).join('');
  };
  mkSwatch(suitOptions, '#suitSwatches', 'suit');
  mkSwatch(skinOptions, '#skinSwatches', 'skin');
  mkSwatch(hairColorOptions, '#hairColors', 'hair');
  mkSwatch(eyeColorOptions, '#eyeColors', 'eyes');
  $('#hairStyles').innerHTML = hairStyleOptions.map(o => `<button class="pill" data-key="hairStyle" data-id="${o.id}" aria-pressed="false">${o.n}</button>`).join('');
  $('#facialHair').innerHTML = facialHairOptions.map(o => `<button class="pill" data-key="beard" data-id="${o.id}" aria-pressed="false">${o.n}</button>`).join('');

  $$('#suitSwatches .swatch, #skinSwatches .swatch, #hairColors .swatch, #eyeColors .swatch').forEach(sw =>
    sw.addEventListener('click', () => {
      const p = getPersonalize();
      p[sw.dataset.key] = sw.dataset.n;
      store.set(personalizeKey, p);
      applyPersonalize();
    }));
  $$('#hairStyles .pill, #facialHair .pill').forEach(pi =>
    pi.addEventListener('click', () => {
      const p = getPersonalize();
      p[pi.dataset.key] = pi.dataset.id;
      store.set(personalizeKey, p);
      applyPersonalize();
    }));
  $('#frecklesToggle').addEventListener('change', e => {
    const p = getPersonalize();
    p.freckles = e.target.checked;
    store.set(personalizeKey, p);
    applyPersonalize();
  });
}
$('#personalizeBtn').addEventListener('click', () => {
  const panel = $('#personalizePanel');
  panel.hidden = !panel.hidden;
  $('#personalizeBtn').setAttribute('aria-expanded', String(!panel.hidden));
});
$('#personalizeReset').addEventListener('click', () => { store.del(personalizeKey); applyPersonalize(); toast('Avatar restaurado ao padrão Aurora.'); });

/* ═════════ 10 · INIT ═════════ */
// O <symbol>#avatarBody serve de template; clonamos o conteúdo para dentro de
// cada <svg class="avatar"> para que os atributos data-* controlem
// cabelo/barba/sardas/humor via CSS (com <use> os seletores não alcançavam os clones).
function hydrateAvatars() {
  const tpl = document.getElementById('avatarBody');
  if (!tpl) return;
  const html = tpl.innerHTML;
  $$('.avatar').forEach(a => { a.innerHTML = html; });
}

async function init() {
  hydrateAvatars();
  buildPersonalizePanel();
  applyPersonalize();
  tickClock();
  setInterval(tickClock, 1000);
  setInterval(refreshVitals, 5000);

  await refreshVitals();
  try { routineTemplate = (await (await fetch('/api/routines')).json()).periods; } catch { routineTemplate = []; }
  try { achievements = (await (await fetch('/api/achievements')).json()).achievements; } catch { achievements = []; }
  try {
    const stock = (await (await fetch('/api/stock')).json()).items;
    $('#stockList').innerHTML = stock.map(i => `<li class="stock-item"><b>${i.name}</b>${i.qty != null ? ` · ${i.qty} un.` : ''}<small>${i.for}</small></li>`).join('');
  } catch {}

  buildRoutines();
  persistHistory();          // registra snapshot do dia e dispara verificação de conquistas
  updateRoutinesUI();
  evaluateAchievements(true);
  await loadExams();

  $('#dxHistoryCount').textContent = String((store.get('bip.diagnoses', []) || []).length);
  renderChat();
  $('#routineDate').textContent = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
}
init();
