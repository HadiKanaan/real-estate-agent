from fastapi import FastAPI, HTTPException

from app.llm_chain import stage1_extract, stage2_interpret
from app.predictor import predict, train_stats
from app.schemas import AgentResponse, ExtractionResult, PredictionRequest

app = FastAPI(title="AI Real Estate Agent")


@app.get("/health")
def health() -> dict[str, str]:
    """Used by Docker and UI to verify the API is reachable."""
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractionResult)
def extract_features(body: dict) -> ExtractionResult:
    """
    Stage 1 only endpoint.
    The UI calls this to display extracted vs missing features before prediction.
    """
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query field is required")
    return stage1_extract(query)


@app.post("/predict", response_model=AgentResponse)
def predict_price(request: PredictionRequest) -> AgentResponse:
    """
    Full chain endpoint.
    1) Use user-confirmed features if provided, otherwise run Stage 1 extraction
    2) Predict with sklearn pipeline
    3) Interpret prediction with Stage 2 prompt
    4) Return structured response for UI rendering
    """
    try:
        features_dump = request.features.model_dump()
        provided = {k: v for k, v in features_dump.items() if v is not None}

        if provided:
            features = request.features
            extracted = list(provided.keys())
            missing = [k for k, v in features_dump.items() if v is None]
            confidence = "high" if len(extracted) >= 7 else "medium" if len(extracted) >= 4 else "low"
        else:
            extraction = stage1_extract(request.query)
            features = extraction.features
            extracted = extraction.extracted_fields
            missing = extraction.missing_fields
            confidence = extraction.confidence

        predicted_price = predict(features)
        interpretation = stage2_interpret(features, predicted_price, train_stats)

        return AgentResponse(
            predicted_price=predicted_price,
            interpretation=interpretation,
            extracted_fields=extracted,
            missing_fields=missing,
            confidence=confidence,
            warning=(
                "Low confidence - many features were missing or inferred from defaults."
                if confidence == "low"
                else None
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
