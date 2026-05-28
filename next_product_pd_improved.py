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

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DATA_PATH = Path("abt_app_PD_INS.xlsx")
OUTPUT_DIR = Path("outputs/pd_css_cross")

MODEL_ID = "PD_CSS_CROSS"
TARGET = "default_cross12"
ID_COLUMN = "aid"
PERIOD_COLUMN = "period"
PD_COLUMN = "PD_CSS_CROSS"
RAW_PD_COLUMN = "RAW_PD_CSS_CROSS"
SCORE_COLUMN = "SCORE_PD_CSS_CROSS"

PERIOD_FROM = "197501"
PERIOD_TO = "198712"
RANDOM_STATE = 1234
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15
MIN_HOLDOUT_ROWS = 250
MIN_CV_TRAIN_ROWS = 500
MIN_CV_VALIDATION_ROWS = 100

APPLICATION_PRODUCT = "ins"
FALLBACK_PRODUCT_WHEN_INS_ABSENT = "css"
DECISION = "A"

CANDIDATE_PREFIXES = ("app", "act", "agr", "ags")
MAX_MISSING_RATE = 0.98
MAX_CATEGORY_LEVELS = 50
MAX_DOMINANT_SHARE = 0.995
MIN_UNIVARIATE_GINI = 0.02
LEAKAGE_TOKENS = (
    "default",
    "cross_response",
    "cross_after",
    "cross_aid",
    "pd_",
    "score_",
)


def gini(y_true, probability):
    return 2.0 * roc_auc_score(y_true, probability) - 1.0


def safe_abs_gini(y_true, score):
    if pd.Series(score).nunique(dropna=True) < 2:
        return 0.0
    auc = roc_auc_score(y_true, score)
    return float(abs(2.0 * auc - 1.0))


def load_abt():
    if DATA_PATH.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(DATA_PATH)
    elif DATA_PATH.suffix.lower() == ".sas7bdat":
        df = pd.read_sas(DATA_PATH, encoding="LATIN2")
    else:
        raise ValueError(f"Unsupported ABT file type: {DATA_PATH.suffix}")

    object_columns = df.select_dtypes(include="object").columns
    for column in object_columns:
        df[column] = df[column].str.strip()
        df[column] = df[column].replace("", np.nan)
    return df


