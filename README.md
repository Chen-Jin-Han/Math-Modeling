# Final Math Modeling

This repository contains the final no-summary code version for the strategy-game retention and payment optimization modeling task.

## Environment

- Python 3.13
- Git LFS is required for the raw datasets.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Order

```bash
python -X utf8 q1_retention_model.py
python -X utf8 q2_resource_payment_model.py
python -X utf8 q3_strategy_optimization.py
python -X utf8 q4_data_collection_closure.py
python -X utf8 model_analysis_report.py
```

## Data

Raw contest datasets are not committed because several files are larger than normal GitHub limits. To run the scripts, place the dataset folder locally at:

```text
B题：附件 数据集/
```

The scripts automatically locate the folder when it contains `pickdata1.csv` and `pickdata2.csv`.
