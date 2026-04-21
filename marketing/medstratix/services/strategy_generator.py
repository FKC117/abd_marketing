import json
import os
import time
from decimal import Decimal, ROUND_HALF_UP

from google import genai


def _response_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        assembled = "".join(getattr(part, "text", "") for part in parts if getattr(part, "text", ""))
        if assembled.strip():
            return assembled.strip()
    return ""


def _usage_metadata(response) -> dict:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0,
        }
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    response_tokens = getattr(usage, "candidates_token_count", 0) or 0
    total_tokens = getattr(usage, "total_token_count", 0) or (prompt_tokens + response_tokens)
    return {
        "prompt_tokens": int(prompt_tokens),
        "response_tokens": int(response_tokens),
        "total_tokens": int(total_tokens),
    }


def _estimate_cost_usd(prompt_tokens: int, response_tokens: int) -> Decimal:
    input_rate = Decimal(os.getenv("GEMINI_INPUT_COST_PER_1M", "0"))
    output_rate = Decimal(os.getenv("GEMINI_OUTPUT_COST_PER_1M", "0"))
    cost = ((Decimal(prompt_tokens) / Decimal(1_000_000)) * input_rate) + (
        (Decimal(response_tokens) / Decimal(1_000_000)) * output_rate
    )
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _compact_pair_summary(comparison_pair: dict | None) -> dict:
    if not comparison_pair:
        return {}
    return {
        "competitor_panel": getattr(comparison_pair.get("competitor_panel"), "name", ""),
        "overlap_count": comparison_pair.get("overlap_count", 0),
        "your_only_count": comparison_pair.get("your_only_count", 0),
        "competitor_only_count": comparison_pair.get("competitor_only_count", 0),
        "your_coverage_percent": comparison_pair.get("your_coverage_percent", 0),
        "competitor_coverage_percent": comparison_pair.get("competitor_coverage_percent", 0),
        "sample_type_match": comparison_pair.get("sample_type_match", False),
        "price_delta_bdt": _json_safe(comparison_pair.get("price_delta")),
        "overlap_preview": comparison_pair.get("overlap_preview", [])[:10],
        "your_only_preview": comparison_pair.get("your_only_preview", [])[:10],
        "competitor_only_preview": comparison_pair.get("competitor_only_preview", [])[:10],
    }


def _compact_guideline_coverage(coverage: dict | None) -> dict:
    if not coverage:
        return {}
    results = coverage.get("results", []) or []
    compact_results = []
    for item in results[:12]:
        compact_results.append(
            {
                "cancer_type": getattr(item.get("guideline"), "cancer_type", ""),
                "guideline_name": getattr(item.get("guideline"), "name", ""),
                "coverage_percent": item.get("coverage_percent", 0),
                "matched_count": item.get("matched_count", 0),
                "missing_count": item.get("missing_count", 0),
                "matched_symbols": item.get("matched_symbols", [])[:8],
                "missing_symbols": item.get("missing_symbols", [])[:8],
                "matched_variants": item.get("matched_variants", [])[:6],
                "missing_variants": item.get("missing_variants", [])[:6],
                "assay_fit_summary": _json_safe(item.get("assay_fit_summary", {})),
            }
        )
    return {
        "guideline_count": coverage.get("guideline_count", 0),
        "average_coverage": _json_safe(coverage.get("average_coverage", 0)),
        "covered_guidelines": [
            {
                "cancer_type": getattr(item.get("guideline"), "cancer_type", ""),
                "guideline_name": getattr(item.get("guideline"), "name", ""),
                "coverage_percent": item.get("coverage_percent", 0),
                "matched_symbols": item.get("matched_symbols", [])[:8],
            }
            for item in (coverage.get("covered_guidelines", []) or [])[:10]
        ],
        "gap_guidelines": [
            {
                "cancer_type": getattr(item.get("guideline"), "cancer_type", ""),
                "guideline_name": getattr(item.get("guideline"), "name", ""),
                "coverage_percent": item.get("coverage_percent", 0),
                "missing_symbols": item.get("missing_symbols", [])[:8],
            }
            for item in (coverage.get("gap_guidelines", []) or [])[:10]
        ],
        "results_preview": compact_results,
    }


