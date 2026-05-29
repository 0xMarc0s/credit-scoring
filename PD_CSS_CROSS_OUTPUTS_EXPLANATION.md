# PD Css Cross - Explanation of Outputs

This document explains the contents of:

```text
outputs/pd_css_cross/
```

The folder contains outputs for the **PD Css Cross** model:

```text
P(default_cross12 = 1)
```

The business task is to estimate the probability that a cross-sold cash loan defaults within 12 months, using information available at the time of applying for an instalment loan.

## 1. `sample_definition.csv`

This file describes the modelling sample.

Important fields:

```text
model_id = PD_CSS_CROSS
target = default_cross12
product = ins
decision = A
cross_response = 1
```

Interpretation:

The model is built on accepted instalment-loan applications where the customer accepted/took the cross-sold cash loan. The target `default_cross12` tells whether the related cross-sold cash loan defaulted within 12 months.

Important defence point:

> Missing `default_cross12` values are not treated as non-defaults. The model uses only observations where the cross-loan default outcome is known.

## 2. `split_definition.csv`

This file shows the out-of-time split:

```text
train
validation
test
```

Older periods are used for training. Newer periods are used for validation and testing.

Why this matters:

> In credit scoring, the model must work on future applications. Therefore, out-of-time validation is more realistic than a random split.

## 3. `raw_candidate_features.csv`

This file lists all raw candidate variables considered before feature screening.

The script uses variables with prefixes:

```text
app_
act_
agr_
ags_
```

Meaning:

- `app_` - application-time variables.
- `act_` - current customer/account state.
- `agr_`, `ags_` - historical behavioural aggregates.

## 4. `feature_quality.csv`

This is the feature-quality report.

For each variable, it contains:

```text
missing_rate_train
nunique_train
top_value_share_train
univariate_abs_gini_train
selected
rejection_reason
```

The report checks:

- missing-value rate;
- number of distinct values;
- whether one value dominates;
- individual predictive power;
- whether the feature was accepted or rejected.

Defence point:

> Before modelling, I performed a basic feature-quality screen and rejected variables that were constant, too sparse, too dominated by one value, too high-cardinality, or weak in univariate Gini.

## 5. `selected_features.csv`

This file lists features that passed the quality screen and were allowed into the modelling pipeline.

It does not mean every feature is highly important in the final model. It means the feature passed the screening rules and was available for model training.

## 6. `metrics.csv`

This is the main model-performance file.

It contains metrics for:

```text
train
validation
test
```

Important columns:

```text
bad_rate
predicted_pd_mean
auc
gini
brier
log_loss
```

Current model results are approximately:

```text
Train Gini:      0.5370
Validation Gini: 0.5488
Test Gini:       0.5462
```

Interpretation:

> The model has moderate discriminatory power. The validation and test Gini are close to each other, which is more important than the earlier Excel-based result because this run uses the raw SAS source population.

Also compare:

```text
test bad_rate          ~= 0.2606
test predicted_pd_mean ~= 0.2939
```

Interpretation:

> The average predicted PD is somewhat higher than the actual default rate on the out-of-time test sample, so calibration should be reviewed bucket by bucket rather than judged only by the average.

## 7. `oot_test_calibration.csv`

This file checks calibration on the out-of-time test sample.

The test sample is divided into PD buckets. For each bucket, the file shows:

```text
mean_pd
observed_default_rate
absolute_calibration_error
```

Interpretation:

> The calibration table checks whether low-PD customers really have low default rates, and high-PD customers really have high default rates.

Ideally:

```text
mean_pd ~= observed_default_rate
```

Some differences are normal because the test sample is not very large.

## 8. `predictions.csv`

This file contains predictions for all splits:

```text
train
validation
test
```

Important columns:

```text
aid
period
default_cross12
SCORE_PD_CSS_CROSS
PD_CSS_CROSS
split
```

For each observation, the file contains:

- actual target value;
- model score;
- predicted probability of default;
- data split.

## 9. `oot_test_predictions.csv`

This file contains predictions only for the out-of-time test sample.

It is useful when showing performance specifically on future/unseen periods.

## 10. `top_feature_importance.csv`

This file lists the most important transformed model features.

Columns:

```text
feature
coefficient
importance
```

Important note:

> These are features after pipeline transformations, such as standardized numeric variables and one-hot encoded categorical variables.

Example:

```text
cat__app_char_job_code_Contract
```

means the `Contract` category from `app_char_job_code`.

## 11. `sas_scoring_terms.csv`

This is a technical audit file for the SAS exporter.

It shows which model terms were translated into SAS scoring code.

Defence point:

> I used this file to verify which transformed model terms were exported into the SAS scoring code.

## 12. `scoring_code.sas`

This is the most important file for the SAS simulation process.

It creates:

```sas
SCORE_PD_CSS_CROSS
PD_CSS_CROSS
```

The probability is calculated as:

```sas
1/(1+exp(-calculated SCORE_PD_CSS_CROSS)) as PD_CSS_CROSS
```

Interpretation:

> The SAS code first calculates the logistic model score, then converts that score into the probability of `default_cross12 = 1`.

This file is intended to be included by `%include` in `decision_engine.sas`.

## Full Process to Explain During Defence

