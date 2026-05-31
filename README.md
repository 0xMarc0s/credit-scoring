# Credit Scoring

Python workflow for the credit scoring project.

## Current Layout

- `pd_css_cross_final_single_use.ipynb` - active final PD Css Cross notebook. It is linear single-use code, with no helper-function cells.
- `abt_app.sas7bdat`, `abt_app_PD_INS.xlsx`, `gini_curves_template.xlsx` - input data/templates kept in the repository root because the notebooks/scripts read them from there.
- `outputs/pd_css_cross/` - current PD Css Cross generated outputs.
- `outputs/asb_step_by_step/` - legacy ASB/root-generated output files moved out of the root.
- `src/` - Python script exports and reference scripts.
- `notebooks/` - older/reference notebooks.
- `docs/` - project documentation and output explanations.
- `archive/remove_candidates/` - files that look disposable or duplicate, kept instead of deleted.

## Setup

Requires Python 3.11.

On macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows:

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

Open and run:

`pd_css_cross_final_single_use.ipynb`

The active notebook writes its generated files into `outputs/pd_css_cross/`.

Legacy/reference workflows are kept in `notebooks/` and `src/`.
