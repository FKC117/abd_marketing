import json
import logging
import os

from .marketing_plan_schema import build_marketing_plan_blueprint, marketing_plan_focus_text
from .strategy_generator import (
    _call_gemini_with_retry,
    _estimate_cost_usd,
    _extract_json_payload,
    _make_genai_client,
    _response_text,
    _usage_metadata,
)


logger = logging.getLogger("medstratix.marketing_plan")


def _marketing_plan_timeout_ms() -> int:
    raw = (os.getenv("GEMINI_MARKETING_PLAN_TIMEOUT_MS", os.getenv("GEMINI_TIMEOUT_MS", "45000")) or "45000").strip()
    try:
        return max(int(raw), 10000)
    except ValueError:
        return 45000


def _marketing_plan_max_attempts() -> int:
    raw = (os.getenv("GEMINI_MARKETING_PLAN_MAX_ATTEMPTS", "1") or "1").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 1


def _trim_list(values, max_items: int):
    return list((values or [])[:max_items])


def _compact_context_for_plan_type(
    *,
    output_style: str,
    market_accounts_summary: list[dict],
    stakeholder_contexts: list[dict] | None,
    your_panel_summary: dict | None,
    competitor_panel_summary: dict | None,
    comparison_summary: dict | None,
    source_plan_contexts: list[dict] | None,
) -> dict:
    if output_style != "brief_plan":
        return {
            "market_accounts_summary": market_accounts_summary,
            "stakeholder_contexts": stakeholder_contexts or [],
            "your_panel_summary": your_panel_summary or {},
            "competitor_panel_summary": competitor_panel_summary or {},
            "comparison_summary": comparison_summary or {},
            "source_plan_contexts": source_plan_contexts or [],
        }

    compact_source_plans = []
    for item in _trim_list(source_plan_contexts or [], 3):
        compact_source_plans.append(
            {
                "title": item.get("title", ""),
                "output_style_label": item.get("output_style_label", ""),
                "executive_summary": item.get("executive_summary", {}),
                "human_section_overrides": item.get("human_section_overrides", {}),
            }
        )

    def _compact_panel_summary(panel_summary: dict | None) -> dict:
        panel_summary = panel_summary or {}
        return {
            "name": panel_summary.get("name", ""),
            "company_name": panel_summary.get("company_name", ""),
            "sample_type_label": panel_summary.get("sample_type_label", ""),
            "price_label": panel_summary.get("price_label", ""),
            "tat_label": panel_summary.get("tat_label", ""),
            "panel_count": panel_summary.get("panel_count", 0),
            "panel_names": panel_summary.get("panel_names", [])[:6],
        }

    return {
        "market_accounts_summary": _trim_list(market_accounts_summary or [], 4),
        "stakeholder_contexts": _trim_list(stakeholder_contexts or [], 8),
        "your_panel_summary": _compact_panel_summary(your_panel_summary),
        "competitor_panel_summary": _compact_panel_summary(competitor_panel_summary),
        "comparison_summary": comparison_summary or {},
        "source_plan_contexts": compact_source_plans,
    }


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


def build_marketing_plan_request(
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
    model_name = (model_name_override or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")).strip() or "gemini-2.5-pro"
    compact_context = _compact_context_for_plan_type(
        output_style=output_style,
        market_accounts_summary=market_accounts_summary,
        stakeholder_contexts=stakeholder_contexts,
        your_panel_summary=your_panel_summary,
        competitor_panel_summary=competitor_panel_summary,
        comparison_summary=comparison_summary,
        source_plan_contexts=source_plan_contexts,
    )

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
{json.dumps(compact_context["market_accounts_summary"], indent=2)}

Stakeholder context:
{json.dumps(compact_context["stakeholder_contexts"], indent=2)}

Your product context:
{json.dumps(compact_context["your_panel_summary"], indent=2)}

Competitor context:
{json.dumps(compact_context["competitor_panel_summary"], indent=2)}

Comparison summary:
{json.dumps(compact_context["comparison_summary"], indent=2)}

Source plan contexts:
{json.dumps(compact_context["source_plan_contexts"], indent=2)}

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

    timeout_ms = _marketing_plan_timeout_ms()
    max_attempts = _marketing_plan_max_attempts()
    return {
        "model_name": model_name,
        "prompt_text": prompt,
        "timeout_ms": timeout_ms,
        "max_attempts": max_attempts,
    }


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

    request_payload = build_marketing_plan_request(
        title=title,
        objective=objective,
        geography=geography,
        disease_focus=disease_focus,
        output_style=output_style,
        include_product_context=include_product_context,
        sales_expectation=sales_expectation,
        strategist_note=strategist_note,
        market_accounts_summary=market_accounts_summary,
        stakeholder_contexts=stakeholder_contexts,
        your_panel_summary=your_panel_summary,
        competitor_panel_summary=competitor_panel_summary,
        comparison_summary=comparison_summary,
        source_plan_contexts=source_plan_contexts,
        model_name_override=model_name_override,
    )
    model_name = request_payload["model_name"]
    prompt = request_payload["prompt_text"]
    timeout_ms = request_payload["timeout_ms"]
    max_attempts = request_payload["max_attempts"]
    logger.info(
        "Generating marketing plan title=%s model=%s output_style=%s timeout_ms=%s max_attempts=%s",
        title,
        model_name,
        output_style,
        timeout_ms,
        max_attempts,
    )
    client = _make_genai_client(api_key, timeout_ms=timeout_ms)
    response = _call_gemini_with_retry(
        client=client,
        model_name=model_name,
        prompt=prompt,
        max_attempts=max_attempts,
        timeout_ms=timeout_ms,
    )
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
