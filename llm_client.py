import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class LlmClient:
    def __init__(self, api_base: str, api_key: str = "", default_model: str = "") -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model

    def request(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        timeout_s: int = 60,
        headers: Optional[Dict[str, str]] = None,
        model: str = "",
    ) -> Dict[str, Any]:
        url = f"{self.api_base}{path}"

        body_payload = payload
        if model:
            body_payload = dict(payload)
            body_payload["model"] = model
        elif self.default_model and "model" not in payload:
            body_payload = dict(payload)
            body_payload["model"] = self.default_model

        body = json.dumps(body_payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url=url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                resp_body = resp.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {err_body}") from e

        return json.loads(resp_body.decode("utf-8"))

    def chat_completions(
        self,
        payload: Dict[str, Any],
        *,
        timeout_s: int = 60,
        headers: Optional[Dict[str, str]] = None,
        model: str = "",
    ) -> Dict[str, Any]:
        return self.request(
            "/v1/chat/completions",
            payload,
            timeout_s=timeout_s,
            headers=headers,
            model=model,
        )


def load_client_from_config(config_path: str = "llm_configs.json") -> LlmClient:
    api_base = os.environ.get("OPENAI_API_BASE", "").strip()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    default_model = os.environ.get("OPENAI_MODEL", "").strip()

    if api_base and api_key:
        return LlmClient(api_base=api_base, api_key=api_key, default_model=default_model)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    api_base = (api_base or cfg.get("openai_api_base") or "").strip()
    api_key = api_key or (cfg.get("openai_api_key") or "").strip()
    if not default_model:
        default_model = (cfg.get("default_model") or "").strip()

    return LlmClient(api_base=api_base, api_key=api_key, default_model=default_model)
