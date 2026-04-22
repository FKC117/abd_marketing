from __future__ import annotations

from copy import deepcopy


MARKETING_PLAN_STYLE_LABELS = {
    "brief_plan": "Brief Marketing Plan",
    "detailed_plan": "Detailed Marketing Plan",
    "launch_plan": "90-Day Launch Plan",
    "growth_plan": "Growth Plan",
    "account_plan": "Account Plan",
}


PLAN_SCHEMAS = {
    "brief_plan": {
        "structure_version": 2,
        "label": MARKETING_PLAN_STYLE_LABELS["brief_plan"],
        "focus": "A concise strategic snapshot for leadership or quick alignment.",
        "sections": [
            {"key": "executive_summary", "label": "Executive Summary", "kind": "object"},
            {"key": "core_market_problem", "label": "Core Market Problem", "kind": "object"},
            {"key": "target_segments", "label": "Target Segments", "kind": "list"},
            {"key": "positioning_angle", "label": "Positioning Angle", "kind": "object"},
            {"key": "top_campaigns", "label": "Top Campaigns", "kind": "list"},
            {"key": "priority_risks", "label": "Priority Risks", "kind": "list"},
            {"key": "recommended_next_steps", "label": "Recommended Next Steps", "kind": "list"},
        ],
        "blueprint": """
Required top-level keys:
- title
- executive_summary
- core_market_problem
- target_segments
- positioning_angle
- top_campaigns
- priority_risks
- recommended_next_steps

Detailed schema rules:
- `executive_summary` must include:
  - mission
  - value_gap
  - core_goal
  - summary

- `core_market_problem` must include:
  - market_reality
  - urgent_problem
  - why_it_matters_now

- `target_segments` must be a list of 3 to 5 objects with:
  - segment
  - why_this_segment
  - priority_message
  - main_barrier

- `positioning_angle` must include:
  - core_positioning
  - proof_points
  - differentiation

- `top_campaigns` must be a list of exactly 5 to 7 objects with:
  - name
  - audience
  - objective
  - message
  - channel
  - call_to_action

- `priority_risks` must be a list of strings.
- `recommended_next_steps` must be a list of concrete actions.
""".strip(),
    },
    "detailed_plan": {
        "structure_version": 2,
        "label": MARKETING_PLAN_STYLE_LABELS["detailed_plan"],
        "focus": "A fuller strategic blueprint with commercial, clinical, campaign, and financial planning depth.",
        "sections": [
            {"key": "executive_summary", "label": "Executive Summary", "kind": "object"},
            {"key": "market_research", "label": "Market Research", "kind": "object"},
            {"key": "swot", "label": "SWOT", "kind": "object"},
            {"key": "target_audience_personas", "label": "Target Audience & Personas", "kind": "list"},
            {"key": "unique_value_proposition", "label": "Unique Value Proposition", "kind": "object"},
            {"key": "product_pricing_strategy", "label": "Product & Pricing Strategy", "kind": "object"},
            {"key": "promotional_channel_strategy", "label": "Promotional & Channel Strategy", "kind": "object"},
            {"key": "sales_compliance_plan", "label": "Sales & Compliance Plan", "kind": "object"},
            {"key": "execution_roadmap", "label": "Execution Roadmap", "kind": "list"},
            {"key": "revenue_model", "label": "Revenue Model", "kind": "list"},
            {"key": "spreadsheet_model", "label": "Spreadsheet Model", "kind": "list"},
            {"key": "gantt_data", "label": "Gantt Data", "kind": "list"},
            {"key": "campaign_plan", "label": "Campaign Plan", "kind": "list"},
            {"key": "follow_up_control_kpis", "label": "Follow-up, Control & KPIs", "kind": "object"},
            {"key": "sales_pitch", "label": "Sales Pitch", "kind": "object"},
            {"key": "recommended_next_steps", "label": "Recommended Next Steps", "kind": "list"},
        ],
        "blueprint": """
Required top-level keys:
- title
- executive_summary
- market_research
- swot
- target_audience_personas
- unique_value_proposition
- product_pricing_strategy
- promotional_channel_strategy
- sales_compliance_plan
- execution_roadmap
- revenue_model
- campaign_plan
- follow_up_control_kpis
- sales_pitch
- recommended_next_steps

Detailed schema rules:
- `executive_summary` must include:
  - mission
  - value_gap
  - core_goal
  - summary

- `market_research` must include:
  - market_landscape
  - competitor_audit
  - key_constraints
  - market_distortion
  - opportunity_map

- `swot` must include:
  - strengths
  - weaknesses
  - opportunities
  - threats
  Each must be a list of strings.

- `target_audience_personas` must be a list of at least 3 objects with:
  - persona
  - role
  - priority
  - motivations
  - barriers
  - engagement_approach

- `unique_value_proposition` must include:
  - headline
  - proof_points
  - why_now

- `product_pricing_strategy` must include:
  - portfolio_strategy
  - pricing_logic
  - access_strategy
  - premium_justification

- `promotional_channel_strategy` must include:
  - medical_affairs
  - academic_partnerships
  - digital_content
  - field_activation
  - channel_mix_summary

- `sales_compliance_plan` must include:
  - anti_corruption_play
  - institutional_strategy
  - logistics_management
  - objection_handling
  - compliance_guardrails

- `execution_roadmap` must be a list of at least 6 objects with:
  - phase
  - timeline
  - owner
  - priority
  - deliverable
  - success_metric

- `revenue_model` must be a list of at least 3 objects with:
  - period
  - sample_volume_assumption
  - pricing_context
  - revenue_projection
  - key_driver

- `spreadsheet_model` must be a list of at least 3 objects with:
  - row_type
  - label
  - period
  - formula_logic
  - numeric_value
  - notes

- `gantt_data` must be a list of at least 6 objects with:
  - task
  - phase
  - owner
  - start_period
  - end_period
  - dependency
  - status_signal

- `campaign_plan` must be a list of at least 10 objects with:
  - name
  - audience
  - objective
  - message
  - channel_mix
  - timeline
  - call_to_action
  - kpi

- `follow_up_control_kpis` must include:
  - adoption_rate
  - retention_rate
  - clinical_impact
  - account_growth
  - campaign_effectiveness

- `sales_pitch` must include:
  - elevator_pitch
  - clinician_pitch
  - institution_pitch

- `recommended_next_steps` must be a list of concrete actions.
""".strip(),
    },
    "launch_plan": {
        "structure_version": 2,
        "label": MARKETING_PLAN_STYLE_LABELS["launch_plan"],
        "focus": "A 90-day execution plan with concrete launch sequencing, ownership, and milestones.",
        "sections": [
            {"key": "launch_summary", "label": "Launch Summary", "kind": "object"},
            {"key": "launch_assumptions", "label": "Launch Assumptions", "kind": "list"},
            {"key": "priority_accounts", "label": "Priority Accounts", "kind": "list"},
            {"key": "ninety_day_timeline", "label": "90-Day Timeline", "kind": "list"},
            {"key": "launch_campaigns", "label": "Launch Campaigns", "kind": "list"},
            {"key": "resource_plan", "label": "Resource Plan", "kind": "list"},
            {"key": "spreadsheet_model", "label": "Spreadsheet Model", "kind": "list"},
            {"key": "gantt_data", "label": "Gantt Data", "kind": "list"},
            {"key": "launch_risks", "label": "Launch Risks", "kind": "list"},
            {"key": "launch_kpis", "label": "Launch KPIs", "kind": "object"},
            {"key": "recommended_next_steps", "label": "Immediate Next Steps", "kind": "list"},
        ],
        "blueprint": """
Required top-level keys:
- title
- launch_summary
- launch_assumptions
- priority_accounts
- ninety_day_timeline
- launch_campaigns
- resource_plan
- launch_risks
- launch_kpis
- recommended_next_steps

Detailed schema rules:
- `launch_summary` must include:
  - launch_objective
  - launch_thesis
  - win_condition
  - summary

- `launch_assumptions` must be a list of strings.

- `priority_accounts` must be a list of at least 4 objects with:
  - account_or_segment
  - why_priority
  - target_stakeholders
  - desired_action

- `ninety_day_timeline` must be a list of at least 8 objects with:
  - phase
  - week_range
  - action
  - owner
  - deliverable
  - dependency
  - success_metric

- `launch_campaigns` must be a list of 6 to 10 objects with:
  - name
  - audience
  - objective
  - message
  - channel_mix
  - timing
  - call_to_action

- `resource_plan` must be a list of at least 5 objects with:
  - workstream
  - owner
  - support_needed
  - risk_if_missing

- `spreadsheet_model` must be a list of at least 3 objects with:
  - row_type
  - label
  - period
  - formula_logic
  - numeric_value
  - notes

- `gantt_data` must be a list of at least 8 objects with:
  - task
  - phase
  - owner
  - start_period
  - end_period
  - dependency
  - status_signal

- `launch_risks` must be a list of strings.

- `launch_kpis` must include:
  - account_activation
  - doctor_engagement
  - sample_inquiries
  - confirmed_samples
  - launch_learning_signal

- `recommended_next_steps` must be a list of immediate actions.
""".strip(),
    },
    "growth_plan": {
        "structure_version": 2,
        "label": MARKETING_PLAN_STYLE_LABELS["growth_plan"],
        "focus": "A scale-up plan focused on expansion levers, retention, partnerships, and revenue growth.",
        "sections": [
            {"key": "growth_summary", "label": "Growth Summary", "kind": "object"},
            {"key": "growth_levers", "label": "Growth Levers", "kind": "list"},
            {"key": "expansion_priorities", "label": "Expansion Priorities", "kind": "list"},
            {"key": "retention_strategy", "label": "Retention Strategy", "kind": "object"},
            {"key": "partnership_strategy", "label": "Partnership Strategy", "kind": "object"},
            {"key": "quarterly_roadmap", "label": "Quarterly Roadmap", "kind": "list"},
            {"key": "revenue_model", "label": "Revenue Model", "kind": "list"},
            {"key": "spreadsheet_model", "label": "Spreadsheet Model", "kind": "list"},
            {"key": "gantt_data", "label": "Gantt Data", "kind": "list"},
            {"key": "growth_kpis", "label": "Growth KPIs", "kind": "object"},
            {"key": "recommended_next_steps", "label": "Recommended Next Steps", "kind": "list"},
        ],
        "blueprint": """
Required top-level keys:
- title
- growth_summary
- growth_levers
- expansion_priorities
- retention_strategy
- partnership_strategy
- quarterly_roadmap
- revenue_model
- growth_kpis
- recommended_next_steps

Detailed schema rules:
- `growth_summary` must include:
  - growth_goal
  - current_position
  - scaling_thesis
  - summary

- `growth_levers` must be a list of at least 5 objects with:
  - lever
  - why_it_matters
  - expected_impact
  - main_risk

- `expansion_priorities` must be a list of at least 4 objects with:
  - opportunity
  - target_region_or_segment
  - reason
  - first_move

- `retention_strategy` must include:
  - doctor_retention
  - account_retention
  - service_retention
  - evidence_retention

- `partnership_strategy` must include:
  - institutional_partnerships
  - academic_partnerships
  - channel_partnerships
  - data_or_research_partnerships

- `quarterly_roadmap` must be a list of at least 4 objects with:
  - quarter
  - theme
  - key_actions
  - owner
  - success_metric

- `revenue_model` must be a list of at least 4 objects with:
  - period
  - sample_volume_assumption
  - revenue_projection
  - growth_driver
  - risk_note

- `spreadsheet_model` must be a list of at least 4 objects with:
  - row_type
  - label
  - period
  - formula_logic
  - numeric_value
  - notes

- `gantt_data` must be a list of at least 6 objects with:
  - task
  - phase
  - owner
  - start_period
  - end_period
  - dependency
  - status_signal

- `growth_kpis` must include:
  - active_accounts
  - repeat_order_rate
  - new_prescriber_growth
  - revenue_growth
  - strategic_partnerships

- `recommended_next_steps` must be a list of actions.
""".strip(),
    },
    "account_plan": {
        "structure_version": 2,
        "label": MARKETING_PLAN_STYLE_LABELS["account_plan"],
        "focus": "An institution-specific plan centered on stakeholder dynamics, account moves, and revenue potential.",
        "sections": [
            {"key": "account_summary", "label": "Account Summary", "kind": "object"},
            {"key": "stakeholder_map", "label": "Stakeholder Map", "kind": "list"},
            {"key": "account_dynamics", "label": "Account Dynamics", "kind": "object"},
            {"key": "account_value_proposition", "label": "Account Value Proposition", "kind": "object"},
            {"key": "objections_and_responses", "label": "Objections & Responses", "kind": "list"},
            {"key": "account_action_plan", "label": "30/60/90 Account Action Plan", "kind": "list"},
            {"key": "revenue_potential", "label": "Revenue Potential", "kind": "list"},
            {"key": "spreadsheet_model", "label": "Spreadsheet Model", "kind": "list"},
            {"key": "gantt_data", "label": "Gantt Data", "kind": "list"},
            {"key": "account_kpis", "label": "Account KPIs", "kind": "object"},
            {"key": "recommended_next_steps", "label": "Recommended Next Steps", "kind": "list"},
        ],
        "blueprint": """
Required top-level keys:
- title
- account_summary
- stakeholder_map
- account_dynamics
- account_value_proposition
- objections_and_responses
- account_action_plan
- revenue_potential
- account_kpis
- recommended_next_steps

Detailed schema rules:
- `account_summary` must include:
  - target_account
  - strategic_value
  - current_position
  - summary

- `stakeholder_map` must be a list of at least 4 objects with:
  - stakeholder
  - role
  - influence
  - motivation
  - barrier
  - engagement_move

- `account_dynamics` must include:
  - decision_process
  - referral_distortion
  - compliance_watchouts
  - service_expectations

- `account_value_proposition` must include:
  - primary_message
  - clinical_value
  - operational_value
  - institutional_value

- `objections_and_responses` must be a list of at least 5 objects with:
  - objection
  - why_it_exists
  - response
  - proof_point

- `account_action_plan` must be a list of at least 6 objects with:
  - horizon
  - action
  - owner
  - stakeholder_target
  - desired_outcome
  - success_metric

- `revenue_potential` must be a list of at least 3 objects with:
  - period
  - sample_volume_assumption
  - revenue_projection
  - confidence_level

- `spreadsheet_model` must be a list of at least 3 objects with:
  - row_type
  - label
  - period
  - formula_logic
  - numeric_value
  - notes

- `gantt_data` must be a list of at least 6 objects with:
  - task
  - phase
  - owner
  - start_period
  - end_period
  - dependency
  - status_signal

- `account_kpis` must include:
  - stakeholder_coverage
  - meetings_completed
  - trial_to_order_conversion
  - repeat_order_signal
  - revenue_progress

- `recommended_next_steps` must be a list of actions.
""".strip(),
    },
}


