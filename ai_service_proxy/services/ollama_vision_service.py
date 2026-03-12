import json
import ollama
import os
import logging

logger = logging.getLogger(__name__)


def analyze_civic_issue(
    image_path: str,
    description: str,
    department_choices: list[str],
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
    
    # format as numbered list for the prompt
    dept_list = "\n".join(
        [f"{i+1}. {name}" for i, name in enumerate(department_choices)]
    )

    prompt = f"""
You are part of a civic issue analysis system.

Citizen description:
"{description}"

Available departments — you MUST pick EXACTLY one name from this list, copy it character by character:
{dept_list}
You MUST respond with the FULL department name exactly as written above.
For example, do not write "Public Works", write "Public Works / City Engineering Department".
Tasks:
1. Verify if the image and description refer to the SAME civic issue.
2. If they match, classify the issue category.
3. Assign the responsible department — you MUST pick EXACTLY one name from the list above, copy it exactly.
4. Rate severity as one of: "LOW", "MEDIUM", "HIGH", "CRITICAL".
5. Respond ONLY in valid JSON with no extra text:

{{
  "match": true/false,
  "issue_category": "...",
  "department": "exact department name from the list above",
  "severity": "LOW"/"MEDIUM"/"HIGH"/"CRITICAL",
  "reasoning": "short justification"
}}
"""

    response = ollama.chat(
        model="llava",
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

# ai_service_proxy/services/ollama_vision_service.py

import json
import ollama
import os
import logging

logger = logging.getLogger(__name__)


def verify_issue_resolution(
    before_image_path: str,
    after_image_path: str,
    description: str,
) -> dict:
    """
    Compares before and after images to verify if issue is resolved.
    """

    if not os.path.exists(before_image_path):
        raise FileNotFoundError(f"Before image not found: {before_image_path}")
    if not os.path.exists(after_image_path):
        raise FileNotFoundError(f"After image not found: {after_image_path}")

    prompt = f"""
You are a civic issue resolution verification system.

Original issue description reported by citizen:
"{description}"

You are given TWO images:
- Image 1: BEFORE — the original issue reported by the citizen
- Image 2: AFTER — the photo uploaded by the worker claiming the issue is resolved

Your tasks:
1. Compare both images carefully.
2. Determine if the issue visible in Image 1 has been genuinely resolved in Image 2.
3. Look for clear evidence of resolution — repaired road, cleaned area, fixed infrastructure, etc.
4. Be strict — partial fixes or unrelated images should be marked as NOT resolved.

Respond ONLY in valid JSON with no extra text:

{{
  "resolved": true/false,
  "confidence": "LOW"/"MEDIUM"/"HIGH",
  "reasoning": "brief explanation of your decision"
}}
"""

    response = ollama.chat(
        model="llama3.2-vision",
        messages=[
                    {
                        "role": "user",
                        "content": "This is the BEFORE image showing the civic issue:",
                        "images": [before_image_path],
                    },
                    {
                        "role": "assistant", 
                        "content": "I can see the before image showing the issue.",
                    },
                    {
                        "role": "user",
                        "content": f"""This is the AFTER image uploaded by the worker claiming resolution.
                        Original issue description: "{description}"
                        Has the issue been genuinely resolved? Respond ONLY in valid JSON:
                        {{
                        "resolved": true/false,
                        "confidence": "LOW"/"MEDIUM"/"HIGH",
                        "reasoning": "brief explanation"
                        }}""",
                        "images": [after_image_path],
                    },
                ],
    )

    raw = response.get("message", {}).get("content", "").strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1

    if start == -1 or end == -1:
        logger.error(f"Ollama raw response: {raw}")
        raise ValueError("No JSON found in Ollama response")

    return json.loads(raw[start:end])
