"""ORM models (issue #3): the two predefined accounts and their emails.

Only two users ever exist (roles "attacker" and "target"); there is no
registration. The target's profile fields hold synthetic private data that the
later AI-agent experiment probes — they must never be readable by the attacker
through the app/API (enforced in crud.py).
"""
from __future__ import annotations  # PEP 563: allows list[...] on Python 3.8

from datetime import date, datetime
from typing import List, Optional  # SQLAlchemy eval's Mapped annotations on 3.8

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(16), unique=True)  # "attacker" | "target"
    email_address: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # Set by the login system (issue #2); empty until then.
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(80))

    # --- Profile fields (synthetic). For the target these are the private data. ---
    full_name: Mapped[str] = mapped_column(String(120), default="")
    birthdate: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    time_zone: Mapped[str] = mapped_column(String(64), default="")
    workplace: Mapped[str] = mapped_column(String(120), default="")

    sent: Mapped[List["Email"]] = relationship(
        back_populates="sender", foreign_keys="Email.sender_id"
    )
    received: Mapped[List["Email"]] = relationship(
        back_populates="recipient", foreign_keys="Email.recipient_id"
    )


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")  # plain-text view
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # raw HTML, verbatim
    is_html: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    # Set once the local AI agent has handled this email (used only by the agent API).
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Soft-delete per side so each account manages its own copy independently.
    deleted_by_sender: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_by_recipient: Mapped[bool] = mapped_column(Boolean, default=False)

    sender: Mapped["User"] = relationship(back_populates="sent", foreign_keys=[sender_id])
    recipient: Mapped["User"] = relationship(
        back_populates="received", foreign_keys=[recipient_id]
    )
