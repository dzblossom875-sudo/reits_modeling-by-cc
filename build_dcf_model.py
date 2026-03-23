"""
DEPRECATED — 此文件已废弃。

原有的 ProjectDCF 逻辑已迁移至:
  src/models/hotel/dcf.py   (HotelDCFModel / HotelProjectDCF)
  src/models/hotel/noi_engine.py (NOIDeriver)
  src/models/dcf_result.py  (DCFResult / SensitivityEngine)

新用法示例:
    import json
    from src.models import build_dcf_model

    data     = json.load(open("data/huazhu/extracted_params.json"))
    detailed = json.load(open("data/huazhu/extracted_params_detailed.json"))
    hist     = json.load(open("output/historical_financial_3years.json"))

    model  = build_dcf_model("hotel", data, detailed, hist)
    result = model.calculate()
    print(result.summary())

    engine = model.run_sensitivity()
    print(engine.tornado())
"""

raise DeprecationWarning(
    "build_dcf_model.py 已废弃，请使用 src/models/hotel/dcf.py。"
    "详见文件顶部注释。"
)
