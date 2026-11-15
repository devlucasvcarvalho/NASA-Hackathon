"""Tabelas do estado do usuário.

Vitais e sono SÃO gravados (histórico do paciente). O simulador é determinístico
(seed + timestamp), então o backfill e o catch-up preguiçoso são reproduzíveis.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class VitalSample(Base):
    """Histórico das métricas do paciente: 1 amostra a cada STEP segundos (epoch UTC)."""

    __tablename__ = "vitals"
    ts: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    heart_rate: Mapped[float] = mapped_column(Float)
    spo2: Mapped[float] = mapped_column(Float)
    hydration: Mapped[float] = mapped_column(Float)
    bp_sys: Mapped[float] = mapped_column(Float)
    bp_dia: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    hrv: Mapped[float] = mapped_column(Float)
    radiation_rate: Mapped[float] = mapped_column(Float)


class SleepNight(Base):
    """Uma noite de sono; `day` é a data em que a pessoa acorda (YYYY-MM-DD)."""

    __tablename__ = "sleep"
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    hours: Mapped[float] = mapped_column(Float)
    latency_min: Mapped[int] = mapped_column(Integer)
    awakenings: Mapped[int] = mapped_column(Integer)
    deep_pct: Mapped[float] = mapped_column(Float)
    rem_pct: Mapped[float] = mapped_column(Float)
    night_hr: Mapped[float] = mapped_column(Float)


class RoutineLog(Base):
    __tablename__ = "routine_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    task_id: Mapped[str] = mapped_column(String(16))
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Mood(Base):
    __tablename__ = "mood"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    q1: Mapped[int] = mapped_column(Integer)
    q2: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    query: Mapped[str] = mapped_column(Text)
    image_attached: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict] = mapped_column(JSON)


class ChatMessage(Base):
    __tablename__ = "chat"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    role: Mapped[str] = mapped_column(String(12))
    text: Mapped[str] = mapped_column(Text)


class StockMove(Base):
    __tablename__ = "stock_moves"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    item: Mapped[str] = mapped_column(String(120), index=True)
    delta: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(200), default="")


class AchievementUnlocked(Base):
    __tablename__ = "achievements_unlocked"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
