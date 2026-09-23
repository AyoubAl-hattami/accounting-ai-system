"""One agent request is bounded, and the bound is what the proxy allows.

The agent shipped with no timeout on any of its Gemini calls and a retry loop
that slept in the request thread for whatever delay the provider suggested --
"Retrying in 59.8s" in the log, and measured requests of 154s, 170s and 179s
against an nginx proxy_read_timeout of 60s. D2 had already bounded every other
provider call in the codebase; this path was added after it and did not.

What is asserted here:

  - every call carries a timeout, and it is D2's, shortened when less of the
    request budget is left than that;
  - the retry loop is gone, so nothing sleeps in the request thread;
  - the whole request, including the fallback it degrades to, fits inside the
    proxy budget -- measured end to end against a provider that only fails.

No network and no database: the Gemini client is a stub and the session is a
MagicMock. The one real call these tests make is into dispatch_unified_agent.
"""

import ast
import pathlib
import time
from unittest.mock import MagicMock

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import unified_gemini_agent
from app.modules.accounting.services.ai_providers.gemini_provider import (
    REQUEST_TIMEOUT_SECONDS,
    model_calls_enabled,
    model_calls_suppressed,
)

AGENT_SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "services" / "unified_gemini_agent.py"
)

# nginx.production.conf. The budget has to leave room for the fallback to
# answer inside it, not merely to start inside it.
PROXY_READ_TIMEOUT_SECONDS = 60.0


