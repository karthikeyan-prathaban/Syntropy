from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    mobile_enc: Mapped[str] = mapped_column(String(255), default="")
    email_enc: Mapped[str] = mapped_column(String(255), default="")
    vua_enc: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_initials: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    consents: Mapped[list["ConsentRecord"]] = relationship(back_populates="user")
    accounts: Mapped[list["BankAccount"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    request_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    consent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    consent_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="consents")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    linked_acc_ref: Mapped[str] = mapped_column(String(120))
    masked_acc_number: Mapped[str] = mapped_column(String(40))
    account_type: Mapped[str] = mapped_column(String(40), default="DEPOSIT")
    current_balance: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    fip_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"))
    txn_id: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[float] = mapped_column(Float)
    txn_type: Mapped[str] = mapped_column(String(12))
    narration: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(40), default="")
    category: Mapped[str] = mapped_column(String(80), default="Other")
    transaction_timestamp: Mapped[datetime] = mapped_column(DateTime)
    balance_after: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship(back_populates="transactions")
    account: Mapped[BankAccount] = relationship(back_populates="transactions")


class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    utm: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