LEGACY_SECTION_KEYS = {
    "executive_summary",
    "market_research",
    "swot",
    "target_audience_personas",
    "unique_value_proposition",
    "product_pricing_strategy",
    "promotional_channel_strategy",
    "sales_compliance_plan",
    "sales_targets_forecast",
    "follow_up_control_kpis",
    "campaign_plan",
    "sales_pitch",
    "recommended_next_steps",
}


def get_marketing_plan_schema(output_style: str) -> dict:
    return deepcopy(PLAN_SCHEMAS.get(output_style, PLAN_SCHEMAS["brief_plan"]))


def build_marketing_plan_blueprint(output_style: str) -> str:
    schema = get_marketing_plan_schema(output_style)
    return schema["blueprint"]


def marketing_plan_focus_text(output_style: str) -> str:
    schema = get_marketing_plan_schema(output_style)
    return schema["focus"]


def normalize_marketing_plan_payload(output_style: str, payload: dict | None, requested_title: str) -> dict:
    normalized = deepcopy(payload or {})
    schema = get_marketing_plan_schema(output_style)
    normalized["title"] = requested_title
    normalized["plan_type"] = output_style
    normalized["plan_type_label"] = schema["label"]
    normalized["structure_version"] = schema["structure_version"]
    normalized = _ensure_processed_plan_data(output_style, normalized)
    normalized.setdefault("narrative_summary", extract_marketing_plan_summary(normalized))
    return normalized


