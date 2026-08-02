"""Django email backend using Resend's HTTPS API.

Render free web services block outbound SMTP (ports 25/465/587), so SMTP
to smtp.resend.com hangs until the worker is killed. Resend's HTTP API uses
port 443 and works on the free tier.
"""

from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


class ResendAPIEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "") or ""
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError(
                    "RESEND_API_KEY is not set. Add it on Render (your Resend re_… key)."
                )
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send(message, api_key)
                sent += 1
            except Exception:
                logger.exception("Resend API send failed")
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message, api_key: str) -> None:
        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        payload = {
            "from": from_email,
            "to": list(message.to),
            "subject": message.subject or "",
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        body = message.body or ""
        html_body = None
        if hasattr(message, "alternatives"):
            for content, mimetype in message.alternatives:
                if mimetype == "text/html":
                    html_body = content
                    break
        if html_body:
            payload["html"] = html_body
            if body:
                payload["text"] = body
        else:
            payload["text"] = body

        data = json.dumps(payload).encode("utf-8")
        request = Request(
            RESEND_ENDPOINT,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PrettyAffairsHub-ResendBackend/1.0",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Resend API connection failed: {exc.reason}") from exc
