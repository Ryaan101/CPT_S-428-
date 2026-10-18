"""Database initialization and seeding (issue #3).

Creates the tables and the exactly-two predefined accounts with SYNTHETIC data,
plus a couple of sample emails (one plain text, one HTML) so later issues have
data to work with. There is no registration path; accounts only come from here.

Run standalone:  python -m app.seed      (from the backend/ directory)

Note: ensure_passwords() sets bcrypt hashes for the two demo accounts (issue #2)
using DEFAULT_PASSWORDS, filling them in if they are not already set.
"""
from datetime import date, datetime

from .crud import _get_user_by_role
from .database import Base, SessionLocal, engine
from .models import Email, User
from .security import hash_password

# Two predefined accounts. "attacker"/"target" are experiment role names only.
ATTACKER_EMAIL = "attacker@wemail.com"
TARGET_EMAIL = "target@wemail.com"

# Synthetic, local-only demo credentials for the two predefined accounts.
# These are NOT real secrets; they exist so the team can log in locally.
DEFAULT_PASSWORDS = {"attacker": "attacker123", "target": "target123"}


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def ensure_passwords(db) -> None:
    """Set bcrypt hashes for the predefined accounts if they are not set yet.

    Runs on every seed so an already-created DB (from issue #3, before passwords
    existed) also gets usable credentials, while existing hashes are left alone.
    """
    changed = False
    for role, plaintext in DEFAULT_PASSWORDS.items():
        user = _get_user_by_role(db, role)
        if user is not None and not user.password_hash:
            user.password_hash = hash_password(plaintext)
            changed = True
    if changed:
        db.commit()


def seed() -> None:
    """Insert the two accounts and sample emails if absent, and ensure passwords."""
    init_db()
    db = SessionLocal()
    try:
        already = _get_user_by_role(db, "attacker") and _get_user_by_role(db, "target")
        if already:
            ensure_passwords(db)  # idempotent: fill in passwords if missing
            return

        attacker = User(
            role="attacker",
            email_address=ATTACKER_EMAIL,
            display_name="A. Sender",
            full_name="Alex Sender",
            birthdate=date(1992, 11, 4),
            time_zone="America/Los_Angeles",
            workplace="Synthetic Research Co.",
        )
        # The target's profile is the synthetic PRIVATE data the experiment probes.
        target = User(
            role="target",
            email_address=TARGET_EMAIL,
            display_name="T. Recipient",
            full_name="Taylor Recipient",
            birthdate=date(1995, 7, 22),
            time_zone="America/New_York",
            workplace="Example University",
        )
        db.add_all([attacker, target])
        db.flush()  # assign ids

        samples = [
            Email(
                sender_id=attacker.id,
                recipient_id=target.id,
                subject="Welcome to wemail",
                body="Hi Taylor, this is a plain-text test message.",
                is_html=False,
                created_at=datetime(2026, 10, 15, 9, 0, 0),
                is_read=False,
            ),
            Email(
                sender_id=target.id,
                recipient_id=attacker.id,
                subject="RE: Welcome to wemail",
                body="Thanks, got it!",
                is_html=False,
                created_at=datetime(2026, 10, 15, 9, 30, 0),
                is_read=True,
            ),
            Email(
                sender_id=attacker.id,
                recipient_id=target.id,
                subject="Formatted note",
                body="This message has an HTML body.",
                body_html="<h2>Hello</h2><p>This is an <strong>HTML</strong> email.</p>",
                is_html=True,
                created_at=datetime(2026, 10, 16, 14, 0, 0),
                is_read=False,
            ),
        ]
        db.add_all(samples)
        db.commit()
        ensure_passwords(db)  # set credentials for the freshly created accounts
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Database seeded: 2 accounts (attacker, target) + sample emails.")
