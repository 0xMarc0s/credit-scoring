# Credit Scoring Project Tasks

This task list is based on `Project_Description_SAS_CS_EN.pdf` and the current Python workflow in `ASB_step_by_step.py`.

The project can be done mostly in Python. SAS is still needed at the final process-integration stage because the course simulation uses `decision_engine.sas`, model calibration folders, and the generated `profit_1975_1987.html` report.

## Current Starting Point

`ASB_step_by_step.py` already contains a complete Python scorecard workflow for one model:

- reads `abt_app.sas7bdat`
- filters period `197501` to `198712`
- filters accepted applications with `decision == 'A'`
- currently filters `product == 'css'`
- currently models `default12`
- creates numeric and categorical bins
- computes logit encodings, IV, PSI, Gini, missing rates, modes
- selects variables
- fits logistic scorecard model
- creates scorecard points
- calibrates score to PD
- creates model reports and segment reports
- generates `scoring_code.sas`
- contains optional variable clustering and SHAP/XAI sections

So the existing code is closest to the required **PD Css** model, but it should be refactored before building all required models.

## Main Project Goal

Build an improved loan approval and cross-selling strategy for the period `1975-1987`.

The strategy should improve on the benchmark profit:

**PLN 663,327**

The final score depends not only on profit, but also on how well the models, reports, cutoffs, and strategy rules are justified.

## Task 1: Refactor Python Workflow Into a Reusable Model Builder

The current script is hardcoded for one model. Refactor it so the same pipeline can build multiple models.

Recommended configuration parameters:

- `model_id`
- `target_name`
- `product_filter`
- `decision_filter`
- `period_from`
- `period_to`
- `candidate_variable_prefixes`
- `category_order`
- `output_dir`
- `probability_name`
- `score_name`

Expected output:

- reusable Python module or notebook workflow
- one config per model
- no manual edits needed between model runs except config selection

## Task 2: Build PD Ins Model

Build a risk model for instalment loans.

Model definition:

- model name: `PD Ins`
- target: `default12 = 1`
- product: `product == 'ins'`
- decision: `decision == 'A'`
- period: `197501 <= period <= 198712`

Python outputs:

- variable report
- model report
- scorecard table
- calibration table
- Gini over time
- segment report
- generated scoring code

Key checks:

- train/test Gini
- Gini stability
- PSI
- target-rate stability over time
- no negative betas for risk scorecard, unless strongly justified
- p-values and VIF acceptable

## Task 3: Build PD Css Model

Build a risk model for cash loans.

Model definition:

- model name: `PD Css`
- target: `default12 = 1`
- product: `product == 'css'`
- decision: `decision == 'A'`
- period: `197501 <= period <= 198712`

Current script mostly covers this model.

Remaining work:

- verify the current variable selection
- finalize bins and variables
- check generated reports
- improve calibration output
- make `scoring_code.sas` production-ready
- document strengths and weaknesses

## Task 4: Build PD Css Cross Model

Build a risk model for cash-loan default at the time of instalment-loan application.

Model definition from project brief:

- model name: `PD Css Cross`
- target: `default_cross12 = 1`
- built at the time of applying for instalment loan

Work needed:

- inspect `abt_app.sas7bdat` columns and target availability
- confirm correct row filter, probably instalment-loan applications
- confirm how `default_cross12` behaves for missing/non-cross-sold cases
- build the model in the same Python pipeline
- document any population assumptions

Expected outputs:

- model report
- scorecard
- calibration
- scoring code
- explanation of target construction and sample definition

## Task 5: Build PR Css Cross Marketing Model

Build a marketing response model for cross-selling.

Model definition:

- model name: `PR Css Cross`
- target: `cross_response = 1`
- event is response to cross-selling offer

Differences from risk models:

- this is a response model, not a default model
- bin ordering may need `category_order=True`
- interpretation is different: high score/probability should mean higher response probability
- cutoff strategy should consider profit, not only response rate

Expected outputs:

- model report
- response scorecard or model
- probability calibration
- scoring code
- documentation of response drivers

## Task 6: Improve the Existing Python Code as the Required Extra Contribution

The brief requires improving one stage of model building or adding custom code.

Good Python-first options:

- clean SHAP/XAI analysis into reproducible plots
- add variable clustering report using `varclushi`
- add better automatic model comparison
- add model-monitoring charts
- add profit-based cutoff optimization
- add one interpretable non-scorecard model and compare it to the scorecard

