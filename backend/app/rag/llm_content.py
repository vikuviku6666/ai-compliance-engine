"""
LLM Content Generation utilities for compliance training
- Summarize regulation/chunk
- Generate training module proposals
- Generate quiz questions and answers

This module wraps app.services.llm_service.generate_summary
and provides higher-level helpers used by training pipeline.
"""

from typing import Dict, List
from app.services.llm_service import generate_summary


def summarize_text(text: str) -> str:
    """Return a concise summary for the provided text using the LLM.
    This delegates to the project's LLM service which is configured
    for OpenRouter.
    """
    prompt = f"Summarize the following regulatory text in plain English, focusing on obligations, actors, and key requirements. Do not invent any additional regulations, risks, or controls beyond what is explicitly stated. Do not add compliance recommendations:\n\n{text}"
    return generate_summary(prompt)


def generate_training_module(title: str, source_text: str) -> Dict:
    """Generate a training module skeleton from provided source text.

    Returns a dict with name, summary, learning_objectives, duration_minutes, and assessment_quiz (IDs left to populate).
    """
    prompt = (
        f"Create a short training module for compliance staff.\n"
        f"Title: {title}\n"
        f"Source:\n{source_text}\n\n"
        f"Provide:\n"
        f"1) Module name\n"
        f"2) 3-5 concise learning objectives\n"
        f"3) Suggested duration in minutes\n"
        f"4) Short summary (50-100 words)\n"
        f"5) A short 3-question quiz (question and correct answer)\n\n"
        f"IMPORTANT: Base all content strictly on the provided source text. "
        f"Do not invent regulations, risks, or controls not present in the source. "
        f"Do not add governance recommendations.\n\n"
        f"Respond in JSON format with keys: name, objectives, duration_minutes, summary, quiz."
    )

    raw = generate_summary(prompt)

    # Try to parse JSON from the model; be forgiving
    import json
    
    try:
        parsed = json.loads(raw)
        # Ensure keys exist
        name = parsed.get('name') or title
        objectives = parsed.get('objectives', [])
        duration = parsed.get('duration_minutes', 15)
        summary = parsed.get('summary', '')
        quiz = parsed.get('quiz', [])
        return {
            'name': name,
            'objectives': objectives,
            'duration_minutes': duration,
            'summary': summary,
            'quiz': quiz
        }
    except Exception:
        # Fallback: return minimal structure with raw text
        return {
            'name': title,
            'objectives': [],
            'duration_minutes': 15,
            'summary': raw[:800],
            'quiz': []
        }


def generate_quiz_from_text(text: str, num_questions: int = 3) -> List[Dict]:
    """Generate a short quiz (questions + correct answers) from a text chunk.
    Returns a list of {question, answer} dicts.
    """
    prompt = f"Create {num_questions} short multiple-choice questions (with one correct answer) based on the following text. Include choices and indicate the correct answer.\n\nIMPORTANT: Base all questions strictly on the provided text. Do not invent regulations, articles, or facts not present in the source.\n\n{text}\n\nRespond in JSON: [{'{'}\"question\":..., \"choices\":[...], \"answer\":...{'}'}]"
    raw = generate_summary(prompt)
    import json
    try:
        parsed = json.loads(raw)
        return parsed
    except Exception:
        # Heuristic fallback: simple splitting
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        questions = []
        for i in range(min(num_questions, len(lines))):
            questions.append({'question': lines[i][:200], 'choices': [], 'answer': ''})
        return questions


# Convenience combined function used by training pipeline
def build_module_from_chunk(chunk_id: str, section: str, content: str) -> Dict:
    """Produce a training module dict for a single chunk.
    This will create a summary, propose learning objectives and a quiz.
    """
    title = f"Training: {section} ({chunk_id})"
    module = generate_training_module(title, content[:2000])
    # Ensure module has an id
    module['source_chunk'] = chunk_id
    module['source_section'] = section
    return module
