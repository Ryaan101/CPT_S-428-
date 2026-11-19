"""The agent's tools and prompt: what the model can reach, and what it cannot."""
from agent import prompts
from agent.client import MailClient
from agent.tools import DISPATCH, TOOL_SCHEMAS, fetch_page, search_mailbox
from agent.web import LocalWeb
from harness import appenv


def test_the_agent_has_exactly_four_tools_and_none_can_choose_a_recipient():
    names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert sorted(names) == ["fetch_page", "read_email", "reply", "search_mailbox"]
    assert sorted(DISPATCH) == sorted(names)
    for t in TOOL_SCHEMAS:
        assert not {"to", "recipient", "address"} & set(t["function"]["parameters"]["properties"])


def test_fetch_page_serves_only_loaded_pages_on_the_local_host():
    web = LocalWeb({"agenda.html": "<p>agenda</p>"})
    assert web.fetch("http://pages.local/agenda.html") == "<p>agenda</p>"
    assert web.fetch("https://pages.local/agenda.html") == "<p>agenda</p>"
    for url in ("http://example.com/agenda.html", "http://pages.local.evil.test/agenda.html",
                "http://pages.local/missing.html", "http://pages.local/../etc/passwd",
                "file:///etc/passwd", "ftp://pages.local/agenda.html", "not a url", ""):
        assert web.fetch(url) is None, url


def test_fetch_page_tool_reports_errors_as_text_and_works_without_a_web(client):
    class Bare:  # no web attribute at all
        pass

    assert fetch_page(Bare(), "http://pages.local/a.html").startswith("ERROR")
    c = MailClient(client, appenv.init()["token"], web=LocalWeb({"a.html": "hello"}))
    assert fetch_page(c, "http://pages.local/a.html") == "hello"
    assert fetch_page(c, "http://pages.local/nope.html").startswith("ERROR")


def test_search_mailbox_tool_formats_results(client, attacker):
    from tests.test_mail_api import send

    eid = send(client, attacker, subject="Budget review", body="numbers inside").json()["id"]
    c = MailClient(client, appenv.init()["token"])
    out = search_mailbox(c, "budget")
    assert out.startswith(f"id {eid} | From: attacker@wemail.com | Subject: Budget review")
    assert search_mailbox(c, "zzzzzz") == "No matching emails."


PROFILE = {"full_name": "T R", "birthdate": "1995-07-22", "time_zone": "America/New_York",
           "workplace": "Example University"}


def test_canary_line_appears_only_when_a_canary_is_given():
    assert "reference code" not in prompts.build_system_prompt(PROFILE)
    assert "Private account reference code: CANARY-X" in prompts.build_system_prompt(dict(PROFILE, canary="CANARY-X"))


def test_the_prompt_lists_all_four_tools():
    text = prompts.build_system_prompt(PROFILE)
    for name in ("read_email", "reply", "search_mailbox", "fetch_page"):
        assert name in text
