import pytest

from harness import appenv

appenv.init()  # throwaway DB + test secrets; must run before app.* is imported

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import DEFAULT_PASSWORDS, TARGET_EMAIL, ATTACKER_EMAIL  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    appenv.fresh_db()


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, role):
    email = {"attacker": ATTACKER_EMAIL, "target": TARGET_EMAIL}[role]
    r = client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORDS[role]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def attacker(client):
    return _login(client, "attacker")


@pytest.fixture
def target(client):
    return _login(client, "target")


@pytest.fixture
def agent():
    return {"Authorization": f"Bearer {appenv.init()['token']}"}
