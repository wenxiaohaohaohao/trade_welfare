# Data Build Code

Future scripts in this folder should:

- download or read raw OECD ICIO, OECD AMNE, and trade data;
- construct country and sector mappings;
- generate connector exposure measures;
- export MATLAB-ready inputs to `data/model_inputs/`.

The first script should be a small-sample build, not the full global pipeline.

Current BEA direct-investment batch:

```powershell
python -m pip install -r code\data_build\requirements-bea-fdi.txt
python code\data_build\build_bea_direct_investment_country_industry.py --overwrite
```
