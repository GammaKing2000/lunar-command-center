class ChatbotSystem:
    def __init__(self, llm_client):
        self.llm = llm_client

        self.system_prompt = """
You are an autonomous lunar rover assistant.
Explain navigation decisions clearly and concisely.
Do NOT invent data.
Base explanations ONLY on provided rover state.
Keep responses under 2-3 sentences.
"""

    def build_prompt(self, decision, pose, craters, mission_context=None):
        crater_desc = "\n".join(
            [f"- Crater at ({c['x']:.2f},{c['y']:.2f}), radius {c['radius']:.2f}m"
             for c in craters]
        ) if craters else "None detected"

        prompt = f"""
Decision: {decision}

Rover pose:
x={pose['x']:.2f}, y={pose['y']:.2f}, heading={pose['theta']:.2f} rad

Detected craters:
{crater_desc}
"""

        # Add mission context if available
        if mission_context:
            prompt += f"""
Mission status:
- Active: {mission_context.get('active', False)}
- Task: {mission_context.get('task', 'IDLE')}
- Progress: {mission_context.get('progress', 0)}%
- Distance: {mission_context.get('current_distance', 0):.2f}m / {mission_context.get('target_distance', 0):.2f}m
- Findings: {mission_context.get('findings', {})}
"""

        prompt += "\nExplain why this decision was chosen."
        return prompt

    def explain(self, decision, pose, craters, mission_context=None):
        if self.llm is None:
            # Fallback rule-based explanation
            return f"Decision '{decision}' based on {len(craters)} nearby craters."

        try:
            prompt = self.build_prompt(decision, pose, craters, mission_context)

            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                timeout=5  # Don't block telemetry updates
            )

            return response.choices[0].message.content.strip()
        
        except Exception as e:
            # Fallback if LLM fails
            return f"Decision '{decision}' selected ({len(craters)} craters nearby)"