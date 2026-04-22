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


def build_final_marketing_report_xlsx(report) -> bytes:
    root_dir = Path(__file__).resolve().parents[3]
    builder_path = Path(__file__).resolve().parent / "js" / "build_marketing_plan_xlsx.mjs"
    node_binary = Path(
        os.getenv(
            "MEDSTRATIX_NODE_BIN",
            r"C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
        )
    )
    payload = report.report_json or {}
    ordered_sections = payload.get("ordered_plans", []) or []

    if not node_binary.exists():
        raise ValueError(f"Node runtime not found for Excel export: {node_binary}")

    section_rows = [["section", "item", "value"]]
    spreadsheet_rows = [["row_type", "label", "period", "formula_logic", "numeric_value", "notes", "plan_title"]]
    gantt_rows = [["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal", "plan_title"]]
    chronology_rows = [["sequence", "plan_id", "title", "plan_type", "created_at", "summary"]]
    kpi_rows = [["plan_title", "plan_type", "source_label", "metric_label", "metric", "target", "rationale"]]
    timeline_rows = [["plan_title", "plan_type", "source_label", "phase", "window", "owner", "action", "success_signal"]]

    for plan_item in ordered_sections:
        plan_title = stringify_plan_value(plan_item.get("title"))
        plan_type = stringify_plan_value(plan_item.get("output_style_label", ""))
        chronology_rows.append(
            [
                str(len(chronology_rows)),
                stringify_plan_value(plan_item.get("plan_id", "")),
                plan_title,
                plan_type,
                stringify_plan_value(plan_item.get("created_at", "")),
                stringify_plan_value(plan_item.get("summary", "")),
            ]
        )
        for section in plan_item.get("sections", []):
            label = stringify_plan_value(section.get("label"))
            value = section.get("value")
            if isinstance(value, dict):
                for key, item in value.items():
                    section_rows.append([f"{plan_title} | {label}", key.replace("_", " ").title(), stringify_plan_value(item)])
            elif isinstance(value, list):
                if value and all(isinstance(item, dict) for item in value):
                    for index, item in enumerate(value, start=1):
                        for item_key, item_value in item.items():
                            section_rows.append([f"{plan_title} | {label} #{index}", item_key.replace("_", " ").title(), stringify_plan_value(item_value)])
                else:
                    for index, item in enumerate(value, start=1):
                        section_rows.append([f"{plan_title} | {label}", str(index), stringify_plan_value(item)])
            else:
                section_rows.append([f"{plan_title} | {label}", "", stringify_plan_value(value)])

            if label.lower() == "spreadsheet model" and isinstance(value, list):
                for item in value:
                    spreadsheet_rows.append([
                        stringify_plan_value(item.get("row_type", "")),
                        stringify_plan_value(item.get("label", "")),
                        stringify_plan_value(item.get("period", "")),
                        stringify_plan_value(item.get("formula_logic", "")),
                        stringify_plan_value(item.get("numeric_value", "")),
                        stringify_plan_value(item.get("notes", "")),
                        plan_title,
                    ])
            if label.lower() == "gantt data" and isinstance(value, list):
                for item in value:
                    gantt_rows.append([
                        stringify_plan_value(item.get("task", "")),
                        stringify_plan_value(item.get("phase", "")),
                        stringify_plan_value(item.get("owner", "")),
                        stringify_plan_value(item.get("start_period", "")),
                        stringify_plan_value(item.get("end_period", "")),
                        stringify_plan_value(item.get("dependency", "")),
                        stringify_plan_value(item.get("status_signal", "")),
                        plan_title,
                    ])
            if label.lower() in {"follow-up, control & kpis", "launch kpis", "growth kpis", "account kpis"} and isinstance(value, dict):
                for metric_key, metric_value in value.items():
                    if isinstance(metric_value, dict):
                        metric_text = stringify_plan_value(metric_value.get("metric") or metric_value.get("summary") or metric_value)
                        target_text = stringify_plan_value(
                            metric_value.get("target")
                            or metric_value.get("target_y1")
                            or metric_value.get("target_y2")
                            or metric_value.get("goal")
                            or metric_value.get("expected")
                            or ""
                        )
                        rationale_text = stringify_plan_value(
                            metric_value.get("rationale")
                            or metric_value.get("notes")
                            or metric_value.get("signal")
                            or metric_value.get("why_it_matters")
                            or ""
                        )
                    else:
                        metric_text = stringify_plan_value(metric_value)
                        target_text = ""
                        rationale_text = ""
                    kpi_rows.append([
                        plan_title,
                        plan_type,
                        label,
                        metric_key.replace("_", " ").title(),
                        metric_text,
                        target_text,
                        rationale_text,
                    ])
            if label.lower() in {"execution roadmap", "90-day timeline", "quarterly roadmap", "30/60/90 account action plan"} and isinstance(value, list):
                for item in value:
                    timeline_rows.append([
                        plan_title,
                        plan_type,
                        label,
                        stringify_plan_value(item.get("phase") or item.get("theme") or item.get("horizon") or "Execution"),
                        stringify_plan_value(item.get("timeline") or item.get("week_range") or item.get("quarter") or item.get("horizon") or "TBD"),
                        stringify_plan_value(item.get("owner") or "Unassigned"),
                        stringify_plan_value(item.get("action") or item.get("deliverable") or item.get("key_actions") or "Planned action"),
                        stringify_plan_value(item.get("success_metric") or item.get("desired_outcome") or item.get("deliverable") or ""),
                    ])

    export_payload = {
        "title": report.title,
        "reportKind": "final_marketing_report",
        "planType": "final_marketing_report",
        "planTypeLabel": "Final Marketing Report",
        "geography": "",
        "diseaseFocus": "",
        "llmModel": "",
        "summary": report.executive_summary or payload.get("combined_summary") or "",
        "salesExpectation": {},
        "chronologyRows": chronology_rows,
        "kpiRows": kpi_rows,
        "timelineRows": timeline_rows,
        "sectionRows": section_rows,
        "spreadsheetRows": spreadsheet_rows,
        "ganttRows": gantt_rows,
    }

    with tempfile.TemporaryDirectory(prefix="medstratix-final-report-xlsx-") as temp_dir:
        temp_path = Path(temp_dir)
        input_json = temp_path / "report.json"
        output_xlsx = temp_path / "final_marketing_report.xlsx"
        input_json.write_text(json.dumps(export_payload, ensure_ascii=True), encoding="utf-8")

        subprocess.run(
            [str(node_binary), str(builder_path), str(input_json), str(output_xlsx)],
            check=True,
            cwd=root_dir,
            capture_output=True,
            text=True,
        )
        return output_xlsx.read_bytes()
