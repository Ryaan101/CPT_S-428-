"""Static guards for the email-rendering rules. They run without Node."""
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "src"


def test_no_v_html_or_innerhtml_anywhere():
    for f in SRC.rglob("*"):
        if f.suffix in (".vue", ".js"):
            text = f.read_text(encoding="utf-8")
            assert "v-html" not in text, f"{f} uses v-html"
            assert "innerHTML" not in text, f"{f} uses innerHTML"


def test_html_mail_is_rendered_in_a_fully_sandboxed_iframe():
    viewer = (SRC / "components" / "HtmlViewer.vue").read_text(encoding="utf-8")
    assert 'sandbox=""' in viewer  # no allow-scripts, no allow-same-origin
    assert "allow-" not in viewer
    assert "Content-Security-Policy" in viewer