def extract_marketing_plan_summary(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    for key_path in (
        ("executive_summary", "summary"),
        ("launch_summary", "summary"),
        ("growth_summary", "summary"),
        ("account_summary", "summary"),
    ):
        current = payload
        for key in key_path:
            if not isinstance(current, dict):
                current = ""
                break
            current = current.get(key, "")
        if current:
            return str(current).strip()
    return str(payload.get("narrative_summary", "")).strip()


def stringify_plan_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(part for part in (stringify_plan_value(item) for item in value) if part)
    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {part}" for key, part in ((key, stringify_plan_value(item)) for key, item in value.items()) if part
        )
    return str(value)


def marketing_plan_sections(output_style: str, payload: dict | None) -> list[dict]:
    payload = payload or {}
    schema = get_marketing_plan_schema(output_style)

    if payload.get("structure_version") == 2 or any(section["key"] in payload for section in schema["sections"]):
        sections = []
        for section in schema["sections"]:
            value = payload.get(section["key"])
            if value in (None, "", [], {}):
                continue
            sections.append(
                {
                    "key": section["key"],
                    "label": section["label"],
                    "kind": section["kind"],
                    "value": value,
                }
            )
        return sections

    legacy_sections = []
    for key in LEGACY_SECTION_KEYS:
        value = payload.get(key)
        if value in (None, "", [], {}):
            continue
        legacy_sections.append(
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "kind": "object" if isinstance(value, dict) else "list" if isinstance(value, list) else "text",
                "value": value,
            }
        )
    return legacy_sections


