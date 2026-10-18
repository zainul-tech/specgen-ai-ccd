
"""
AI Processing Engine for SpecGen AI.
Uses Google Gemini as the LLM provider.
"""
import os
import json
try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
_client = None


def _get_client():
    """Create the Gemini client only when needed."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise GenerationError(
                "No GEMINI_API_KEY set on the server. "
                "Add it to backend/.env to enable generation."
            )
        _client = genai.Client(api_key=api_key)
    return _client


GENERATION_PROMPT = """You are the AI Processing Engine inside SpecGen AI, a tool that turns a
one-line software project idea into a draft requirements package.

Given this idea:
"{idea}"

Reply with ONLY a JSON object (no prose, no markdown fence) with exactly this shape:
{{
  "classification": {{"type": string, "domain": string, "users": string}},
  "functionalRequirements": [{{"id": string, "text": string, "priority": "High"|"Medium"|"Low"}},
  ],
  "userStories": [{{"role": string, "goal": string, "benefit": string}}],
  "useCases": [{{"name": string, "actor": string, "precondition": string, "mainFlow": string, "postcondition": string}}],
  "risks": [{{"description": string, "likelihood": "Low"|"Medium"|"High", "impact": "Low"|"Medium"|"High", "mitigation": string}}],
  "testCases": [{{"feature": string, "input": string, "expected": string}}],
  "costEstimate": [{{"area": string, "effortLevel": "Low"|"Medium"|"High", "notes": string}}]
}}
Rules: 6-8 functionalRequirements with ids like REQ-1, REQ-2, ordered by priority;
4 userStories; 3 useCases for the highest-priority stories (mainFlow as a short numbered sequence in one string);
4 risks, each with a concrete one-sentence mitigation; 4 testCases;
costEstimate with exactly these 6 areas in this order: "Frontend", "Backend", "AI integration & prompt tuning", "Database", "Export/Reporting", "Testing".
Be specific to the idea given, not generic boilerplate."""


class GenerationError(Exception):
    """Raised when the LLM call fails or returns unparsable output."""


def _extract_json(raw_text: str) -> dict:
    """Parse JSON, including responses wrapped in markdown fences."""
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()

    return json.loads(raw_text)


def _generate_text(prompt: str, max_tokens: int) -> str:
    """Generate text using Gemini."""
    response = _get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        },
    )
    if not response.text:
        raise GenerationError("Gemini returned an empty response.")
    return response.text.strip()


def generate_draft(idea_text: str) -> dict:
    """Generate a requirements draft and return it as a dictionary."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise GenerationError(
            "No GEMINI_API_KEY set on the server. "
            "Add it to backend/.env to enable generation."
        )

    try:
        prompt = GENERATION_PROMPT.format(idea=idea_text)
        raw_text = _generate_text(prompt, 2000)
        return _extract_json(raw_text)
    except json.JSONDecodeError as e:
        raise GenerationError(
            f"Could not parse the model's response as JSON: {e}"
        ) from e
    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(f"Gemini API call failed: {e}") from e


REWORD_PROMPT = """You are helping improve software requirements. For each flagged requirement below,
write ONE improved replacement requirement that fixes the stated problem while keeping the original intent.
Use concrete, measurable criteria where the problem is vagueness.

Flagged requirements (JSON):
{items}

Reply with ONLY a JSON object mapping each req_id to its improved requirement text, e.g.
{{"REQ-3": "The system shall ..."}}. No prose, no markdown fence."""


def suggest_rewordings(flagged: list) -> dict:
    """Return optional AI-generated requirement improvements."""
    if not flagged or not os.environ.get("GEMINI_API_KEY"):
        return {}

    try:
        prompt = REWORD_PROMPT.format(items=json.dumps(flagged))
        raw = _generate_text(prompt, 1200)
        data = _extract_json(raw)

        if not isinstance(data, dict):
            return {}

        return {
            key: value
            for key, value in data.items()
            if isinstance(value, str)
        }
    except Exception:
        # The rule-based review remains available if Gemini fails.
        return {}
