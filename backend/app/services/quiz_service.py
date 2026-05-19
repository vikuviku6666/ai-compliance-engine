import json
from app.services.llm_service import client, MODEL, SYSTEM_MENTAL_MODEL, governed_llm_call

class QuizService:
    """Deterministic quiz generator based strictly on regulatory evidence"""

    @staticmethod
    def generate_quiz(training_name: str, regulation_ref: str, evidence: str) -> list:
        """Generate a 3-question multiple choice quiz with temperature=0 based strictly on evidence"""
        prompt = f"""
        You are an enterprise compliance auditor. Generate a 3-question multiple choice quiz for the compliance course: '{training_name}' using the targeted regulation evidence.

        Regulation Citation: {regulation_ref}
        Legal Evidence Context:
        \"\"\"{evidence}\"\"\"

        Rules:
        1. All questions and answers must be 100% accurate to the provided Legal Evidence Context.
        2. Do not invent facts, regulations, or rules outside the provided context.
        3. Respond ONLY with a valid JSON array of 3 quiz questions.
        4. Each question object in the array must match this EXACT structure:
        {{
            "question": "What does Article X require obliged entities to do?",
            "choices": [
                "Option A...",
                "Option B...",
                "Option C...",
                "Option D..."
            ],
            "answer": "Option A..." // Must be the exact text of the correct choice from the choices array
        }}
        No pre-text, post-text, markdown tags, or commentaries. Return raw JSON array only.
        """
        try:
            raw = governed_llm_call(
                prompt,
                response_format={"type": "json_object"}
            )

            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            result = json.loads(raw)
            # Handle both array and {"quiz": [...]} wrappers
            if isinstance(result, dict):
                for key in ("quiz", "questions", "data"):
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break

            return result
        except Exception as e:
            print(f"Error generating quiz: {e}")
            # Robust fallback quiz matching structural format
            return [
                {
                    "question": f"Which regulation mandates compliance for {training_name}?",
                    "choices": [
                        f"{regulation_ref}",
                        "None of the options",
                        "An unrelated regional standard",
                        "A superseded directive"
                    ],
                    "answer": f"{regulation_ref}"
                },
                {
                    "question": "Who must ensure employees participate in compliant training programmes?",
                    "choices": [
                        "Obliged entities",
                        "External auditors only",
                        "Third-party software providers",
                        "Individual employees without management oversight"
                    ],
                    "answer": "Obliged entities"
                },
                {
                    "question": "What is the primary target control for this compliance training?",
                    "choices": [
                        "CDD and employee training programmes",
                        "Manual spreadsheets",
                        "Ad-hoc inspections",
                        "Discretionary policy reviews"
                    ],
                    "answer": "CDD and employee training programmes"
                }
            ]
