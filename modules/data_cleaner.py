import pandas as pd

def clean_dataframe(df: pd.DataFrame):
    """
    Basic cleaning used by the app:
    - Trim spaces
    - Try to convert text columns to numeric or datetime where sensible
    - Drop duplicate rows
    - Fill missing numeric values with median
    - Fill missing text values with 'Missing'

    Returns
    -------
    df_clean : pd.DataFrame
        The cleaned dataframe.
    report : dict
        Simple metadata about what was done.
    """
    X = df.copy()

    # 1) Trim string columns
    for c in X.select_dtypes(include=["object", "string"]).columns:
        # Cast to str to avoid issues with mixed types, then strip
        X[c] = X[c].astype(str).str.strip()

    # 2) Try numeric / datetime conversions on object columns
    for c in X.columns:
        if X[c].dtype == "object":
            # Try numeric
            try:
                X[c] = pd.to_numeric(X[c])
                continue
            except Exception:
                pass

            # Try datetime
            try:
                X[c] = pd.to_datetime(X[c], errors="raise", infer_datetime_format=True)
            except Exception:
                pass

    # 3) Drop duplicate rows
    before = len(X)
    X = X.drop_duplicates()
    dropped = before - len(X)

    # 4) Handle missing values
    # Numeric → median
    for c in X.select_dtypes(include=["float", "int"]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())

    # Text / category → "Missing"
    for c in X.select_dtypes(include=["object", "string", "category"]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna("Missing")

    report = {
        "rows_before": int(before),
        "rows_after": int(len(X)),
        "duplicates_removed": int(dropped),
        "steps": [
            "trim_string_columns",
            "type_inference_numeric_datetime",
            "drop_duplicates",
            "impute_numeric_with_median",
            "impute_text_with_Missing",
        ],
    }

    return X, report
