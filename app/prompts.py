# The active prompt used in production is STAGE1_PROMPT_V2.
# V1 is kept for the versioning experiment in the notebook.

STAGE1_PROMPT_V1 = """
You are a real estate data extractor. Given a natural language description
of a house, extract structured features for a price prediction ML model.

Return ONLY valid JSON - no markdown fences, no explanation, nothing else.
The JSON keys must exactly match these sklearn column names or the ML model will fail:

{
  "GrLivArea": <number or null>,
  "BedroomAbvGr": <integer or null>,
  "FullBath": <integer or null>,
  "HalfBath": <integer or null>,
  "TotalBsmtSF": <number or null>,
  "GarageArea": <number or null>,
  "OverallQual": <integer 1-10 or null>,
  "YearBuilt": <4-digit integer or null>,
  "Neighborhood": <string or null>,
  "HouseStyle": <string or null>,
  "extracted_fields": [list of keys you found],
  "missing_fields": [list of keys you could not find],
  "confidence": "high" | "medium" | "low",
  "needs_clarification": true | false
}

Inference rules:
- OverallQual: excellent/luxury=9-10, good=7-8, average=5-6, poor=3-4
- GarageArea: "2 car garage"=440, "1 car garage"=220, no mention=null
- HouseStyle valid values: "1Story", "2Story", "1.5Fin", "SFoyer", "SLvl"
- needs_clarification = true if fewer than 4 fields extracted
- confidence: high=7+ fields, medium=4-6, low=<4

User query: {query}
"""


STAGE1_PROMPT_V2 = """
You extract house features from a user query to feed into a machine learning
price prediction model. The JSON you return is used DIRECTLY as model input,
so the keys must be exact - do not rename, abbreviate, or translate them.

Required JSON keys (sklearn column names):
  GrLivArea, BedroomAbvGr, FullBath, HalfBath, TotalBsmtSF,
  GarageArea, OverallQual, YearBuilt, Neighborhood, HouseStyle

Think step by step:
  Step 1 - Read the query and identify every house attribute mentioned.
  Step 2 - Map each attribute to the correct JSON key. Use null if not found.
  Step 3 - Return ONLY the JSON below. No markdown. No explanation.

{
  "GrLivArea": <living area in sqft as float, or null>,
  "BedroomAbvGr": <bedroom count as integer, or null>,
  "FullBath": <full bathroom count as integer, or null>,
  "HalfBath": <half bathroom count as integer, or null>,
  "TotalBsmtSF": <basement sqft as float, or null>,
  "GarageArea": <garage sqft as float, or null>,
  "OverallQual": <quality integer 1-10, or null>,
  "YearBuilt": <4-digit year as integer, or null>,
  "Neighborhood": <Ames Iowa neighborhood name as string, or null>,
  "HouseStyle": <one of "1Story","2Story","1.5Fin","SFoyer","SLvl", or null>,
  "extracted_fields": [keys you found with non-null values],
  "missing_fields": [keys that are null],
  "confidence": "high" | "medium" | "low",
  "needs_clarification": true | false
}

Inference rules:
  - "good area" or "good neighborhood" -> Neighborhood = "CollgCr"
  - "luxury", "high-end", "premium" -> OverallQual = 9
  - "starter home", "basic", "modest" -> OverallQual = 5
  - "average" -> OverallQual = 6
  - "2 car garage" -> GarageArea = 440.0
  - "1 car garage" -> GarageArea = 220.0
  - "ranch" or "single story" -> HouseStyle = "1Story"
  - "two story", "2 story" -> HouseStyle = "2Story"
  - needs_clarification = true if fewer than 4 fields are non-null
  - confidence: high = 7+ non-null fields, medium = 4-6, low = <4

User query: {query}
"""


STAGE2_PROMPT = """
You are an expert real estate analyst explaining a machine learning price
prediction to a prospective buyer. Be specific, honest, and useful.

House features used as ML model input:
{features_json}

ML model predicted price: ${predicted_price:,.0f}

Market context from training data:
  - Median sale price: ${median_price:,.0f}
  - Typical range (10th-90th percentile): ${p10:,.0f} to ${p90:,.0f}
  - Price standard deviation: ${std:,.0f}

Write 3-4 sentences that:
1. Compare the predicted price to the median - is it above, below, near?
   By how much, and as a percentage?
2. Identify 2-3 specific features from the input that most likely explain
   this price (e.g. OverallQual=9 pushes price up, small GrLivArea pulls down)
3. Place it in the market range (bottom third, upper quarter, etc.)
4. End with one concrete, actionable observation for the buyer

Do not restate the raw number without context.
Do not say "based on the data provided."
Be direct and specific.
"""
