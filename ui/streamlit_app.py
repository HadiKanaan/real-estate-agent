import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
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

if "extraction" not in st.session_state:
    st.session_state.extraction = None
if "prediction" not in st.session_state:
    st.session_state.prediction = None
if "manual_features" not in st.session_state:
    st.session_state.manual_features = {}

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
                detail = resp.json().get("detail", resp.text)
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
                detail = resp.json().get("detail", resp.text)
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
    st.info(prediction.get("interpretation", "No interpretation was returned."))

    if prediction.get("confidence") == "low":
        st.warning(prediction.get("warning") or "Low confidence prediction.")
