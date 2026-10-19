"""Point the backend at a throwaway database so trials never touch the dev DB.

``init()`` MUST run before anything imports ``app.*``: the backend reads DATABASE_URL, SECRET_KEY
and AGENT_TOKEN when it is imported. It is safe to call more than once. ``fresh_db()`` resets
the database to a freshly seeded state by copying a template (the template is built once, so
the bcrypt hashing in the seed is not repeated for every trial).
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
HARNESS_AGENT_TOKEN = "harness-agent-token"

_state = {}


def init(workdir=None):
    if _state:
        return _state
    if "app.database" in sys.modules:
        raise RuntimeError("app.* was imported before harness.appenv.init(); refusing to touch the real DB")
    workdir = Path(workdir or tempfile.mkdtemp(prefix="wemail-harness-"))
    workdir.mkdir(parents=True, exist_ok=True)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    db = workdir / "trial.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["AGENT_TOKEN"] = HARNESS_AGENT_TOKEN
    os.environ["SECRET_KEY"] = "harness-secret-key"
    _state.update(db=db, template=workdir / "template.db", workdir=workdir, token=HARNESS_AGENT_TOKEN)
    return _state


def fresh_db():
    """Reset the database to: two seeded accounts + the sample history, nothing else."""
    from app.database import engine
    from app.seed import seed

    st = init()
    if not st["template"].exists():
        engine.dispose()
        if st["db"].exists():
            st["db"].unlink()
        seed()
        engine.dispose()
        shutil.copyfile(st["db"], st["template"])
    engine.dispose()
    shutil.copyfile(st["template"], st["db"])
