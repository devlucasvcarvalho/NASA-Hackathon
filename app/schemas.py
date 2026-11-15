"""Schema e guardrails da resposta de diagnóstico (Gemini ou motor offline)."""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# Regra do produto: o tripulante está FORA da Terra, nunca mandar "procurar médico/hospital".
FORBIDDEN = re.compile(
    r"procure\s+(um\s+)?m[eé]dico|v[aá]\s+(ao|para\s+o|a)\s+(hospital|pronto[- ]socorro)|pronto[- ]socorro|procure\s+atendimento"
    r"|see\s+a\s+doctor|go\s+to\s+(the\s+)?(hospital|emergency\s+room|er\b)|visit\s+(a|the)\s+(doctor|hospital)"
    r"|busca\s+(a\s+)?un\s+m[eé]dico|ve\s+(al|a\s+un)\s+(hospital|m[eé]dico)|acude\s+(al|a\s+un)\s+(hospital|m[eé]dico)|sala\s+de\s+urgencias",
    re.IGNORECASE,
)
DEFAULT_ACTION = {"leve": "onboard", "moderado": "telemedicine", "grave": "abort"}


class Cause(BaseModel):
    name: str
    likelihood: int = Field(ge=0, le=100)
    why: str = ""

    @field_validator("likelihood", mode="before")
    @classmethod
    def _coerce(cls, v):
        return int(round(float(v)))


class Rx(BaseModel):
    item: str
    dose: str = ""
    frequency: str = ""
    duration: str = ""
    instructions: str = ""


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=3)
    severity: Literal["leve", "moderado", "grave"]
    summary: str = Field(min_length=10)
    causes: list[Cause] = Field(min_length=1)
    prescription: list[Rx] = []
    procedures: list[str] = Field(min_length=1)
    monitoring: str = ""
    triage_action: Literal["onboard", "telemedicine", "abort"]
    red_flags: list[str] = []
    factors_used: list[str] = []
    disclaimer: str = "Decision support based on onboard data — the final word belongs to the MCC flight surgeon."


def _all_text(d: Any) -> str:
    if isinstance(d, dict):
        return " ".join(_all_text(v) for v in d.values())
    if isinstance(d, list):
        return " ".join(_all_text(v) for v in d)
    return str(d)


def validate_diagnosis(raw: Any) -> dict | None:
    """Devolve o dict normalizado, ou None se inválido / violar guardrail."""
    if not isinstance(raw, dict):
        return None
    raw = dict(raw)
    sev = str(raw.get("severity", "")).lower()
    raw["severity"] = sev
    if raw.get("triage_action") not in DEFAULT_ACTION.values() and sev in DEFAULT_ACTION:
        raw["triage_action"] = DEFAULT_ACTION[sev]  # IA esqueceu/errou a triagem: deriva da gravidade
    for k in ("monitoring", "summary", "title"):
        if isinstance(raw.get(k), (list, dict)):
            raw[k] = _all_text(raw[k])
    try:
        out = DiagnosisOut.model_validate(raw).model_dump()
    except ValidationError:
        return None
    if FORBIDDEN.search(_all_text(out)):
        return None
    # coerência: gravidade grave exige abortar/MCC
    if out["severity"] == "grave":
        out["triage_action"] = "abort"
    return out