class _AlwaysUnavailable:
    """A provider that fails the way the real one failed: 503, immediately."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.models = self
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "config": config})
        raise RuntimeError("503 UNAVAILABLE. This model is experiencing high demand.")


def test_the_budget_fits_inside_the_proxy_timeout():
    assert unified_gemini_agent.AGENT_BUDGET_SECONDS < PROXY_READ_TIMEOUT_SECONDS, (
        "The request budget must leave the proxy room to receive an answer."
    )
    assert (
        PROXY_READ_TIMEOUT_SECONDS - unified_gemini_agent.AGENT_BUDGET_SECONDS
        >= REQUEST_TIMEOUT_SECONDS / 2
    ), (
        "Too little of the proxy budget is left for the fallback to answer in."
    )


def test_every_call_is_bounded_by_the_smaller_of_the_two_limits():
    far = time.monotonic() + 3600
    assert unified_gemini_agent._remaining_ms(far) == int(REQUEST_TIMEOUT_SECONDS * 1000)

    near = time.monotonic() + 1.0
    bounded = unified_gemini_agent._remaining_ms(near)
    assert 0 < bounded <= 1000, (
        "With one second of budget left, a call must not be given twenty."
    )

    with pytest.raises(unified_gemini_agent._BudgetExhausted):
        unified_gemini_agent._remaining_ms(time.monotonic() - 0.01)


def test_the_timeout_reaches_the_sdk_call():
    client = _AlwaysUnavailable()
    with pytest.raises(RuntimeError):
        unified_gemini_agent._generate_content_within_budget(
            client=client,
            model="gemini-test",
            contents=[],
            config=unified_gemini_agent.types.GenerateContentConfig(temperature=0.1),
            deadline=time.monotonic() + 3600,
        )

    assert len(client.calls) == 1, "A transient failure must not be retried."
    http_options = client.calls[0]["config"].http_options
    assert http_options is not None, "The call went out with no timeout at all."
    assert http_options.timeout == int(REQUEST_TIMEOUT_SECONDS * 1000)


def test_the_timeout_is_real_against_a_slow_server():
    """The assertion above reads the config; this one watches the socket.

    A timeout that the SDK accepts and ignores would pass every test here and
    hang in production, so the call goes through the real google-genai client
    to a stub HTTP server on localhost -- no external network, no API key.
    """
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    delay = [0.0]

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
            time.sleep(delay[0])
            body = json.dumps(
                {
                    "candidates": [
                        {
                            "content": {"role": "model", "parts": [{"text": "stub answer"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    class _QuietServer(HTTPServer):
        def handle_error(self, request, client_address):
            pass  # the aborted connection IS the assertion below

    server = _QuietServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = unified_gemini_agent.genai.Client(
            api_key="stub",
            http_options={"base_url": f"http://127.0.0.1:{server.server_address[1]}"},
        )
        contents = [
            unified_gemini_agent.types.Content(
                role="user",
                parts=[unified_gemini_agent.types.Part.from_text(text="hi")],
            )
        ]
        config = unified_gemini_agent.types.GenerateContentConfig(temperature=0.1)

        answered = unified_gemini_agent._generate_content_within_budget(
            client=client,
            model="gemini-test",
            contents=contents,
            config=config,
            deadline=time.monotonic() + 3600,
        )
        assert answered.text == "stub answer"

        delay[0] = 3.0
        started = time.monotonic()
        with pytest.raises(Exception) as caught:
            unified_gemini_agent._generate_content_within_budget(
                client=client,
                model="gemini-test",
                contents=contents,
                config=config,
                deadline=time.monotonic() + 0.8,
            )
        elapsed = time.monotonic() - started
        assert elapsed < 2.0, (
            f"A call given 0.8s of budget ran for {elapsed:.1f}s against a server "
            "that answers in 3s. The timeout did not reach the socket."
        )
        # What the abort surfaces as is the platform's business: httpx raises
        # ReadTimeout when it gives up reading, and ReadError (WinError 10053)
        # when Windows tears the socket down first. Both are the timeout
        # firing, and both reach the caller as the exception that triggers the
        # fallback -- which is the behaviour being pinned. Asserting on the
        # message would pin the platform instead.
        assert caught.value is not None
    finally:
        server.shutdown()
        server.server_close()


def test_nothing_sleeps_in_the_request_thread():
    """The retry loop slept; the shape that did it must not come back."""
    sleeps = [
        node
        for node in ast.walk(ast.parse(AGENT_SOURCE.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "sleep"
    ]
    assert not sleeps, (
        f"{AGENT_SOURCE.name} sleeps in the request thread at line(s) "
        f"{[node.lineno for node in sleeps]}. Waiting out a 429 costs the whole "
        "request; the deterministic fallback answers the same question."
    )


def test_a_failing_provider_answers_from_the_fallback_inside_the_budget(monkeypatch):
    """End to end: the agent path fails on every call, and the request still
    returns an answer well inside the proxy budget."""
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _AlwaysUnavailable)
    monkeypatch.setattr(
        unified_gemini_agent.ProjectKnowledgeService,
        "get_or_create_store",
        lambda self: "fileSearchStores/probe",
    )

    seen: dict[str, object] = {}

    def _fallback(**kwargs):
        seen["model_calls_enabled"] = model_calls_enabled()
        return "fallback reply"

    monkeypatch.setattr(
        "app.modules.accounting.services.gemini_assistant_service."
        "dispatch_gemini_assistant",
        _fallback,
    )

    started = time.monotonic()
    reply = unified_gemini_agent.dispatch_unified_agent(
        db=MagicMock(),
        company_id=1,
        user_role="admin",
        message="What is our net profit?",
        page_context=PageContext(page="dashboard", route="/dashboard"),
        language="en",
    )
    elapsed = time.monotonic() - started

    assert reply == "fallback reply"
    assert elapsed < PROXY_READ_TIMEOUT_SECONDS, (
        f"The request took {elapsed:.1f}s against a {PROXY_READ_TIMEOUT_SECONDS:.0f}s "
        "proxy timeout."
    )
    assert seen["model_calls_enabled"] is False, (
        "The fallback ran with model calls still enabled, so it could open two "
        "fresh 20s calls after the budget was already spent."
    )


def test_suppression_is_scoped_to_the_block():
    """A leaked suppression would silently turn the model off for later
    requests on the same worker thread."""
    assert model_calls_enabled() is True
    with model_calls_suppressed():
        assert model_calls_enabled() is False
    assert model_calls_enabled() is True

    with pytest.raises(ValueError):
        with model_calls_suppressed():
            raise ValueError("boom")
    assert model_calls_enabled() is True
