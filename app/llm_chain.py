import json
import os
import re
import traceback

import google.generativeai as genai
from dotenv import load_dotenv

from app.prompts import STAGE1_PROMPT_V2, STAGE2_PROMPT
from app.schemas import ExtractionResult, HouseFeatures

load_dotenv()

# Read the API key once on module import so bad configuration fails fast.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env before running the app.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

FEATURE_FIELDS = [
    "GrLivArea",
    "BedroomAbvGr",
    "FullBath",
    "HalfBath",
    "TotalBsmtSF",
    "GarageArea",
    "OverallQual",
    "YearBuilt",
    "Neighborhood",
    "HouseStyle",
]


def _call_gemini(prompt: str) -> str:
    """
    Thin wrapper around Gemini so Stage 1 and Stage 2 share one call path.
    This function is isolated to make future mocking/testing easier.
    """
    response = model.generate_content(prompt)
    return response.text


def _strip_fences(text: str) -> str:
    """
    Remove markdown fences if the model wraps JSON in ```json ... ```.
    """
    text = re.sub(r"```(?:json)?", "", text)
    return text.strip()


def stage1_extract(query: str) -> ExtractionResult:
    """
    Run Stage 1 extraction and convert model JSON output into ExtractionResult.
    On any parsing or API failure, return a safe fallback response.
    """
    # Use direct placeholder replacement because the prompt contains many
    # JSON braces that are not Python format placeholders.
    prompt = STAGE1_PROMPT_V2.replace("{query}", query)
    raw = ""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_fences(raw)
        data = json.loads(cleaned)

        # Keep only the schema contract keys that feed the ML pipeline.
        feature_data = {k: data.get(k) for k in FEATURE_FIELDS}
        features = HouseFeatures(**feature_data)

        extracted = data.get(
            "extracted_fields",
            [k for k in FEATURE_FIELDS if data.get(k) is not None],
        )
        missing = data.get(
            "missing_fields",
            [k for k in FEATURE_FIELDS if data.get(k) is None],
        )
        confidence = data.get("confidence", "low")
        needs_clarification = data.get("needs_clarification", len(extracted) < 4)

        # Enforce contract consistency in case LLM returns invalid field names.
        extracted = [k for k in extracted if k in FEATURE_FIELDS]
        missing = [k for k in missing if k in FEATURE_FIELDS]

        # Rebuild missing if lists are inconsistent or incomplete.
        if len(set(extracted) | set(missing)) < len(FEATURE_FIELDS):
            extracted = [k for k in FEATURE_FIELDS if getattr(features, k) is not None]
            missing = [k for k in FEATURE_FIELDS if getattr(features, k) is None]

        return ExtractionResult(
            features=features,
            extracted_fields=extracted,
            missing_fields=missing,
            confidence=confidence,
            needs_clarification=needs_clarification,
        )

    except json.JSONDecodeError as e:
        print(f"[stage1] JSON parse failed: {e}\\nRaw output: {raw}")
        print(traceback.format_exc())
        return ExtractionResult(
            features=HouseFeatures(),
            extracted_fields=[],
            missing_fields=FEATURE_FIELDS,
            confidence="low",
            needs_clarification=True,
        )
    except Exception as e:
        print(f"[stage1] Unexpected error: {e}")
        print(traceback.format_exc())
        return ExtractionResult(
            features=HouseFeatures(),
            extracted_fields=[],
            missing_fields=FEATURE_FIELDS,
            confidence="low",
            needs_clarification=True,
        )


def stage2_interpret(features: HouseFeatures, predicted_price: float, train_stats: dict) -> str:
    """
    Run Stage 2 interpretation by sending confirmed features + prediction context.
    Returns plain text explanation; falls back to a deterministic summary on errors.
    """
    features_json = json.dumps(
        {k: v for k, v in features.model_dump().items() if v is not None},
        indent=2,
    )

    prompt = STAGE2_PROMPT.format(
        features_json=features_json,
        predicted_price=predicted_price,
        median_price=train_stats["median_price"],
        p10=train_stats["price_10th_percentile"],
        p90=train_stats["price_90th_percentile"],
        std=train_stats["price_std"],
    )

    try:
        return _call_gemini(prompt).strip()
    except Exception as e:
        print(f"[stage2] Gemini call failed: {e}")
        print(traceback.format_exc())
        return (
            f"The predicted price is ${predicted_price:,.0f}. "
            f"Market median is ${train_stats['median_price']:,.0f}. "
            "(Full interpretation unavailable due to Gemini API error.)"
        )
