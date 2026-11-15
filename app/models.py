"""Tabelas do estado do usuário.

Vitais e sono NÃO são gravados: o simulador será determinístico (seed + timestamp),
então o histórico é recalculado sob demanda.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
