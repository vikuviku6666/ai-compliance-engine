from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
import uuid


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)


class Responsibility(Base):
    __tablename__ = "responsibilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)


class Risk(Base):
    __tablename__ = "risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    severity = Column(String)


class Control(Base):
    __tablename__ = "controls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)


class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id = Column(String)
    title = Column(String)
    text = Column(String)


class TrainingModule(Base):
    __tablename__ = "training_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    duration_minutes = Column(Integer)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    plan_id = Column(String, primary_key=True)
    role = Column(String)
    responsibilities = Column(String)  # JSON or serialized text
    risks = Column(String)             # JSON or serialized text
    status = Column(String, default="draft")  # draft, revised, approved
    reviewer_notes = Column(String, nullable=True)
    overall_score = Column(Integer, default=0)
    created_at = Column(String)


class TrainingPlanModule(Base):
    __tablename__ = "training_plan_modules"

    id = Column(String, primary_key=True)
    plan_id = Column(String)
    quarter = Column(String)  # Q1 Foundation, Q2 Application, etc.
    module = Column(String)
    role_reference = Column(String)
    regulation_reference = Column(String)
    risk_reference = Column(String)
    competency_reference = Column(String)
    behavioural_outcome = Column(String)

