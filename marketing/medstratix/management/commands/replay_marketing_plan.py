from django.core.management.base import BaseCommand, CommandError

from medstratix.models import MarketingPlan
from medstratix.services.marketing_plan_generator import generate_marketing_plan


class Command(BaseCommand):
    help = "Replay a marketing plan generation request outside Celery using the saved generation_request payload."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True, help="MarketingPlan ID to replay")

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        try:
            plan = MarketingPlan.objects.get(pk=plan_id)
        except MarketingPlan.DoesNotExist as exc:
            raise CommandError(f"MarketingPlan {plan_id} does not exist.") from exc

        request_payload = dict((plan.report_json or {}).get("generation_request", {}) or {})
        if not request_payload:
            raise CommandError(f"MarketingPlan {plan_id} has no saved generation_request payload.")

        self.stdout.write(self.style.WARNING(f"Replaying MarketingPlan {plan_id}: {plan.title}"))
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
        self.stdout.write(self.style.SUCCESS("Replay finished successfully."))
        self.stdout.write(f"Model: {result['model']}")
        self.stdout.write(f"Prompt tokens: {result['prompt_tokens']}")
        self.stdout.write(f"Response tokens: {result['response_tokens']}")
        self.stdout.write(f"Total tokens: {result['total_tokens']}")

