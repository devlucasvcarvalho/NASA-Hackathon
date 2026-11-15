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
// definições de cards de sinais vitais (reconstruídas por idioma)
function vitalDefs() {
  const T = window.t ? window.t : (k) => k;
  return [
  { key: 'heart_rate', label: T('vital.hr'), unit: 'bpm', iconClass: '', delta: T('vital.delta_hr'), deltaKind: 'ok', status: T('vital.status.normal'), statusKind: 'ok', sparkSeed: 1.6, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20.3s-6.6-4.4-9.1-9.1C1.7 8.6 3.8 6 7 6c2.1 0 3.7 1.2 5 3 1.3-1.8 2.9-3 5-3 3.2 0 5.3 2.6 4.1 5.2-2.5 4.7-9.1 9.1-9.1 9.1Z"/></svg>' },
  { key: 'spo2', label: T('vital.spo2'), unit: '%', iconClass: 'sky', delta: T('vital.delta_spo2'), deltaKind: 'ok', status: T('vital.status.normal'), statusKind: 'ok', sparkSeed: 4.1, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c3.2 4.4 5.4 7.7 5.4 11a5.4 5.4 0 0 1-10.8 0C6.6 10.7 8.8 7.4 12 3Z"/><path d="M9.5 14.5a2.6 2.6 0 0 0 2.5 2.7"/></svg>' },
  { key: 'sleep', label: 'Sleep', unit: 'h last night', iconClass: 'indigo', delta: 'Debt-free · target 7.5 h', deltaKind: 'ok', status: 'OK', statusKind: 'ok', meter: true, meterRatio: true, sparkSeed: 0, sleepBtn: true, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.4 13.6A8.8 8.8 0 1 1 10.4 3.6a7.1 7.1 0 0 0 10 10Z"/><path d="M17 3.5h3l-3 3h3"/></svg>' },
  { key: 'radiation', label: T('vital.rad'), unit: 'mSv/dia', iconClass: 'gold', delta: T('vital.delta_rad'), deltaKind: 'warn', status: T('vital.status.watch'), statusKind: 'watch', meter: true, meterMax: 180, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/><path d="M12 2a10 10 0 0 1 8.7 5.1l-4.4 2.5M12 22a10 10 0 0 1-8.7-5.1l4.4-2.5M22 12a10 10 0 0 1-5 8.7l-2.5-4.4M2 12a10 10 0 0 1 5-8.7l2.5 4.4"/></svg>' },
  { key: 'bp', label: T('vital.bp'), unit: 'mmHg', iconClass: 'terra', delta: T('vital.delta_bp'), deltaKind: 'ok', status: T('vital.status.normal'), statusKind: 'ok', sparkSeed: 2.8, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4a8 8 0 0 1 8 8h-2.4"/><path d="M12 4a8 8 0 0 0-8 8h2.4"/><path d="M12 12l3.4-3.4"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/></svg>' },
  { key: 'temperature', label: T('vital.temp'), unit: '°C', iconClass: '', delta: T('vital.delta_temp'), deltaKind: 'ok', status: T('vital.status.normal'), statusKind: 'ok', sparkSeed: 5.3, icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13.6V5a2 2 0 0 1 4 0v8.6a4.5 4.5 0 1 1-4 0Z"/><circle cx="12" cy="17.5" r="1.4" fill="currentColor" stroke="none"/></svg>' },
  ];
}

function renderVitals(v) {
  lastVitals = v;
  const T = window.t;
  const sleep = lastSleep && lastSleep.nights && lastSleep.nights.length ? lastSleep.nights[lastSleep.nights.length - 1] : null;
  $('#vitalsGrid').innerHTML = vitalDefs().map(def => {
    let valueHtml, footExtra = '', opening = '<article class="vital-card">', closing = '</article>';
    if (def.key === 'bp') {
      valueHtml = `${Math.round(v.bp_sys)}<small>/</small>${Math.round(v.bp_dia)}<small> mmHg</small>`;
    } else if (def.key === 'radiation') {
      valueHtml = `${v.radiation_dose_rate.toFixed(2)}<small> mSv/dia</small>`;
      const pct = Math.min(100, (v.radiation_cumulative / 180) * 100);
      footExtra = `<div class="meter radiation" title="${v.radiation_cumulative.toFixed(1)} mSv / 180 mSv"><span style="width:${pct.toFixed(1)}%"></span></div><div class="vital-delta delta-warn" style="margin-top:4px">${v.radiation_cumulative.toFixed(1)} mSv · ${pct.toFixed(1)}% ${T('vital.rad_of_limit')}</div>`;
    } else if (def.key === 'sleep') {
      const hours = sleep ? sleep.hours : (v.sleep_hours || 7.0);
      const ratio = Math.min(100, (hours / 7.5) * 100);
      const deep = sleep ? sleep.deep_pct : 18;
      const debt = sleep ? computeWeekDebt(lastSleep.nights) : 0;
      const status = debt <= 0 ? 'OK' : 'DEBT';
      const statusKind = debt <= 0 ? 'ok' : 'watch';
      const fmt = fmtSleepHours(hours);
      valueHtml = `${fmt}`;
      footExtra = `<div class="meter sleep-meter" title="Mission target: 7.5 h / night"><span style="width:${ratio.toFixed(1)}%"></span></div><div class="vital-delta delta-ok" style="margin-top:4px">Deep ${deep}%</div>`;
      opening = `<button class="vital-card vital-card-btn" data-open-sleep type="button" aria-label="Open sleep and recovery details">`;
      closing = `</button>`;
      return `${opening}
        <div class="vital-top"><span class="vital-icon indigo">${def.icon}</span><span class="vital-label">${def.label}</span><span class="vital-open-hint" aria-hidden="true"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg></span></div>
        <div class="vital-value">${valueHtml}<small> h last night</small></div>
        ${footExtra}
        <div class="vital-foot"><span class="vital-delta delta-${statusKind === 'ok' ? 'ok' : 'warn'}">${debt <= 0 ? 'On target' : '−' + fmtSleepHours(debt) + ' debt'}</span><span class="vital-status ${statusKind}">${status}</span></div>
      ${closing}`;
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
function moonPhaseIdx(p) {
  if (p < 0.033 || p > 0.967) return 'moon.new';
  if (p < 0.216) return 'moon.waxcres';
  if (p < 0.283) return 'moon.waxq';
  if (p < 0.466) return 'moon.waxgib';
  if (p < 0.534) return 'moon.full';
  if (p < 0.717) return 'moon.waningib';
  if (p < 0.784) return 'moon.waningq';
  return 'moon.waningc';
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
  const T = window.t;
  const locale = window.LOCALES[window.BIP_LANG];
  const isMars = currentTz === 'mars';
  let hour, hhmmss, dateLabel;
  if (isMars) {
    const mn = marsNow();
    hour = mn.hour; hhmmss = mn.hhmmss;
    dateLabel = `Sol ${mn.sol} · Ares`;
    $('#stripMoon').textContent = `Sol ${mn.sol}`;
    $('#stripMoonName').textContent = T('strip.sol_label');
  } else {
    const en = earthNow(TZ_META[currentTz].tz);
    hour = en.hour; hhmmss = en.hhmmss;
    dateLabel = new Intl.DateTimeFormat(locale, { timeZone: TZ_META[currentTz].tz, weekday: 'short', day: '2-digit', month: 'short' }).format(new Date()).replaceAll('.', '');
    const ph = moonPhase();
    $('#stripMoon').textContent = `${Math.round(ph.illum * 100)}%`;
    $('#stripMoonName').textContent = T(moonPhaseIdx(ph.p)).toUpperCase();
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

  $('#greetName').textContent = `${hour < 6 ? T('greet.dawn') : hour < 12 ? T('greet.morning') : hour < 18 ? T('greet.afternoon') : T('greet.night')}, Elena`;
  const rd = $('#routineDate');
  if (rd) rd.textContent = isMars ? `Sol ${marsNow().sol} · Base Ares`
    : new Intl.DateTimeFormat(locale, { timeZone: TZ_META[currentTz].tz, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
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

let routinesBound = false;
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
            <span class="task-meta"><span class="task-time">${t.time}</span><span class="late-tag" hidden>${window.t('rotina.late_tag')}</span></span>
            <span class="task-hint">${t.hint}</span>
          </span>
        </label>`).join('')}
    </div>`).join('');

  if (!routinesBound) {
    routinesBound = true;
    grid.addEventListener('change', e => {
      const id = e.target.dataset.id; if (!id) return;
      if (e.target.checked) { if (!doneIds.includes(id)) doneIds.push(id); }
      else doneIds = doneIds.filter(x => x !== id);
      store.set(ROUTINE_KEY(), doneIds);
      persistHistory();
      updateRoutinesUI();
    });
  }
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
      toast(`${window.t('toast.achievement')}${a.title}!`);
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
  currentMood = mood;
  $$('.avatar').forEach(a => { if (!a.classList.contains('react-wave') && !a.classList.contains('react-hop') && !a.classList.contains('react-laugh')) a.setAttribute('data-mood', mood); });
  $('#moodLine').textContent = window.t(`home.mood_${mood}`);
  $('#moodCallout').textContent = window.t(`rotina.callout_${mood}`);

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
    chip.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 3h6v4a4 4 0 0 1-6 0Z"/><path d="M9 7H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3"/></svg><span>${pendingExamContext.label} ${window.t('dx.attached')}</span>`;
  } else { chip.hidden = true; }
}

$('#dxSuggestChips').addEventListener('click', e => {
  const btn = e.target.closest('.chip'); if (!btn) return;
  $('#dxText').value = window.t(btn.dataset.fillKey);
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
  if (text.length < 4 && !dxImageDataUrl) { toast(window.t('dx.describe_first')); return; }
  showDxView('loading');
  animateScanSteps();

  const chat = store.get('bip.chat', []);
  const chatSummary = chat.filter(m => m.role === 'user').slice(-3).map(m => m.text).join(' | ');
  const v = lastVitals || {};
  // exames relevantes no idioma da interface
  const flagged = (exams || []).filter(e => (e.values || []).some(x => x.flag && x.flag !== 'normal')).slice(0, 4);
  const examSummary = flagged.map(e => `${e.name}: ${e.summary}`).join(' · ');
  const context = {
    heart_rate: v.heart_rate ? `${Math.round(v.heart_rate)} bpm` : undefined,
    spo2: v.spo2 ? `${v.spo2}%` : undefined,
    bp: v.bp_sys ? `${Math.round(v.bp_sys)}/${Math.round(v.bp_dia)} mmHg` : undefined,
    temperature: v.temperature ? `${v.temperature} °C` : undefined,
    sleep_hours: '7.2 h',
    radiation_cumulative: v.radiation_cumulative ? `${v.radiation_cumulative.toFixed(1)} mSv` : undefined,
    routine_score: routineScore(),
    chat_summary: chatSummary || undefined,
    exams: examSummary || undefined,
    exam_sent: pendingExamContext ? pendingExamContext.detail : undefined,
    crew: 'Elena Ricci · Flight Engineer · SpEx-47 · Expedition AURORA-7',
  };
  Object.keys(context).forEach(k => context[k] === undefined && delete context[k]);

  let result = null;
  try {
    const res = await fetch('/api/diagnose', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text || `(${window.t('dx.image_attached')})`, image: dxImageDataUrl, context, lang: window.BIP_LANG }),
    });
    result = await res.json();
  } catch (e) { console.error(e); }

  await new Promise(r => setTimeout(r, Math.max(0, 2400 - 0))); // garante a animação mínima
  if (!result || !result.severity) {
    showDxView('form');
    toast(window.t('dx.fail'));
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

const TRIAGE_KEY = { leve: 'leve', moderado: 'mod', grave: 'grave' };
const SEV_ICON = {
  leve: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  moderado: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v5"/><path d="M12 16.5h.01"/><circle cx="12" cy="12" r="9.2"/></svg>',
  grave: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 10v4.5M12 17.2h.01"/></svg>',
};

function renderDiagnosisResult(d) {
  showDxView('result');
  const sev = (d.severity || 'leve').toLowerCase();
  const key = TRIAGE_KEY[sev] || 'leve';
  const T = window.t;
  const banner = $('#triageBanner');
  banner.dataset.level = sev;
  $('#triageIcon').innerHTML = SEV_ICON[sev] || SEV_ICON.leve;
  $('#triageTitle').textContent = T(`triage.${key}_title`);
  $('#triageDetail').textContent = T(`triage.${key}_detail`);

  const locale = window.LOCALES[window.BIP_LANG];
  $('#dxAnalyzedAt').textContent = `${T('dx.analyzed_at')} ${d.analyzed_at ? new Date(d.analyzed_at).toLocaleString(locale) : T('dx.new')}${d.image_attached ? ' · ' + T('dx.image_attached') : ''}`;
  $('#dxResultTitle').textContent = d.title || T('dx.history_title');
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
          ${p.dose ? `<span><b>${window.t('rx.dose')}</b> ${p.dose}</span>` : ''}
          ${p.frequency ? `<span><b>${window.t('rx.freq')}</b> ${p.frequency}</span>` : ''}
          ${p.duration ? `<span><b>${window.t('rx.dur')}</b> ${p.duration}</span>` : ''}
        </div>
        ${p.instructions ? `<small>${p.instructions}</small>` : ''}
      </span>
    </div>`).join('');

  $('#dxProcedures').innerHTML = (d.procedures || []).map(p => `<li>${p}</li>`).join('');
  $('#dxMonitoring').textContent = d.monitoring || '—';
  $('#dxRedFlags').innerHTML = (d.red_flags || []).map(r => `<li>${r}</li>`).join('');
  $('#dxDisclaimer').textContent = d.disclaimer || window.t('rx.disclaimer_default');
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
    list.innerHTML = `<div class="history-empty">${window.t('dx.empty')}</div>`;
    return;
  }
  list.innerHTML = diagnoses.map((d, i) => `
    <button class="history-item" data-idx="${diagnoses.length - 1 - i}">
      <span class="history-sev ${d.severity || 'leve'}"></span>
      <span><h4>${d.title || window.t('dx.analyzed_at')}</h4>
      <p>${d.analyzed_at ? new Date(d.analyzed_at).toLocaleString(window.LOCALES[window.BIP_LANG]) : ''} · “${(d.query || '').slice(0, 90)}${(d.query || '').length > 90 ? '…' : ''}”</p></span>
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
let examFilter = 'all';
let examQuery = '';
const examFlagLabel = (flag) => window.t(`exams.flag_${flag || 'normal'}`);
const examStatusLabel = (status) => status === 'concluido' ? window.t('exams.concluido') : status === 'agendado' ? window.t('exams.agendado') : window.t('exams.pendente');

async function loadExams() {
  try { exams = (await (await fetch(`/api/exams?lang=${window.BIP_LANG}`)).json()).exams; } catch { exams = []; }
  const allLabel = window.t('exams.all');
  const cats = ['all', ...new Set(exams.map(e => e.category))];
  $('#examFilters').innerHTML = cats.map(c => `<button class="filter-chip${c === examFilter ? ' is-active' : ''}" data-cat="${c}">${c === 'all' ? allLabel : c}</button>`).join('');
  renderExams();
}
function renderExams() {
  const locale = window.LOCALES[window.BIP_LANG];
  const q = examQuery.trim().toLowerCase();
  const filtered = exams.filter(e => (examFilter === 'all' || e.category === examFilter) &&
    (!q || `${e.name} ${e.summary} ${e.date}`.toLowerCase().includes(q)));
  $('#examsGrid').innerHTML = filtered.map(e => {
    const flagged = (e.values || []).filter(v => v.flag && v.flag !== 'normal');
    return `<button class="exam-card" data-id="${e.id}">
      <div class="exam-card-top"><h3>${e.name}</h3><span class="exam-cat">${e.category}</span></div>
      <span class="exam-date mono">${new Date(e.date + 'T00:00:00').toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' })}</span>
      <p class="exam-summary">${e.summary}</p>
      ${flagged.length ? `<div class="flag-row">${flagged.map(f => `<span class="mini-flag ${f.flag}">${f.name}: ${examFlagLabel(f.flag)}</span>`).join('')}</div>` : ''}
      <span class="status-badge ${e.status}">${examStatusLabel(e.status)}</span>
    </button>`;
  }).join('') || `<p class="muted" style="grid-column:1/-1;text-align:center;padding:40px">${window.t('exams.empty')}</p>`;
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
  const locale = window.LOCALES[window.BIP_LANG];
  const dt = new Date(exam.date + 'T00:00:00');
  $('#edMeta').textContent = `${dt.toLocaleDateString(locale)} · ${exam.lab}`;
  $('#edTitle').textContent = exam.name;
  $('#edStatus').textContent = examStatusLabel(exam.status);
  $('#edStatus').className = `status-badge ${exam.status}`;
  $('#edSummary').textContent = exam.summary;
  const tbody = $('#edTable tbody');
  tbody.innerHTML = (exam.values || []).map(v => `<tr><td>${v.name}</td><td class="mono">${v.value}${v.unit ? ' ' + v.unit : ''}</td><td>${v.ref || '—'}</td><td><span class="mini-flag ${v.flag || 'normal'}">${examFlagLabel(v.flag)}</span></td></tr>`).join('') || `<tr><td colspan="4" class="muted">${window.t('exams.no_report')}</td></tr>`;
  $('#examDetail').hidden = false;
});
$('#examDetailClose').addEventListener('click', () => { $('#examDetail').hidden = true; });
$('#examDetail').addEventListener('click', e => { if (e.target.id === 'examDetail') $('#examDetail').hidden = true; });
$('#edSendToDx').addEventListener('click', () => {
  if (!currentExam) return;
  const locale = window.LOCALES[window.BIP_LANG];
  pendingExamContext = {
    label: `${currentExam.name} (${new Date(currentExam.date + 'T00:00:00').toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })})`,
    detail: `${currentExam.name} (${currentExam.date}): ${currentExam.summary}`,
  };
  applyDxContextChip();
  $('#examDetail').hidden = true;
  switchScreen('screen-diagnostico');
  toast(window.t('exams.sent'));
});

/* ═════════ 8 · CHAT COM O B.I.P ═════════ */
const chatPanel = $('#chatPanel');
const chatMessages = $('#chatMessages');
const chatQuick = $('#chatQuick');
let chatHistory = store.get('bip.chat', []);

const REDFLAG = /(chest pain|can'?t breathe|cannot breathe|shortness of breath|hardly breathing|bleeding|blood loss|faint|collapse|passed out|severe pain|suicid|self.?harm|panic attack|vision loss|can'?t see)/i;
const PHYS = { great: ['Full power', 0], good: ['Good enough', 1], off: ['A little off', 2], rough: ['Rough', 3] };
const SYMPTOM = { none: ['None', 0], headache: ['Headache', 1], nausea: ['Nausea', 1], dizziness: ['Dizziness', 1], fatigue: ['Fatigue', 1], other: ['Something else', 1] };
const MENTAL = { calm: ['Calm and focused', 0], tense: ['Tense', 1], over: ['Overwhelmed', 2], low: ['Low and flat', 3] };
const SLEEP = { great: ['Great', 0], ok: ['Okay', 1], poor: ['Poorly', 2], vpoor: ['Very poorly', 3] };
const CI_TABLES = { phys: PHYS, symptom: SYMPTOM, mental: MENTAL, sleep: SLEEP };

const DEFAULT_CHIPS = [
  { text: 'How am I really doing?', ci: '__start__', cls: 'chip-start' },
  { text: 'Tell me a joke', qKey: 'chat.q_joke' },
  { text: "Today's pending", qKey: 'chat.q_today' },
  { text: 'I have a headache', qKey: 'chat.q_headache' },
  { text: 'Bad sleep', qKey: 'chat.q_sleep' },
  { text: 'Water goal', qKey: 'chat.q_water' },
];

const checkIn = { step: null, phys: null, symptom: null, mental: null, sleep: null, physScore: 0, symptomScore: 0, mentalScore: 0, sleepScore: 0 };

function chatTimestamp() { return new Date().toLocaleTimeString(window.LOCALES[window.BIP_LANG], { hour: '2-digit', minute: '2-digit' }); }
function renderChat() {
  chatMessages.innerHTML = '';
  chatHistory.forEach(m => chatMessages.appendChild(buildMsgEl(m)));
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function buildMsgEl(m) {
  const cls = m.role === 'user' ? 'msg-user' : m.alert ? 'msg-alert' : 'msg-bip';
  const el = document.createElement('div');
  el.className = `msg ${cls}`;
  el.innerHTML = `${escapeHtml(m.text)}<div class="msg-time">${escapeHtml(m.time || '')}</div>`;
  return el;
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function appendMsg(m) {
  chatMessages.appendChild(buildMsgEl(m));
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function addChatMsg(role, text, opts = {}) {
  chatHistory.push({ role, text, time: chatTimestamp(), ...(opts.alert ? { alert: true } : {}) });
  chatHistory = chatHistory.slice(-40);
  store.set('bip.chat', chatHistory);
  appendMsg(chatHistory[chatHistory.length - 1]);
}
function renderChips(list) {
  chatQuick.innerHTML = list.map(c => `<button class="chip${c.cls ? ' ' + c.cls : ''}" ${c.ci ? `data-ci="${c.ci}"` : ''} ${c.qKey ? `data-q-key="${c.qKey}"` : ''}>${escapeHtml(c.text)}</button>`).join('');
}
function showTyping() {
  const el = document.createElement('div');
  el.className = 'msg msg-bip'; el.id = 'typingMsg';
  el.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
  chatMessages.appendChild(el); chatMessages.scrollTop = chatMessages.scrollHeight;
  return el;
}

function bipSay(text, delay = 720, opts = {}) {
  return new Promise(resolve => {
    const typing = showTyping();
    setTimeout(() => {
      typing.remove();
      addChatMsg('bip', text, opts);
      resolve();
    }, delay);
  });
}

const CI_QUESTIONS = {
  phys: 'Before anything else — how is the body treating you today? Answer honestly.',
  symptom: 'Got it. Any physical symptoms showing up right now? Headache, nausea, dizziness, fatigue…',
  mental: 'And the other half of the mission — how is your headspace? Calm, tense, overwhelmed, flat…',
  sleep: 'Last one: how did you sleep last night?',
};

function chipsFor(step) {
  return Object.entries(CI_TABLES[step]).map(([key, [label]]) => ({ text: label, ci: key }));
}

async function askCheckIn(step, delay = 720) {
  checkIn.step = step;
  await bipSay(CI_QUESTIONS[step], delay);
  renderChips(chipsFor(step));
}

function startCheckIn() {
  Object.assign(checkIn, { step: null, phys: null, symptom: null, mental: null, sleep: null, physScore: 0, symptomScore: 0, mentalScore: 0, sleepScore: 0 });
  bipSay('Hey, Elena — good to see you. Ask me anything: the mission, jokes, life… or let me do a quick head-to-toe, body and mind.', 600)
    .then(() => askCheckIn('phys', 750));
}

const CI_KEYWORDS = {
  phys: [[/rough|terrible|awful|awfully|bad|ache|pain|sick|ill|exhaust|weak|fever/, 'rough'], [/off|strange|weird|not great|meh|low energy|tired|drained/, 'off'], [/great|full power|amazing|perfect|awesome|fantastic/, 'great']],
  symptom: [[/headache|head hurts|migraine/, 'headache'], [/nause|queasy|throw ?up|threw up/, 'nausea'], [/dizz|lighthead|spinning/, 'dizziness'], [/fatigue|tired|exhausted|no energy/, 'fatigue'], [/none|nothing|no symptom|all good/, 'none']],
  mental: [[/overwhelm|stress|swamped|too much|panic|anxious/, 'over'], [/tense|antsy|on edge|irritated/, 'tense'], [/low|flat|down|sad|depress|empty|lonely/, 'low'], [/calm|fine|good|great|focused|motivat|ok/, 'calm']],
  sleep: [[/great|amazing|slept well|full night/, 'great'], [/ok|okay|alright|not bad/, 'ok'], [/barely|restless|poor|bad|badly|poorly/, 'poor'], [/very poorly|terrible|no sleep|insomn|didn'?t sleep|nightmare/, 'vpoor']],
};

function classify(text, step) {
  const t = String(text).toLowerCase();
  for (const [re, key] of (CI_KEYWORDS[step] || [])) if (re.test(t)) return key;
  return 'other';
}

async function finishCheckIn() {
  const { phys, symptom, mental, sleep } = checkIn;
  const score = checkIn.physScore + checkIn.symptomScore + checkIn.mentalScore + checkIn.sleepScore;
  const level = score <= 2
    ? 'you look mission-ready.'
    : score <= 6
      ? 'you are carrying a bit more than usual — and I notice it.'
      : 'this is heavier than “fine”, and I am taking it seriously.';
  const recs = [];
  if (symptom === 'Headache') recs.push('half a liter of water and 15 minutes off screens');
  if (symptom === 'Nausea') recs.push('small sips of water and a light snack from the kit');
  if (symptom === 'Dizziness') recs.push('sit down, hydrate, re-check your blood pressure');
  if (symptom === 'Fatigue') recs.push('a real 20-minute rest — not “eyes open, lying down”');
  if (sleep === 'Poorly' || sleep === 'Very poorly') recs.push('dim the cabin 30 minutes before bed and skip the late EVA sim');
  if (mental === 'Overwhelmed' || mental === 'Low and flat') recs.push('two minutes of 4-7-8 breathing — and it is not weak to say the word at MCC');
  if (phys === 'Rough') recs.push('skip the workout block tonight; rest is an order from your favorite bot');
  if (!recs.length) recs.push('hydrate, move, log it — carry on being the mission');
  checkIn.step = null;
  await bipSay(`Here is what I am logging in your daily entry (SOL 455):\n• Body → ${phys}\n• Symptoms → ${symptom}\n• Mind → ${mental}\n• Sleep → ${sleep}`, 850);
  await bipSay(`My honest read: ${level} Start with ${recs.join('; ')}. If it sticks around past the next meal, bring it up at the MCC window (15:10–15:45) — that is what they are there for.`, 950, score >= 7 ? { alert: true } : {});
  renderChips(DEFAULT_CHIPS);
}

async function handleCheckIn(text, chipKey) {
  const step = checkIn.step;
  const table = CI_TABLES[step];
  const key = chipKey || classify(text, step);
  const [label, score] = (table[key] || table.other || table.none || ['Something else', 1]);
  checkIn[step] = label;
  checkIn[`${step}Score`] = score;
  const order = ['phys', 'symptom', 'mental', 'sleep'];
  const next = order[order.indexOf(step) + 1];
  if (next) return askCheckIn(next, 800);
  return finishCheckIn();
}

async function sendChat(text) {
  const trimmed = text.trim(); if (!trimmed) return;
  addChatMsg('user', trimmed);
  if (REDFLAG.test(trimmed)) {
    checkIn.step = null;
    renderChips(DEFAULT_CHIPS);
    return bipSay('Stop. That is a red flag, not a check-in item. Stop the activity, sit down somewhere safe, and contact Mission Control now — the 15:10–15:45 telemedicine window or the emergency channel. I am flagging this as urgent on your log. Use the kit stabilization protocol until you are through to MCC.', 900, { alert: true });
  }
  if (checkIn.step) return handleCheckIn(trimmed);
  const typing = showTyping();
  let reply = null;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: trimmed, history: chatHistory.slice(-8), context: { ...(lastVitals || {}), pending_tasks: $$('#periodsGrid .task.late').length, routine_score: routineScore() }, lang: window.BIP_LANG }),
    });
    reply = (await res.json()).reply;
  } catch { reply = window.t('chat.offline'); }
  typing.remove();
  addChatMsg('bip', reply || 'Hmm, me perdi por aqui. Repete?');
}

function isChatOpen() { return !chatPanel.hidden; }
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── B.I.P voando do canto para o chat (FLIP) ──
function flyClone(fromRect, toRect, opts = {}) {
  const floatBtn = $('#bipBotBtn');
  const clone = document.createElement('div');
  clone.className = 'bip-fly';
  clone.innerHTML = '<svg viewBox="0 0 96 112" aria-hidden="true"><use href="#bipBot"></use></svg>';
  clone.style.left = `${fromRect.left}px`;
  clone.style.top = `${fromRect.top}px`;
  clone.style.width = `${fromRect.width}px`;
  clone.style.height = `${fromRect.height}px`;
  document.body.appendChild(clone);

  const dx = (toRect.left + toRect.width / 2) - (fromRect.left + fromRect.width / 2);
  const dy = (toRect.top + toRect.height / 2) - (fromRect.top + fromRect.height / 2);
  const scale = Math.min(toRect.width / fromRect.width, 7) * (opts.big ? 1.02 : 1);

  if (prefersReducedMotion) {
    clone.remove();
    return Promise.resolve();
  }

  const anim = clone.animate([
    { transform: 'translate(0px, 0px) scale(1) rotate(0deg)', offset: 0 },
    { transform: `translate(${dx * 0.36}px, ${dy * 0.6 - 110}px) scale(${scale * 0.92}) rotate(-11deg)`, offset: 0.36 },
    { transform: `translate(${dx * 0.82}px, ${dy * 0.92 - 26}px) scale(${scale * 1.06}) rotate(7deg)`, offset: 0.82 },
    { transform: `translate(${dx}px, ${dy}px) scale(${scale}) rotate(0deg)`, offset: 1 },
  ], { duration: 760, easing: 'cubic-bezier(.28,.95,.32,1)', fill: 'forwards' });

  // faíscas de comemoração no pouso
  const sparks = document.createElement('div');
  sparks.className = 'bip-sparks';
  sparks.innerHTML = '<i></i><i></i><i></i><i></i><i></i><i></i>';
  sparks.style.left = `${fromRect.left + fromRect.width / 2}px`;
  sparks.style.top = `${fromRect.top + fromRect.height / 2}px`;
  document.body.appendChild(sparks);

  return anim.finished.then(() => {
    // solta as faíscas na posição final
    sparks.style.left = `${toRect.left + toRect.width / 2}px`;
    sparks.style.top = `${toRect.top + toRect.height / 2}px`;
    sparks.classList.add('bip-sparks-burst');
    sparks.style.setProperty('--dx', `${dx}px`);
    sparks.style.setProperty('--dy', `${dy}px`);
    clone.remove();
    setTimeout(() => sparks.remove(), 650);
  }).catch(() => { clone.remove(); sparks.remove(); });
}

function openChat() {
  const floatBtn = $('#bipBotBtn');
  const heroRobot = $('#chatHeroRobot');
  const floatRect = floatBtn.getBoundingClientRect();

  chatPanel.hidden = false;
  document.body.classList.add('chat-open');
  renderChat();
  if (!chatHistory.length) startCheckIn();
  else renderChips(DEFAULT_CHIPS);

  if (prefersReducedMotion) {
    heroRobot.style.visibility = 'visible';
    $('#chatHero').classList.add('bip-landed');
    floatBtn.classList.add('bip-ghost');
    setTimeout(() => $('#chatInput').focus(), 80);
    return;
  }

  const heroRect = heroRobot.getBoundingClientRect();
  heroRobot.style.visibility = 'hidden';
  $('#chatHero').classList.remove('bip-landed');
  floatBtn.classList.add('bip-ghost');

  flyClone(floatRect, heroRect).then(() => {
    $('#chatHero').classList.add('bip-landed');
    heroRobot.style.visibility = 'visible';
  });

  setTimeout(() => $('#chatInput').focus(), 130);
}

function closeChat() {
  const heroRobot = $('#chatHeroRobot');
  const floatBtn = $('#bipBotBtn');

  if (prefersReducedMotion) {
    chatPanel.hidden = true;
    document.body.classList.remove('chat-open');
    heroRobot.style.visibility = 'visible';
    floatBtn.classList.remove('bip-ghost');
    return;
  }

  const heroRect = heroRobot.getBoundingClientRect();
  const floatRect = floatBtn.getBoundingClientRect();
  $('#chatHero').classList.remove('bip-landed');
  heroRobot.style.visibility = 'hidden';
  floatBtn.classList.remove('bip-ghost');

  flyClone(heroRect, floatRect, { big: true });
  chatPanel.hidden = true;
  document.body.classList.remove('chat-open');
}

$('#bipBotBtn').addEventListener('click', () => { isChatOpen() ? closeChat() : openChat(); });
$('#chatCloseBtn').addEventListener('click', closeChat);
chatPanel.addEventListener('click', e => { if (e.target === chatPanel) closeChat(); });
window.addEventListener('keydown', e => { if (e.key === 'Escape' && isChatOpen()) closeChat(); });
$('#chatForm').addEventListener('submit', e => {
  e.preventDefault();
  const input = $('#chatInput');
  sendChat(input.value); input.value = '';
});
$('#chatQuick').addEventListener('click', e => {
  const chip = e.target.closest('.chip'); if (!chip) return;
  if (chip.dataset.ci === '__start__') { addChatMsg('user', chip.textContent.trim()); return startCheckIn(); }
  if (chip.dataset.ci && checkIn.step) { addChatMsg('user', chip.textContent.trim()); return handleCheckIn('', chip.dataset.ci); }
  if (chip.dataset.qKey) return sendChat(window.t(chip.dataset.qKey));
});
renderChips(DEFAULT_CHIPS);

/* ═════════ 9 · PERSONALIZAÇÃO DO AVATAR ═════════ */
// Variáveis CSS vivem no :root (document.documentElement): assim os gradientes
// do <symbol> compartilhado enxergam a cor escolhida em TODAS as instâncias.
const outfitOptions = ['astronaut', 'casual', 'voo', 'cargo'].map(id => ({ id, tkey: `outfit.${id}` }));
const skinOptions = [
  { id: 'clara', a: '#f6d3b3', b: '#ddb08a', tkey: 'skin.clara' },
  { id: 'medio', a: '#f2c4a0', b: '#d9a074', tkey: 'skin.medio' },
  { id: 'media', a: '#d9a97b', b: '#b87f52', tkey: 'skin.media' },
  { id: 'bronze', a: '#c98e5a', b: '#a06a3d', tkey: 'skin.bronze' },
  { id: 'escura', a: '#8a5a33', b: '#5f3a1e', tkey: 'skin.escura' },
  { id: 'profunda', a: '#5f3d24', b: '#3a2412', tkey: 'skin.profunda' },
];
const hairStyleOptions = ['bald', 'crop', 'sweep', 'curly', 'ponytail', 'bob', 'bun'].map(id => ({ id, tkey: `hairstyle.${id}` }));
const hairColorOptions = [
  { id: 'preto', c: '#1d1712', tkey: 'hairc.preto' },
  { id: 'escuro', c: '#3a2a1e', tkey: 'hairc.escuro' },
  { id: 'castanho', c: '#6b4a2a', tkey: 'hairc.castanho' },
  { id: 'ruivo', c: '#a8552f', tkey: 'hairc.ruivo' },
  { id: 'loiro', c: '#d9b36a', tkey: 'hairc.loiro' },
  { id: 'grisalho', c: '#c9c9c9', tkey: 'hairc.grisalho' },
  { id: 'violeta', c: '#7a3fa0', tkey: 'hairc.violeta' },
];
const facialHairOptions = ['none', 'beard', 'mustache', 'goatee'].map(id => ({ id, tkey: `beard.${id}` }));
const eyeColorOptions = [
  { id: 'castanho', c: '#4a3423', tkey: 'eye.castanho' },
  { id: 'avela', c: '#6b4a2a', tkey: 'eye.avela' },
  { id: 'verde', c: '#2e7d5b', tkey: 'eye.verde' },
  { id: 'azul', c: '#3f7fa6', tkey: 'eye.azul' },
  { id: 'cinza', c: '#6b6b6b', tkey: 'eye.cinza' },
];
const personalizeKey = 'bip.personalize';
const PERSONALIZE_DEFAULTS = { outfit: 'astronaut', skin: 'medio', hairStyle: 'sweep', hair: 'escuro', beard: 'none', eyes: 'castanho', freckles: false };
// migração de nome (PT) -> id
const LEGACY_ID = { 'Clara': 'clara', 'Médio-clara': 'medio', 'Média': 'media', 'Bronzeada': 'bronze', 'Escura': 'escura', 'Profunda': 'profunda', 'Preto': 'preto', 'Castanho escuro': 'escuro', 'Castanho': 'castanho', 'Ruivo': 'ruivo', 'Loiro': 'loiro', 'Grisalho': 'grisalho', 'Violeta fantasia': 'violeta', 'Avelã': 'avela', 'Verde': 'verde', 'Azul': 'azul', 'Cinza': 'cinza' };

function getPersonalize() {
  const stored = store.get(personalizeKey, {});
  const migrated = { ...stored };
  for (const key of ['skin', 'hair', 'eyes']) {
    if (migrated[key] && LEGACY_ID[migrated[key]]) migrated[key] = LEGACY_ID[migrated[key]];
  }
  // legado: nomes de saída em PT -> id
  if (migrated.suit && !migrated.outfit) {
    migrated.outfit = 'astronaut';
  }
  return { ...PERSONALIZE_DEFAULTS, ...migrated };
}

function applyPersonalize() {
  const p = getPersonalize();
  const root = document.documentElement;
  const skin = skinOptions.find(s => s.id === p.skin) || skinOptions[1];
  const hair = hairColorOptions.find(s => s.id === p.hair) || hairColorOptions[1];
  const eyes = eyeColorOptions.find(s => s.id === p.eyes) || eyeColorOptions[0];
  root.style.setProperty('--skin-a', skin.a);
  root.style.setProperty('--skin-b', skin.b);
  root.style.setProperty('--hair', hair.c);
  root.style.setProperty('--iris', eyes.c);
  $$('.avatar').forEach(a => {
    a.setAttribute('data-hair', p.hairStyle);
    a.setAttribute('data-beard', p.beard);
    a.setAttribute('data-freckles', p.freckles ? 'on' : 'off');
    a.setAttribute('data-outfit', p.outfit || 'astronaut');
  });
  const mark = (container, value) =>
    $$(`${container} [data-id]`).forEach(el => el.setAttribute('aria-pressed', String(el.dataset.id === value)));
  mark('#skinSwatches', skin.id);
  mark('#hairColors', hair.id);
  mark('#eyeColors', eyes.id);
  mark('#hairStyles', p.hairStyle);
  mark('#facialHair', p.beard);
  mark('#outfitPicker', p.outfit || 'astronaut');
  const ft = $('#frecklesToggle');
  if (ft) ft.checked = !!p.freckles;
}

function buildPersonalizePanel() {
  const mkSwatch = (opts, containerId, key) => {
    $(containerId).innerHTML = opts.map(o => {
      const label = window.t(o.tkey);
      return `<button class="swatch" style="background:${o.a ? `linear-gradient(150deg, ${o.a}, ${o.b})` : o.c}" data-key="${key}" data-id="${o.id}" aria-pressed="false" aria-label="${label}" title="${label}"></button>`;
    }).join('');
  };
  mkSwatch(skinOptions, '#skinSwatches', 'skin');
  mkSwatch(hairColorOptions, '#hairColors', 'hair');
  mkSwatch(eyeColorOptions, '#eyeColors', 'eyes');
  $('#outfitPicker').innerHTML = outfitOptions.map(o => `<button class="pill" data-key="outfit" data-id="${o.id}" aria-pressed="false">${window.t(o.tkey)}</button>`).join('');
  $('#hairStyles').innerHTML = hairStyleOptions.map(o => `<button class="pill" data-key="hairStyle" data-id="${o.id}" aria-pressed="false">${window.t(o.tkey)}</button>`).join('');
  $('#facialHair').innerHTML = facialHairOptions.map(o => `<button class="pill" data-key="beard" data-id="${o.id}" aria-pressed="false">${window.t(o.tkey)}</button>`).join('');

  $$('#skinSwatches .swatch, #hairColors .swatch, #eyeColors .swatch').forEach(sw =>
    sw.addEventListener('click', () => {
      const p = getPersonalize();
      p[sw.dataset.key] = sw.dataset.id;
      store.set(personalizeKey, p);
      applyPersonalize();
    }));
  $$('#hairStyles .pill, #facialHair .pill, #outfitPicker .pill').forEach(pi =>
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
$('#personalizeReset').addEventListener('click', () => { store.del(personalizeKey); applyPersonalize(); toast(window.t('toast.reset')); });

/* ═════════ 10 · INIT ═════════ */
// O <symbol>#avatarBody serve de template; clonamos o conteúdo para dentro de
// cada <svg class="avatar"> para que os atributos data-* controlem
// cabelo/barba/sardas/humor/roupa via CSS (com <use> os seletores não alcançavam os clones).
function hydrateAvatars() {
  const tpl = document.getElementById('avatarBody');
  if (!tpl) return;
  const html = tpl.innerHTML;
  $$('.avatar').forEach(a => { a.innerHTML = html; });
}

/* ═════════ 10.5 · Reações ao toque (avatar interativo) ═════════ */
let currentMood = 'calm';
const reactionCycle = [
  { cls: 'react-wave', text: () => window.t('react.hi') },
  { cls: 'react-hop', text: () => window.t('react.allgood') },
  { cls: 'react-laugh', text: () => window.t('react.lol') },
  { cls: 'react-wave', text: () => window.t('react.hail') },
  { cls: 'react-hop', text: () => window.t('react.eureka') },
];
let reactionIdx = 0;
function bindAvatarReactions() {
  const bubble = $('#avatarBubble');
  let bubbleTimer = null;
  const trigger = (svg) => {
    const reaction = reactionCycle[reactionIdx % reactionCycle.length];
    reactionIdx++;
    ['react-wave', 'react-hop', 'react-laugh'].forEach(c => $$('.avatar').forEach(a => a.classList.remove(c)));
    void svg.getBoundingClientRect(); // reflow: reinicia a animação
    svg.classList.add(reaction.cls);
    $$('.avatar').forEach(a => a.setAttribute('data-mood', 'happy'));
    ding(1318);
    if (bubble) {
      bubble.textContent = reaction.text();
      bubble.hidden = false;
      clearTimeout(bubbleTimer);
    }
    bubbleTimer = setTimeout(() => {
      if (bubble) bubble.hidden = true;
      $$('.avatar').forEach(a => { a.setAttribute('data-mood', currentMood); a.classList.remove('react-wave', 'react-hop', 'react-laugh'); });
    }, 2400);
  };
  $$('.avatar').forEach(svg => {
    svg.addEventListener('click', () => trigger(svg));
    svg.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); trigger(svg); }
    });
  });
}

/* ═════════ SLEEP — card + painel Sleep & Recovery ═════════ */
let lastSleep = null;
const SLEEP_TARGET = 7.5;
const clampNum = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const fmtSleepHours = (h) => { const total = Math.round(h * 60); return `${Math.floor(total / 60)}h ${String(total % 60).padStart(2, '0')}m`; };
const fmtH = (h) => `${h.toFixed(1)}h`;
function computeWeekDebt(nights) {
  if (!nights || !nights.length) return 0;
  return nights.slice(-7).reduce((acc, n) => acc + Math.max(0, SLEEP_TARGET - n.hours), 0);
}
function sleepEfficiency(n) {
  return clampNum(Math.round(100 - (n.latency_min || 0) * 0.35 - (n.awakenings || 0) * 2.2), 62, 98);
}
async function refreshSleep() {
  try { lastSleep = await (await fetch('/api/sleep')).json(); } catch (e) { console.warn('sleep offline', e); }
  if (lastVitals) renderVitals(lastVitals);
}

// ── card no grid de vitais ──
$('#vitalsGrid').addEventListener('click', e => {
  const card = e.target.closest('[data-open-sleep]'); if (!card) return;
  openSleepSheet();
});
$('#vitalsGrid').addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const card = e.target.closest('[data-open-sleep]'); if (!card) return;
  e.preventDefault();
  openSleepSheet();
});

function sleepLastNight() {
  const nights = lastSleep && lastSleep.nights;
  return nights && nights.length ? nights[nights.length - 1] : null;
}
function stageSegments(n) {
  const awake = clampNum((n.latency_min || 0) / ((n.hours || 7) * 60) * 100 + (n.awakenings || 0) * 1.2, 2, 12);
  const deep = clampNum(n.deep_pct || 18, 4, 40);
  const rem = clampNum(n.rem_pct || 21, 4, 40);
  const light = Math.max(0, 100 - awake - deep - rem);
  return [
    { key: 'deep', label: 'Deep', pct: deep, color: '#4a4f9e' },
    { key: 'light', label: 'Light', pct: light, color: '#5fc7b0' },
    { key: 'rem', label: 'REM', pct: rem, color: '#f2b366' },
    { key: 'awake', label: 'Awake', pct: awake, color: '#cfc6b8' },
  ];
}

function renderWeekChart(nights) {
  const svg = $('#sleepWeekChart');
  if (!nights || !nights.length) { svg.innerHTML = ''; return; }
  const week = nights.slice(-7);
  const W = 340, H = 132, top = 16, bottom = 30, barW = 30, gap = (W - 16 - barW * 7) / 6;
  const maxH = 9;
  const scaleH = v => (v / maxH) * (H - top - bottom);
  let x = 8;
  const bars = week.map(n => {
    const h = scaleH(n.hours);
    const y = H - bottom - h;
    const good = n.hours >= SLEEP_TARGET;
    const d = new Date(n.day + 'T00:00:00Z');
    const dow = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'][d.getUTCDay()];
    const bar = `<rect x="${x}" y="${y}" width="${barW}" height="${Math.max(3, h)}" rx="5" fill="${good ? '#146c6b' : '#c4714b'}" opacity="${good ? '.92' : '.9'}"/>
      <text class="wk-val" x="${x + barW / 2}" y="${y - 3}">${n.hours.toFixed(1)}</text>
      <text class="wk-day" x="${x + barW / 2}" y="${H - 12}">${dow}</text>`;
    x += barW + gap;
    return bar;
  }).join('');
  const targetY = H - bottom - scaleH(SLEEP_TARGET);
  svg.innerHTML = `<line class="wk-grid" x1="0" y1="${H - bottom}" x2="${W}" y2="${H - bottom}"/>
    <line class="wk-target" x1="0" y1="${targetY}" x2="${W}" y2="${targetY}"/>
    <text class="wk-target-lbl" x="${W - 2}" y="${targetY - 3}" text-anchor="end">7.5h</text>
    ${bars}`;
}

function renderDayStrip() {
  const svg = $('#sleepDayStrip');
  const W = 560, barY = 26, barH = 30;
  const px = h => (h / 24) * W;
  // segmentos de luz artificial da cabine
  const segs = [
    { x0: 0, x1: 6.5, color: '#131f36', r: 'url(#segL)' },
    { x0: 6.5, x1: 19.5, color: '#e8b96a' },
    { x0: 19.5, x1: 22.5, color: '#57402c' },
    { x0: 22.5, x1: 24, color: '#131f36' },
  ];
  const now = new Date();
  const hourNow = now.getHours() + now.getMinutes() / 60;
  const youX = px(hourNow);
  const segRects = segs.map(s => `<rect x="${px(s.x0)}" y="${barY}" width="${px(s.x1) - px(s.x0)}" height="${barH}" fill="${s.color}"/>`).join('');
  // faixa de sono (atravessa a meia-noite): 22:30→24 + 0→6:30
  const sleepA = `<rect x="${px(22.5)}" y="${barY - 5}" width="${px(24) - px(22.5)}" height="${barH + 10}" fill="rgba(87,230,201,.16)" stroke="#57e6c9" stroke-width="1.6" stroke-dasharray="5 4" rx="4"/>`;
  const sleepB = `<rect x="0" y="${barY - 5}" width="${px(6.5)}" height="${barH + 10}" fill="rgba(87,230,201,.16)" stroke="#57e6c9" stroke-width="1.6" stroke-dasharray="5 4" rx="4"/>`;
  const ticks = [
    { h: 6.5, lbl: '06:30 sunrise' },
    { h: 19.5, lbl: '19:30 dim' },
    { h: 22.5, lbl: '22:30 lights out' },
  ].map(t => {
    const x = px(t.h);
    return `<line x1="${x}" y1="${barY - 8}" x2="${x}" y2="${barY + barH + 8}" stroke="rgba(255,255,255,.75)" stroke-width="1.4"/>
      <text class="wk-day" x="${x}" y="${barY + barH + 21}" fill="#5f7a7a">${t.lbl}</text>`;
  }).join('');
  svg.innerHTML = `<defs><clipPath id="barClip"><rect x="0" y="${barY}" width="${W}" height="${barH}" rx="15"/></clipPath></defs>
    <g clip-path="url(#barClip)">${segRects}${sleepA}${sleepB}</g>
    <rect x="0" y="${barY}" width="${W}" height="${barH}" rx="15" fill="none" stroke="rgba(23,58,58,.25)"/>
    ${ticks}
    <g transform="translate(${youX}, ${barY + barH / 2})">
      <circle r="7.5" fill="#ffd166" stroke="#0f3e3d" stroke-width="2.4"/>
      <text y="-13" text-anchor="middle" style="font:800 8px 'Nunito';fill:#0f3e3d;letter-spacing:.14em">YOU</text>
    </g>`;
}

function renderSleepSheet() {
  const nights = lastSleep && lastSleep.nights ? lastSleep.nights : [];
  const last = sleepLastNight();
  const v = lastVitals || {};
  const sheetDate = $('#sleepSheetDate');
  if (!last) { sheetDate.textContent = 'No sleep data onboard yet'; return; }

  const d = new Date(last.day + 'T00:00:00Z');
  sheetDate.textContent = `Night of ${d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}`;

  // Última noite
  const eff = sleepEfficiency(last);
  $('#sleepDuration').textContent = fmtSleepHours(last.hours);
  $('#sleepEfficiency').textContent = `${eff}%`;
  $('#sleepLatency').textContent = `${last.latency_min} min`;
  $('#sleepAwakenings').textContent = String(last.awakenings);
  const segs = stageSegments(last);
  $('#sleepStageBar').innerHTML = segs.map(s => `<div class="sleep-stage-seg" style="width:${s.pct}%;background:${s.color}" title="${s.label} ${s.pct.toFixed(0)}%"></div>`).join('');
  $('#sleepStageLegend').innerHTML = segs.map(s => `<span><i class="sleep-stage-dot" style="background:${s.color}"></i>${s.label} <b class="mono">${s.pct.toFixed(0)}%</b></span>`).join('');

  // Semana
  renderWeekChart(nights);
  const debt = computeWeekDebt(nights);
  const below = nights.slice(-7).filter(n => n.hours < SLEEP_TARGET).length;
  $('#sleepDebtTotal').textContent = debt <= 0 ? '0h debt' : `−${fmtSleepHours(debt)} sleep debt`;
  $('#sleepDebtNights').textContent = String(below);
  const debtBadge = $('#sleepDebtBadge');
  const avgWeek = nights.length ? nights.slice(-7).reduce((a, n) => a + n.hours, 0) / Math.min(7, nights.length) : 0;
  debtBadge.textContent = debt <= 0 ? 'ON TARGET' : (avgWeek >= 6.2 ? 'SLEEP DEBT' : 'CRITICAL');
  debtBadge.className = `status-badge ${debt <= 0 ? 'concluido' : (avgWeek >= 6.2 ? 'pendente' : 'pendente')}`;

  // Circadiano
  renderDayStrip();
  const syncBadge = $('#sleepSyncBadge');
  if (avgWeek >= 7.2) { syncBadge.textContent = 'IN SYNC'; syncBadge.className = 'status-badge concluido'; }
  else if (avgWeek >= 6.2) { syncBadge.textContent = 'STRAINED'; syncBadge.className = 'status-badge pendente'; }
  else { syncBadge.textContent = 'DESYNC'; syncBadge.className = 'status-badge pendente'; }
  $('#sleepLightNote').innerHTML = avgWeek >= 7.2
    ? 'Cabin lights follow the artificial day/night cycle — you are <b>in sync</b> with it.'
    : 'You\'re drifting against the cabin light cycle. <b>Avoid bright light after 21:30</b>; lean on the dim-evening scene to pull your clock back.';

  // Recuperação
  const hrv = v.hrv ?? 62;
  $('#sleepHrv').innerHTML = `${Math.round(hrv)}<small> ms</small>`;
  $('#sleepHrvDelta').textContent = 'overnight · recovery marker';
  $('#sleepNightHr').innerHTML = `${Math.round(last.night_hr)}<small> bpm</small>`;
  $('#sleepDeep').innerHTML = `${last.deep_pct.toFixed(0)}<small>%</small>`;
  $('#sleepRem').innerHTML = `${last.rem_pct.toFixed(0)}<small>%</small>`;

  // Prontidão cognitiva + anel
  const readiness = clampNum(Math.round(56 + (eff - 70) * 0.62 + (last.deep_pct || 18) * 0.72 - (last.awakenings || 0) * 1.6), 35, 98);
  $('#sleepReadiness').textContent = String(readiness);
  const ring = $('#sleepRingFg');
  const C = 2 * Math.PI * 22; // 138.17
  ring.style.strokeDashoffset = String(C * (1 - readiness / 100));
  ring.style.stroke = readiness >= 75 ? '#57e6c9' : readiness >= 55 ? '#f2b366' : '#ff8a5c';

  const inertia = $('#sleepInertiaNote');
  inertia.hidden = !(last.deep_pct >= 22 && readiness < 62);
}

window.openSleepSheet = async function () {
  await refreshSleep();
  renderSleepSheet();
  $('#sleepSheet').hidden = false;
};
function closeSleepSheet() { $('#sleepSheet').hidden = true; }
$('#sleepSheetClose').addEventListener('click', closeSleepSheet);
$('#sleepSheet').addEventListener('click', e => { if (e.target.id === 'sleepSheet') closeSleepSheet(); });
window.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#sleepSheet').hidden) closeSleepSheet(); });

// (re)carrega o conteúdo que depende do idioma e re-renderiza
async function loadDynamicContent() {
  try { routineTemplate = (await (await fetch(`/api/routines?lang=${window.BIP_LANG}`)).json()).periods; } catch { routineTemplate = []; }
  try { achievements = (await (await fetch(`/api/achievements?lang=${window.BIP_LANG}`)).json()).achievements; } catch { achievements = []; }
  try {
    const stock = (await (await fetch(`/api/stock?lang=${window.BIP_LANG}`)).json()).items;
    $('#stockList').innerHTML = stock.map(i => `<li class="stock-item"><b>${i.name}</b>${i.qty != null ? ` · ${i.qty} un.` : ''}<small>${i.for}</small></li>`).join('');
  } catch {}
  buildRoutines();
  updateRoutinesUI();
  renderAchievements(computeMetrics());
  await loadExams();
  renderChat();
}

// ═══════════ BOOT — abertura ═══════════
function bootSequence() {
  const screen = document.getElementById('bootScreen');
  const bot = document.getElementById('bootBot');
  const floatBtn = document.getElementById('bipBotBtn');
  if (!screen || !bot || !floatBtn) return;
  if (prefersReducedMotion) {
    screen.style.display = 'none';
    return;
  }
  floatBtn.style.visibility = 'hidden';
  screen.classList.add('is-active');

  // pop-in do B.I.P com bounce
  bot.animate([
    { transform: 'scale(.25) translateY(40px)', opacity: 0 },
    { transform: 'scale(1.22) translateY(0)', opacity: 1, offset: .52 },
    { transform: 'scale(.94)', offset: .78 },
    { transform: 'scale(1)' },
  ], { duration: 720, easing: 'cubic-bezier(.2,1.3,.35,1)', fill: 'forwards' });

  // depois de pop + pausa, voa para o canto
  window.setTimeout(() => {
    const target = floatBtn.querySelector('.bip-bot-svg') || floatBtn;
    const to = target.getBoundingClientRect();
    const from = bot.getBoundingClientRect();
    const dx = (to.left + to.width / 2) - (from.left + from.width / 2);
    const dy = (to.top + to.height / 2) - (from.top + from.height / 2);
    const scale = to.width / from.width;

    screen.classList.add('is-revealing'); // funde o fundo, revelando o app
    bot.animate([
      { transform: 'translate(0px, 0px) scale(1) rotate(0deg)' },
      { transform: `translate(${dx * 0.42}px, ${dy * 0.58 - 70}px) scale(${scale * 1.5}) rotate(-9deg)`, offset: .42 },
      { transform: `translate(${dx}px, ${dy}px) scale(${scale}) rotate(0deg)` },
    ], { duration: 700, easing: 'cubic-bezier(.3,.9,.35,1)', fill: 'forwards' }).onfinish = () => {
      screen.style.display = 'none';
      floatBtn.style.visibility = '';
    };
  }, 1050);
}

async function init() {
  bootSequence();
  hydrateAvatars();
  buildPersonalizePanel();
  applyPersonalize();
  // liga o seletor de idioma → recarrega conteúdo e reaplica textos
  $$('.lang-pill').forEach(btn => btn.addEventListener('click', () => window.bipSetLang(btn.dataset.lang)));
  window.bipRefreshContent = async () => {
    buildPersonalizePanel();   // reconstrói rótulos no idioma novo
    applyPersonalize();
    await loadDynamicContent();
    tickClock();
    refreshVitals();
    applyLang();               // reaplica data-i18n (sem persistir de novo)
  };
  tickClock();
  setInterval(tickClock, 1000);
  setInterval(refreshVitals, 5000);

  await refreshVitals();
  await refreshSleep();
  await loadDynamicContent();
  persistHistory();          // registra snapshot do dia e dispara verificação de conquistas
  evaluateAchievements(true);
  bindAvatarReactions();

  $('#dxHistoryCount').textContent = String((store.get('bip.diagnoses', []) || []).length);
  renderChat();
  window.applyLang && window.applyLang();
}
init();
