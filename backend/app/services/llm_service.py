from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from typing import Any, Optional

load_dotenv(override=True)

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    api_key=os.getenv("GEMINI_API_KEY", "").strip()
)

MODEL = "gemini-2.5-flash"

SYSTEM_MENTAL_MODEL = """
You are NOT a compliance decision maker.

You are an AI learning and explainability layer operating inside a deterministic enterprise compliance orchestration system.

Your job is to:
- explain,
- summarize,
- generate training content,
- generate quizzes,
- generate simulations,
- and provide legal context support.

You MUST NOT:
- invent regulations,
- invent risks,
- invent controls,
- create governance logic,
- or dynamically change compliance mappings.

Core Architectural Rules:
- You NEVER decide: Role -> Risk, Risk -> Control, Control -> Regulation.
- Those relationships are predefined and governed by Neo4j.
- You ONLY operate AFTER the governance layer has produced outputs.
- Treat all provided inputs as authoritative enterprise governance data.

Temperature Requirement:
- Use temperature=0 for all outputs.
- This ensures stable outputs, consistent wording, and reduced hallucinations.

Citation Rule:
- Only cite retrieved recitals, articles, and regulation references.
- Never fabricate citations.
- If a regulation reference is not in the provided context, do not use it.

Output Style:
- All outputs must be deterministic, explainable, professional, audit-safe, enterprise-style, and regulation-grounded.

Architecture Roles:
- Neo4j = enterprise compliance brain (governance graph)
- LightRAG / PostgreSQL = legal memory (regulation storage)
- LLM = learning and explanation assistant (NOT decision engine)

Prioritize:
- Governance,
- Explainability,
- Traceability,
- Auditability,
over autonomous reasoning, dynamic legal interpretation, and agentic decision making.

GOOD output example:
"CDD Fundamentals helps KYC Analysts verify customer identity and reduce identity fraud risk during onboarding activities."

BAD output example (do not do this):
"This training may also support cybersecurity governance and blockchain risk management."
"""


import json
from typing import Any, Optional


class GovernanceViolationError(Exception):
    """Raised when LLM output violates governance rules"""
    pass


def governed_llm_call(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0,
    response_format: Optional[dict] = None
) -> str:
    """Call LLM with governance guardrails, structured output support, and output validation.

    Args:
        user_prompt: The user message content
        system_prompt: Override system prompt (defaults to SYSTEM_MENTAL_MODEL)
        temperature: Model temperature (defaults to 0 for deterministic outputs)
        response_format: Optional structured output format e.g. {"type": "json_object"}

    Returns:
        The LLM response content string

    Raises:
        GovernanceViolationError: If output contains hallucinated content
    """
    messages = [
        {"role": "system", "content": system_prompt or SYSTEM_MENTAL_MODEL},
        {"role": "user", "content": user_prompt}
    ]

    kwargs = {
        "model": MODEL,
        "temperature": temperature,
        "messages": messages,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content.strip()

    # Basic governance validation — catch obvious hallucinations
    from app.services.validators import validate_governance_boundaries
    violations = validate_governance_boundaries(content)
    if violations:
        raise GovernanceViolationError(
            f"LLM output violated governance rules: {violations}"
        )

    return content


def generate_summary(topic):
    prompt = f"""
    Explain this AML topic strictly based on provided context. Do not invent any regulations, risks, or controls.

    Topic: {topic}

    Rules:
    - Only state what is factually known about this topic.
    - Do not add compliance recommendations.
    - Do not reference regulations, articles, or recitals that are not explicitly provided.
    - Keep the response concise and professional.
    """

    return governed_llm_call(prompt)
