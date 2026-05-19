import re
import json
from typing import List, Dict, Any, Optional


def validate_governance_boundaries(output_text: str) -> List[str]:
    """Check LLM output for potential governance violations.

    Scans for:
    - Hallucinated regulation references
    - Phrases that imply governance decision-making
    - Invented risk/control names
    - Override of governance mapping

    Returns:
        List of violation descriptions. Empty list if no violations.
    """
    violations = []

    if not output_text:
        return violations

    # Check for governance decision-making phrases
    governance_phrases = [
        r"\byou should add training\b",
        r"\bthis role also requires\b",
        r"\bI recommend implementing\b",
        r"\badditional mandatory training\b",
        r"\bshould receive additional\b",
        r"\byou need to implement\b",
    ]

    for phrase in governance_phrases:
        if re.search(phrase, output_text, re.IGNORECASE):
            violations.append(
                f"Governance decision-making detected: output suggests adding/changing compliance requirements '{phrase}'"
            )

    # Check for vague risk/control inventions
    vague_patterns = [
        r"\bblockchain\s+(monitoring|risk|compliance)\b",
        r"\bcyber[-\s]?security\s+(risk|control|training)\b",
        r"\bAI\s+governance\b",
        r"\bdigital\s+transformation\s+(risk|compliance)\b",
    ]

    for pattern in vague_patterns:
        if re.search(pattern, output_text, re.IGNORECASE):
            violations.append(
                f"Potentially invented risk/control detected: '{pattern}' not in governance graph"
            )

    return violations


def validate_no_hallucinated_regulations(
    output_text: str,
    known_regulations: List[str]
) -> List[str]:
    """Check that all regulation references in output exist in known set.

    Args:
        output_text: LLM output to check
        known_regulations: List of regulation names from Neo4j/graph

    Returns:
        List of hallucinated regulation references
    """
    violations = []

    # Extract all "Article X" and "Recital X" references
    article_refs = re.findall(r'Article\s+(\d+)', output_text, re.IGNORECASE)
    recital_refs = re.findall(r'Recital\s+(\d+)', output_text, re.IGNORECASE)

    for ref in article_refs + recital_refs:
        found = False
        for known in known_regulations:
            if ref in known or known in ref:
                found = True
                break
        if not found:
            violations.append(f"Hallucinated regulation reference: Article/Recital {ref}")

    return violations


def validate_structured_output(
    data: Any,
    expected_type: str
) -> List[str]:
    """Validate that a parsed JSON output matches expected schema.

    Args:
        data: Parsed JSON data
        expected_type: One of 'quiz', 'simulation', 'plan', 'evaluation', 'role_info'

    Returns:
        List of schema violations
    """
    violations = []

    schemas = {
        "quiz": {
            "type": list,
            "item_fields": ["question", "choices", "answer"],
            "item_type": dict,
        },
        "simulation": {
            "type": dict,
            "item_fields": ["scenario_title", "background", "challenge", "options"],
        },
        "plan": {
            "type": list,
            "item_fields": ["quarter", "module", "role_reference", "regulation_reference",
                           "risk_reference", "competency_reference", "behavioural_outcome"],
            "item_type": dict,
        },
        "evaluation": {
            "type": dict,
            "item_fields": ["overall", "dimensions"],
        },
        "role_info": {
            "type": dict,
            "item_fields": ["role", "responsibilities", "risks"],
        },
    }

    schema = schemas.get(expected_type)
    if not schema:
        return violations

    if not isinstance(data, schema["type"]):
        violations.append(
            f"Expected {schema['type'].__name__} but got {type(data).__name__}"
        )
        return violations

    if schema["type"] == list:
        item_fields = schema.get("item_fields", [])
        for i, item in enumerate(data):
            if not isinstance(item, schema.get("item_type", dict)):
                violations.append(f"Item {i}: expected dict, got {type(item).__name__}")
                continue
            for field in item_fields:
                if field not in item:
                    violations.append(f"Item {i}: missing required field '{field}'")

    elif schema["type"] == dict:
        for field in schema.get("item_fields", []):
            if field not in data:
                violations.append(f"Missing required field '{field}'")

    return violations