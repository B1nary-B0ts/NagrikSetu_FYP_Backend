import json
import ollama
import os
import logging

logger = logging.getLogger(__name__)


def analyze_civic_issue(
    image_path: str,
    description: str,
) -> dict:
    """
    Uses Ollama LLaMA 3.2 Vision to:
    - validate image vs description
    - classify issue
    - detect department
    - calculate severity
    """

    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    prompt = f"""
You are part of a civic issue analysis system.

Citizen description:
"{description}"

Tasks:
1. Verify if the image and description refer to the SAME issue.
2. If they match, classify the issue category.
3. Assign the responsible department.
4. Rate severity from "LOW", "MEDIUM", "HIGH", "CRITICAL".
5. Respond ONLY in valid JSON:

{{
  "match": true/false,
  "issue_category": "...",
  "department": "...",
  "severity": "LOW"/"MEDIUM"/"HIGH"/"CRITICAL",
  "reasoning": "short justification"
}}
"""

    response = ollama.chat(
        model="llama3.2-vision",
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_path],  # 🔥 directly use local file
            }
        ],
    )

    raw = response.get("message", {}).get("content", "").strip()

    # Safe JSON extraction
    start = raw.find("{")
    end = raw.rfind("}") + 1

    if start == -1 or end == -1:
        logger.error(f"Ollama raw response: {raw}")
        raise ValueError("No JSON found in Ollama response")

    return json.loads(raw[start:end])
