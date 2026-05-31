# ASB_step_by_step.py Documentation

This document explains what `ASB_step_by_step.py` does, step by step. The file is an exported Jupyter notebook, so execution is linear and many variables are reused across later cells.

## High-Level Purpose

`ASB_step_by_step.py` builds an application credit risk scorecard for the `default12` target. The workflow:

1. Loads and filters application data.
2. Splits observations into train and test samples.
3. Creates bins for numeric and categorical predictors.
4. Builds variable-level scorecard statistics.
5. Selects candidate variables using Gini, Information Value, and stability filters.
6. Fits and compares logistic regression scorecard models.
7. Converts the selected model into scorecard points.
8. Scores train, test, and full datasets.
9. Evaluates discrimination, stability, lift, gains, calibration, and segments.
10. Generates Excel reports, a SAS scoring script, variable clustering output, and exploratory SHAP plots.

## Required Inputs

The script expects these files in the working directory:

- `abt_app.sas7bdat` - source application dataset.
- `gini_curves_template.xlsx` - Excel template used to create `gini_curves_model.xlsx`.

The data must contain at least:

- Target: `default12`.
- Time field: `period`.
- ID field: `aid`.
- Filtering fields: `product`, `decision`.
- Loan amount fields: `app_loan_amount`, `app_n_installments`.
- Predictor fields starting with `app` or `act`.

## Main Outputs

Running the script overwrites or creates these files:

- `Big_scorecard.xlsx` - bin-level statistics for all variables.
- `Gini_vars.xlsx` - variable-level Gini, IV, PSI, missingness, mode, and type statistics.
- `Variable_report.xlsx` - selected-variable stability and bad-rate report with charts.
- `Model_report.xlsx` - final model measures, effects, scorecard, calibration, variable importance, and variable sheets.
- `Segments3_report.xlsx` - 3-segment score report by count and balance.
- `gini_curves_model.xlsx` - populated Gini curve workbook.
- `scoring_code.sas` - SAS scoring code for scorecard points.
- `Variable_Clustering.xlsx` - variable clustering output from `varclushi`.

The script also displays plots for profit cutoff analysis and SHAP/XAI, but does not save those plots to files.

## Important Configuration

At the top of the script, many string constants define report column names and model field names. Key ones are:

- `target_name = 'default12'`
- `time_name = 'period'`
- `prob_event = 'PD'`
- `score_name = 'Score'`
- `intercept_name = 'Intercept'`
- `id_row = 'aid'`

Binning parameters:

- Numeric variables use up to `ncategories_int = 4` bins.
- Numeric bins require at least `minimum_share_int = 0.03` of non-missing observations.
- Missing numeric values are labeled as `Missing` when missingness is large enough.
- Categorical variables use up to `ncategories_nom = 4` clusters.
- Rare categorical values are assigned to `<OTHERS>`.
- `category_order = False` means scorecard groups are ordered by descending bad rate for a risk model.

## Step-by-Step Workflow

### 1. Import Libraries

The script imports `pandas`, `numpy`, `math`, and `warnings`, then suppresses warnings. Later sections import `scikit-learn`, `statsmodels`, `xlsxwriter`, `openpyxl`, `matplotlib`, `varclushi`, and `shap` only when needed.

### 2. Load Source Data

The script reads:

```python
df = pd.read_sas('abt_app.sas7bdat', encoding='LATIN2')
```

It then prints the type and first value of `app_char_job_code`, apparently to check how SAS character data was decoded.

### 3. Filter the Modelling Population

The dataset is restricted to:

- `period` from `197501` to `198712`, inclusive.
- `product == 'css'`.
- `decision == 'A'`.

This creates the accepted CSS loan application population used for modelling.

### 4. Add Helper Columns

The script adds:

- `Intercept = 1` for logistic regression.
- `outstanding_bad = app_loan_amount * default12`, a balance-weighted bad amount.
- `outstanding = app_loan_amount`, the exposure/balance amount.

These are used later in logistic models, balance reports, and profit/cutoff analysis.

### 5. Drop Missing Targets

