import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .models import LLMGenerationLog, MarketingPlan
from .services.marketing_plan_generator import build_marketing_plan_request, generate_marketing_plan
from .services.marketing_plan_schema import MARKETING_PLAN_STYLE_LABELS, extract_marketing_plan_summary, normalize_marketing_plan_payload


logger = logging.getLogger("medstratix.tasks")


def _write_marketing_plan_prompt_snapshot(*, plan_id: int, task_id: str, prompt_text: str) -> str:
    prompt_dir = Path(settings.LOGS_DIR) / "marketing_plan_prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    file_path = prompt_dir / f"plan_{plan_id}_task_{task_id}.txt"
    file_path.write_text(prompt_text, encoding="utf-8")
    return str(file_path)


@shared_task(bind=True, ignore_result=False)
def generate_marketing_plan_task(self, plan_id: int) -> dict:
    plan = MarketingPlan.objects.get(pk=plan_id)
    request_payload = dict((plan.report_json or {}).get("generation_request", {}) or {})

    logger.info("Async marketing plan task started plan_id=%s task_id=%s", plan_id, self.request.id)
    report_json = dict(plan.report_json or {})
    report_json["async_task"] = {
        "id": self.request.id,
        "state": "STARTED",
    }
    plan.status = "running"
    plan.report_json = report_json
    plan.save(update_fields=["status", "report_json", "updated_at"])

    try:
        request_preview = build_marketing_plan_request(
            title=request_payload.get("title", plan.title),
            objective=request_payload.get("objective", plan.objective),
            geography=request_payload.get("geography", plan.geography),
            disease_focus=request_payload.get("disease_focus", plan.disease_focus),
            output_style=request_payload.get("output_style", plan.output_style),
            include_product_context=bool(request_payload.get("include_product_context", plan.include_product_context)),
            sales_expectation=request_payload.get("sales_expectation", {}),
            strategist_note=request_payload.get("strategist_note", plan.strategist_note),
            market_accounts_summary=request_payload.get("market_accounts_summary", []),
            stakeholder_contexts=request_payload.get("stakeholder_contexts", []),
            your_panel_summary=request_payload.get("your_panel_summary", {}),
            competitor_panel_summary=request_payload.get("competitor_panel_summary", {}),
            comparison_summary=request_payload.get("comparison_summary", {}),
            source_plan_contexts=request_payload.get("source_plan_contexts", []),
            model_name_override=request_payload.get("strategy_model", plan.llm_model),
        )
        prompt_path = _write_marketing_plan_prompt_snapshot(
            plan_id=plan_id,
            task_id=self.request.id,
            prompt_text=request_preview["prompt_text"],
        )
        report_json = dict(plan.report_json or {})
        report_json["debug_prompt_path"] = prompt_path
        report_json["async_task"] = {
            "id": self.request.id,
            "state": "STARTED",
        }
        plan.report_json = report_json
        plan.save(update_fields=["report_json", "updated_at"])
        logger.info("Async marketing plan prompt snapshot saved plan_id=%s task_id=%s path=%s", plan_id, self.request.id, prompt_path)

        result = generate_marketing_plan(
            title=request_payload.get("title", plan.title),
            objective=request_payload.get("objective", plan.objective),
            geography=request_payload.get("geography", plan.geography),
            disease_focus=request_payload.get("disease_focus", plan.disease_focus),
            output_style=request_payload.get("output_style", plan.output_style),
            include_product_context=bool(request_payload.get("include_product_context", plan.include_product_context)),
            sales_expectation=request_payload.get("sales_expectation", {}),
            strategist_note=request_payload.get("strategist_note", plan.strategist_note),
            market_accounts_summary=request_payload.get("market_accounts_summary", []),
            stakeholder_contexts=request_payload.get("stakeholder_contexts", []),
            your_panel_summary=request_payload.get("your_panel_summary", {}),
            competitor_panel_summary=request_payload.get("competitor_panel_summary", {}),
            comparison_summary=request_payload.get("comparison_summary", {}),
            source_plan_contexts=request_payload.get("source_plan_contexts", []),
            model_name_override=request_payload.get("strategy_model", plan.llm_model),
        )
        payload = normalize_marketing_plan_payload(
            request_payload.get("output_style", plan.output_style),
            result["response_json"],
            request_payload.get("title", plan.title),
        )

        report_json = dict(plan.report_json or {})
        report_json.pop("generation_error", None)
        report_json["async_task"] = {
            "id": self.request.id,
            "state": "SUCCESS",
        }
        report_json["plan_title_source"] = "user_input"
        report_json["plan_style_label"] = MARKETING_PLAN_STYLE_LABELS.get(plan.output_style, plan.output_style)

        plan.status = "completed"
        plan.llm_provider = result["provider"]
        plan.llm_model = result["model"]
        plan.executive_summary = extract_marketing_plan_summary(payload)
        plan.plan_json = payload
        plan.plan_text = result["response_text"]
        plan.report_json = report_json
        plan.save(
            update_fields=[
                "status",
                "llm_provider",
                "llm_model",
                "executive_summary",
                "plan_json",
                "plan_text",
                "report_json",
                "updated_at",
            ]
        )

        LLMGenerationLog.objects.create(
            marketing_plan=plan,
            provider=result["provider"],
            model_name=result["model"],
            operation="marketing_plan_generation",
            status="completed",
            prompt_text=result["prompt_text"],
            response_text=result["response_text"],
            response_json=payload,
            prompt_tokens=result["prompt_tokens"],
            response_tokens=result["response_tokens"],
            total_tokens=result["total_tokens"],
            estimated_cost_usd=result["estimated_cost_usd"],
        )
        logger.info("Async marketing plan task completed plan_id=%s task_id=%s", plan_id, self.request.id)
        return {"plan_id": plan_id, "status": "completed"}
    except Exception as exc:
        logger.exception("Async marketing plan task failed plan_id=%s task_id=%s", plan_id, self.request.id)
        report_json = dict(plan.report_json or {})
        report_json["async_task"] = {
            "id": self.request.id,
            "state": "FAILURE",
        }
        report_json["generation_error"] = str(exc)
        plan.status = "failed"
        plan.report_json = report_json
        plan.save(update_fields=["status", "report_json", "updated_at"])
        LLMGenerationLog.objects.create(
            marketing_plan=plan,
            provider="google_genai",
            model_name=request_payload.get("strategy_model", ""),
            operation="marketing_plan_generation",
            status="failed",
            response_text=str(exc),
            response_json={"error": str(exc)},
        )
        raise
