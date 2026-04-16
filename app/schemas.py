from typing import Optional

from pydantic import BaseModel, Field


class HouseFeatures(BaseModel):
    """
    Structured features extracted by Stage 1 LLM.
    These field names must exactly match the sklearn pipeline column names.
    This object is serialized to a DataFrame row and passed to pipeline.predict().
    All fields are Optional because Stage 1 may not find every feature.
    """

    GrLivArea: Optional[float] = None
    BedroomAbvGr: Optional[int] = None
    FullBath: Optional[int] = None
    HalfBath: Optional[int] = None
    TotalBsmtSF: Optional[float] = None
    GarageArea: Optional[float] = None
    OverallQual: Optional[int] = Field(None, ge=1, le=10)
    YearBuilt: Optional[int] = Field(None, ge=1800, le=2024)
    Neighborhood: Optional[str] = None
    HouseStyle: Optional[str] = None


class ExtractionResult(BaseModel):
    """
    Full output of Stage 1. The 'features' field is what gets passed
    to the ML model after the user reviews and fills any missing values.
    """

    features: HouseFeatures
    extracted_fields: list[str]
    missing_fields: list[str]
    confidence: str
    needs_clarification: bool


class PredictionRequest(BaseModel):
    """
    Sent by the UI to /predict after the user has reviewed and
    optionally filled in missing features. The features dict here
    goes directly into the ML pipeline.
    """

    query: str
    features: HouseFeatures


class AgentResponse(BaseModel):
    """Final response returned to the UI."""

    predicted_price: float
    interpretation: str
    extracted_fields: list[str]
    missing_fields: list[str]
    confidence: str
    warning: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: str
    fallback_message: str
