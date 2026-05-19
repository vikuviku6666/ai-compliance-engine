import json
from app.services.llm_service import client, MODEL, SYSTEM_MENTAL_MODEL, governed_llm_call

class SimulationService:
    """Deterministic simulation generator based strictly on regulatory evidence and graph pathways"""

    @staticmethod
    def generate_simulation(training_name: str, responsibility: str, risk: str, control: str, regulation_ref: str, evidence: str) -> dict:
        """Generate a stable compliance simulation scenario/gameplay with temperature=0 based strictly on inputs"""
        prompt = f"""
        You are a compliance training scenario designer. Generate an interactive, text-based compliance simulation/scenario for: '{training_name}'.
        The simulation must focus strictly on managing the targeted risk through the designated control pursuant to the regulation.

        Governance Context:
        - Targeted Duty: {responsibility}
        - Financial Crime Risk: {risk}
        - Mandated Control: {control}
        - Regulation Reference: {regulation_ref}
        - Legal Evidence Context:
        \"\"\"{evidence}\"\"\"

        Rules:
        1. Base the scenario STRICTLY on factual compliance requirements in the Legal Evidence Context.
        2. Respond ONLY with a valid JSON object matching the following structure:
        {{
            "scenario_title": "Onboarding High-Risk Client Scenario",
            "background": "A brief background paragraph describing a compliance challenge the learner faces in their daily role...",
            "challenge": "A specific decision point or challenge related to the risk and control...",
            "options": [
                {{
                    "text": "Option 1 description...",
                    "feedback": "Feedback for selecting Option 1 based on the regulation...",
                    "compliant": false
                }},
                {{
                    "text": "Option 2 description...",
                    "feedback": "Feedback for selecting Option 2 based on the regulation...",
                    "compliant": true
                }}
            ]
        }}
        No pre-text, post-text, markdown tags, or commentaries. Return raw JSON object only.
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

            return json.loads(raw)
        except Exception as e:
            print(f"Error generating simulation: {e}")
            # Robust fallback simulation matching structural format
            return {
                "scenario_title": f"{training_name} Practical Exercise",
                "background": f"While executing your responsibility of {responsibility}, you notice an anomaly that introduces a high risk of {risk}. You must immediately verify if the mandated control of {control} has been fully satisfied.",
                "challenge": f"According to {regulation_ref}, what is your immediate required action to satisfy the control of {control}?",
                "options": [
                    {
                        "text": f"Bypass standard onboarding and log a verbal approval note.",
                        "feedback": "Bypassing CDD measures violates AMLR obligations and exposes the company to severe regulatory enforcement actions.",
                        "compliant": False
                    },
                    {
                        "text": f"Enforce complete customer due diligence (CDD) measures and record verified official documentation.",
                        "feedback": f"Correct! Obliged entities must satisfy complete CDD pursuant to {regulation_ref} as a key pillar of employee training programmes and operational compliance.",
                        "compliant": True
                    }
                ]
            }