Rows with missing `default12` are removed into `df_notempty`. All modelling uses this non-missing target sample.

### 6. Build Variable Lists

Predictors are selected by name prefix:

```python
vars = [var for var in list(df) if var[0:3].lower() in ['app', 'act']]
```

The script then separates predictors into:

- `varsn` - numeric predictors.
- `varsc` - object/categorical predictors.

The train/test data also carries target, time, intercept, balance helper fields, and ID.

### 7. Split Train and Test

The non-missing target sample is split randomly:

- Train: 60%.
- Test: 40%.
- Random seed: `1234`.

The train sample is used to learn bins, scorecard statistics, variable filters, and model coefficients. The test sample is used for stability and validation checks.

### 8. Create Numeric Bins

For each numeric variable:

1. The script estimates the non-missing share.
2. It adjusts the minimum bin share to avoid tiny bins after missing values are removed.
3. It fits a `DecisionTreeClassifier` using the variable as one predictor and `default12` as target.
4. Tree split thresholds become bin cut points.
5. The bin list starts with `-inf` and `inf`.
6. If the variable has enough missing values, a separate `Missing` bin is appended.

The result is stored in:

```python
labsn[feature] = bins
```

This is supervised binning because the target is used to find numeric cutoffs.

### 9. Create Categorical Bins

For each categorical variable:

1. The script calculates category frequency and bad rate on the train sample.
2. Categories with share below `minimum_share_unique = 0.03` are excluded from clustering.
3. Remaining categories are clustered by bad rate using `AgglomerativeClustering`.
4. Up to `ncategories_nom = 4` clusters are created.
5. If excluded/rare categories exist, an `<OTHERS>` group is added.

The result is stored in:

```python
labsc[feature] = bins
```

This is also supervised grouping because categories are clustered by target rate.

### 10. Convert Bins to Human-Readable Conditions

Numeric bins are converted to textual conditions such as:

- `feature < cutoff`
- `lower <= feature < upper`
- `lower <= feature`
- `feature = Missing`
- `feature <> Missing`

Categorical clusters are converted to comma-separated lists of category values, with rare values represented by `<OTHERS>`.

These condition strings are later used in reports and to reapply the bins.

### 11. Assign Initial Group IDs on Train

The script creates `train_grp` by replacing each raw predictor value with a group number:

- Numeric variables are assigned by comparing each value to the learned cut points.
- Missing numeric values go to the missing group when available.
- Categorical variables are assigned to the cluster number learned earlier.
- Unknown or rare categorical values fall into the `<OTHERS>` group when it exists.

This first grouping is used to build bin-level statistics.

### 12. Build `Big_scorecard`

For every numeric and categorical variable, the script calculates train-sample bin statistics:

- Count of observations: `All`.
- Count of bads: `Bad`.
- Count of goods: `Good`.
- Bad rate: `BR = Bad / All`.
- Logit: `log((Bad + 0.0001) / (Good + 0.0001))`.
- Population share: `Share`.
- Human-readable condition.
- Group number: `GRP`.
- Variable type: `INT` or `NOM`.

Bins are sorted by bad rate using `category_order = False`, so high bad-rate bins come first. Group IDs are then reset according to this order.

The script also calculates:

- `Bad share = Bad / total bads`
- `Good share = Good / total goods`
- `Infomration Value` using the standard bin-level IV contribution formula.

The full table is exported to `Big_scorecard.xlsx`.

### 13. Reapply Final Groups to Train and Test

After `Big_scorecard` reorders groups by bad rate, the script creates:

- `grp_train`
- `grp_test`

These datasets contain final `GRP` values for every predictor. The grouping is reapplied by parsing the textual condition strings from `Big_scorecard`.

### 14. Calculate Test-Sample Bin Shares

The script creates `Big_scorecard_test` from `grp_test`, with:

- Test population share by variable/group.
- Test bad share by variable/group.

This is merged into `Big_scorecard`.

### 15. Calculate PSI Metrics

Two stability metrics are added to `Big_scorecard`:

- `Population Stability Index` compares train vs. test population share.
- `Population Stability Index for bads` compares train vs. test bad share.

