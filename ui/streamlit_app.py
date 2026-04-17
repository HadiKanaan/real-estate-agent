import os
import re
import unicodedata

import requests
import streamlit as st
from dotenv import load_dotenv

# Load .env so local Streamlit runs pick up API_URL and GEMINI_API_KEY settings.
load_dotenv()

# Determine API_URL with fallback strategy:
# 1. Check RAILWAY_BACKEND_URL (set by Railway service linking)
# 2. Check API_URL environment variable (from .env or OS)
# 3. Default to localhost:8000 for local development
API_URL_DEFAULT = (
    os.getenv("RAILWAY_BACKEND_URL") or
    os.getenv("API_URL") or
    "http://localhost:8000"
)
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
NUMERIC_FLOAT_FIELDS = {"GrLivArea", "TotalBsmtSF", "GarageArea"}
NUMERIC_INT_FIELDS = {"BedroomAbvGr", "FullBath", "HalfBath", "OverallQual", "YearBuilt"}
TEXT_FIELDS = {"Neighborhood", "HouseStyle"}

st.set_page_config(page_title="AI Real Estate Agent", page_icon="🏠", layout="wide")
st.title("AI Real Estate Agent")
st.caption("Two-stage flow: extract features -> confirm missing values -> predict price")


def _clean_interpretation(text: str) -> str:
    """Normalize odd unicode/spacing artifacts that occasionally appear in LLM output."""
    if not text:
        return "No interpretation was returned."

    cleaned = unicodedata.normalize("NFKC", str(text))
    cleaned = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff]", "", cleaned)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").replace("\t", " ")

    # Repair numbers split by spaces around commas (e.g., "153 , 091" -> "153,091").
    cleaned = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", cleaned)

    common_words = [
        "approximately",
        "predicted",
        "prediction",
        "property",
        "features",
        "market",
        "median",
        "range",
        "price",
        "value",
        "buyer",
        "home",
        "house",
        "upper",
        "lower",
        "portion",
        "quarter",
        "third",
        "above",
        "below",
        "near",
        "with",
        "this",
        "that",
        "comes",
        "from",
        "into",
        "high",
        "low",
        "in",
        "of",
        "to",
        "by",
        "and",
        "the",
        "a",
        "an",
        "is",
    ]

    def _segment_if_possible(token: str) -> str:
        """Split long joined strings into words when all segments are recognized."""
        t = token.lower()
        i = 0
        parts = []
        dictionary = sorted(common_words, key=len, reverse=True)

        while i < len(t):
            match = next((w for w in dictionary if t.startswith(w, i)), None)
            if not match:
                return token
            parts.append(match)
            i += len(match)

        return " ".join(parts)

    # Repair words split into single characters (e.g., "c o m e s" -> "comes").
    cleaned = re.sub(
        r"\b(?:[A-Za-z]\s+){3,}[A-Za-z]\b",
        lambda m: _segment_if_possible(m.group(0).replace(" ", ""))
        if len(m.group(0).replace(" ", "")) > 12
        else m.group(0).replace(" ", ""),
        cleaned,
    )

    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned

if "api_url" not in st.session_state:
    st.session_state.api_url = API_URL_DEFAULT
if "extraction" not in st.session_state:
    st.session_state.extraction = None
if "prediction" not in st.session_state:
    st.session_state.prediction = None
if "manual_features" not in st.session_state:
    st.session_state.manual_features = {}

st.sidebar.subheader("Backend Settings")
st.session_state.api_url = st.sidebar.text_input("API URL", value=st.session_state.api_url).strip()
API_URL = st.session_state.api_url.rstrip("/")
st.sidebar.caption(f"Current backend: {API_URL}")

try:
    health_resp = requests.get(f"{API_URL}/health", timeout=5)
    if health_resp.status_code == 200:
        try:
            health_json = health_resp.json()
            # This app returns exactly {"status": "ok"}. Extra keys strongly suggest a different backend.
            if set(health_json.keys()) != {"status"}:
                st.sidebar.warning(
                    "Connected backend does not look like this project API. "
                    "Set API URL to your container/backend port (for example http://localhost:8002)."
                )
        except ValueError:
            st.sidebar.warning("Backend health response is not JSON. Verify API URL.")
except requests.RequestException:
    st.sidebar.warning("Could not reach backend health endpoint. Verify API URL and backend status.")

query = st.text_area(
    "Step 1 - Describe the house",
    placeholder="Example: 3 bedroom house in a good neighborhood with a 2 car garage built in 2008",
    height=120,
)

