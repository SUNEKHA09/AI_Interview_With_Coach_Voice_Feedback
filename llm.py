import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent / ".env")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PREFERRED = os.getenv("GEMINI_MODEL", "").strip().replace("models/", "")

ROLE_FOCUS = {
    "AI Engineer": "Focus: LLMs, prompt engineering, RAG, vector databases, agents, APIs, deployment, evaluation of AI systems.",
    "ML Engineer": "Focus: ML algorithms, feature engineering, model evaluation metrics, overfitting, MLOps, deployment, data pipelines.",
    "Data Scientist": "Focus: statistics, ML modelling, experiments, SQL, storytelling with data.",
    "Data Analyst": "Focus: SQL, Excel, dashboards, statistics, business insights.",
    "Python Developer": "Focus: Python core, OOP, data structures, APIs, testing, databases.",
}

_BAD = ("image", "tts", "live", "audio", "embed", "native", "robotics", "computer", "veo", "imagen")
_state = {"discovered": None, "good": None}


class LLMError(Exception):
    pass


def has_key() -> bool:
    return bool(API_KEY) and API_KEY != "your_key_here"


def _client():
    try:
        opts = types.HttpOptions(timeout=40000, retry_options=types.HttpRetryOptions(attempts=1))
    except Exception:
        opts = types.HttpOptions(timeout=40000)
    return genai.Client(api_key=API_KEY, http_options=opts)


def _discover():
    """Find flash models available for this key (cached)."""
    if _state["discovered"] is not None:
        return _state["discovered"]
    names = []
    try:
        c = _client()
        for m in c.models.list():
            n = m.name.replace("models/", "")
            acts = getattr(m, "supported_actions", None)
            if acts and "generateContent" not in acts:
                continue
            if "flash" not in n or any(b in n for b in _BAD):
                continue
            names.append(n)
        c.close()
    except Exception:
        pass
    names.sort(reverse=True)
    names.sort(key=lambda n: 0 if "lite" in n else 1)  # lite = fastest
    _state["discovered"] = names
    return names


def _call(client, model, prompt, json_mode):
    kw = {"response_mime_type": "application/json"} if json_mode else {}
    configs = []
    try:  # thinking off = much faster
        configs.append(types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0), **kw))
    except Exception:
        pass
    configs.append(types.GenerateContentConfig(**kw) if kw else None)
    last = None
    for cfg in configs:
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            text = (r.text or "").strip()
            if text:
                return text
            last = ValueError("empty response")
        except Exception as e:
            last = e
            if "400" in str(e) or "INVALID_ARGUMENT" in str(e):
                continue
            raise
    raise last


def _friendly(e: Exception) -> str:
    m = str(e)
    if "API_KEY_INVALID" in m or "API key not valid" in m or "403" in m or "PERMISSION_DENIED" in m:
        return "API key problem. Check GEMINI_API_KEY in your .env file."
    if "429" in m or "RESOURCE_EXHAUSTED" in m:
        return "Free AI limit reached for now. Wait 1 minute and try again."
    if "503" in m or "UNAVAILABLE" in m or "timed out" in m.lower() or "timeout" in m.lower():
        return "Google AI server is busy. Wait 20 seconds and try again."
    if "404" in m or "NOT_FOUND" in m:
        return "No working AI model found for your key. Check GEMINI_MODEL in .env."
    return f"AI error: {m[:150]}"


def _ask(prompt: str, json_mode: bool = False) -> str:
    if not has_key():
        raise LLMError("API key missing. Put GEMINI_API_KEY in your .env file and restart.")
    candidates = []
    for m in [_state["good"], PREFERRED] + _discover():
        if m and m not in candidates:
            candidates.append(m)
    if not candidates:
        candidates = ["gemini-2.5-flash"]
    last = None
    for model in candidates[:5]:
        for attempt in range(2):
            client = _client()
            try:
                text = _call(client, model, prompt, json_mode)
                _state["good"] = model
                return text
            except Exception as e:
                last = e
                msg = str(e)
                if "API_KEY_INVALID" in msg or "API key not valid" in msg:
                    raise LLMError(_friendly(e))
                if "404" in msg or "NOT_FOUND" in msg:
                    break  # try next model
                time.sleep(1.5)
            finally:
                client.close()
    raise LLMError(_friendly(last) if last else "Unknown AI error.")


def _parse_json(raw: str):
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else None


def generate_questions(role, level, n, context, weak_topics):
    prompt = f"""You are a senior interviewer hiring a {level} {role}.
{ROLE_FOCUS.get(role, '')}
Candidate context (job description / resume, may be empty): {context[:3500]}
Known weak areas to probe if relevant: {weak_topics}
Write exactly {n} interview questions ordered from easy to hard.
Mix technical and behavioural questions. If candidate context is present, base at least one question on it.
Each question: a single question, max 35 words, no numbering.
Return ONLY JSON: {{"questions": ["...", "..."]}}"""
    raw = _ask(prompt, json_mode=True)
    qs = []
    try:
        data = _parse_json(raw)
        qs = [str(q).strip() for q in data.get("questions", []) if str(q).strip()]
    except Exception:
        qs = [ln.strip(" -*0123456789.") for ln in raw.splitlines() if "?" in ln]
    if not qs:
        raise LLMError("AI did not return questions. Please click Start again.")
    return qs[:n]


def evaluate(role, level, question, answer):
    prompt = f"""You are a strict but kind interview coach. Role: {level} {role}.
Question: {question}
Candidate answer (transcript): {answer[:2500]}

Return ONLY JSON with exactly these keys:
{{"clarity":1-10,"relevance":1-10,"confidence":1-10,"technical":1-10,
"star_used":true/false,
"strengths":["max 2 short points"],
"improvements":["max 2 short points"],
"better_answer":"strong sample answer, 3-4 sentences",
"weak_topic":"2-3 word topic to practise"}}"""
    raw = _ask(prompt, json_mode=True)
    try:
        ev = _parse_json(raw) or {}
    except Exception:
        ev = {}
    keys = ["clarity", "relevance", "confidence", "technical"]
    vals = []
    for k in keys:
        try:
            v = max(1.0, min(10.0, float(ev.get(k, 5))))
        except Exception:
            v = 5.0
        ev[k] = int(v) if v == int(v) else v
        vals.append(v)
    ev["score"] = round(sum(vals) / 4, 1)
    ev["star_used"] = bool(ev.get("star_used", False))
    ev["strengths"] = [str(x) for x in ev.get("strengths", [])][:3]
    ev["improvements"] = [str(x) for x in ev.get("improvements", [])][:3]
    ev["better_answer"] = str(ev.get("better_answer", ""))
    ev["weak_topic"] = str(ev.get("weak_topic", "general"))
    return ev