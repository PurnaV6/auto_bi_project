import pandas as pd

def guess_role(s: pd.Series) -> str:
    """
    Infer a simple semantic role for a column:
    - 'dimension' for categories, dates, booleans
    - 'measure' for generally continuous numeric fields
    """
    if pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_bool_dtype(s):
        return "dimension"

    if pd.api.types.is_numeric_dtype(s):
        # if many unique values -> treat as measure
        return "measure" if s.nunique(dropna=True) > 15 else "dimension"

    # non-numeric: low unique -> dimension, else treat as high-cardinality dimension
    if s.nunique(dropna=True) <= max(50, len(s) // 20):
        return "dimension"

    return "dimension"

def infer_schema(df: pd.DataFrame) -> dict:
    """
    Build a simple schema description for the uploaded dataframe.
    Returns:
        {
          "row_count": int,
          "fields": {
             col_name: {
                "role": "dimension" | "measure",
                "dtype": str,
                "distinct": int
             }, ...
          }
        }
    """
    fields = {}
    for c in df.columns:
        col = df[c]
        fields[c] = {
            "role": guess_role(col),
            "dtype": str(col.dtype),
            "distinct": int(col.nunique(dropna=True)),
        }

    return {
        "row_count": int(len(df)),
        "fields": fields,
    }