def marketing_plan_csv_rows(output_style: str, payload: dict | None) -> list[list[str]]:
    rows = [["section", "item", "value"]]
    for section in marketing_plan_sections(output_style, payload):
        value = section["value"]
        if isinstance(value, dict):
            for key, item in value.items():
                rows.append([section["label"], key.replace("_", " ").title(), stringify_plan_value(item)])
        elif isinstance(value, list):
            for index, item in enumerate(value, start=1):
                if isinstance(item, dict):
                    for item_key, item_value in item.items():
                        rows.append([f"{section['label']} #{index}", item_key.replace("_", " ").title(), stringify_plan_value(item_value)])
                else:
                    rows.append([section["label"], str(index), stringify_plan_value(item)])
        else:
            rows.append([section["label"], "", stringify_plan_value(value)])
    return rows


def _ensure_processed_plan_data(output_style: str, payload: dict) -> dict:
    normalized = deepcopy(payload)

    if output_style in {"detailed_plan", "growth_plan"} and not normalized.get("spreadsheet_model"):
        revenue_rows = normalized.get("revenue_model", []) or []
        normalized["spreadsheet_model"] = [
            {
                "row_type": "revenue_driver",
                "label": stringify_plan_value(item.get("growth_driver") or item.get("key_driver") or item.get("period") or f"Row {index}"),
                "period": stringify_plan_value(item.get("period")),
                "formula_logic": "Derived from plan revenue model",
                "numeric_value": stringify_plan_value(item.get("revenue_projection")),
                "notes": stringify_plan_value(item.get("sample_volume_assumption") or item.get("pricing_context") or item.get("risk_note")),
            }
            for index, item in enumerate(revenue_rows, start=1)
            if isinstance(item, dict)
        ]

    if output_style == "account_plan" and not normalized.get("spreadsheet_model"):
        revenue_rows = normalized.get("revenue_potential", []) or []
        normalized["spreadsheet_model"] = [
            {
                "row_type": "account_revenue",
                "label": stringify_plan_value(item.get("period") or f"Row {index}"),
                "period": stringify_plan_value(item.get("period")),
                "formula_logic": "Derived from account revenue potential",
                "numeric_value": stringify_plan_value(item.get("revenue_projection")),
                "notes": stringify_plan_value(item.get("sample_volume_assumption") or item.get("confidence_level")),
            }
            for index, item in enumerate(revenue_rows, start=1)
            if isinstance(item, dict)
        ]

    if output_style == "launch_plan" and not normalized.get("spreadsheet_model"):
        timeline_rows = normalized.get("ninety_day_timeline", []) or []
        normalized["spreadsheet_model"] = [
            {
                "row_type": "launch_activity",
                "label": stringify_plan_value(item.get("action") or item.get("phase") or f"Row {index}"),
                "period": stringify_plan_value(item.get("week_range")),
                "formula_logic": "Derived from 90-day launch timeline",
                "numeric_value": "",
                "notes": stringify_plan_value(item.get("success_metric") or item.get("deliverable")),
            }
            for index, item in enumerate(timeline_rows, start=1)
            if isinstance(item, dict)
        ]

    if not normalized.get("gantt_data"):
        source_rows = (
            normalized.get("ninety_day_timeline", [])
            or normalized.get("execution_roadmap", [])
            or normalized.get("quarterly_roadmap", [])
            or normalized.get("account_action_plan", [])
            or []
        )
        normalized["gantt_data"] = [
            {
                "task": stringify_plan_value(
                    item.get("action")
                    or item.get("deliverable")
                    or item.get("theme")
                    or item.get("desired_outcome")
                    or item.get("phase")
                    or f"Task {index}"
                ),
                "phase": stringify_plan_value(item.get("phase") or item.get("horizon") or item.get("quarter") or "Execution"),
                "owner": stringify_plan_value(item.get("owner") or "Unassigned"),
                "start_period": stringify_plan_value(item.get("week_range") or item.get("timeline") or item.get("quarter") or item.get("horizon") or "TBD"),
                "end_period": stringify_plan_value(item.get("week_range") or item.get("timeline") or item.get("quarter") or item.get("horizon") or "TBD"),
                "dependency": stringify_plan_value(item.get("dependency") or ""),
                "status_signal": stringify_plan_value(item.get("priority") or item.get("success_metric") or "Planned"),
            }
            for index, item in enumerate(source_rows, start=1)
            if isinstance(item, dict)
        ]

    return normalized