Both use a small `0.0001` smoothing constant to avoid division by zero in logs.

### 16. Create Logit-Encoded Train and Test Data

The script creates:

- `logit_train`
- `logit_test`

Each predictor value is replaced by the bin-level `Logit` from `Big_scorecard`. These logit-encoded predictors are used for variable Gini calculations, RFE, and logistic scorecard modelling.

### 17. Calculate Variable-Level Statistics

For each variable, the script calculates:

- Train Gini using the logit-encoded predictor.
- Test Gini using the logit-encoded predictor.
- Relative Gini difference: `abs(train - test) / train`.

It then joins:

- Total IV across bins.
- Total PSI across bins.
- Total target PSI across bins.
- Missing percentage.
- Number of distinct values.
- Mode.
- Mode share.
- Type: `INT` or `NOM`.

The resulting `Gini_vars` table is exported to `Gini_vars.xlsx`.

### 18. Select Candidate Variables

Variables are selected into `vars_selected` if they satisfy:

- `Gini train > 0.05`
- `R. Gini < 0.2`
- `Population Stability Index for bads < 0.1`
- `Population Stability Index < 0.1`

This keeps variables that are individually predictive and stable from train to test.

### 19. Create Full Grouped Dataset and Time Field

The script concatenates grouped train and test into `grp_all`.

It also creates `Time` as the first four characters of `period`, so reports are aggregated by year.

### 20. Build `Variable_report.xlsx`

The variable report contains:

- A `Variable` sheet with `Gini_vars`.
- One sheet per selected variable.

For each selected variable, the sheet includes:

- Bin-level train scorecard statistics.
- Time-series statistics by group and year.
- Line chart for bad rate over time.
- Line chart for population share over time.

This report is intended to support variable review and stability checks.

### 21. Rank Variables with RFE

The script fits `LogisticRegression` on `logit_train[vars_selected]` and uses recursive feature elimination:

```python
rfe = RFE(estimator=model, n_features_to_select=1, step=1)
```

It ranks all selected variables by predictive usefulness in the logistic model.

### 22. Evaluate Model Combinations

The script sets:

- `number_vars = 12`
- `number_features = 6`

It takes the top 12 RFE-ranked variables, then evaluates all 6-variable combinations among them. For each candidate set, the helper function `assess(selected_vars)` fits a `statsmodels.Logit` model and calculates:

- Number of negative non-intercept coefficients.
- Maximum p-value among predictors.
- Train Gini.
- Test Gini.
- Relative train-test Gini difference.
- Maximum VIF.
- Maximum condition index.
- Maximum absolute Pearson correlation.

The script stores all candidate results in `Model_list`.

### 23. Select the Final Model

Candidate models are filtered to:

- `nnegative_betas == 0`
- `max_pvalue <= 0.01`
- `max_vif <= 3.0`

The remaining models are sorted by `gini_test` descending. The first row becomes the final selected model.

This means the chosen model prioritizes:

1. Coefficients with expected positive direction after bin ordering.
2. Statistical significance.
3. Low multicollinearity.
4. Best test-sample Gini among valid candidates.

### 24. Fit Final Logistic Model

The script refits `statsmodels.Logit` on the selected final variables plus `Intercept`.

It stores model diagnostics in the `result` dictionary:

- Coefficients and standard errors.
- Wald test statistics.
- P-values.
- Train Gini.
- Test Gini.
- Relative Gini difference.
- Maximum p-value.
- Number of negative betas.
- Maximum VIF.
- Maximum condition index.
- Maximum Pearson correlation.
- Placeholders for KS, PSI score, gains, and lift.

### 25. Convert Model to Scorecard Points

The scorecard is built from the selected variables' rows in `Big_scorecard`.

For each selected variable/bin, the script:

1. Joins the logistic coefficient.
2. Uses `factor = 20 / log(2)`, meaning 20 points correspond to a doubling of odds.
3. Uses the first group of each variable as a reference through `FBeta`.
4. Distributes the intercept across variables.
5. Rounds each bin score to whole points.

The formula is:

