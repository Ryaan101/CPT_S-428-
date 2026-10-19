"""HTTP client for the backend's /agent/* routes.

It works against a live server (``MailClient.from_url``) or in-process against the
FastAPI app (pass a ``fastapi.testclient.TestClient``), which is how the harness runs.
"""


class AgentApiError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


class MailClient:
    def __init__(self, http, token):
        self.http = http
        self.headers = {"Authorization": f"Bearer {token}"}

    @classmethod
    def from_url(cls, base_url, token, timeout=30.0):
        import httpx

        return cls(httpx.Client(base_url=base_url, timeout=timeout), token)

    def _call(self, method, path, **kwargs):
        r = self.http.request(method, path, headers=self.headers, **kwargs)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise AgentApiError(r.status_code, detail)
        return r.json() if r.content else None

    def context(self):
        return self._call("GET", "/agent/context")

    def list_unprocessed(self):
        return self._call("GET", "/agent/emails")

    def get_email(self, email_id):
        return self._call("GET", f"/agent/emails/{int(email_id)}")

    def reply(self, email_id, body):
        return self._call("POST", f"/agent/emails/{int(email_id)}/reply", json={"body": str(body)})

    def mark_processed(self, email_id):
        return self._call("POST", f"/agent/emails/{int(email_id)}/processed")