def _market_accounts_context(market_accounts, stakeholders) -> str:
    if not market_accounts:
        return ""

    account_lines = []
    for account in market_accounts:
        account_lines.append(
            (
                f"- Account: {account.name} | type={account.get_institution_type_display()} | city={account.city or 'N/A'} "
                f"| decision_style={account.get_decision_style_display()} | disease_focus={account.disease_focus or 'N/A'} "
                f"| test_volume={account.estimated_test_volume or 'N/A'} | evidence={account.get_evidence_sensitivity_display()} "
                f"| price={account.get_price_sensitivity_display()} | tat={account.get_tat_sensitivity_display()} "
                f"| conference_interest={'yes' if account.conference_interest else 'no'} "
                f"| education_interest={'yes' if account.education_interest else 'no'} "
                f"| corruption_pressure={account.get_market_corruption_pressure_display()} "
                f"| referral_distortion={account.get_referral_distortion_risk_display()} "
                f"| compliance_red_flags={account.compliance_red_flags or 'N/A'} "
                f"| ethical_growth_goal={account.ethical_growth_goal or 'N/A'} "
                f"| notes={account.notes or 'N/A'}"
            )
        )

    stakeholder_lines = []
    for stakeholder in (stakeholders or [])[:18]:
        stakeholder_lines.append(
            (
                f"- {stakeholder.name} | account={stakeholder.account.name} | role={stakeholder.get_role_display()} "
                f"| specialty={stakeholder.specialty or 'N/A'} | influence={stakeholder.get_influence_level_display()} "
                f"| evidence_preference={stakeholder.get_evidence_preference_display()} "
                f"| conference_interest={'yes' if stakeholder.conference_interest else 'no'} "
                f"| service_expectation={stakeholder.service_expectation or 'N/A'} "
                f"| notes={stakeholder.behavioral_notes or 'N/A'}"
            )
        )

    return (
        "Market account context:\n"
        + "\n".join(account_lines)
        + "\n\nStakeholder summaries:\n"
        + ("\n".join(stakeholder_lines) if stakeholder_lines else "- No stakeholder notes provided")
    )


def _call_gemini_with_retry(*, client, model_name: str, prompt: str):
    last_error = None
    for attempt in range(3):
        try:
            return client.models.generate_content(model=model_name, contents=prompt)
        except Exception as exc:
            last_error = exc
            error_text = str(exc).upper()
            transient = any(token in error_text for token in ("503", "UNAVAILABLE", "TIMEOUT", "TIMED OUT", "DEADLINE"))
            if not transient or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise last_error


def generate_structured_strategy(
    *,
    your_panel,
    competitor_panel,
    comparison_pair: dict | None,
    your_guideline_coverage: dict | None,
    competitor_guideline_coverage: dict | None,
    disease_filter: str = "",
    market_accounts=None,
    stakeholders=None,
) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured in the environment.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    compact_comparison_pair = _compact_pair_summary(comparison_pair)
    compact_your_guideline_coverage = _compact_guideline_coverage(your_guideline_coverage)
    compact_competitor_guideline_coverage = _compact_guideline_coverage(competitor_guideline_coverage)
    market_context = _market_accounts_context(market_accounts or [], stakeholders or [])

    prompt = f"""
You are helping build a strategic oncology panel intelligence report for MedStratix.

Return valid JSON only.

Required top-level keys:
- title
- executive_summary
- swot
- market_gap
- guideline_coverage_and_advantages
- marketing_campaigns
- sales_pitch
- recommended_next_steps

Rules:
- `swot` must contain keys: strengths, weaknesses, opportunities, threats
- each SWOT key must be a list of strings
- `market_gap` must contain keys: unmet_need, competitor_gap, your_gap, positioning_space
- `guideline_coverage_and_advantages` must contain keys: your_advantages, competitor_advantages, clinical_watchouts
- `marketing_campaigns` must be a list of at least 10 objects
- each campaign object must include:
  - name
  - audience
  - message
  - channel_mix
  - proof_point
  - call_to_action
- `sales_pitch` must be a persuasive multi-line string
- `recommended_next_steps` must be a list of strings

Use plain business language that an oncology commercial lead can use.
Be specific, comparative, and commercial-clinical.
Treat corruption pressure and referral distortion as a market obstacle that must be addressed ethically and compliantly.
Do not recommend bribery, cash inducements, kickbacks, or any illegal/unethical doctor payment scheme.
Recommend compliant alternatives such as evidence, service quality, turnaround reliability, institutional contracting, education, conference support when compliant, and account strategy.

Disease focus: {disease_filter or "All reviewed NCCN diseases"}

Your panel:
- Name: {your_panel.name}
- Company: {your_panel.company.name}
- Sample type: {your_panel.get_sample_type_display()}
- Price BDT: {your_panel.price or "N/A"}
- TAT: {your_panel.tat or "N/A"}

Competitor panel:
- Name: {competitor_panel.name}
- Company: {competitor_panel.company.name}
- Sample type: {competitor_panel.get_sample_type_display()}
- Price BDT: {competitor_panel.price or "N/A"}
- TAT: {competitor_panel.tat or "N/A"}

Panel-to-panel comparison:
{json.dumps(_json_safe(compact_comparison_pair), indent=2)}

Your NCCN coverage:
{json.dumps(_json_safe(compact_your_guideline_coverage), indent=2)}

Competitor NCCN coverage:
{json.dumps(_json_safe(compact_competitor_guideline_coverage), indent=2)}

{market_context}
""".strip()

    client = genai.Client(api_key=api_key)
    response = _call_gemini_with_retry(client=client, model_name=model_name, prompt=prompt)
    text = _response_text(response)
    if not text:
        raise ValueError("Gemini returned an empty response.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {exc}") from exc

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
