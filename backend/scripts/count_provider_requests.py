# -*- coding: utf-8 -*-
"""Count provider HTTP requests, at the transport, not at the client object.

WHY THIS EXISTS
---------------
Every "provider calls" figure in `docs/` up to 2026-09-29 was produced by
wrapping ``google.genai.Client.__init__`` and counting CONSTRUCTIONS. That
answers "how many times did we build a client", which is not the question. It
cannot see a second request issued through one client, and it cannot see an
SDK-internal retry at all -- so a row reported as one call was one client and
an unknown number of requests.

This counts requests. ``google.genai`` issues them through
``httpx.Client.send`` (`_api_client.py:1380`), and any retry policy re-enters
that method, so a wrapper there sees every attempt. ``HTTPTransport.handle_request``
is wrapped underneath it as well, because a connection-level retry happens
below ``send`` and would otherwise be invisible -- if the two numbers ever
disagree, the difference IS the hidden work.

Only requests to the provider host are attributed; the process makes other
HTTP calls and counting those would repeat the original error in a new place.

USE
---
    from scripts.count_provider_requests import counting_provider_requests

    with counting_provider_requests() as counter:
        ...                      # whatever you are measuring
    print(counter.summary())     # attempts, statuses, the requests themselves

Run it directly to measure one clarification turn end to end:

    python scripts/count_provider_requests.py [company_id]
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

import httpx

PROVIDER_HOSTS = ("generativelanguage.googleapis.com", "aiplatform.googleapis.com")


@dataclass
class ProviderRequest:
    """One HTTP attempt against the provider, whatever its outcome."""

    method: str
    path: str
    status: int | None
    error: str | None
    seconds: float
    layer: str  # "send" or "transport"


@dataclass
class RequestCounter:
    requests: list[ProviderRequest] = field(default_factory=list)

    @property
    def attempts(self) -> int:
        """HTTP attempts seen at `httpx.Client.send`."""
        return sum(1 for r in self.requests if r.layer == "send")

    @property
    def transport_attempts(self) -> int:
        """Attempts seen one layer lower. Larger means a hidden retry."""
        return sum(1 for r in self.requests if r.layer == "transport")

    def summary(self) -> str:
        lines = [
            f"provider HTTP attempts (send)      : {self.attempts}",
            f"provider HTTP attempts (transport) : {self.transport_attempts}",
        ]
        if self.transport_attempts > self.attempts:
            lines.append(
                f"  -> {self.transport_attempts - self.attempts} retried BELOW send; "
                "a client-object counter could never have seen these"
            )
        for request in self.requests:
            if request.layer != "send":
                continue
            outcome = request.error or f"HTTP {request.status}"
            lines.append(f"   {request.method} {request.path}  {outcome}"
                         f"  {request.seconds:.2f}s")
        return "\n".join(lines)


def _is_provider(url) -> bool:
    return any(host in str(url.host) for host in PROVIDER_HOSTS)


@contextmanager
def counting_provider_requests():
    """Count every provider HTTP attempt made inside the block."""
    counter = RequestCounter()
    real_send = httpx.Client.send
    real_handle = httpx.HTTPTransport.handle_request

    def send(self, request, **kwargs):
        if not _is_provider(request.url):
            return real_send(self, request, **kwargs)
        started = time.time()
        try:
            response = real_send(self, request, **kwargs)
        except Exception as exc:
            counter.requests.append(ProviderRequest(
                request.method, request.url.path, None, type(exc).__name__,
                time.time() - started, "send"))
            raise
        counter.requests.append(ProviderRequest(
            request.method, request.url.path, response.status_code, None,
            time.time() - started, "send"))
        return response

    def handle_request(self, request):
        if not _is_provider(request.url):
            return real_handle(self, request)
        started = time.time()
        try:
            response = real_handle(self, request)
        except Exception as exc:
            counter.requests.append(ProviderRequest(
                request.method, request.url.path, None, type(exc).__name__,
                time.time() - started, "transport"))
            raise
        counter.requests.append(ProviderRequest(
            request.method, request.url.path, response.status_code, None,
            time.time() - started, "transport"))
        return response

    httpx.Client.send = send
    httpx.HTTPTransport.handle_request = handle_request
    try:
        yield counter
    finally:
        httpx.Client.send = real_send
        httpx.HTTPTransport.handle_request = real_handle


def _measure(company_id: int) -> None:
    """One clarification turn, three ways, with the requests counted."""
    sys.path.insert(0, ".")
    sys.stdout.reconfigure(encoding="utf-8")

    from app.core.database import SessionLocal
    from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
    from app.modules.accounting.services import gemini_assistant_service as svc

    db = SessionLocal()
    page = PageContext(page="dashboard", route="/dashboard")

    def turn_one():
        with counting_provider_requests() as counter:
            reply = svc.dispatch_gemini_assistant(
                db=db, company_id=company_id, user_role="admin",
                message="دفعت 300 كهربا", page_context=page, language="ar")
        return reply, counter

    def turn_two(first, answer):
        with counting_provider_requests() as counter:
            reply = svc.dispatch_gemini_assistant(
                db=db, company_id=company_id, user_role="admin", message=answer,
                page_context=page, language="ar",
                pending_context_token=first.pending_context_token)
        return reply, counter

    print("== turn 1: the message that opens the clarification ==")
    first, counter = turn_one()
    print(counter.summary())
    print()

    for label, answer in (("an offered option", "2"),
                          ("an escalated reply", "من محفظة جيب")):
        print(f"== turn 2, {label}: {answer!r} ==")
        first, _ = turn_one()
        reply, counter = turn_two(first, answer)
        account = None
        if reply.suggested_action and reply.suggested_action.payload:
            for line in reply.suggested_action.payload.lines:
                if str(line.account_code).startswith("1"):
                    account = f"{line.account_code} {line.account_name}"
        print(f"   drafted: {account or '(' + str(reply.intent) + ')'}")
        print(counter.summary())
        print()


if __name__ == "__main__":
    _measure(int(sys.argv[1]) if len(sys.argv) > 1 else 13116)
