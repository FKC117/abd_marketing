import json
import logging
import os

from google import genai

from .strategy_generator import (
    _call_gemini_with_retry,
    _estimate_cost_usd,
    _extract_json_payload,
    _response_text,
    _usage_metadata,
)


logger = logging.getLogger("medstratix.marketing_plan")


def generate_marketing_plan(
    *,
    title: str,
    objective: str,
    geography: str,
    disease_focus: str,
    output_style: str,
    include_product_context: bool,
    strategist_note: str,
    market_accounts_summary: list[dict],
    your_panel_summary: dict | None,
    competitor_panel_summary: dict | None,
    comparison_summary: dict | None,
    model_name_override: str = "",
) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured in the environment.")

    model_name = (model_name_override or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")).strip() or "gemini-2.5-pro"

    prompt = f"""
You are building a strategic oncology marketing plan for MedStratix.

Return valid JSON only.
Do not wrap the JSON in markdown fences.
Do not include commentary before or after the JSON.

Required top-level keys:
- title
- executive_summary
- market_landscape
- target_segments
- positioning
- campaign_plan
- sales_enablement
- next_steps

Rules:
- `market_landscape` must include: situation, barriers, opportunities
- `target_segments` must be a list of objects with: segment, priority, rationale
- `positioning` must include: core_message, differentiators, proof_points
- `campaign_plan` must be a list of at least 6 objects with: name, audience, objective, message, channel_mix, timeline
- `sales_enablement` must include: talking_points, objection_handling, field_actions
- `next_steps` must be a list of strings

Plan title: {title}
Objective: {objective or "Not specified"}
Geography: {geography or "Not specified"}
Disease focus: {disease_focus or "Broad oncology"}
Output style: {output_style}
Include product context: {"yes" if include_product_context else "no"}

Strategist note:
{strategist_note or "No extra strategist note provided."}

Market account summary:
{json.dumps(market_accounts_summary, indent=2)}

Your product context:
{json.dumps(your_panel_summary or {}, indent=2)}

Competitor context:
{json.dumps(competitor_panel_summary or {}, indent=2)}

Comparison summary:
{json.dumps(comparison_summary or {}, indent=2)}

Keep the plan commercially realistic, field-executable, and compliant.
Do not recommend bribery, kickbacks, or unethical inducement schemes.
""".strip()

    logger.info("Generating marketing plan title=%s model=%s output_style=%s", title, model_name, output_style)
    client = genai.Client(api_key=api_key)
    response = _call_gemini_with_retry(client=client, model_name=model_name, prompt=prompt)
    text = _response_text(response)
    payload = _extract_json_payload(text)
    usage = _usage_metadata(response)
    return {
        "provider": "google_genai",
        "model": model_name,
        "prompt_text": prompt,
        "response_text": text,
        "response_json": payload,
        "prompt_tokens": usage["prompt_tokens"],
        "response_tokens": usage["response_tokens"],
        "total_tokens": usage["total_tokens"],
        "estimated_cost_usd": _estimate_cost_usd(
            usage["prompt_tokens"],
            usage["response_tokens"],
        ),
    }