def load_sample():
    df = load_abt()
    df[PERIOD_COLUMN] = df[PERIOD_COLUMN].astype(str)

    base_mask = (
        df[PERIOD_COLUMN].between(PERIOD_FROM, PERIOD_TO)
        & df["decision"].eq(DECISION)
    )
    application_mask = base_mask & df["product"].eq(APPLICATION_PRODUCT)

    sample_note = (
        f"Primary PD Css Cross sample: decision={DECISION}, "
        f"product={APPLICATION_PRODUCT}, target={TARGET} not missing."
    )
    modelling_mask = application_mask

    if application_mask.sum() == 0:
        fallback_mask = base_mask & df["product"].eq(FALLBACK_PRODUCT_WHEN_INS_ABSENT)
        if fallback_mask.sum() == 0:
            raise ValueError(
                "No rows found for the intended instalment-loan application "
                f"population product={APPLICATION_PRODUCT!r}, and no fallback "
                f"rows found for product={FALLBACK_PRODUCT_WHEN_INS_ABSENT!r}."
            )

        sample_note = (
            "No instalment-loan application rows exist in this ABT. "
            f"Using product={FALLBACK_PRODUCT_WHEN_INS_ABSENT!r} rows with "
            f"non-missing {TARGET} as the available cross-sold cash-loan "
            "risk sample. Do not interpret missing target rows as non-defaults."
        )
        modelling_mask = fallback_mask

    target_mask = modelling_mask & df[TARGET].notna()
    if target_mask.sum() == 0:
        raise ValueError(
            f"No modelling rows have non-missing {TARGET}. "
            "Check target construction before fitting PD Css Cross."
        )

    sample = df.loc[target_mask].reset_index(drop=True)
    sample.attrs["sample_note"] = sample_note
    sample.attrs["sample_audit"] = {
        "model_id": MODEL_ID,
        "target": TARGET,
        "period_from": PERIOD_FROM,
        "period_to": PERIOD_TO,
        "decision": DECISION,
        "intended_application_product": APPLICATION_PRODUCT,
        "actual_product_values": ", ".join(sorted(map(str, sample["product"].unique()))),
        "base_rows": int(base_mask.sum()),
        "intended_product_rows": int(application_mask.sum()),
        "fallback_product_rows": int(
            (base_mask & df["product"].eq(FALLBACK_PRODUCT_WHEN_INS_ABSENT)).sum()
        ),
        "target_non_missing_rows": int(target_mask.sum()),
        "target_missing_rows_in_product_sample": int(
            (modelling_mask & df[TARGET].isna()).sum()
        ),
        "target_not_missing_share_in_product_sample": float(
            df.loc[modelling_mask, TARGET].notna().mean()
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

    ratios = {
        "eng_app_loan_to_income": ("app_loan_amount", "app_income"),
        "eng_app_installment_to_income": ("app_installment", "app_income"),
        "eng_app_spending_to_income": ("app_spendings", "app_income"),
        "eng_act_loaninc_to_income": ("act_loaninc", "app_income"),
        "eng_act_cc_to_income": ("act_cc", "app_income"),
    }

    for new_column, (numerator, denominator) in ratios.items():
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


def time_series_cross_validation(sample, X_all, y):
    years = sorted(sample[PERIOD_COLUMN].str[:4].unique())
    rows = []

    for validation_year in years:
        train_mask = sample[PERIOD_COLUMN].str[:4] < validation_year
        validation_mask = sample[PERIOD_COLUMN].str[:4] == validation_year

        if train_mask.sum() < MIN_CV_TRAIN_ROWS:
            continue
        if validation_mask.sum() < MIN_CV_VALIDATION_ROWS:
            continue
        if y.loc[train_mask].nunique() < 2 or y.loc[validation_mask].nunique() < 2:
            continue

        fold_feature_report = feature_quality_report(X_all, y, train_mask)
        fold_features = selected_features_from_report(fold_feature_report)
        if not fold_features:
            continue

        fold_model = build_model(X_all[fold_features])
        fold_model.fit(X_all.loc[train_mask, fold_features], y.loc[train_mask])
        probability = fold_model.predict_proba(
            X_all.loc[validation_mask, fold_features]
        )[:, 1]
        auc = roc_auc_score(y.loc[validation_mask], probability)

        rows.append(
            {
                "validation_year": validation_year,
                "train_period_min": sample.loc[train_mask, PERIOD_COLUMN].min(),
                "train_period_max": sample.loc[train_mask, PERIOD_COLUMN].max(),
                "validation_period_min": sample.loc[
                    validation_mask, PERIOD_COLUMN
                ].min(),
                "validation_period_max": sample.loc[
                    validation_mask, PERIOD_COLUMN
                ].max(),
                "train_rows": int(train_mask.sum()),
                "validation_rows": int(validation_mask.sum()),
                "train_bad_rate": float(y.loc[train_mask].mean()),
                "validation_bad_rate": float(y.loc[validation_mask].mean()),
                "n_features": int(len(fold_features)),
                "auc": float(auc),
                "gini": float(2.0 * auc - 1.0),
                "predicted_pd_mean": float(np.mean(probability)),
            }
        )

    cv = pd.DataFrame(rows)
    if cv.empty:
        return cv

    summary = pd.DataFrame(
        [
            {
                "n_folds": int(cv.shape[0]),
                "mean_gini": float(cv["gini"].mean()),
                "std_gini": float(cv["gini"].std(ddof=0)),
                "min_gini": float(cv["gini"].min()),
                "max_gini": float(cv["gini"].max()),
                "mean_auc": float(cv["auc"].mean()),
                "mean_validation_bad_rate": float(cv["validation_bad_rate"].mean()),
                "mean_predicted_pd": float(cv["predicted_pd_mean"].mean()),
            }
        ]
    )
    cv.to_csv(OUTPUT_DIR / "time_series_cv.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "time_series_cv_summary.csv", index=False)
    return cv


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
        class_weight="balanced",
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


def fit_calibrator(validation_scores, y_validation):
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    calibrator.fit(validation_scores.reshape(-1, 1), y_validation)
    return calibrator


def calibrated_probability(calibrator, scores):
    return calibrator.predict_proba(scores.reshape(-1, 1))[:, 1]


def make_predictions(sample, mask, raw_probabilities, probabilities, scores):
    predictions = sample.loc[
        mask, [ID_COLUMN, PERIOD_COLUMN, "product", "decision", TARGET]
    ].copy()
    predictions[SCORE_COLUMN] = scores
    predictions[RAW_PD_COLUMN] = raw_probabilities
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
    cv = time_series_cross_validation(sample, X_all, y)
    X = X_all[selected_features]

    model = build_model(X)
    model.fit(X.loc[masks["train"]], y.loc[masks["train"]])

    metrics = []
    raw_probabilities = {}
    probabilities = {}
    scores = {}

    validation_scores = model.decision_function(X.loc[masks["validation"]])
    calibrator = fit_calibrator(validation_scores, y.loc[masks["validation"]])

    for split_name, mask in masks.items():
        scores[split_name] = model.decision_function(X.loc[mask])
        raw_probabilities[split_name] = model.predict_proba(X.loc[mask])[:, 1]
        probabilities[split_name] = calibrated_probability(
            calibrator, scores[split_name]
        )
        metrics.append(metrics_row(split_name, y.loc[mask], probabilities[split_name]))

    pd.DataFrame(metrics).to_csv(OUTPUT_DIR / "metrics.csv", index=False)

    all_predictions = []
    for split_name, mask in masks.items():
        predictions = make_predictions(
            sample,
            mask,
            raw_probabilities[split_name],
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
    joblib.dump(model, OUTPUT_DIR / "pd_css_cross_model.joblib")
    joblib.dump(calibrator, OUTPUT_DIR / "pd_css_cross_calibrator.joblib")

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
    if not cv.empty:
        print(f"Time-series CV folds: {cv.shape[0]}")
        print(f"Time-series CV mean Gini: {cv['gini'].mean():.4f}")
        print(f"Time-series CV Gini std: {cv['gini'].std(ddof=0):.4f}")
    print(f"Outputs written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