Recommended choice:

Build a clean XAI and model-comparison report, because `ASB_step_by_step.py` already contains unfinished SHAP and variable-clustering sections.

Expected output:

- documented Python code
- charts/tables included in model documentation
- short explanation of how this improves the original workflow

## Task 7: Generate Model Documentation for Each Model

For every final model, prepare:

- sample definition
- target definition
- selected variables
- rejected variables and reason, if relevant
- binning table
- scorecard table
- coefficient table
- Gini train/test
- Gini over time
- PSI
- KS
- gains/lift
- calibration table
- segment report
- strengths
- weaknesses
- known limitations

Most of this can be generated from Python.

## Task 8: Fix Python Generation of SAS Scoring Code

`ASB_step_by_step.py` already generates `scoring_code.sas`, but the calibrated probability formula is currently commented out.

Required changes:

- generate score components
- generate total score
- generate calibrated probability, for example:
  - `PD_INS`
  - `PD_CSS`
  - `PD_CSS_CROSS`
  - `PR_CSS_CROSS`
- make variable names model-specific
- make output table names model-specific
- test that generated SAS syntax is valid

Even if the model is built in Python, the final simulation still needs SAS-compatible scoring code unless the project environment is changed.

## Task 9: Calibrate Probabilities and Choose Cutoffs

For each model:

- calibrate score to probability
- check average observed event rate versus average predicted probability
- check calibration by score bands
- check calibration over time

For strategy:

- define candidate cutoffs for each model
- evaluate profit impact
- consider separate cutoffs by product and possibly by time period
- document why chosen cutoffs are reasonable

The current script has a basic cutoff/profit section, but it is model-level only. It needs to become strategy-level.

## Task 10: Build Acceptance and Cross-Sell Strategy Rules

Define final decision rules using:

- `PD Ins`
- `PD Css`
- `PD Css Cross`
- `PR Css Cross`
- available ABT variables at application time
- product type
- customer activity status
- financial/profit assumptions

Important restriction:

- rule `998 not active customer` must not be changed

Possible rule types:

- reject high-risk instalment-loan applicants
- reject high-risk cash-loan applicants
- offer cross-sell only when response probability is high enough and risk is acceptable
- use different thresholds for different products or segments
- use time-dependent rules if justified

## Task 11: Integrate Models With the Simulation Process

Required project process:

- copy each model's `scoring_code.sas` to the proper calibration folder
- update model configuration files if needed
- update `decision_engine.sas`
- run the full process for `1975-1987`
- generate `profit_1975_1987.html`

This is the main SAS-dependent part of the project.

Python can produce model artifacts and scoring code, but the final benchmark profit must come from the course simulation process.

## Task 12: Compare Against Benchmark Strategy

Benchmark:

- profit: `PLN 663,327`

For each strategy version, track:

- total profit
- profit by product
- acceptance rate
- bad rate
- cross-sell response rate
- cross-sell default rate
- rejection reasons
- effect of each model/rule on final profit

Keep a small experiment log so the final strategy can be defended.

## Task 13: Prepare Final Strategy Documentation

Prepare documentation containing:

- final decision rules
- final cutoffs
- final profit result
- comparison to benchmark
- model list and role of each model
- business interpretation
- rejected alternatives
- strengths and weaknesses
- known risks

The project defence emphasizes argument quality, not only final profit.

## Task 14: Prepare Defence Arguments

Be ready to explain:

- why each target and sample was chosen
- why the selected variables are reasonable
- why rejected variables were excluded
- why bins are monotonic or otherwise acceptable
- why model statistics are good enough
- where each model is weak
- how calibration was checked
- why the cutoffs maximize or improve profit
- why the final decision rules are business-reasonable
- how rejected applications may bias model estimation

## Recommended Work Order

1. Refactor `ASB_step_by_step.py` into a configurable Python pipeline.
2. Build and validate `PD Css`, since it is already closest to done.
3. Build `PD Ins`.
4. Inspect data and define the exact sample for `PD Css Cross`.
5. Build `PD Css Cross`.
6. Build `PR Css Cross`.
7. Clean up XAI or variable-clustering code as the extra contribution.
8. Generate model documentation for all models.
9. Generate deployable scoring code for all models.
10. Calibrate probabilities and test cutoffs.
11. Implement decision rules in the simulation.
12. Run full `1975-1987` profit simulation.
13. Iterate rules until profit improves over benchmark.
14. Prepare final documentation and defence notes.

