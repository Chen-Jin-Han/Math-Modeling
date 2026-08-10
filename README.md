# Final Math Modeling

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch 2.9.1](https://img.shields.io/badge/PyTorch-2.9.1-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Mathematical Modeling](https://img.shields.io/badge/project-mathematical%20modeling-blueviolet.svg)](README.md)
[![Last Commit](https://img.shields.io/github/last-commit/Chen-Jin-Han/Final-Math-Modeling?color=orange)](https://github.com/Chen-Jin-Han/Final-Math-Modeling/commits/main)
[![Repository Size](https://img.shields.io/github/repo-size/Chen-Jin-Han/Final-Math-Modeling?color=lightgrey)](https://github.com/Chen-Jin-Han/Final-Math-Modeling)

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

## License

This project is open source under the [MIT License](LICENSE).
