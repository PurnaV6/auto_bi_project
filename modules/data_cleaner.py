import pandas as pd

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic cleaning used by the app:
    - Trim spaces
    - Try to convert text columns to numeric or datetime where sensible
    - Drop duplicate rows
    - Fill missing numeric values with median
    - Fill missing text values with 'Missing'
    """
    X = df.copy()

    # 1) Trim string columns
    for c in X.select_dtypes(include=["object", "string"]).columns:
        X[c] = X[c].astype(str).str.strip()

    # 2) Try numeric / datetime conversions on object columns
    for c in X.columns:
        if X[c].dtype == "object":
            # try numeric
            try:
                X[c] = pd.to_numeric(X[c])
                continue
            except Exception:
                pass
            # try datetime
            try:
                X[c] = pd.to_datetime(X[c], errors="raise", infer_datetime_format=True)
            except Exception:
                pass

    # 3) Drop duplicate rows
    X = X.drop_duplicates()

    # 4) Handle missing values
    # numeric → median
    for c in X.select_dtypes(include=["float", "int"]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())

    # text / category → "Missing"
    for c in X.select_dtypes(include=["object", "string", "category"]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna("Missing")

    return X
