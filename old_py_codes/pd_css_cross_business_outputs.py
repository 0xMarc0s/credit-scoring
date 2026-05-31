"""Business outputs for the PD Css Cross model."""

from pathlib import Path

import numpy as np
import pandas as pd

import pd_css_cross as model_code


OUTPUT_DIR = Path("outputs/pd_css_cross")
BUSINESS_REPORT_PATH = OUTPUT_DIR / "Business_product_drivers.xlsx"


def business_group(variable):
    name = str(variable).lower()
    if name == "product":
        return "Current application product"
    if name.startswith("app_char"):
        return "Application profile"
    if name.startswith("app_") or name.startswith("eng_app"):
        return "Application affordability"
    if "cins" in name:
        return "Current instalment-loan behaviour"
    if "ccss" in name:
        return "Current cash-loan behaviour"
    if name.startswith("act_call"):
        return "Current call-loan behaviour"
    if name.startswith("act_cc") or name == "eng_act_cc_to_income":
        return "Current credit-card behaviour"
    if name.startswith("act_") or name.startswith("eng_act"):
        return "Current customer state"
    if name.startswith("agr") or name.startswith("ags"):
        return "Historical arrears behaviour"
    return "Other"


def risk_direction(coefficient):
    if pd.isna(coefficient) or abs(coefficient) <= 1e-12:
        return "neutral / not used"
    if coefficient > 0:
        return "higher value/category increases PD"
    return "higher value/category decreases PD"


def term_importance(fitted_model, label):
    importance = model_code.feature_importance(fitted_model)
    preprocess = fitted_model.named_steps["preprocess"]
    numeric_columns = list(preprocess.transformers_[0][2])
    categorical_columns = list(preprocess.transformers_[1][2])
    importance["raw_feature"] = importance["feature"].apply(
        lambda value: model_code.transformed_feature_to_raw(
            value, numeric_columns, categorical_columns
        )
    )
    importance["business_group"] = importance["raw_feature"].apply(business_group)
    importance["risk_direction"] = importance["coefficient"].apply(risk_direction)
    importance["model"] = label
    return importance[
        [
            "model",
            "business_group",
            "raw_feature",
            "feature",
            "coefficient",
            "risk_direction",
            "importance",
        ]
    ]


def raw_driver_summary(fitted_model, label):
    terms = term_importance(fitted_model, label)
    terms["positive_abs"] = np.where(terms["coefficient"] > 0, terms["importance"], 0.0)
    terms["negative_abs"] = np.where(terms["coefficient"] < 0, terms["importance"], 0.0)
    summary = (
        terms.groupby(["model", "business_group", "raw_feature"], as_index=False)
        .agg(
            coefficient_abs_sum=("importance", "sum"),
            signed_coefficient_sum=("coefficient", "sum"),
            max_abs_coefficient=("importance", "max"),
            positive_abs_sum=("positive_abs", "sum"),
            negative_abs_sum=("negative_abs", "sum"),
            nonzero_terms=("importance", lambda value: int((value > 1e-12).sum())),
        )
        .sort_values(["model", "coefficient_abs_sum"], ascending=[True, False])
        .reset_index(drop=True)
    )
    total = summary.groupby("model")["coefficient_abs_sum"].transform("sum")
    summary["importance_share"] = np.where(
        total > 0, summary["coefficient_abs_sum"] / total, 0.0
    )
    summary["dominant_direction"] = np.select(
        [
            summary["positive_abs_sum"] > summary["negative_abs_sum"],
            summary["negative_abs_sum"] > summary["positive_abs_sum"],
        ],
        ["mostly increases PD", "mostly decreases PD"],
        default="mixed / neutral",
    )
    return summary


def product_sample_summary(sample, y, masks):
    rows = []
    for split_name, mask in masks.items():
        frame = sample.loc[mask, ["product"]].copy()
        frame[model_code.TARGET] = y.loc[mask].values
        for product, group in frame.groupby("product"):
            rows.append(
                {
                    "split": split_name,
                    "product": product,
                    "n_obs": int(group.shape[0]),
                    "bad_rate": float(group[model_code.TARGET].mean()),
                }
            )
    return pd.DataFrame(rows)


