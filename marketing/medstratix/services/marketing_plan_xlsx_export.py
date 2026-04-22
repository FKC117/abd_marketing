from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .marketing_plan_schema import marketing_plan_csv_rows, marketing_plan_sections, stringify_plan_value


def _section_rows(plan) -> list[list[str]]:
    rows = [["section", "item", "value"]]
    for section in marketing_plan_sections(plan.output_style, plan.plan_json or {}):
        value = section["value"]
        if isinstance(value, dict):
            for key, item in value.items():
                rows.append([section["label"], key.replace("_", " ").title(), stringify_plan_value(item)])
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                for index, item in enumerate(value, start=1):
                    for item_key, item_value in item.items():
                        rows.append([f"{section['label']} #{index}", item_key.replace("_", " ").title(), stringify_plan_value(item_value)])
            else:
                for index, item in enumerate(value, start=1):
                    rows.append([section["label"], str(index), stringify_plan_value(item)])
        else:
            rows.append([section["label"], "", stringify_plan_value(value)])
    return rows


def _object_rows(items: list[dict], headers: list[str]) -> list[list[str]]:
    rows = [headers]
    for item in items or []:
        rows.append([stringify_plan_value(item.get(header, "")) for header in headers])
    return rows


def build_marketing_plan_xlsx(plan) -> bytes:
    root_dir = Path(__file__).resolve().parents[3]
    builder_path = Path(__file__).resolve().parent / "js" / "build_marketing_plan_xlsx.mjs"
    node_binary = Path(
        os.getenv(
            "MEDSTRATIX_NODE_BIN",
            r"C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
        )
    )
    payload = plan.plan_json or {}

    if not node_binary.exists():
        raise ValueError(f"Node runtime not found for Excel export: {node_binary}")

    spreadsheet_rows = _object_rows(
        payload.get("spreadsheet_model", []) or [],
        ["row_type", "label", "period", "formula_logic", "numeric_value", "notes"],
    )
    gantt_rows = _object_rows(
        payload.get("gantt_data", []) or [],
        ["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"],
    )

    export_payload = {
        "title": plan.title,
        "planType": plan.output_style,
        "planTypeLabel": payload.get("plan_type_label", plan.output_style),
        "geography": plan.geography,
        "diseaseFocus": plan.disease_focus,
        "llmModel": plan.llm_model,
        "summary": payload.get("narrative_summary") or plan.executive_summary,
        "salesExpectation": dict((plan.report_json or {}).get("sales_expectation", {}) or {}),
        "sectionRows": _section_rows(plan),
        "spreadsheetRows": spreadsheet_rows,
        "ganttRows": gantt_rows,
    }

    with tempfile.TemporaryDirectory(prefix="medstratix-plan-xlsx-") as temp_dir:
        temp_path = Path(temp_dir)
        input_json = temp_path / "plan.json"
        output_xlsx = temp_path / "marketing_plan.xlsx"
        input_json.write_text(json.dumps(export_payload, ensure_ascii=True), encoding="utf-8")

        subprocess.run(
            [str(node_binary), str(builder_path), str(input_json), str(output_xlsx)],
            check=True,
            cwd=root_dir,
            capture_output=True,
            text=True,
        )
        return output_xlsx.read_bytes()