```python
Score = -(
    Logit * Beta
    - FBeta
    + Intercept / number_of_features
) * factor + alp / number_of_features
```

The script calculates `alp` so the score scale is anchored around 300 points.

### 26. Score Full, Train, and Test Data

The script creates:

- `scored_all`
- `scored_train`
- `scored_test`

For each selected variable, the grouped value is merged with the corresponding scorecard points. Total `Score` is the sum of all selected variable point contributions.

The exports for these scored datasets are present in comments but currently disabled.

### 27. Calculate KS, Gains, Lift, and Score PSI

The helper function `ks()` groups scored data by exact score and calculates:

- Cumulative event rate.
- Cumulative non-event rate.
- Cumulative total share.
- KS statistic.

On `scored_test`, the script calculates:

- `KS score`
- Gains at 1%, 2%, 3%, 4%, 5%, 10%, and 50%.
- Lift at the same cutoffs.

It also calculates score-level PSI by splitting combined train/test scores into five quantile buckets and comparing train vs. test bucket shares.

### 28. Create Gini Curve Workbook

The full scored sample is ranked by `Score` and split into 20 groups. For each group, the script calculates bad and good counts.

It opens `gini_curves_template.xlsx`, writes bad/good counts into predefined cells, and saves:

```text
gini_curves_model.xlsx
```

### 29. Calculate Gini Overall and Over Time

The script calculates overall Gini on `scored_all`.

It also calculates yearly Gini by grouping on the derived `Time` field. The yearly Gini table is later included in `Model_report.xlsx`.

### 30. Calibrate Score to PD

The script fits a calibration logistic regression:

```python
default12 ~ Score + Intercept
```

It defines:

```python
PD = 1 / (1 + exp(-(score_coef * Score + intercept)))
```

Then it adds calibrated `PD` to:

- `cal_scored`
- `scored_all`

It also creates a yearly calibration table comparing:

- Count of observations.
- Actual default rate `BR`.
- Average predicted `PD`.

### 31. Create Calibration Bands

The script splits `scored_all` into 10 score-ranked groups and calculates by segment:

- Minimum score.
- Maximum score.
- Actual default rate.
- Average `PD`.

This is an additional calibration check, displayed in memory but not directly exported except through later model report content.

### 32. Build `Model_report.xlsx`

The model report contains:

- `Main_measures` - final model metrics from `result`.
- `Effects` - model coefficients, Wald tests, p-values, and standard errors.
- `Gini_over_time` - yearly Gini plus a chart.
- `Scorecard` - final bin-level scorecard points.
- `Variable importance` - score range per variable and relative importance.
- `Calibration` - yearly actual bad rate vs. predicted PD and calibration formula.
- `Variable` - `Gini_vars` filtered to final model variables.
- One sheet per final variable with scorecard rows, time-series group statistics, and charts.

### 33. Create 3 Score Segments

The script creates `n_groups = 3` ranked score segments on `scored_all`.

For each segment it calculates:

- Minimum and maximum score.
- Observation default rate.
- Observation count and share.
- Bad count.
- Balance-weighted default rate.
- Bad balance.
- Total balance.
- Balance share.

It also calculates the same measures by segment and year.

### 34. Build `Segments3_report.xlsx`

The segment report has two sheets:

- `Numbers` - segment performance based on observation counts.
- `Balances` - segment performance based on loan balances.

Both sheets include total segment tables, time-series tables, bad-rate charts, and share charts.

### 35. Profit Cutoff Analysis

The script sets profitability assumptions:

- `apr = 0.18`
- `lgd = 0.55`
- `provision = 0`

It calculates a simplified profit for each observation:

- If defaulted: `-app_loan_amount * lgd`.
- If not defaulted: total installments plus provision-adjusted principal impact.

It then groups by calibrated `PD`, calculates cumulative profit, and plots:

- `PD` vs. cumulative profit.
- Acceptance rate vs. cumulative profit.

Finally, it sorts cumulative profit descending to identify the maximum-profit cutoff area.

### 36. Generate SAS Scoring Code

The script writes `scoring_code.sas`.

For each final scorecard variable:

