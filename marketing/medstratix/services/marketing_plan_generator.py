import json
import logging
import os

from google import genai

from .marketing_plan_schema import build_marketing_plan_blueprint, marketing_plan_focus_text
from .strategy_generator import (
    _call_gemini_with_retry,
    _estimate_cost_usd,
    _extract_json_payload,
    _response_text,
    _usage_metadata,
)


logger = logging.getLogger("medstratix.marketing_plan")


def _market_reality_guidance(geography: str, strategist_note: str) -> str:
    geography_text = (geography or "").lower()
    strategist_text = (strategist_note or "").lower()
    bangladesh_like = any(
        token in geography_text or token in strategist_text
        for token in ("bangladesh", "dhaka", "bdt", "local market")
    )
    if not bangladesh_like:
        return ""
    return """
Market-specific emphasis:
- reflect high price sensitivity
- account for biological sample shipping or cross-border logistics hurdles
- treat unethical competitor referral pressure as a market distortion and compliance risk
- recommend compliant counter-strategies only
- make campaigns and field actions realistic for Bangladesh oncology institutions
""".strip()


def generate_marketing_plan(
    *,
    title: str,
    objective: str,
    geography: str,
    disease_focus: str,
    output_style: str,
    include_product_context: bool,
    sales_expectation: dict | None,
    strategist_note: str,
    market_accounts_summary: list[dict],
    stakeholder_contexts: list[dict] | None,
    your_panel_summary: dict | None,
    competitor_panel_summary: dict | None,
    comparison_summary: dict | None,
    source_plan_contexts: list[dict] | None = None,
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

This plan type is: {output_style}
Plan-type focus:
{marketing_plan_focus_text(output_style)}

{build_marketing_plan_blueprint(output_style)}

Commercial rules:
- Keep the plan commercially realistic, field-executable, and compliant.
- Do not recommend bribery, kickbacks, unethical inducement schemes, or covert referral payments.
- If the market has corruption or referral distortion pressure, address it through ethical counter-strategy, institutional contracting, education, evidence, service quality, and compliance-safe positioning.
- The plan should read like something a serious oncology commercial team could actually use.

Plan title: {title}
Objective: {objective or "Not specified"}
Geography: {geography or "Not specified"}
Disease focus: {disease_focus or "Broad oncology"}
Output style: {output_style}
Include product context: {"yes" if include_product_context else "no"}

Strategist note:
{strategist_note or "No extra strategist note provided."}

Sales expectation guardrails:
{json.dumps(sales_expectation or {}, indent=2)}

{_market_reality_guidance(geography, strategist_note)}

Market account summary:
{json.dumps(market_accounts_summary, indent=2)}

Stakeholder context:
{json.dumps(stakeholder_contexts or [], indent=2)}

Your product context:
{json.dumps(your_panel_summary or {}, indent=2)}

Competitor context:
{json.dumps(competitor_panel_summary or {}, indent=2)}

Comparison summary:
{json.dumps(comparison_summary or {}, indent=2)}

Source plan contexts:
{json.dumps(source_plan_contexts or [], indent=2)}

Make the plan specific enough to support:
- executive decision-making
- field execution
- medical affairs activation
- compliant commercial positioning
- campaign planning
- sales messaging
- spreadsheet export readiness through structured timelines, revenue assumptions, and action lists whenever relevant to the selected plan type
- include spreadsheet-ready rows for revenue or execution tracking when the selected plan type supports it
- include gantt-ready task rows with phase, owner, start_period, end_period, dependency, and status_signal when the selected plan type supports it
- treat the user-provided sales expectation guardrails as the primary planning anchor for volume and revenue estimates
- do not inflate sample volume or revenue projections beyond those guardrails unless you explicitly explain why a higher case is justified
- do not invent KOL names or doctor identities
- only use named people if they are explicitly present in verified stakeholder context
- if stakeholder input is unverified, refer to that person only by segment, role, or specialty

If source plan contexts are provided:
- treat them as prior strategic thinking that should be reused and refined, not ignored
- prioritize any human_section_overrides inside those source plans over earlier generated text
- build continuity from the source plans instead of starting from zero

If you cannot fully calculate spreadsheet_model or gantt_data precisely:
- still return the best structured draft rows possible from the plan logic
- never omit the field just because some numbers or dates are estimated
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
