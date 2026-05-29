"""PD Css Cross model.

This is a simplified, single-model version of the workflow from
ASB_step_by_step.py.  It models `default_cross12`, the 12-month default flag for
the cash loan in the cross-sell setting.

Business definition:
    PD Css Cross estimates the probability that a cross-sold cash loan defaults
    within 12 months, using information available at the instalment-loan
    application moment.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier


DATA_PATH = Path("abt_app.sas7bdat")
OUTPUT_DIR = Path("outputs/pd_css_cross")
SAS_PATH = OUTPUT_DIR / "scoring_code.sas"

MODEL_ID = "PD_CSS_CROSS"
TARGET = "default_cross12"
ID_COLUMN = "aid"
PERIOD_COLUMN = "period"
PD_COLUMN = "PD_CSS_CROSS"
SCORE_COLUMN = "SCORE_PD_CSS_CROSS"

PERIOD_FROM = "197501"
PERIOD_TO = "198712"
RANDOM_STATE = 1234
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15
MIN_HOLDOUT_ROWS = 250

APPLICATION_PRODUCT = "ins"
DECISION = "A"
CROSS_RESPONSE = 1

CANDIDATE_PREFIXES = ("app", "act", "agr", "ags")
MAX_MISSING_RATE = 0.98
MAX_CATEGORY_LEVELS = 50
MAX_DOMINANT_SHARE = 0.995
MIN_UNIVARIATE_GINI = 0.02
ANALYSIS_MAX_BINS = 4
ANALYSIS_MIN_BIN_SHARE = 0.05
MAX_VARIABLE_REPORT_SHEETS = 50
EPSILON = 0.0001
LEAKAGE_TOKENS = (
    "default",
    "cross_response",
    "cross_after",
    "cross_aid",
    "pd_",
    "score_",
)

ENGINEERED_RATIOS = {
    "eng_app_loan_to_income": ("app_loan_amount", "app_income"),
    "eng_app_installment_to_income": ("app_installment", "app_income"),
    "eng_app_spending_to_income": ("app_spendings", "app_income"),
    "eng_act_loaninc_to_income": ("act_loaninc", "app_income"),
    "eng_act_cc_to_income": ("act_cc", "app_income"),
}


def safe_abs_gini(y_true, score):
    if pd.Series(score).nunique(dropna=True) < 2:
        return 0.0
    auc = roc_auc_score(y_true, score)
    return float(abs(2.0 * auc - 1.0))


def load_sample():
    df = pd.read_sas(DATA_PATH, encoding="LATIN2")
    df[PERIOD_COLUMN] = df[PERIOD_COLUMN].astype(str)
    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].str.strip().replace("", np.nan)

    application_mask = (
        df[PERIOD_COLUMN].between(PERIOD_FROM, PERIOD_TO)
        & df["decision"].eq(DECISION)
        & df["product"].eq(APPLICATION_PRODUCT)
    )
    cross_response_mask = application_mask & df["cross_response"].eq(CROSS_RESPONSE)
    target_mask = cross_response_mask & df[TARGET].notna()
    if target_mask.sum() == 0:
        raise ValueError(f"No rows found with non-missing {TARGET}.")

    sample = df.loc[target_mask].reset_index(drop=True)
    sample_note = (
        f"PD Css Cross sample: decision={DECISION}, product={APPLICATION_PRODUCT}, "
        f"cross_response={CROSS_RESPONSE}, target={TARGET} not missing."
    )
    sample.attrs["sample_note"] = sample_note
    sample.attrs["sample_audit"] = {
        "model_id": MODEL_ID,
        "target": TARGET,
        "period_from": PERIOD_FROM,
        "period_to": PERIOD_TO,
        "decision": DECISION,
        "product": APPLICATION_PRODUCT,
        "cross_response": CROSS_RESPONSE,
        "application_rows": int(application_mask.sum()),
        "cross_response_rows": int(cross_response_mask.sum()),
        "target_non_missing_rows": int(target_mask.sum()),
        "target_missing_rows_in_cross_response_sample": int(
            (cross_response_mask & df[TARGET].isna()).sum()
        ),
        "target_not_missing_share_in_cross_response_sample": float(
            df.loc[cross_response_mask, TARGET].notna().mean()
        ),
        "duplicate_id_rows": int(sample.duplicated(ID_COLUMN).sum()),
        "event_rate": float(sample[TARGET].mean()),
        "sample_note": sample_note,
    }
    return sample


def select_features(df):
    return [
        column
        for column in df.columns
        if column[:3].lower() in CANDIDATE_PREFIXES
        and not any(token in column.lower() for token in LEAKAGE_TOKENS)
    ]


def add_features(X):
    X = X.copy()

    for new_column, (numerator, denominator) in ENGINEERED_RATIOS.items():
        if numerator in X.columns and denominator in X.columns:
            X[new_column] = X[numerator] / X[denominator].replace(0, np.nan)

    X["eng_missing_count"] = X.isna().sum(axis=1)
    return X.replace([np.inf, -np.inf], np.nan)


def write_sample_audit(sample, raw_features, selected_features, feature_report):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([sample.attrs["sample_audit"]]).to_csv(
        OUTPUT_DIR / "sample_definition.csv", index=False
    )
    pd.Series(raw_features, name="feature").to_csv(
        OUTPUT_DIR / "raw_candidate_features.csv", index=False
    )
    pd.Series(selected_features, name="feature").to_csv(
        OUTPUT_DIR / "selected_features.csv", index=False
    )
    feature_report.to_csv(OUTPUT_DIR / "feature_quality.csv", index=False)


def temporal_holdout_masks(sample):
    sample_periods = sample[[PERIOD_COLUMN]].copy()
    sample_periods["row_number"] = np.arange(sample.shape[0])
    period_counts = (
        sample_periods.groupby(PERIOD_COLUMN)
        .size()
        .sort_index()
        .rename("n_obs")
        .reset_index()
    )

    test_target = max(MIN_HOLDOUT_ROWS, int(round(sample.shape[0] * TEST_FRACTION)))
    validation_target = max(
        MIN_HOLDOUT_ROWS, int(round(sample.shape[0] * VALIDATION_FRACTION))
    )

    reversed_counts = period_counts.iloc[::-1].copy()
    reversed_counts["cum_recent"] = reversed_counts["n_obs"].cumsum()
    test_start = reversed_counts.loc[
        reversed_counts["cum_recent"] >= test_target, PERIOD_COLUMN
    ].iloc[0]

    pre_test_counts = period_counts[period_counts[PERIOD_COLUMN] < test_start].copy()
    reversed_pre_test = pre_test_counts.iloc[::-1].copy()
    reversed_pre_test["cum_recent"] = reversed_pre_test["n_obs"].cumsum()
    validation_start = reversed_pre_test.loc[
        reversed_pre_test["cum_recent"] >= validation_target, PERIOD_COLUMN
    ].iloc[0]

    period = sample[PERIOD_COLUMN]
    masks = {
        "train": period < validation_start,
        "validation": (period >= validation_start) & (period < test_start),
        "test": period >= test_start,
    }
    split_definition = {
        "validation_start": validation_start,
        "test_start": test_start,
        "validation_target_rows": validation_target,
        "test_target_rows": test_target,
    }
    return masks, split_definition


def split_by_time(sample):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    masks, split_definition = temporal_holdout_masks(sample)

    empty_splits = [name for name, mask in masks.items() if mask.sum() == 0]
    if empty_splits:
        raise ValueError(f"Empty temporal split(s): {', '.join(empty_splits)}")

    single_class_splits = [
        name for name, mask in masks.items() if sample.loc[mask, TARGET].nunique() < 2
    ]
    if single_class_splits:
        raise ValueError(
            "The target has only one class in temporal split(s): "
            f"{', '.join(single_class_splits)}"
        )

    pd.DataFrame(
        [
            {
                "split": split_name,
                "n_obs": int(mask.sum()),
                "period_min": sample.loc[mask, PERIOD_COLUMN].min(),
                "period_max": sample.loc[mask, PERIOD_COLUMN].max(),
                "bad_rate": float(sample.loc[mask, TARGET].mean()),
                **split_definition,
            }
            for split_name, mask in masks.items()
        ]
    ).to_csv(OUTPUT_DIR / "split_definition.csv", index=False)

    return masks


def categorical_univariate_score(series, y):
    grouped = (
        pd.DataFrame({"value": series.fillna("__MISSING__"), "target": y})
        .groupby("value")["target"]
        .mean()
    )
    return series.fillna("__MISSING__").map(grouped).fillna(float(np.mean(y)))


def numeric_univariate_score(series):
    numeric = pd.to_numeric(series, errors="coerce")
    median = numeric.median()
    if pd.isna(median):
        return pd.Series(0.0, index=series.index)
    return numeric.fillna(median)


def feature_quality_report(X, y, train_mask):
    y_train = y.loc[train_mask]
    rows = []
    for column in X.columns:
        train_col = X.loc[train_mask, column]
        missing_rate = float(train_col.isna().mean())
        nunique = int(train_col.nunique(dropna=True))
        top_share = float(train_col.value_counts(dropna=False, normalize=True).iloc[0])
        is_numeric = pd.api.types.is_numeric_dtype(train_col)

        if is_numeric:
            score = numeric_univariate_score(train_col)
        else:
            score = categorical_univariate_score(train_col, y_train)

        univariate_gini = safe_abs_gini(y_train, score)

        rejection_reasons = []
        if missing_rate > MAX_MISSING_RATE:
            rejection_reasons.append("too_many_missing")
        if nunique <= 1:
            rejection_reasons.append("constant_or_empty")
        if top_share > MAX_DOMINANT_SHARE:
            rejection_reasons.append("dominant_single_value")
        if not is_numeric and nunique > MAX_CATEGORY_LEVELS:
            rejection_reasons.append("too_many_category_levels")
        if univariate_gini < MIN_UNIVARIATE_GINI:
            rejection_reasons.append("weak_univariate_gini")

        rows.append(
            {
                "feature": column,
                "dtype": str(train_col.dtype),
                "is_numeric": bool(is_numeric),
                "missing_rate_train": missing_rate,
                "nunique_train": nunique,
                "top_value_share_train": top_share,
                "univariate_abs_gini_train": univariate_gini,
                "selected": not rejection_reasons,
                "rejection_reason": ";".join(rejection_reasons),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["selected", "univariate_abs_gini_train"], ascending=[False, False]
    )


def selected_features_from_report(feature_report):
    return feature_report.loc[feature_report["selected"], "feature"].tolist()


def build_model(X):
    numeric_columns = X.select_dtypes(include="number").columns.tolist()
    categorical_columns = [
        column for column in X.columns if column not in numeric_columns
    ]

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=0.01),
            ),
        ]
    )

    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_columns),
            ("cat", categorical_pipe, categorical_columns),
        ]
    )

    model = LogisticRegression(
        penalty="l1",
        solver="liblinear",
        C=0.05,
        max_iter=2000,
        random_state=RANDOM_STATE,
    )

    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def metrics_row(split_name, y_true, probability):
    auc = roc_auc_score(y_true, probability)
    return {
        "model_id": MODEL_ID,
        "split": split_name,
        "n_obs": int(len(y_true)),
        "bad_rate": float(np.mean(y_true)),
        "predicted_pd_mean": float(np.mean(probability)),
        "auc": float(auc),
        "gini": float(2.0 * auc - 1.0),
        "brier": float(brier_score_loss(y_true, probability)),
        "log_loss": float(log_loss(y_true, probability)),
    }


def calibration_table(y_true, probability, n_bins=10):
    scored = pd.DataFrame({"target": y_true, PD_COLUMN: probability})
    scored["bucket"] = pd.qcut(scored[PD_COLUMN], q=n_bins, duplicates="drop")

    table = (
        scored.groupby("bucket", observed=True)
        .agg(
            n_obs=("target", "size"),
            min_pd=(PD_COLUMN, "min"),
            max_pd=(PD_COLUMN, "max"),
            mean_pd=(PD_COLUMN, "mean"),
            observed_default_rate=("target", "mean"),
            bads=("target", "sum"),
        )
        .reset_index(drop=True)
    )
    table["absolute_calibration_error"] = (
        table["mean_pd"] - table["observed_default_rate"]
    ).abs()
    return table


def format_number(value):
    if pd.isna(value):
        return "Missing"
    if abs(value) >= 100:
        return f"{value:.0f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def numeric_condition(feature, left, right):
    if left == -np.inf:
        return f"{feature} < {format_number(right)}"
    if right == np.inf:
        return f"{format_number(left)} <= {feature}"
    return f"{format_number(left)} <= {feature} < {format_number(right)}"


def fit_numeric_bins(feature, series, y_train):
    numeric = pd.to_numeric(series, errors="coerce")
    non_missing = numeric.dropna()
    thresholds = []

    if non_missing.nunique() > 1 and y_train.loc[non_missing.index].nunique() > 1:
        min_leaf = max(
            20, int(np.ceil(non_missing.shape[0] * ANALYSIS_MIN_BIN_SHARE))
        )
        tree = DecisionTreeClassifier(
            max_leaf_nodes=ANALYSIS_MAX_BINS,
            min_samples_leaf=min_leaf,
            random_state=RANDOM_STATE,
        )
        tree.fit(non_missing.to_frame(), y_train.loc[non_missing.index])
        thresholds = sorted(
            {
                float(threshold)
                for threshold in tree.tree_.threshold
                if threshold != -2 and np.isfinite(threshold)
            }
        )

    if not thresholds and non_missing.nunique() > 1:
        n_bins = min(ANALYSIS_MAX_BINS, int(non_missing.nunique()))
        quantiles = np.linspace(0, 1, n_bins + 1)[1:-1]
        thresholds = sorted(
            {
                float(value)
                for value in np.nanquantile(non_missing, quantiles)
                if np.isfinite(value)
            }
        )

    edges = [-np.inf] + thresholds + [np.inf]
    specs = []
    for idx, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
        specs.append(
            {
                "raw_group": f"bin_{idx}",
                "left": left,
                "right": right,
                "condition": numeric_condition(feature, left, right),
            }
        )
    if numeric.isna().any():
        specs.append(
            {
                "raw_group": "missing",
                "left": np.nan,
                "right": np.nan,
                "condition": f"{feature} = Missing",
            }
        )
    return specs


def assign_numeric_bins(series, specs):
    numeric = pd.to_numeric(series, errors="coerce")
    groups = pd.Series(index=series.index, dtype="object")
    interval_specs = [spec for spec in specs if spec["raw_group"] != "missing"]
    for spec in interval_specs:
        mask = numeric.ge(spec["left"]) & numeric.lt(spec["right"])
        groups.loc[mask] = spec["raw_group"]
    missing_specs = [spec for spec in specs if spec["raw_group"] == "missing"]
    fallback = interval_specs[0]["raw_group"] if interval_specs else "missing"
    groups.loc[numeric.isna()] = missing_specs[0]["raw_group"] if missing_specs else fallback
    return groups.fillna(fallback)


def normalize_category(series):
    values = series.astype("object").where(series.notna(), "__MISSING__")
    return values.astype(str)


def display_category(value):
    return "Missing" if value == "__MISSING__" else value


def format_category_condition(values):
    display_values = [display_category(value) for value in values]
    if len(display_values) > 12:
        display_values = display_values[:12] + [f"... +{len(values) - 12} more"]
    return ", ".join(display_values)


def fit_categorical_bins(series, y_train):
    values = normalize_category(series)
    counts = values.value_counts(dropna=False)
    shares = counts / counts.sum()

    rare = set(shares[shares < ANALYSIS_MIN_BIN_SHARE].index)
    if counts.shape[0] > 20:
        rare.update(counts.iloc[20:].index)

    frequent = [value for value in counts.index if value not in rare]
    bad_rates = (
        pd.DataFrame({"value": values, "target": y_train})
        .groupby("value")["target"]
        .mean()
    )
    frequent = sorted(
        frequent, key=lambda value: bad_rates.get(value, 0.0), reverse=True
    )
    n_groups = min(ANALYSIS_MAX_BINS, max(1, len(frequent)))

    specs = []
    if frequent:
        for idx, chunk in enumerate(np.array_split(frequent, n_groups)):
            chunk_values = [str(value) for value in chunk if len(chunk)]
            if not chunk_values:
                continue
            specs.append(
                {
                    "raw_group": f"cat_{idx}",
                    "values": set(chunk_values),
                    "condition": format_category_condition(chunk_values),
                    "is_other": False,
                }
            )

    if rare:
        specs.append(
            {
                "raw_group": "other",
                "values": set(str(value) for value in rare),
                "condition": "<OTHERS>",
                "is_other": True,
            }
        )

    if not specs:
        all_values = [str(value) for value in counts.index]
        specs.append(
            {
                "raw_group": "cat_0",
                "values": set(all_values),
                "condition": format_category_condition(all_values),
                "is_other": False,
            }
        )
    return specs


def assign_categorical_bins(series, specs):
    values = normalize_category(series)
    value_to_group = {}
    other_group = None
    for spec in specs:
        if spec.get("is_other"):
            other_group = spec["raw_group"]
        for value in spec["values"]:
            value_to_group[value] = spec["raw_group"]
    fallback = other_group or specs[0]["raw_group"]
    return values.map(value_to_group).fillna(fallback)


def make_feature_bins(feature, series, y_train):
    is_numeric = pd.api.types.is_numeric_dtype(series)
    if is_numeric:
        specs = fit_numeric_bins(feature, series, y_train)
    else:
        specs = fit_categorical_bins(series, y_train)
    return is_numeric, specs


def assign_feature_bins(series, specs, is_numeric):
    if is_numeric:
        return assign_numeric_bins(series, specs)
    return assign_categorical_bins(series, specs)


def summarize_groups(groups, y):
    frame = pd.DataFrame({"raw_group": groups, "target": y})
    summary = (
        frame.groupby("raw_group", dropna=False)["target"]
        .agg(Bad="sum", All="count")
        .reset_index()
    )
    summary["Good"] = summary["All"] - summary["Bad"]
    summary["BR"] = summary["Bad"] / summary["All"]
    summary["Logit"] = np.log((summary["Bad"] + EPSILON) / (summary["Good"] + EPSILON))
    return summary


def build_feature_analysis(feature, series, y, sample, masks):
    train_mask = masks["train"]
    test_mask = masks["test"]
    y_train = y.loc[train_mask]
    y_test = y.loc[test_mask]
    is_numeric, specs = make_feature_bins(feature, series.loc[train_mask], y_train)
    condition_map = {spec["raw_group"]: spec["condition"] for spec in specs}

    train_raw_groups = assign_feature_bins(series.loc[train_mask], specs, is_numeric)
    train_summary = summarize_groups(train_raw_groups, y_train)
    train_summary["Variable"] = feature
    train_summary["Condition"] = train_summary["raw_group"].map(condition_map)
    train_summary["Share"] = train_summary["All"] / train_summary["All"].sum()

    train_bad_total = max(float(train_summary["Bad"].sum()), EPSILON)
    train_good_total = max(float(train_summary["Good"].sum()), EPSILON)
    train_summary["Bad share"] = train_summary["Bad"] / train_bad_total
    train_summary["Good share"] = train_summary["Good"] / train_good_total
    train_summary["Infomration Value"] = (
        (train_summary["Good share"] - train_summary["Bad share"])
        * np.log(
            (train_summary["Good share"] + EPSILON)
            / (train_summary["Bad share"] + EPSILON)
        )
    )
    train_summary = train_summary.sort_values("BR", ascending=False).reset_index(
        drop=True
    )
    train_summary["GRP"] = train_summary.index
    train_summary["Type"] = "INT" if is_numeric else "NOM"
    group_map = dict(zip(train_summary["raw_group"], train_summary["GRP"]))

    test_raw_groups = assign_feature_bins(series.loc[test_mask], specs, is_numeric)
    test_groups = test_raw_groups.map(group_map).fillna(0).astype(int)
    test_summary = (
        pd.DataFrame({"GRP": test_groups, "target": y_test})
        .groupby("GRP")["target"]
        .agg(Bad_test="sum", All_test="count")
        .reindex(train_summary["GRP"], fill_value=0)
        .reset_index()
    )
    test_bad_total = max(float(test_summary["Bad_test"].sum()), EPSILON)
    test_summary["Share test"] = test_summary["All_test"] / max(
        float(test_summary["All_test"].sum()), EPSILON
    )
    test_summary["Bad share test"] = test_summary["Bad_test"] / test_bad_total

    big = train_summary.merge(test_summary, on="GRP", how="left")
    big["Population Stability Index"] = (
        (big["Share"] - big["Share test"])
        * np.log((big["Share"] + EPSILON) / (big["Share test"] + EPSILON))
    )
    big["Population Stability Index for bads"] = (
        (big["Bad share"] - big["Bad share test"])
        * np.log((big["Bad share"] + EPSILON) / (big["Bad share test"] + EPSILON))
    )

    logit_by_group = big.set_index("GRP")["Logit"]
    train_groups = train_raw_groups.map(group_map).fillna(0).astype(int)
    train_scores = train_groups.map(logit_by_group)
    test_scores = test_groups.map(logit_by_group)

    gini_train = safe_abs_gini(y_train, train_scores)
    gini_test = safe_abs_gini(y_test, test_scores)
    relative_gini = (
        abs(gini_train - gini_test) / gini_train if gini_train > 0 else 0.0
    )

    train_series = series.loc[train_mask]
    non_missing = train_series.dropna()
    mode = non_missing.mode().iloc[0] if not non_missing.empty else np.nan
    mode_share = (
        float((non_missing == mode).mean()) if not non_missing.empty else np.nan
    )

    gini_row = {
        "Variable": feature,
        "Gini train": gini_train,
        "Gini test": gini_test,
        "R. Gini": relative_gini,
        "Infomration Value": float(big["Infomration Value"].sum()),
        "Population Stability Index": float(big["Population Stability Index"].sum()),
        "Population Stability Index for bads": float(
            big["Population Stability Index for bads"].sum()
        ),
        "Missing percent": float(train_series.isna().mean()),
        "Number of distinct": int(train_series.nunique(dropna=True)),
        "Mode": mode,
        "P. mode": mode_share,
        "Type": "INT" if is_numeric else "NOM",
    }

    all_raw_groups = assign_feature_bins(series, specs, is_numeric)
    all_groups = all_raw_groups.map(group_map).fillna(0).astype(int)
    years = sorted(sample[PERIOD_COLUMN].astype(str).str[:4].unique())
    group_ids = big["GRP"].tolist()
    time_frame = pd.DataFrame(
        {
            "GRP": all_groups,
            "Time": sample[PERIOD_COLUMN].astype(str).str[:4],
            "target": y,
        }
    )
    yearly_totals = time_frame.groupby("Time")["target"].count().rename("Year_All")
    time_summary = (
        time_frame.groupby(["GRP", "Time"])["target"]
        .agg(Bad="sum", All="count")
        .reindex(
            pd.MultiIndex.from_product([group_ids, years], names=["GRP", "Time"]),
            fill_value=0,
        )
        .reset_index()
    )
    time_summary = time_summary.merge(yearly_totals, on="Time", how="left")
    time_summary["Good"] = time_summary["All"] - time_summary["Bad"]
    time_summary["BR"] = np.where(
        time_summary["All"] > 0, time_summary["Bad"] / time_summary["All"], np.nan
    )
    time_summary["Share"] = time_summary["All"] / time_summary["Year_All"]
    time_summary = time_summary[
        ["GRP", "Time", "Bad", "All", "Good", "BR", "Share"]
    ]

    detail = big[
        [
            "GRP",
            "Condition",
            "BR",
            "Share",
            "All",
            "Bad",
            "Good",
            "Logit",
        ]
    ].copy()
    big = big[
        [
            "Variable",
            "Condition",
            "BR",
            "Share",
            "All",
            "Bad",
            "Good",
            "Logit",
            "GRP",
            "Type",
            "Bad share",
            "Good share",
            "Infomration Value",
            "Share test",
            "Bad share test",
            "Population Stability Index",
            "Population Stability Index for bads",
        ]
    ]
    return big, gini_row, detail, time_summary


def safe_sheet_name(name, used_names):
    invalid = set("[]:*?/\\")
    clean = "".join("_" if char in invalid else char for char in str(name))
    clean = clean[:31] or "Sheet"
    candidate = clean
    counter = 1
    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = clean[: 31 - len(suffix)] + suffix
        counter += 1
    used_names.add(candidate)
    return candidate


def set_excel_columns(worksheet, dataframe, workbook, start_col=0):
    percent_format = workbook.add_format({"num_format": "0.0%"})
    numeric_format = workbook.add_format({"num_format": "#,##0.000"})
    integer_format = workbook.add_format({"num_format": "#,##0"})
    percent_tokens = ("BR", "Share", "Gini", "PSI", "percent", "P. mode")
    integer_columns = {"All", "Bad", "Good", "GRP", "Number of distinct"}

    for idx, column in enumerate(dataframe.columns):
        width = max(len(str(column)) + 2, 10)
        if not dataframe.empty:
            width = max(
                width,
                min(45, int(dataframe[column].astype(str).str.len().quantile(0.95)) + 2),
            )
        cell_format = None
        if any(token in str(column) for token in percent_tokens):
            cell_format = percent_format
        elif column in integer_columns or str(column).endswith("_test"):
            cell_format = integer_format
        elif pd.api.types.is_numeric_dtype(dataframe[column]):
            cell_format = numeric_format
        worksheet.set_column(start_col + idx, start_col + idx, width, cell_format)


def write_dataframe_sheet(writer, sheet_name, dataframe):
    dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
    for col_idx, column in enumerate(dataframe.columns):
        worksheet.write(0, col_idx, column, header_format)
    if dataframe.shape[0] > 0 and dataframe.shape[1] > 0:
        worksheet.autofilter(0, 0, dataframe.shape[0], dataframe.shape[1] - 1)
    worksheet.freeze_panes(1, 0)
    set_excel_columns(worksheet, dataframe, workbook)


def write_single_sheet_workbook(path, dataframe):
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        write_dataframe_sheet(writer, "Sheet1", dataframe)


def add_variable_charts(workbook, worksheet, sheet_name, detail_rows, time_rows):
    if detail_rows == 0 or time_rows == 0:
        return
    first_data_row = 4
    groups = detail_rows
    years_per_group = int(time_rows / groups) if groups else 0
    if years_per_group == 0:
        return

    for metric_name, column_letter, anchor_offset in [
        ("BR", "N", 6),
        ("Share", "O", 22),
    ]:
        chart = workbook.add_chart({"type": "line"})
        chart.set_title({"name": metric_name})
        chart.set_x_axis({"name": "Time", "num_font": {"rotation": 45}})
        chart.set_legend({"position": "bottom"})
        for idx in range(groups):
            start = first_data_row + idx * years_per_group
            end = start + years_per_group - 1
            chart.add_series(
                {
                    "name": f"='{sheet_name}'!$I${start}",
                    "categories": f"='{sheet_name}'!$J${first_data_row}:$J${first_data_row + years_per_group - 1}",
                    "values": f"='{sheet_name}'!${column_letter}${start}:${column_letter}${end}",
                }
            )
        worksheet.insert_chart(f"A{detail_rows + anchor_offset}", chart)


def write_variable_report(path, gini_vars, variable_details):
    report_vars = gini_vars.head(MAX_VARIABLE_REPORT_SHEETS)["Variable"].tolist()
    used_sheet_names = set()
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        gini_vars.to_excel(writer, sheet_name="Variable", startrow=1, index=False)
        workbook = writer.book
        worksheet = writer.sheets["Variable"]
        header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
        for col_idx, column in enumerate(gini_vars.columns):
            worksheet.write(1, col_idx, column, header_format)
        worksheet.freeze_panes(2, 0)
        worksheet.autofilter(1, 0, gini_vars.shape[0] + 1, gini_vars.shape[1] - 1)
        set_excel_columns(worksheet, gini_vars, workbook)
        used_sheet_names.add("Variable")

        title_format = workbook.add_format({"bold": True, "size": 18})
        header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
        for feature in report_vars:
            detail, time_summary = variable_details[feature]
            sheet_name = safe_sheet_name(feature, used_sheet_names)
            detail.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
            time_summary.to_excel(
                writer, sheet_name=sheet_name, startrow=2, startcol=8, index=False
            )
            worksheet = writer.sheets[sheet_name]
            worksheet.write(0, 0, f"Variable: {feature}", title_format)
            for col_idx, column in enumerate(detail.columns):
                worksheet.write(2, col_idx, column, header_format)
            for col_idx, column in enumerate(time_summary.columns):
                worksheet.write(2, 8 + col_idx, column, header_format)
            worksheet.freeze_panes(3, 0)
            set_excel_columns(worksheet, detail, workbook)
            set_excel_columns(worksheet, time_summary, workbook, start_col=8)
            add_variable_charts(
                workbook,
                worksheet,
                sheet_name,
                detail.shape[0],
                time_summary.shape[0],
            )


def write_excel_analysis_reports(X, y, sample, masks):
    big_frames = []
    gini_rows = []
    variable_details = {}
    for feature in X.columns:
        big, gini_row, detail, time_summary = build_feature_analysis(
            feature, X[feature], y, sample, masks
        )
        big_frames.append(big)
        gini_rows.append(gini_row)
        variable_details[feature] = (detail, time_summary)

    big_scorecard = pd.concat(big_frames, ignore_index=True)
    gini_vars = pd.DataFrame(gini_rows).sort_values(
        "Gini train", ascending=False
    ).reset_index(drop=True)

    write_single_sheet_workbook(OUTPUT_DIR / "Big_scorecard.xlsx", big_scorecard)
    write_single_sheet_workbook(OUTPUT_DIR / "Gini_vars.xlsx", gini_vars)
    write_variable_report(OUTPUT_DIR / "Variable_report.xlsx", gini_vars, variable_details)
    return big_scorecard, gini_vars, variable_details


def transformed_feature_to_raw(name, numeric_columns, categorical_columns):
    if name.startswith("num__missingindicator_"):
        return name.replace("num__missingindicator_", "", 1)
    if name.startswith("num__"):
        return name.replace("num__", "", 1)
    if name.startswith("cat__"):
        payload = name.replace("cat__", "", 1)
        for column in sorted(categorical_columns, key=len, reverse=True):
            if payload == column or payload.startswith(f"{column}_"):
                return column
    return name


def final_raw_feature_importance(fitted_model):
    importance = feature_importance(fitted_model)
    preprocess = fitted_model.named_steps["preprocess"]
    numeric_columns = list(preprocess.transformers_[0][2])
    categorical_columns = list(preprocess.transformers_[1][2])
    importance["raw_feature"] = importance["feature"].apply(
        lambda name: transformed_feature_to_raw(
            name, numeric_columns, categorical_columns
        )
    )
    raw_importance = (
        importance.groupby("raw_feature", as_index=False)
        .agg(
            coefficient_abs_sum=("importance", "sum"),
            max_abs_coefficient=("importance", "max"),
            nonzero_terms=("importance", lambda value: int((value > 1e-12).sum())),
        )
        .rename(columns={"raw_feature": "Variable"})
        .sort_values("coefficient_abs_sum", ascending=False)
        .reset_index(drop=True)
    )
    total = raw_importance["coefficient_abs_sum"].sum()
    raw_importance["Importance"] = (
        raw_importance["coefficient_abs_sum"] / total if total else 0.0
    )
    return importance, raw_importance


def gini_over_time(sample, y, probability):
    frame = pd.DataFrame(
        {
            "Time": sample[PERIOD_COLUMN].astype(str).str[:4],
            "target": y,
            "probability": probability,
        }
    )
    rows = []
    for period, group in frame.groupby("Time"):
        if group["target"].nunique() < 2:
            gini = np.nan
        else:
            gini = 2.0 * roc_auc_score(group["target"], group["probability"]) - 1.0
        rows.append({"Time": period, "Gini": gini, "n_obs": int(group.shape[0])})
    return pd.DataFrame(rows)


def write_model_variable_sheets(writer, workbook, variables, variable_details):
    used_sheet_names = set(writer.sheets.keys())
    title_format = workbook.add_format({"bold": True, "size": 18})
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
    for feature in variables[:MAX_VARIABLE_REPORT_SHEETS]:
        if feature not in variable_details:
            continue
        detail, time_summary = variable_details[feature]
        sheet_name = safe_sheet_name(feature, used_sheet_names)
        detail.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
        time_summary.to_excel(
            writer, sheet_name=sheet_name, startrow=2, startcol=8, index=False
        )
        worksheet = writer.sheets[sheet_name]
        worksheet.write(0, 0, f"Variable: {feature}", title_format)
        for col_idx, column in enumerate(detail.columns):
            worksheet.write(2, col_idx, column, header_format)
        for col_idx, column in enumerate(time_summary.columns):
            worksheet.write(2, 8 + col_idx, column, header_format)
        worksheet.freeze_panes(3, 0)
        set_excel_columns(worksheet, detail, workbook)
        set_excel_columns(worksheet, time_summary, workbook, start_col=8)
        add_variable_charts(
            workbook,
            worksheet,
            sheet_name,
            detail.shape[0],
            time_summary.shape[0],
        )


def write_model_report(
    sample,
    y,
    masks,
    probabilities,
    fitted_model,
    metrics,
    big_scorecard,
    gini_vars,
    variable_details,
):
    full_probability = pd.Series(index=sample.index, dtype=float)
    for split_name, mask in masks.items():
        full_probability.loc[mask] = probabilities[split_name]

    transformed_importance, raw_importance = final_raw_feature_importance(fitted_model)
    final_variables = raw_importance.loc[
        raw_importance["coefficient_abs_sum"] > 1e-12, "Variable"
    ].tolist()
    scorecard = big_scorecard[big_scorecard["Variable"].isin(final_variables)].copy()
    model_gini_vars = gini_vars[gini_vars["Variable"].isin(final_variables)].copy()
    metrics_by_split = {row["split"]: row for row in metrics}
    test_calibration = calibration_table(y.loc[masks["test"]], probabilities["test"])

    main_measures = pd.DataFrame(
        [
            ("Model ID", MODEL_ID),
            ("Target", TARGET),
            ("Application product", APPLICATION_PRODUCT),
            ("Cross response", CROSS_RESPONSE),
            ("Rows", int(sample.shape[0])),
            ("Event rate", float(y.mean())),
            ("Gini train", metrics_by_split["train"]["gini"]),
            ("Gini validation", metrics_by_split["validation"]["gini"]),
            ("Gini test", metrics_by_split["test"]["gini"]),
            ("AUC train", metrics_by_split["train"]["auc"]),
            ("AUC validation", metrics_by_split["validation"]["auc"]),
            ("AUC test", metrics_by_split["test"]["auc"]),
            ("Test bad rate", metrics_by_split["test"]["bad_rate"]),
            ("Test mean PD", metrics_by_split["test"]["predicted_pd_mean"]),
            ("Selected features", int(gini_vars.shape[0])),
            ("Final non-zero raw features", len(final_variables)),
        ],
        columns=["Measure", "Value"],
    )

    with pd.ExcelWriter(OUTPUT_DIR / "Model_report.xlsx", engine="xlsxwriter") as writer:
        write_dataframe_sheet(writer, "Main_measures", main_measures)
        write_dataframe_sheet(
            writer,
            "Effects",
            transformed_importance.loc[transformed_importance["importance"] > 1e-12],
        )
        write_dataframe_sheet(
            writer,
            "Gini_over_time",
            gini_over_time(sample, y, full_probability),
        )
        write_dataframe_sheet(writer, "Scorecard", scorecard)
        write_dataframe_sheet(writer, "Variable importance", raw_importance)
        write_dataframe_sheet(writer, "Calibration", test_calibration)
        write_dataframe_sheet(writer, "Variable", model_gini_vars)
        write_model_variable_sheets(
            writer, writer.book, final_variables, variable_details
        )


def segment_summary(frame):
    grouped = (
        frame.groupby("Segment")
        .agg(
            **{
                "Min score": (SCORE_COLUMN, "min"),
                "Max score": (SCORE_COLUMN, "max"),
                "All": (TARGET, "size"),
                "Bad": (TARGET, "sum"),
            }
        )
        .reset_index()
    )
    grouped["BR"] = grouped["Bad"] / grouped["All"]
    grouped["Share"] = grouped["All"] / grouped["All"].sum()
    return grouped[["Segment", "Min score", "Max score", "BR", "Share", "All", "Bad"]]


def segment_time_summary(frame):
    years = sorted(frame["Time"].unique())
    segments = sorted(frame["Segment"].unique())
    yearly_totals = frame.groupby("Time")[TARGET].count().rename("Year_All")
    grouped = (
        frame.groupby(["Segment", "Time"])[TARGET]
        .agg(Bad="sum", All="count")
        .reindex(
            pd.MultiIndex.from_product([segments, years], names=["Segment", "Time"]),
            fill_value=0,
        )
        .reset_index()
        .merge(yearly_totals, on="Time", how="left")
    )
    grouped["BR"] = np.where(grouped["All"] > 0, grouped["Bad"] / grouped["All"], np.nan)
    grouped["Share"] = grouped["All"] / grouped["Year_All"]
    return grouped[["Segment", "Time", "BR", "Share", "All", "Bad"]]


def segment_balance_summary(frame):
    grouped = (
        frame.groupby("Segment")
        .agg(
            **{
                "Min score": (SCORE_COLUMN, "min"),
                "Max score": (SCORE_COLUMN, "max"),
                "outstanding": ("outstanding", "sum"),
                "outstanding_bad": ("outstanding_bad", "sum"),
            }
        )
        .reset_index()
    )
    grouped["BRBal"] = grouped["outstanding_bad"] / grouped["outstanding"]
    grouped["Balance share"] = grouped["outstanding"] / grouped["outstanding"].sum()
    return grouped[
        [
            "Segment",
            "Min score",
            "Max score",
            "BRBal",
            "Balance share",
            "outstanding",
            "outstanding_bad",
        ]
    ]


def segment_balance_time_summary(frame):
    years = sorted(frame["Time"].unique())
    segments = sorted(frame["Segment"].unique())
    yearly_totals = frame.groupby("Time")["outstanding"].sum().rename("Year_Balance")
    grouped = (
        frame.groupby(["Segment", "Time"])
        .agg(outstanding=("outstanding", "sum"), outstanding_bad=("outstanding_bad", "sum"))
        .reindex(
            pd.MultiIndex.from_product([segments, years], names=["Segment", "Time"]),
            fill_value=0,
        )
        .reset_index()
        .merge(yearly_totals, on="Time", how="left")
    )
    grouped["BRBal"] = np.where(
        grouped["outstanding"] > 0,
        grouped["outstanding_bad"] / grouped["outstanding"],
        np.nan,
    )
    grouped["Balance share"] = grouped["outstanding"] / grouped["Year_Balance"]
    return grouped[
        ["Segment", "Time", "BRBal", "Balance share", "outstanding", "outstanding_bad"]
    ]


def write_segment_report_sheet(writer, sheet_name, left, right):
    left.to_excel(writer, sheet_name=sheet_name, startrow=2, index=False)
    right.to_excel(writer, sheet_name=sheet_name, startrow=2, startcol=8, index=False)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
    for col_idx, column in enumerate(left.columns):
        worksheet.write(2, col_idx, column, header_format)
    for col_idx, column in enumerate(right.columns):
        worksheet.write(2, 8 + col_idx, column, header_format)
    worksheet.freeze_panes(3, 0)
    set_excel_columns(worksheet, left, workbook)
    set_excel_columns(worksheet, right, workbook, start_col=8)

    if not right.empty:
        segments = left.shape[0]
        years_per_segment = int(right.shape[0] / segments) if segments else 0
        chart_column = "K"
        share_column = "L"
        if "BRBal" in right.columns:
            chart_column = "K"
            share_column = "L"
        for title, column, anchor in [
            ("Bad rate", chart_column, "A8"),
            ("Share", share_column, "A24"),
        ]:
            chart = workbook.add_chart({"type": "line"})
            chart.set_title({"name": title})
            chart.set_x_axis({"name": "Time", "num_font": {"rotation": 45}})
            chart.set_legend({"position": "bottom"})
            for idx in range(segments):
                start = 4 + idx * years_per_segment
                end = start + years_per_segment - 1
                chart.add_series(
                    {
                        "name": f"='{sheet_name}'!$I${start}",
                        "categories": f"='{sheet_name}'!$J$4:$J${3 + years_per_segment}",
                        "values": f"='{sheet_name}'!${column}${start}:${column}${end}",
                    }
                )
            worksheet.insert_chart(anchor, chart)


def write_segments_report(sample, y, masks, probabilities, scores, n_segments=3):
    full_probability = pd.Series(index=sample.index, dtype=float)
    full_score = pd.Series(index=sample.index, dtype=float)
    for split_name, mask in masks.items():
        full_probability.loc[mask] = probabilities[split_name]
        full_score.loc[mask] = scores[split_name]

    scored = sample[[TARGET, PERIOD_COLUMN]].copy()
    scored[PD_COLUMN] = full_probability
    scored[SCORE_COLUMN] = full_score
    scored["Time"] = scored[PERIOD_COLUMN].astype(str).str[:4]
    rank_segment = pd.qcut(
        scored[PD_COLUMN].rank(method="first"),
        q=n_segments,
        labels=False,
        duplicates="drop",
    ).astype(int)
    scored["Segment"] = (n_segments - 1) - rank_segment

    balance_column = (
        "cross_app_loan_amount"
        if "cross_app_loan_amount" in sample.columns
        else "app_loan_amount"
    )
    scored["outstanding"] = sample[balance_column].fillna(sample["app_loan_amount"])
    scored["outstanding_bad"] = scored["outstanding"] * y

    numbers = segment_summary(scored)
    numbers_time = segment_time_summary(scored)
    balances = segment_balance_summary(scored)
    balances_time = segment_balance_time_summary(scored)

    with pd.ExcelWriter(
        OUTPUT_DIR / f"Segments{n_segments}_report.xlsx", engine="xlsxwriter"
    ) as writer:
        write_segment_report_sheet(writer, "Numbers", numbers, numbers_time)
        write_segment_report_sheet(writer, "Balances", balances, balances_time)


def feature_importance(fitted_model):
    preprocess = fitted_model.named_steps["preprocess"]
    classifier = fitted_model.named_steps["model"]

    return (
        pd.DataFrame(
            {
                "feature": preprocess.get_feature_names_out(),
                "coefficient": classifier.coef_[0],
                "importance": np.abs(classifier.coef_[0]),
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def sas_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def sas_numeric_expression(feature, raw_features):
    if feature in ENGINEERED_RATIOS:
        numerator, denominator = ENGINEERED_RATIOS[feature]
        return (
            f"(case when missing({denominator}) or {denominator}=0 then . "
            f"else {numerator}/{denominator} end)"
        )
    if feature == "eng_missing_count":
        return "sum(" + ", ".join(f"missing({feature})" for feature in raw_features) + ")"
    return feature


def sas_standardized_numeric_term(feature, coefficient, median, mean, scale, raw_features):
    expression = sas_numeric_expression(feature, raw_features)
    return (
        f"{coefficient:.12f} * "
        f"((coalesce({expression}, {median:.12f}) - {mean:.12f}) / {scale:.12f})"
    )


def sas_missing_indicator_term(feature, coefficient, mean, scale):
    return (
        f"{coefficient:.12f} * "
        f"(((case when missing({feature}) then 1 else 0 end) - {mean:.12f}) / {scale:.12f})"
    )


def sas_category_equals(feature, category, mode):
    category_condition = f"{feature} = {sas_quote(category)}"
    if str(category) == str(mode):
        return f"({category_condition} or missing({feature}))"
    return f"({category_condition})"


def sas_category_in(feature, values, mode):
    clean_values = [str(value) for value in values if pd.notna(value)]
    conditions = []
    if clean_values:
        quoted = ", ".join(sas_quote(value) for value in clean_values)
        conditions.append(f"{feature} in ({quoted})")
    if str(mode) in clean_values:
        conditions.append(f"missing({feature})")
    return "(" + " or ".join(conditions) + ")" if conditions else "(0)"


def export_sas_scoring_code(fitted_model, raw_features):
    preprocess = fitted_model.named_steps["preprocess"]
    classifier = fitted_model.named_steps["model"]
    coefficients = pd.Series(
        classifier.coef_[0], index=preprocess.get_feature_names_out()
    )
    terms = []

    numeric_pipeline = preprocess.named_transformers_["num"]
    numeric_columns = list(preprocess.transformers_[0][2])
    numeric_imputer = numeric_pipeline.named_steps["imputer"]
    numeric_scaler = numeric_pipeline.named_steps["scaler"]
    numeric_output_names = numeric_imputer.get_feature_names_out(numeric_columns)
    numeric_medians = dict(zip(numeric_columns, numeric_imputer.statistics_))

    for idx, output_name in enumerate(numeric_output_names):
        full_name = f"num__{output_name}"
        coefficient = float(coefficients.get(full_name, 0.0))
        if abs(coefficient) < 1e-12:
            continue

        mean = float(numeric_scaler.mean_[idx])
        scale = float(numeric_scaler.scale_[idx])
        if output_name.startswith("missingindicator_"):
            feature = output_name.replace("missingindicator_", "", 1)
            term = sas_missing_indicator_term(feature, coefficient, mean, scale)
        else:
            feature = output_name
            median = float(numeric_medians[feature])
            term = sas_standardized_numeric_term(
                feature, coefficient, median, mean, scale, raw_features
            )
        terms.append({"feature": full_name, "coefficient": coefficient, "term": term})

    categorical_pipeline = preprocess.named_transformers_["cat"]
    categorical_columns = list(preprocess.transformers_[1][2])
    categorical_imputer = categorical_pipeline.named_steps["imputer"]
    encoder = categorical_pipeline.named_steps["onehot"]
    modes = dict(zip(categorical_columns, categorical_imputer.statistics_))

    for idx, feature in enumerate(categorical_columns):
        categories = [str(value) for value in encoder.categories_[idx]]
        infrequent = getattr(encoder, "infrequent_categories_", None)
        infrequent_values = []
        if infrequent is not None and infrequent[idx] is not None:
            infrequent_values = [str(value) for value in infrequent[idx]]

        frequent_categories = [
            category for category in categories if category not in set(infrequent_values)
        ]
        mode = str(modes[feature])

        for category in frequent_categories:
            full_name = f"cat__{feature}_{category}"
            coefficient = float(coefficients.get(full_name, 0.0))
            if abs(coefficient) < 1e-12:
                continue
            condition = sas_category_equals(feature, category, mode)
            terms.append(
                {
                    "feature": full_name,
                    "coefficient": coefficient,
                    "term": f"{coefficient:.12f} * (case when {condition} then 1 else 0 end)",
                }
            )

        if infrequent_values:
            full_name = f"cat__{feature}_infrequent_sklearn"
            coefficient = float(coefficients.get(full_name, 0.0))
            if abs(coefficient) >= 1e-12:
                condition = sas_category_in(feature, infrequent_values, mode)
                terms.append(
                    {
                        "feature": full_name,
                        "coefficient": coefficient,
                        "term": f"{coefficient:.12f} * (case when {condition} then 1 else 0 end)",
                    }
                )

    with open(SAS_PATH, "w", encoding="utf-8") as file:
        file.write("proc sql;\n")
        file.write("create table &zbior._score as\n")
        file.write("select indataset.*\n")
        file.write(", (\n")
        file.write(f"  {float(classifier.intercept_[0]):.12f}\n")
        for row in terms:
            file.write(f"  + {row['term']}\n")
        file.write(f") as {SCORE_COLUMN}\n")
        file.write(f", 1/(1+exp(-calculated {SCORE_COLUMN})) as {PD_COLUMN}\n")
        file.write("from &zbior as indataset;\n")
        file.write("quit;\n")

    pd.DataFrame(terms).to_csv(OUTPUT_DIR / "sas_scoring_terms.csv", index=False)


def make_predictions(sample, mask, probabilities, scores):
    predictions = sample.loc[
        mask, [ID_COLUMN, PERIOD_COLUMN, "product", "decision", TARGET]
    ].copy()
    predictions[SCORE_COLUMN] = scores
    predictions[PD_COLUMN] = probabilities
    return predictions


def main():
    sample = load_sample()
    raw_features = select_features(sample)
    X_all = add_features(sample[raw_features])
    y = sample[TARGET].astype(int)
    masks = split_by_time(sample)
    feature_report = feature_quality_report(X_all, y, masks["train"])
    selected_features = selected_features_from_report(feature_report)

    if not selected_features:
        raise ValueError("No features passed data-quality screening.")

    write_sample_audit(sample, raw_features, selected_features, feature_report)
    X = X_all[selected_features]
    big_scorecard, gini_vars, variable_details = write_excel_analysis_reports(
        X, y, sample, masks
    )

    model = build_model(X)
    model.fit(X.loc[masks["train"]], y.loc[masks["train"]])

    metrics = []
    probabilities = {}
    scores = {}

    for split_name, mask in masks.items():
        scores[split_name] = model.decision_function(X.loc[mask])
        probabilities[split_name] = model.predict_proba(X.loc[mask])[:, 1]
        metrics.append(metrics_row(split_name, y.loc[mask], probabilities[split_name]))

    pd.DataFrame(metrics).to_csv(OUTPUT_DIR / "metrics.csv", index=False)

    all_predictions = []
    for split_name, mask in masks.items():
        predictions = make_predictions(
            sample,
            mask,
            probabilities[split_name],
            scores[split_name],
        )
        predictions["split"] = split_name
        all_predictions.append(predictions)

    pd.concat(all_predictions, ignore_index=True).to_csv(
        OUTPUT_DIR / "predictions.csv", index=False
    )
    all_predictions[-1].to_csv(OUTPUT_DIR / "oot_test_predictions.csv", index=False)

    calibration_table(y.loc[masks["test"]], probabilities["test"]).to_csv(
        OUTPUT_DIR / "oot_test_calibration.csv", index=False
    )
    feature_importance(model).head(100).to_csv(
        OUTPUT_DIR / "top_feature_importance.csv", index=False
    )
    write_model_report(
        sample,
        y,
        masks,
        probabilities,
        model,
        metrics,
        big_scorecard,
        gini_vars,
        variable_details,
    )
    write_segments_report(sample, y, masks, probabilities, scores)
    export_sas_scoring_code(model, raw_features)

    test_metrics = metrics[-1]
    print("PD Css Cross model: L1 regularized logistic regression")
    print(f"Model ID: {MODEL_ID}")
    print(f"Target: {TARGET}")
    print(sample.attrs["sample_note"])
    print(f"Train rows: {masks['train'].sum()}")
    print(f"Validation rows: {masks['validation'].sum()}")
    print(f"OOT test rows: {masks['test'].sum()}")
    print(f"OOT test AUC: {test_metrics['auc']:.4f}")
    print(f"OOT test Gini: {test_metrics['gini']:.4f}")
    print(f"SAS scoring code: {SAS_PATH}")
    print(f"Outputs written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
