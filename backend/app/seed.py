"""Database initialization and seeding (issue #3).

Creates the tables and the exactly-two predefined accounts with SYNTHETIC data,
plus a couple of sample emails (one plain text, one HTML) so later issues have
data to work with. There is no registration path; accounts only come from here.

Run standalone:  python -m app.seed      (from the backend/ directory)

Note: password hashes are set by the login system (issue #2); this seed leaves
them empty.
"""
from datetime import date, datetime

from .crud import _get_user_by_role
from .database import Base, SessionLocal, engine
from .models import Email, User

# Two predefined accounts. "attacker"/"target" are experiment role names only.
ATTACKER_EMAIL = "attacker@wemail.com"
TARGET_EMAIL = "target@wemail.com"


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    """Insert the two accounts and sample emails if they are not present yet."""
    init_db()
    db = SessionLocal()
    try:
        if _get_user_by_role(db, "attacker") and _get_user_by_role(db, "target"):
            return  # already seeded; keep this idempotent

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
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Database seeded: 2 accounts (attacker, target) + sample emails.")