def train_submodels_with_importance(sample, X, y):
    metrics_rows = []
    driver_frames = []
    term_frames = []
    for product in sorted(sample["product"].dropna().unique()):
        product_mask = sample["product"].eq(product)
        sub_sample = sample.loc[product_mask].reset_index(drop=True)
        sub_X = X.loc[product_mask].reset_index(drop=True)
        sub_y = y.loc[product_mask].reset_index(drop=True)
        sub_masks, split_definition = model_code.temporal_holdout_masks(sub_sample)
        model_code.validate_split_masks(sub_sample, sub_masks)

        fitted = model_code.build_model(sub_X)
        fitted.fit(sub_X.loc[sub_masks["train"]], sub_y.loc[sub_masks["train"]])
        label = f"{product}_submodel"
        driver_frames.append(raw_driver_summary(fitted, label))
        term_frames.append(term_importance(fitted, label))

        for split_name, mask in sub_masks.items():
            probability = fitted.predict_proba(sub_X.loc[mask])[:, 1]
            metrics_rows.append(
                model_code.safe_metrics_row(
                    model_code.MODEL_ID,
                    split_name,
                    sub_y.loc[mask],
                    probability,
                    submodel_product=product,
                    validation_start=split_definition["validation_start"],
                    test_start=split_definition["test_start"],
                    status="ok",
                )
            )
    return (
        pd.DataFrame(metrics_rows),
        pd.concat(driver_frames, ignore_index=True),
        pd.concat(term_frames, ignore_index=True),
    )


def compare_css_ins_drivers(raw_drivers):
    comparison = raw_drivers.pivot_table(
        index=["business_group", "raw_feature"],
        columns="model",
        values=["coefficient_abs_sum", "importance_share", "signed_coefficient_sum"],
        aggfunc="first",
    )
    comparison.columns = [f"{metric}_{model}" for metric, model in comparison.columns]
    comparison = comparison.reset_index()
    for column in [
        "importance_share_css_submodel",
        "importance_share_ins_submodel",
        "signed_coefficient_sum_css_submodel",
        "signed_coefficient_sum_ins_submodel",
    ]:
        if column not in comparison.columns:
            comparison[column] = 0.0
    comparison["importance_gap_ins_minus_css"] = (
        comparison["importance_share_ins_submodel"].fillna(0.0)
        - comparison["importance_share_css_submodel"].fillna(0.0)
    )
    comparison["same_direction_css_ins"] = np.sign(
        comparison["signed_coefficient_sum_css_submodel"].fillna(0.0)
    ).eq(np.sign(comparison["signed_coefficient_sum_ins_submodel"].fillna(0.0)))
    return comparison.sort_values(
        "importance_gap_ins_minus_css", key=lambda value: value.abs(), ascending=False
    ).reset_index(drop=True)