if st.button("Step 2 - Extract Features", type="primary"):
    if not query.strip():
        st.error("Please enter a house description first.")
    else:
        try:
            resp = requests.post(
                f"{API_URL}/extract",
                json={"query": query.strip()},
                timeout=30,
            )
            if resp.status_code >= 400:
                try:
                    detail = resp.json().get("detail", resp.text)
                except ValueError:
                    detail = resp.text

                if resp.status_code == 404:
                    st.error(
                        (
                            f"Extraction failed: Not Found at {API_URL}/extract. "
                            "This usually means API_URL points to a different service."
                        )
                    )
                else:
                    st.error(f"Extraction failed: {detail}")
            else:
                st.session_state.extraction = resp.json()
                st.session_state.prediction = None
                st.session_state.manual_features = {}
        except requests.exceptions.ConnectionError:
            st.error(
                f"Could not connect to API at {API_URL}. Start FastAPI first (uvicorn app.main:app --reload)."
            )
        except requests.RequestException as exc:
            st.error(f"Request error while extracting features: {exc}")

extraction = st.session_state.extraction

if extraction:
    st.subheader("Step 3 - Review extracted and missing fields")
    features = extraction.get("features", {})
    extracted_fields = extraction.get("extracted_fields", [])
    missing_fields = extraction.get("missing_fields", [])

    left, right = st.columns(2)

    with left:
        st.markdown("### Extracted features")
        if extracted_fields:
            for field in extracted_fields:
                st.success(f"✅ {field}: {features.get(field)}")
        else:
            st.info("No fields were confidently extracted.")

    with right:
        st.markdown("### Missing fields (fill these in)")
        if missing_fields:
            for field in missing_fields:
                default_val = st.session_state.manual_features.get(field)

                if field in NUMERIC_FLOAT_FIELDS:
                    val = st.number_input(
                        field,
                        value=float(default_val) if default_val is not None else 0.0,
                        step=1.0,
                        key=f"input_{field}",
                    )
                    st.session_state.manual_features[field] = float(val)
                elif field in NUMERIC_INT_FIELDS:
                    if field == "OverallQual":
                        val = st.number_input(
                            field,
                            min_value=1,
                            max_value=10,
                            value=int(default_val) if default_val is not None else 6,
                            step=1,
                            key=f"input_{field}",
                        )
                    elif field == "YearBuilt":
                        val = st.number_input(
                            field,
                            min_value=1800,
                            max_value=2026,
                            value=int(default_val) if default_val is not None else 1973,
                            step=1,
                            key=f"input_{field}",
                        )
                    else:
                        val = st.number_input(
                            field,
                            min_value=0,
                            value=int(default_val) if default_val is not None else 0,
                            step=1,
                            key=f"input_{field}",
                        )
                    st.session_state.manual_features[field] = int(val)
                elif field in TEXT_FIELDS:
                    val = st.text_input(
                        field,
                        value=str(default_val) if default_val is not None else "",
                        key=f"input_{field}",
                    )
                    st.session_state.manual_features[field] = val.strip() if val.strip() else None
        else:
            st.success("No missing fields detected.")

    if st.button("Step 4 - Predict Price", type="primary"):
        payload_features = {}

        # Start from extracted values and keep only non-null values.
        for k in FEATURE_FIELDS:
            val = features.get(k)
            if val is not None:
                payload_features[k] = val

        # Overlay user manual inputs for missing fields.
        for k, v in st.session_state.manual_features.items():
            if v is not None and (not isinstance(v, str) or v.strip()):
                payload_features[k] = v

        payload = {
            "query": query.strip(),
            "features": {k: payload_features.get(k) for k in FEATURE_FIELDS},
        }

        try:
            resp = requests.post(f"{API_URL}/predict", json=payload, timeout=60)
            if resp.status_code >= 400:
                try:
                    detail = resp.json().get("detail", resp.text)
                except ValueError:
                    detail = resp.text

                if resp.status_code == 404:
                    st.error(
                        (
                            f"Prediction failed: Not Found at {API_URL}/predict. "
                            "This usually means API_URL points to a different service."
                        )
                    )
                else:
                    st.error(f"Prediction failed: {detail}")
            else:
                st.session_state.prediction = resp.json()
        except requests.exceptions.ConnectionError:
            st.error(
                f"Could not connect to API at {API_URL}. Start FastAPI first (uvicorn app.main:app --reload)."
            )
        except requests.RequestException as exc:
            st.error(f"Request error while predicting price: {exc}")

prediction = st.session_state.prediction

if prediction:
    st.subheader("Step 5 - Predicted price")
    st.metric("Predicted Sale Price", f"${prediction['predicted_price']:,.0f}")

    st.subheader("Step 6 - Model interpretation")
    st.info(_clean_interpretation(prediction.get("interpretation", "No interpretation was returned.")))

    if prediction.get("confidence") == "low":
        st.warning(prediction.get("warning") or "Low confidence prediction.")
