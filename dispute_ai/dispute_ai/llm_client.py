import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()


def _make_client() -> OpenAI:
    """
    Build the appropriate OpenAI-compatible client based on LLM_PROVIDER.

    - ollama:  Ollama's OpenAI-compatible local endpoint. No API key needed.
    - bedrock: Amazon Bedrock via its OpenAI-compatible endpoint.
               Requires AWS credentials in environment.

    Both use the `openai` SDK — only the base_url and api_key differ.
    AutoGen also uses this client under the hood via autogen-ext[openai].
    """
    if _PROVIDER == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OpenAI(base_url=base_url, api_key="ollama")  # api_key value is ignored by Ollama

    if _PROVIDER == "bedrock":
        # Amazon Bedrock exposes an OpenAI-compatible endpoint.
        # Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars.
        region = os.getenv("AWS_REGION", "ap-south-1")
        return OpenAI(
            base_url=f"https://bedrock-runtime.{region}.amazonaws.com/model",
            api_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
        )

    raise ValueError(f"Unknown LLM_PROVIDER: '{_PROVIDER}'. Must be 'ollama' or 'bedrock'.")


def _get_model() -> str:
    if _PROVIDER == "ollama":
        return os.getenv("OLLAMA_MODEL", "gemma3")
    if _PROVIDER == "bedrock":
        return os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    return "gemma3"


_client = _make_client()
_model = _get_model()


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
            response = _client.chat.completions.create(
                model=_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.1,   # low temperature for consistent structured output
            )
            text = response.choices[0].message.content.strip()

            if expect_json:
                # Strip markdown code fences if the model wraps JSON in them
                if "```" in text:
                    parts = text.split("```")
                    # Find the JSON block: it's between the first and second fence
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
    return {
        "config_list": [
            {
                "model": _model,
                "base_url": (
                    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                    if _PROVIDER == "ollama"
                    else f"https://bedrock-runtime.{os.getenv('AWS_REGION', 'ap-south-1')}.amazonaws.com/model"
                ),
                "api_key": "ollama" if _PROVIDER == "ollama" else os.getenv("AWS_ACCESS_KEY_ID", ""),
                "api_type": "openai",  # AutoGen treats both as OpenAI-compatible
            }
        ],
        "temperature": 0.1,
        "timeout": 120,
    }
