"""Explicit LM Studio compatibility probe; excluded from normal test discovery."""
from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "google/gemma-4-12b-qat"
_ONE_PIXEL_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/"
    "9K3w6QAAAABJRU5ErkJggg=="
)


def _request_completion(messages: list[dict[str, object]]) -> str:
    payload = json.dumps(
        {
            "model": LM_STUDIO_MODEL,
            "temperature": 0,
            "max_tokens": 128,
            "messages": messages,
        }
    ).encode("utf-8")
    request = Request(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise SystemExit(f"LM Studio probe failed: {exc}") from exc
    choices = body.get("choices") if isinstance(body, dict) else None
    message = choices[0].get("message", {}) if choices else {}
    content = message.get("content") or message.get("reasoning_content")
    if not isinstance(content, str) or not content.strip():
        raise SystemExit(f"LM Studio returned an invalid chat completion: {body!r}")
    return content.strip()


def run_probe() -> None:
    """Send text and image schema checks without changing application configuration."""
    if os.environ.get("RUN_LMSTUDIO_INTEGRATION") != "1":
        raise SystemExit("Set RUN_LMSTUDIO_INTEGRATION=1 to run the local LM Studio probe.")

    text_response = _request_completion(
        [
            {"role": "system", "content": "Do not explain your reasoning. Reply with exactly: OK"},
            {"role": "user", "content": "Connectivity test"},
        ]
    )
    if text_response != "OK":
        raise SystemExit(f"LM Studio returned an unexpected text response: {text_response!r}")

    vision_response = _request_completion(
        [
            {
                "role": "system",
                "content": "Answer the question using the attached image.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is the predominant color in this image?"},
                    {"type": "image_url", "image_url": {"url": _ONE_PIXEL_PNG_DATA_URL}},
                ],
            },
        ]
    )
    if "red" not in vision_response.casefold() and "红" not in vision_response:
        raise SystemExit(f"LM Studio did not recognize the probe image: {vision_response!r}")
    print(f"LM Studio text and vision probes passed with {LM_STUDIO_MODEL}")


if __name__ == "__main__":
    run_probe()
