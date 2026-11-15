"""Reference ranges per metric and status classification.

(alert_lo, watch_lo, watch_hi, alert_hi): inside [watch_lo, watch_hi] = normal ("normal");
between alert and watch = "vigilancia" (watch); outside alert = "alerta" (alert). None = no limit.
(Enum values stay in Portuguese: they are part of the API contract.)

SOURCES: space programs only (NASA / ESA / DLR). Each metric states in `source.kind`:
  - "space_program": the limit comes from a space-agency document (see REFERENCES);
  - "placeholder":   NO numeric range from a space-agency source could be verified; the value is a
                     generic adult default and MUST be validated by a flight surgeon before real use.
NASA-STD-3001 Vol. 1 requires monitoring/trending vital signs [V1 3004, item h] but publishes no
numeric limits for them.
"""

# Radiation limits (NASA-STD-3001 Vol. 1 Rev B, via OCHMO-TB-020 Rev E)
CAREER_LIMIT_MSV = 600  # [V1 4030] career effective dose from space radiation
SPE_LIMIT_MSV = 250     # [V1 4031] per solar particle event (design reference SPE)

REFERENCES = {
    "STD3001-V1C": {
        "title": "NASA-STD-3001, Volume 1, Revision C — Crew Health",
        "url": "https://www.nasa.gov/wp-content/uploads/2023/11/nasa-std-3001-vol-1-rev-c-with-signature.pdf",
        "used_for": "[V1 3004, item h]: assess, record, monitor and trend vital signs (no numeric limits)",
    },
    "OCHMO-TB-020": {
        "title": "NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev E — Design for Ionizing Radiation Protection (12/27/2022)",
        "url": "https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf",
        "used_for": "600 mSv career limit [V1 4030]; 250 mSv per SPE [V1 4031]; surface environment ≈0.5 mSv/day; Mars-transit example of 1.5 mSv/day",
    },
    "SIMONSEN-ASCEND": {
        "title": "Simonsen, Zawaski & Weeks — Moon 2 Mars Space Radiation Protection “Buying Down” Risks to Crew (NASA HQ/JSC, ASCEND draft)",
        "url": "https://ntrs.nasa.gov/citations/20250006168",
        "used_for": "ISS: effective dose ≈0.2–0.5 mSv/day; ≈40–90 mSv over a typical 6-month mission (draft document)",
    },
    "NASA-SP-2025-273": {
        "title": "NASA/SP-2025-0000273 — Astronaut physiological deconditioning and countermeasures (Jan 2025)",
        "url": "https://www.nasa.gov/wp-content/uploads/2025/02/sp-20250000273.pdf",
        "used_for": "ISS exercise at 70–90% of max HR; reported mean peaks ≈162–163 bpm (T2 treadmill / CEVIS)",
    },
    "STAHN-2017": {
        "title": "Stahn et al. (DLR/ESA/NASA, Thermolab project) — Increased core body temperature in astronauts during long-duration space missions. Scientific Reports 7:16180 (2017)",
        "url": "https://elib.dlr.de/116228",
        "used_for": "resting core temperature rises ≈1 °C over ≈2.5 months in long spaceflight",
    },
}

_NO_SPACE_RANGE = ("No numeric range from a space agency could be verified; generic adult value (placeholder). "
                   "NASA-STD-3001 Vol.1 requires monitoring/trending but publishes no limits. Validate with the flight surgeon.")

RANGES = {
    "heart_rate": {
        "unit": "bpm", "label": "Heart rate", "limits": (45, 50, 100, 115),
        "source": {"kind": "placeholder", "refs": ["STD3001-V1C", "NASA-SP-2025-273"], "note": _NO_SPACE_RANGE
                   + " Space context: ISS exercise drives peaks of ≈162–163 bpm (70–90% of max HR), so a high HR during the exercise slot is expected."},
    },
    "spo2": {
        "unit": "%", "label": "SpO₂", "limits": (92, 95, None, None),
        "source": {"kind": "placeholder", "refs": ["STD3001-V1C"], "note": _NO_SPACE_RANGE},
    },
    "hydration": {
        "unit": "%", "label": "Hydration", "limits": (50, 60, None, None),
        "source": {"kind": "placeholder", "refs": [], "note": "App-defined index (not a standardized NASA-STD-3001 measure); no source."},
    },
    "bp_sys": {
        "unit": "mmHg", "label": "Systolic BP", "limits": (85, 90, 130, 140),
        "source": {"kind": "placeholder", "refs": ["STD3001-V1C"], "note": _NO_SPACE_RANGE},
    },
    "bp_dia": {
        "unit": "mmHg", "label": "Diastolic BP", "limits": (55, 60, 85, 90),
        "source": {"kind": "placeholder", "refs": ["STD3001-V1C"], "note": _NO_SPACE_RANGE},
    },
    "temperature": {
        "unit": "°C", "label": "Temperature", "limits": (35.3, 35.8, 37.3, 38.0),
        "source": {"kind": "placeholder", "refs": ["STAHN-2017"], "note": _NO_SPACE_RANGE
                   + " Space context: in long flights the resting core temperature rises ≈1 °C (Stahn 2017); fixed terrestrial limits may over-alert, which is why the detector also uses the patient's own baseline."},
    },
    "hrv": {
        "unit": "ms", "label": "HRV (RMSSD)", "limits": (20, 30, None, None),
        "source": {"kind": "placeholder", "refs": [], "note": "No space-agency reference found; app value. The individual baseline (z-score) is the main criterion."},
    },
    "radiation_rate": {
        "unit": "mSv/day", "label": "Radiation rate", "limits": (None, None, 0.5, 1.5),
        "source": {"kind": "space_program", "refs": ["OCHMO-TB-020", "SIMONSEN-ASCEND"],
                   "note": "Normal ≤0.5 mSv/day (ISS 0.2–0.5; surface ≈0.5). Alert >1.5 mSv/day (rate NASA cites for the Mars transit). The 1.5 cut-off is a project choice based on that example, not a requirement."},
    },
}

# During the scheduled exercise a high HR is expected. NASA/SP-2025-0000273: ISS exercise runs at
# 70–90% of max HR, with mean peaks ≈162–163 bpm. The 165 bpm alert cut-off is a PROJECT CHOICE
# (reported peak + a small margin), not a NASA requirement.
EXERCISE_LIMITS = {"heart_rate": (None, None, 150, 165)}

METRICS = list(RANGES)


def status_for(metric: str, value: float, exercising: bool = False) -> str:
    limits = EXERCISE_LIMITS.get(metric) if exercising else None
    alert_lo, watch_lo, watch_hi, alert_hi = limits or RANGES[metric]["limits"]
    if (alert_lo is not None and value < alert_lo) or (alert_hi is not None and value > alert_hi):
        return "alerta"
    if (watch_lo is not None and value < watch_lo) or (watch_hi is not None and value > watch_hi):
        return "vigilancia"
    return "normal"
