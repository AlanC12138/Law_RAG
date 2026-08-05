from __future__ import annotations

import json
import logging

from app.retrieval.reranker import RankedResult

logger = logging.getLogger(__name__)

# Maximum characters of document text sent to the LLM for enrichment tasks
# (summarisation, clause extraction).  Raise this for models with large context windows.
MAX_ENRICHMENT_CHARS = 8_000

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a legal research assistant for a law firm. \
You answer questions strictly and exclusively based on the document excerpts provided to you.

Your rules:
1. ONLY use information from the provided sources. Never add facts, clauses, or interpretations \
from your own training data.
2. ALWAYS cite your sources inline using [SOURCE N] notation immediately after the relevant statement.
3. If the answer cannot be found in the provided sources, respond with exactly: \
"I could not find information about this in the available documents."
4. Use precise legal language. Where the source text is directly relevant, quote it exactly \
rather than paraphrasing.
5. Do not speculate, infer, or draw conclusions beyond what the sources explicitly state.
6. If sources contradict each other, note the contradiction and cite both.

You are assisting qualified attorneys. Accuracy and traceability to source documents \
are more important than brevity."""

SUMMARIZE_SYSTEM_PROMPT = """You are a legal document analyst. \
Write a concise 3-5 sentence summary of the provided legal document text.
Focus on: the document type, the parties involved, the primary subject matter, \
key obligations or rights, and any important dates or deadlines.
Respond with plain prose only — no headers, no bullet points, no markdown."""

CLAUSE_EXTRACTION_SYSTEM_PROMPT = """You are a legal document analyst. \
Extract key structured information from the provided legal document text.

Return a JSON object with these keys (omit any key where the information is not present):
  "document_type"    — e.g. "Non-Disclosure Agreement", "Employment Contract"
  "parties"          — list of party names / roles
  "effective_date"   — date the agreement takes effect
  "expiry_date"      — end date or term, if stated
  "governing_law"    — jurisdiction / governing law clause
  "termination"      — brief description of termination rights
  "key_obligations"  — list of up to 4 primary obligations

Respond with valid JSON only — no explanation, no markdown fences."""


# ---------------------------------------------------------------------------
# Context formatter
# ---------------------------------------------------------------------------


def build_context_block(results: list[RankedResult]) -> str:
    """Format retrieved chunks into a numbered source block for the LLM prompt.

    Each source is clearly delimited so the model can reference it with
    [SOURCE N] notation and so citations can be parsed from the response.

    Args:
        results: Reranked retrieval results (highest relevance first).

    Returns:
        Formatted context string to inject into the prompt.
    """
    if not results:
        return "No relevant document excerpts were found for this query."

    lines: list[str] = ["The following excerpts were retrieved from the firm's documents:\n"]

    for i, result in enumerate(results, start=1):
        section_info = f' | Section: "{result.section_title}"' if result.section_title else ""
        header = (
            f"[SOURCE {i}] "
            f'Document: "{result.filename}" | '
            f"Page: {result.page_number}"
            f"{section_info}"
        )
        lines.append(header)
        lines.append(result.text)
        lines.append("")  # blank line between sources

    return "\n".join(lines)


def parse_llm_json(raw: str) -> dict:
    """Parse a JSON string returned by an LLM, tolerating markdown fences.

    Some models (especially Ollama) wrap JSON in triple-backtick blocks.
    This helper strips those fences before parsing so both OpenAI and
    Ollama providers can share the same post-processing logic.

    Args:
        raw: Raw LLM output, may or may not be wrapped in markdown fences.

    Returns:
        Parsed dict, or ``{}`` if JSON is malformed or empty.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            raw = inner.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("parse_llm_json: could not decode response as JSON")
        return {}


def build_user_message(question: str, context: str) -> str:
    """Combine the context block and the user's question into a single message.

    Args:
        question: The attorney's natural-language question.
        context:  Formatted source block from build_context_block().

    Returns:
        Full user message to send to the LLM.
    """
    return f"{context}\n\nQuestion: {question}"
