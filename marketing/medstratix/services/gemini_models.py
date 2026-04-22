import logging
import os

from .strategy_generator import _make_genai_client


logger = logging.getLogger("medstratix.gemini_models")


FALLBACK_MODELS = [
    {
        "code": "gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "description": "Best for deep reasoning and complex strategy formulation.",
        "recommended": True,
    },
    {
        "code": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "description": "Balanced speed and quality for strategy drafts.",
        "recommended": False,
    },
    {
        "code": "gemini-2.5-flash-lite-preview-09-2025",
        "label": "Gemini 2.5 Flash Lite Preview",
        "description": "Lower-cost option for lighter draft generation.",
        "recommended": False,
    },
]


def _model_option(code: str, display_name: str, description: str = "", recommended: bool = False) -> dict:
    return {
        "code": code,
        "label": display_name,
        "description": description,
        "recommended": recommended,
    }


def list_strategy_models() -> list[dict]:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        logger.warning("GOOGLE_API_KEY missing while listing Gemini models. Falling back to static options.")
        return FALLBACK_MODELS

    fetch_remote = os.getenv("GEMINI_FETCH_MODELS_ON_LOAD", "").strip().lower() in {"1", "true", "yes", "on"}
    if not fetch_remote:
        logger.info("Using static Gemini model list for builder dropdown. Remote model fetch is disabled.")
        return FALLBACK_MODELS

    try:
        client = _make_genai_client(api_key)
        options = []
        for model in client.models.list():
            code = getattr(model, "name", "") or ""
            code = code.replace("models/", "")
            display_name = getattr(model, "display_name", "") or code
            if not code.startswith("gemini"):
                continue

            lowered = code.lower()
            if any(token in lowered for token in ("image", "tts", "audio", "live", "embedding")):
                continue

            description = getattr(model, "description", "") or ""
            recommended = code == "gemini-2.5-pro"
            options.append(_model_option(code, display_name, description, recommended))

        if not options:
            logger.warning("Gemini models.list returned no usable text models. Falling back to static options.")
            return FALLBACK_MODELS

        options.sort(key=lambda item: (not item["recommended"], item["label"].lower()))
        return options
    except Exception:
        logger.exception("Failed to fetch Gemini model list. Falling back to static options.")
        return FALLBACK_MODELS