1. I built the `PD_CSS_CROSS` model using `abt_app.sas7bdat`.
2. The population is accepted instalment-loan applications with `cross_response = 1`.
3. This is correct because the model is supposed to work at the time of applying for an instalment loan.
4. The target is `default_cross12`, which marks default of the related cross-sold cash loan within 12 months.
5. I removed rows where `default_cross12` is missing, because missing target does not mean non-default.
6. Candidate variables came from `app`, `act`, `agr`, and `ags` groups.
7. I excluded leakage variables such as default variables and cross-response variables.
8. I performed feature-quality screening.
9. I split the data out-of-time into train, validation, and test.
10. I trained a logistic regression model.
11. I evaluated the model using Gini, AUC, Brier score, log-loss, and calibration.
12. The out-of-time test Gini is around `0.55`, which indicates moderate discriminatory power.
13. The average predicted PD is somewhat higher than the actual default rate on the test sample, so I reviewed calibration on the test buckets.
14. I generated `scoring_code.sas`, which creates `SCORE_PD_CSS_CROSS` and `PD_CSS_CROSS` for use in the SAS simulation process.

## Short Defence Statement

> The PD Css Cross model measures the risk that a cross-sold cash loan defaults within 12 months, using only information available at the instalment-loan application moment. The model is trained on accepted instalment-loan applications with `cross_response = 1` and known `default_cross12`. It uses out-of-time validation, achieves a test Gini around 0.55, and produces SAS scoring code that calculates both `SCORE_PD_CSS_CROSS` and `PD_CSS_CROSS` for the simulation engine.

## Feature Selection

Feature selection happens in two main stages:

```text
1. raw candidate selection
2. feature-quality and predictive-power screening
```

The final logistic model also uses L1 regularization, which further reduces the impact of weak predictors.

### 1. Raw Candidate Selection

The model starts from the full ABT:

```text
abt_app.sas7bdat
```

It considers variables whose names start with:

```python
("app", "act", "agr", "ags")
```

Business meaning:

- `app_` - application-time variables;
- `act_` - current customer/account state;
- `agr_`, `ags_` - historical behavioural aggregates.

These variables are appropriate because they should be available at the instalment-loan application moment.

### 2. Leakage Exclusion

The script excludes variables whose names contain:

```python
("default", "cross_response", "cross_after", "cross_aid", "pd_", "score_")
```

Examples:

```text
default12
default_cross12
cross_response
cross_aid
```

Reason:

> These variables either are the target, are directly connected to future cross-sell outcomes, or are already model outputs. Using them would create data leakage and artificially inflate performance.

### 3. Engineered Features

The script also creates several ratio variables:

```text
eng_app_loan_to_income
eng_app_installment_to_income
eng_app_spending_to_income
eng_act_loaninc_to_income
eng_act_cc_to_income
eng_missing_count
```

Business interpretation:

- loan amount relative to income;
- instalment amount relative to income;
- spending relative to income;
- credit exposure relative to income;
- number of missing fields.

These variables are useful because affordability and data completeness are common risk indicators.

### 4. Feature-Quality Screening

The feature-quality report is saved in:

```text
outputs/pd_css_cross/feature_quality.csv
```

For every candidate feature, the script calculates:

```text
missing_rate_train
nunique_train
top_value_share_train
univariate_abs_gini_train
selected
rejection_reason
```

Only the training sample is used for this screening. This avoids using validation or test information during model development.

### 5. Missing-Rate Filter

Variables are rejected if more than 98% of training values are missing:

```python
MAX_MISSING_RATE = 0.98
```

Reason:

> A variable that is almost always missing is unlikely to be reliable.

### 6. Constant or Empty Feature Filter

Variables are rejected if they have one or fewer distinct non-missing values:

```python
nunique <= 1
```

Reason:

> A constant variable cannot separate good and bad customers.

### 7. Dominant-Value Filter

Variables are rejected if one value represents more than 99.5% of the training sample:

```python
MAX_DOMINANT_SHARE = 0.995
```

Reason:

> A variable with almost no variation is unstable and not useful for modelling.

### 8. High-Cardinality Categorical Filter

Categorical variables are rejected if they have more than 50 distinct levels:

```python
MAX_CATEGORY_LEVELS = 50
```

Reason:

> Very high-cardinality categorical variables can overfit and are harder to defend in a credit-risk model.

### 9. Univariate Gini Filter

Each variable's standalone predictive power is measured using absolute Gini.

The minimum threshold is:

```python
MIN_UNIVARIATE_GINI = 0.02
```

For numeric variables:

- missing values are filled with the median;
- the numeric value is used as the score.

For categorical variables:

- categories are replaced by their bad rate on the training sample;
- Gini is then calculated from that score.

Reason:

> I kept variables with at least minimal individual predictive power on the training sample.

### 10. Selected Features

Features that pass all filters are saved in:

```text
outputs/pd_css_cross/selected_features.csv
```

Rejected features and reasons are visible in:

```text
outputs/pd_css_cross/feature_quality.csv
```

### 11. Model-Level Selection

After screening, features enter the logistic regression pipeline.

The model uses:

```python
LogisticRegression(
    penalty="l1",
    solver="liblinear",
    C=0.05
)
```

L1 regularization acts as an additional selection mechanism:

- weak predictors receive coefficients close to zero;
- stronger predictors keep meaningful coefficients;
- the model is less likely to overfit.

### 12. Final Feature Importance

The final transformed model terms are saved in:

```text
outputs/pd_css_cross/top_feature_importance.csv
```

The file contains:

```text
feature
coefficient
importance
```

Examples:

```text
num__act_age
cat__app_char_job_code_Contract
```

These names come from the preprocessing pipeline:

- `num__` means numeric feature after imputation and standardization;
- `cat__` means categorical feature after imputation and one-hot encoding.

### Short Defence Statement About Feature Selection

> Candidate variables were taken from application, activity, and historical aggregate fields available at the instalment-loan application moment. I excluded target and future-looking variables to avoid leakage. Then I screened variables on the training sample for missingness, low variation, excessive cardinality, dominance by one value, and weak univariate Gini. The remaining variables were passed to an L1-regularized logistic regression, which further reduced the influence of weak predictors. Final feature importance was reported from the trained model coefficients.
