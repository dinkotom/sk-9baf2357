"""Samostatný klient pro Bakaláři REST API v3 (jen standardní knihovna).

V CI se přihlašuje vždy znovu heslem (běh je efemérní, tokeny se neukládají).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class BakalariError(RuntimeError):
    pass


class BakalariClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api = f"{self.base_url}/api/3"
        self.login_url = f"{self.base_url}/api/login"
        self.username = username
        self.password = password
        self.timeout = timeout
        self._token: str | None = None

    def _send(self, req):
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise BakalariError(f"HTTP {e.code} {e.reason}: {e.read().decode(errors='replace')[:300]}") from e
        except urllib.error.URLError as e:
            raise BakalariError(f"Síťová chyba: {e.reason}") from e

    def login(self) -> None:
        body = urllib.parse.urlencode({
            "client_id": "ANDR",
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }).encode()
        req = urllib.request.Request(
            self.login_url, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
        )
        self._token = self._send(req).get("access_token")
        if not self._token:
            raise BakalariError("Přihlášení selhalo: nevrácen access_token.")

    def _call(self, method: str, path: str) -> Any:
        if not self._token:
            self.login()
        req = urllib.request.Request(
            f"{self.api}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {self._token}"}, method=method,
        )
        return self._send(req)

    def received_messages(self) -> Any:
        return self._call("POST", "komens/messages/received")

    def noticeboard(self) -> Any:
        return self._call("POST", "komens/messages/noticeboard")

    def user_info(self) -> Any:
        return self._call("GET", "user")