def write_business_report():
    sample = model_code.load_sample()
    raw_features = model_code.select_features(sample)
    X_all = model_code.add_features(sample[raw_features])
    y = sample[model_code.TARGET].astype(int)
    masks = model_code.split_by_time(sample)

    feature_report = model_code.feature_quality_report(X_all, y, masks["train"])
    if model_code.FEATURE_SELECTION_MODE == "quality_screen":
        selected_features = model_code.selected_features_from_report(feature_report)
    elif model_code.FEATURE_SELECTION_MODE == "all_leakage_safe":
        selected_features = raw_features
    else:
        raise ValueError(
            f"Unknown FEATURE_SELECTION_MODE: {model_code.FEATURE_SELECTION_MODE}"
        )
    selected_features, _ = model_code.prune_correlated_features(
        X_all, y, masks["train"], selected_features, feature_report
    )
    selected_features, _ = model_code.prune_vif_features(
        X_all, y, masks["train"], selected_features, feature_report
    )

    X = X_all[selected_features]
    pooled_model = model_code.build_model(X)
    pooled_model.fit(X.loc[masks["train"]], y.loc[masks["train"]])

    probabilities = {
        split_name: pooled_model.predict_proba(X.loc[mask])[:, 1]
        for split_name, mask in masks.items()
    }
    metrics = pd.DataFrame(
        [
            model_code.metrics_row(split_name, y.loc[mask], probabilities[split_name])
            for split_name, mask in masks.items()
        ]
    )
    product_metrics = model_code.metrics_by_product(sample, y, masks, probabilities)
    sample_by_product = product_sample_summary(sample, y, masks)

    pooled_raw_drivers = raw_driver_summary(pooled_model, "pooled")
    pooled_terms = term_importance(pooled_model, "pooled")
    submodel_metrics, submodel_raw_drivers, submodel_terms = train_submodels_with_importance(
        sample, X, y
    )
    all_raw_drivers = pd.concat(
        [pooled_raw_drivers, submodel_raw_drivers], ignore_index=True
    )
    all_terms = pd.concat([pooled_terms, submodel_terms], ignore_index=True)
    driver_comparison = compare_css_ins_drivers(submodel_raw_drivers)

    top_css = submodel_raw_drivers.loc[
        submodel_raw_drivers["model"].eq("css_submodel")
    ].head(30)
    top_ins = submodel_raw_drivers.loc[
        submodel_raw_drivers["model"].eq("ins_submodel")
    ].head(30)

    executive_summary = pd.DataFrame(
        [
            {
                "topic": "Performance difference",
                "business_output": (
                    "The risk model behaves differently by current application "
                    "product. Product-level Gini and driver sheets should be used "
                    "instead of relying only on the pooled model."
                ),
            },
            {
                "topic": "CSS drivers",
                "business_output": "; ".join(top_css["raw_feature"].head(8).tolist()),
            },
            {
                "topic": "INS drivers",
                "business_output": "; ".join(top_ins["raw_feature"].head(8).tolist()),
            },
            {
                "topic": "How to read direction",
                "business_output": (
                    "Positive coefficient direction means the value/category "
                    "increases predicted PD. Negative direction means it lowers PD."
                ),
            },
        ]
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(BUSINESS_REPORT_PATH, engine="xlsxwriter") as writer:
        sheets = {
            "Executive_summary": executive_summary,
            "Pooled_metrics": metrics,
            "Pooled_by_product": product_metrics,
            "Submodel_metrics": submodel_metrics,
            "Sample_by_product": sample_by_product,
            "Css_vs_ins_drivers": driver_comparison,
            "Raw_driver_summary": all_raw_drivers,
            "Top_css_drivers": top_css,
            "Top_ins_drivers": top_ins,
            "Term_level_drivers": all_terms,
        }
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
        percent = workbook.add_format({"num_format": "0.00%"})
        number = workbook.add_format({"num_format": "0.0000"})
        for sheet_name, dataframe in sheets.items():
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, max(0, dataframe.shape[0]), max(0, dataframe.shape[1] - 1))
            for col, column in enumerate(dataframe.columns):
                worksheet.write(0, col, column, header)
                worksheet.set_column(col, col, 18)
            if sheet_name in {
                "Pooled_metrics",
                "Pooled_by_product",
                "Submodel_metrics",
                "Sample_by_product",
            }:
                worksheet.set_column(3, 10, 14, number)
            if sheet_name in {
                "Css_vs_ins_drivers",
                "Raw_driver_summary",
                "Top_css_drivers",
                "Top_ins_drivers",
            }:
                worksheet.set_column(3, 8, 14, number)
                worksheet.set_column(8, 10, 14, percent)

    all_raw_drivers.to_csv(OUTPUT_DIR / "business_raw_driver_summary.csv", index=False)
    driver_comparison.to_csv(OUTPUT_DIR / "business_css_vs_ins_drivers.csv", index=False)
    return BUSINESS_REPORT_PATH


if __name__ == "__main__":
    path = write_business_report()
    print(f"Business report written to: {path}")
