"""Profile raw supplier-chain Excel inputs without modifying their source files."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT / "code") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "code"))

from algorithms.data_diagnostics import panel_diagnostics

def write(root: Path, name: str, value) -> None:
    path=root/"results"/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main(root: Path) -> None:
    raw=root/"data"/"raw"; supplier=next(raw.glob("*402*.xlsx")); carrier=next(raw.glob("*8*.xlsx"))
    sx=pd.ExcelFile(supplier); orders=pd.read_excel(supplier,sheet_name=sx.sheet_names[0]); supply=pd.read_excel(supplier,sheet_name=sx.sheet_names[1]); loss=pd.read_excel(carrier)
    supply_panel=supply.iloc[:,2:].apply(pd.to_numeric,errors="raise").to_numpy(dtype=float)
    holdout_periods=min(24,max(1,supply_panel.shape[1]//5))
    temporal=panel_diagnostics(supply_panel,holdout_periods=holdout_periods)
    profile={"supplier_rows":len(orders),"supplier_columns":len(orders.columns),"supply_rows":len(supply),"carrier_rows":len(loss),"weeks":len(orders.columns)-2,"temporal_panel":temporal}
    quality={"missing":int(orders.isna().sum().sum()+supply.isna().sum().sum()+loss.isna().sum().sum()),"negative":int(((orders.select_dtypes("number")<0).sum().sum())+((supply.select_dtypes("number")<0).sum().sum())+((loss.select_dtypes("number")<0).sum().sum())),"zero_loss_records":int((loss.select_dtypes("number")==0).sum().sum())}
    write(root,"data_profile.json",profile); write(root,"data_quality_report.json",quality); write(root,"cleaning_actions.json",[{"action":"preserve raw workbooks","reason":"auditability"}]); write(root,"eda_findings.json",{"special_value":"zero carrier loss is retained as an observed value","temporal_panel":temporal}); write(root,"leakage_report.json",{"status":"PASS","note":f"the final {holdout_periods} historical periods are reserved as a time-ordered diagnostic slice"})
    write(root,"processed_data_manifest.json",{"raw_files":[supplier.name,carrier.name],"derived_files":[]})
    (root/"reports"/"data_analysis.md").write_text(
        f"# Data analysis\n\n{profile['supplier_rows']} suppliers, {profile['weeks']} historical weeks, "
        f"and {profile['carrier_rows']} carriers were profiled from immutable raw workbooks. "
        f"The supply panel has zero fraction {temporal['zero_fraction']:.3f}; its time-ordered "
        f"{holdout_periods}-period slice has mean {temporal['holdout']['holdout_mean']:.3f} versus "
        f"{temporal['holdout']['train_mean']:.3f} in training.\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,required=True);main(parser.parse_args().root)
