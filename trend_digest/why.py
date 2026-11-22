"""The optional "Why it matters" sentence under each item.

One model call covers the whole digest: it gets every item's id, title and
summary and must answer with a JSON object {id: sentence}. A sentence longer
than 25 words, or missing, leaves that item without one. If the call fails, the
digest is sent without any of these sentences.

`llm_from_env(config)` builds the model function from environment variables:
LLM_API_KEY (required to turn this on), LLM_BASE_URL (an OpenAI-compatible
base URL, default https://api.everyinfra.com/api/v1) and LLM_MODEL (default:
`llm_model` in digest.toml).
"""

import json
import os
import re

from .client import post_json

MAX_WORDS = 25
DEFAULT_BASE_URL = "https://api.everyinfra.com/api/v1"


def build_prompt(items):
    rows = [{"id": item["id"], "title": item["title"], "summary": item.get("summary") or ""}
            for item in items]
    return (
        "For each item below, write one sentence (at most 25 words) on why it matters to "
        "developers. Use only facts in its title and summary; do not add anything else. "
        "Answer with one JSON object that maps each id to its sentence, and nothing else.\n\n"
        + json.dumps(rows, ensure_ascii=False, indent=1)
    )


def parse_answer(answer):
    """Find the JSON object in the model's answer. Returns a dict or {}."""
    match = re.search(r"\{.*\}", answer or "", re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def usable(sentence):
    if not isinstance(sentence, str):
        return None
    sentence = " ".join(sentence.split())
    if not sentence or len(sentence.split()) > MAX_WORDS:
        return None
    return sentence


def add_why(items, llm):
    """Set item['why'] for every item the model answered well. Returns items."""
    if not llm or not items:
        return items
    try:
        answers = parse_answer(llm(build_prompt(items)))
    except Exception:  # the sentence is optional; never fail the digest over it
        answers = {}
    for item in items:
        item["why"] = usable(answers.get(item["id"]))
    return items


def llm_from_env(config, environ=None):
    """Return a callable(prompt) -> str, or None when LLM_API_KEY is not set."""
    environ = os.environ if environ is None else environ
    key = (environ.get("LLM_API_KEY") or "").strip()
    if not key:
        return None
    base = (environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = (environ.get("LLM_MODEL") or config.get("llm_model") or "").strip()

    def call(prompt):
        body = {"model": model, "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]}
        _, text = post_json(base + "/chat/completions", body, {"Authorization": f"Bearer {key}"})
        return json.loads(text)["choices"][0]["message"]["content"]

    return call
