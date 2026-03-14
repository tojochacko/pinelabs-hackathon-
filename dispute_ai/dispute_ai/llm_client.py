import json
import logging
import os
import time
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("dispute_ai.bedrock")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()


def _get_model() -> str:
    if _PROVIDER == "ollama":
        return os.getenv("OLLAMA_MODEL", "gemma3")
    if _PROVIDER == "bedrock":
        return os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    return "gemma3"


_model = _get_model()


def _make_openai_client() -> OpenAI:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return OpenAI(base_url=base_url, api_key="ollama")


def _call_bedrock(system: str, user: str, max_tokens: int) -> str:
    """
    Call Bedrock Converse API using a Bearer token (Bedrock API key).
    Uses httpx directly — boto3 does not support Bearer token auth.
    """
    region = os.getenv("AWS_REGION", "us-east-1")
    token = os.getenv("AWS_BEARER_TOKEN_BEDROCK", "")
    encoded_model = quote(_model, safe="")
    url = f"https://bedrock-runtime.{region}.amazonaws.com/model/{encoded_model}/converse"

    payload = {
        "system": [{"text": system}],
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.1},
    }

    logger.info("Bedrock request | model=%s | max_tokens=%d | system_len=%d | user_len=%d",
                _model, max_tokens, len(system), len(user))

    start = time.monotonic()
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        elapsed = time.monotonic() - start
        response.raise_for_status()
        body = response.json()
        text = body["output"]["message"]["content"][0]["text"].strip()
        usage = body.get("usage", {})
        logger.info(
            "Bedrock response | status=%d | latency=%.2fs | input_tokens=%s | output_tokens=%s | response_len=%d",
            response.status_code,
            elapsed,
            usage.get("inputTokens", "?"),
            usage.get("outputTokens", "?"),
            len(text),
        )
        return text
    except httpx.HTTPStatusError as e:
        elapsed = time.monotonic() - start
        logger.error("Bedrock error | status=%d | latency=%.2fs | body=%s",
                     e.response.status_code, elapsed, e.response.text[:500])
        raise
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("Bedrock error | latency=%.2fs | error=%s", elapsed, e)
        raise


def call_llm(
    system: str,
    user: str,
    expect_json: bool = True,
    max_tokens: int = 1500,
) -> dict | str:
    """
    Provider-agnostic LLM call with retry logic.
    Returns a parsed dict if expect_json=True, otherwise a raw string.
    """
    for attempt in range(3):
        try:
            if _PROVIDER == "bedrock":
                text = _call_bedrock(system, user, max_tokens)
            else:
                client = _make_openai_client()
                response = client.chat.completions.create(
                    model=_model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    temperature=0.1,
                )
                text = response.choices[0].message.content.strip()

            if expect_json:
                if "```" in text:
                    parts = text.split("```")
                    for part in parts:
                        cleaned = part.strip()
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:].strip()
                        try:
                            return json.loads(cleaned)
                        except json.JSONDecodeError:
                            continue
                return json.loads(text)

            return text

        except json.JSONDecodeError as e:
            if attempt == 2:
                raise ValueError(
                    f"LLM returned invalid JSON after 3 attempts.\n"
                    f"Raw response: {text}\n"
                    f"Error: {e}"
                )
            time.sleep(1)

        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)


def get_autogen_llm_config() -> dict:
    """
    Returns an AutoGen-compatible llm_config dict.
    Used by pipeline.py to configure AssistantAgents.
    """
    if _PROVIDER == "bedrock":
        region = os.getenv("AWS_REGION", "us-east-1")
        return {
            "config_list": [
                {
                    "model": _model,
                    "base_url": f"https://bedrock-runtime.{region}.amazonaws.com",
                    "api_key": os.getenv("AWS_BEARER_TOKEN_BEDROCK", ""),
                    "api_type": "openai",
                }
            ],
            "temperature": 0.1,
            "timeout": 120,
        }
    return {
        "config_list": [
            {
                "model": _model,
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                "api_key": "ollama",
                "api_type": "openai",
            }
        ],
        "temperature": 0.1,
        "timeout": 120,
    }
