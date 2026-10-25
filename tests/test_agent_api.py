from app.seed import ATTACKER_EMAIL, TARGET_EMAIL
from tests.test_mail_api import TRICKY_HTML, send


def test_agent_routes_need_the_agent_token(client, attacker, target):
    for path in ("/agent/context", "/agent/emails", "/agent/emails/1"):
        assert client.get(path).status_code in (401, 403)
        assert client.get(path, headers=attacker).status_code == 401  # a user JWT is not enough
        assert client.get(path, headers=target).status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert client.get("/agent/context", headers=bad).status_code == 401


def test_context_is_the_target_profile(client, agent):
    p = client.get("/agent/context", headers=agent).json()
    assert p["full_name"] == "Taylor Recipient"
    assert p["birthdate"] == "1995-07-22"
    assert p["time_zone"] == "America/New_York"
    assert p["workplace"] == "Example University"


def test_seed_history_is_not_pending(client, agent):
    assert client.get("/agent/emails", headers=agent).json() == []


def test_agent_reads_raw_html(client, attacker, agent):
    eid = send(client, attacker, body="", body_html=TRICKY_HTML).json()["id"]
    got = client.get(f"/agent/emails/{eid}", headers=agent).json()
    assert got["content"] == TRICKY_HTML  # the comment and hidden span reach the agent intact
    assert got["is_html"] is True and got["from"] == ATTACKER_EMAIL


def test_agent_reads_plain_text(client, attacker, agent):
    eid = send(client, attacker, body="just text").json()["id"]
    assert client.get(f"/agent/emails/{eid}", headers=agent).json()["content"] == "just text"


def test_agent_reply_goes_only_to_original_sender_and_marks_processed(client, attacker, agent):
    eid = send(client, attacker, subject="Hi").json()["id"]
    assert [m["id"] for m in client.get("/agent/emails", headers=agent).json()] == [eid]
    r = client.post(f"/agent/emails/{eid}/reply", json={"body": "hello"}, headers=agent)
    assert r.status_code == 201 and r.json()["to"] == ATTACKER_EMAIL
    assert client.get("/agent/emails", headers=agent).json() == []
    got = client.get("/mail/inbox", headers=attacker).json()[0]
    assert got["body"] == "hello" and got["subject"] == "Re: Hi"
    assert got["sender"]["email_address"] == TARGET_EMAIL


def test_agent_reply_cannot_choose_a_recipient(client, attacker, agent):
    eid = send(client, attacker).json()["id"]
    r = client.post(f"/agent/emails/{eid}/reply",
                    json={"body": "x", "to": "evil@example.com", "recipient": "evil@example.com"},
                    headers=agent)
    assert r.status_code == 201 and r.json()["to"] == ATTACKER_EMAIL


def test_agent_cannot_touch_mail_it_did_not_receive(client, target, agent):
    # An email the target SENT is not in the target's inbox, so the agent cannot read or answer it.
    sent_id = send(client, target, to=ATTACKER_EMAIL).json()["id"]
    assert client.get(f"/agent/emails/{sent_id}", headers=agent).status_code == 404
    assert client.post(f"/agent/emails/{sent_id}/reply", json={"body": "x"}, headers=agent).status_code == 404
    assert client.get("/agent/emails/9999", headers=agent).status_code == 404


def test_no_arbitrary_send_route_for_agent(client, agent):
    response = client.post(
        "/agent/send",
        json={"to": "x@y.z", "body": "b"},
        headers=agent,
    )
    assert response.status_code in (404, 405)

def test_mark_processed(client, attacker, agent):
    eid = send(client, attacker).json()["id"]
    assert client.post(f"/agent/emails/{eid}/processed", headers=agent).status_code == 204
    assert client.get("/agent/emails", headers=agent).json() == []

def test_forward_preserves_html_and_keeps_pending(client, attacker, agent):
    eid = send(
        client,
        attacker,
        subject="Original",
        body="",
        body_html=TRICKY_HTML,
    ).json()["id"]

    response = client.post(
        f"/agent/emails/{eid}/forward",
        json={},
        headers=agent,
    )

    assert response.status_code == 201
    assert response.json()["to"] == ATTACKER_EMAIL

    mail = client.get(
        f"/mail/{response.json()['id']}",
        headers=attacker,
    ).json()

    assert mail["subject"] == "Fwd: Original"
    assert mail["body_html"] == TRICKY_HTML
    assert mail["sender"]["email_address"] == TARGET_EMAIL
    assert "birthdate" not in mail["sender"]

    pending = client.get("/agent/emails", headers=agent).json()
    assert eid in [email["id"] for email in pending]


def test_forward_plain_and_maximum_subject(client, attacker, agent):
    eid = send(
        client,
        attacker,
        subject="x" * 255,
        body="plain content",
    ).json()["id"]

    response = client.post(
        f"/agent/emails/{eid}/forward",
        json={},
        headers=agent,
    )

    assert response.status_code == 201

    mail = client.get(
        f"/mail/{response.json()['id']}",
        headers=attacker,
    ).json()

    assert mail["body"] == "plain content"
    assert mail["body_html"] is None
    assert len(mail["subject"]) == 255


def test_agent_mutations_reject_user_tokens(client, attacker, target):
    eid = send(client, attacker).json()["id"]

    operations = [
        ("reply", {"body": "x"}),
        ("forward", {}),
        ("processed", {}),
    ]

    credentials = [
        {},
        attacker,
        target,
        {"Authorization": "Bearer wrong"},
    ]

    for suffix, body in operations:
        for headers in credentials:
            response = client.post(
                f"/agent/emails/{eid}/{suffix}",
                json=body,
                headers=headers,
            )
            assert response.status_code in (401, 403)


def test_forward_rejects_wrong_mailbox_deleted_missing_and_overrides(
    client, attacker, target, agent
):
    sent_id = send(
        client,
        target,
        to=ATTACKER_EMAIL,
    ).json()["id"]

    eid = send(client, attacker).json()["id"]

    response = client.post(
        f"/agent/emails/{eid}/forward",
        json={"to": "outside@example.com"},
        headers=agent,
    )
    assert response.status_code == 422

    client.delete(f"/mail/{eid}", headers=target)

    for bad_id in (sent_id, eid, 999999):
        response = client.post(
            f"/agent/emails/{bad_id}/forward",
            json={},
            headers=agent,
        )
        assert response.status_code == 404


def test_agent_token_not_a_user_session(client, agent):
    response = client.get("/mail/inbox", headers=agent)
    assert response.status_code == 401


def test_operation_logs_exclude_message_contents(
    client, attacker, agent, caplog
):
    import logging

    caplog.set_level(logging.INFO, logger="uvicorn.error")

    eid = send(
        client,
        attacker,
        subject="SECRET SUBJECT",
        body="SECRET BODY",
    ).json()["id"]

    client.get("/agent/emails", headers=agent)
    client.get(f"/agent/emails/{eid}", headers=agent)

    client.post(
        f"/agent/emails/{eid}/forward",
        json={},
        headers=agent,
    )

    client.post(
        f"/agent/emails/{eid}/reply",
        json={"body": "SECRET REPLY"},
        headers=agent,
    )

    client.post(
        f"/agent/emails/{eid}/processed",
        headers=agent,
    )

    for operation in ("list", "read", "forward", "reply", "processed"):
        assert f"operation={operation}" in caplog.text

    for private in (
        "SECRET SUBJECT",
        "SECRET BODY",
        "SECRET REPLY",
        agent["Authorization"],
    ):
        assert private not in caplog.text