- Numeric variables become SAS `case when` statements based on scorecard conditions.
- Categorical variables become SAS `case when var in (...)` statements.
- Each variable score is emitted as `PSC_<variable>`.

The script also writes total score:

```sas
SCORECARD_POINTS = 0.0 + calculated PSC_var1 + calculated PSC_var2 + ...
```

The calibrated PD formula is written as a commented-out SAS expression, not active production code.

### 37. Variable Clustering

The script uses:

```python
VarClusHi(logit_train[vars_selected], maxeigval2=0.1, maxclus=None)
```

It writes:

- Cluster summary to `Variable_Clustering.xlsx`, sheet `Info`.
- Variable R-square table to `Variable_Clustering.xlsx`, sheet `Clusters`.

This section is exploratory and uses the candidate variable set, not only the final model variables.

### 38. SHAP / XAI Exploration

The script builds a `LogisticRegression` model on `scored_train[features]`, where features are already scorecard point contributions.

Then it manually sets:

- Every coefficient to `1.0`.
- Intercept to `0.0`.

This makes the model output equal to the sum of scorecard point variables. SHAP values therefore explain the score contribution structure rather than the original logistic PD model.

The script creates:

- Bar summary plot.
- Bar plot.
- Violin summary plot.
- Beeswarm plot.
- Waterfall plot for the first observation.
- Force plot for the first observation.

It also prints feature contributions for the first observation and checks that summed SHAP values align with summed score contributions.

## Key Data Objects

| Object | Meaning |
| --- | --- |
| `df` | Raw SAS data after loading, then filtered population. |
| `df_notempty` | Filtered population with non-missing target. |
| `train`, `test` | Raw train/test modelling samples. |
| `labsn`, `labsc` | Learned numeric and categorical bin definitions. |
| `train_grp` | Initial grouped train sample used for scorecard statistics. |
| `Big_scorecard` | Main bin-level scorecard statistics table. |
| `grp_train`, `grp_test`, `grp_all` | Final grouped train/test/full samples. |
| `logit_train`, `logit_test` | Final binned data encoded by bin logits. |
| `Gini_vars` | Variable-level predictive power and stability table. |
| `vars_selected` | Variables passing Gini/PSI filters. |
| `Model_list` | Candidate model diagnostics for RFE-selected combinations. |
| `subModel_list` | Candidate models passing beta, p-value, and VIF filters. |
| `result` | Final model diagnostics and performance metrics. |
| `Scorecard` | Final variable/bin scorecard points. |
| `scored_all`, `scored_train`, `scored_test` | Point-scored datasets. |
| `cal_scored` | Scored data with calibrated PD. |
| `sss`, `sss_time` | Segment summaries used for segment reports. |

## Modelling Logic Summary

The script models credit risk using a traditional scorecard pipeline:

1. Supervised binning turns raw predictors into risk-ordered groups.
2. Each group is represented by its log bad/good odds.
3. Variables are screened for predictive power and stability.
4. A logistic regression is fitted on logit-encoded variables.
5. Candidate models are constrained to avoid negative betas, high p-values, and high VIF.
6. The final logistic model is converted into scorecard points.
7. Scorecard points are calibrated back to PD with a separate logistic model.

## Notes and Caveats

- The script is sequential notebook-style code, not a reusable function-based pipeline.
- Many outputs are overwritten when the script is rerun.
- Some report writers call `writer.close()` twice. This is redundant.
- The column name `Infomration Value` contains a typo but is used consistently.
- Several assignments use chained indexing, which can trigger pandas copy/view issues if warnings are re-enabled.
- Categorical grouping reapplies bins by searching category text inside condition strings. This can misclassify categories if one category name is a substring of another.
- The final model selection assumes higher grouped logits and positive coefficients correspond to higher risk.
- `Scorecard.xlsx`, `Scored_all.xlsx`, and similar scored-data exports are commented out.
- The SAS PD formula is commented out, so generated SAS code currently produces scorecard points but not active PD unless edited.
- The SHAP section explains score point contributions after manually forcing coefficients to `1.0`; it is not a direct SHAP explanation of the calibrated PD model.

