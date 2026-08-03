#!/bin/bash
cd ~/Development/python/shokuba-lens
PY=/Volumes/GM71TB/mlx-conversions/venvs/v068/bin/python
echo "=== REG construction start ==="
$PY -m shokuba_lens.analyze --images samples/construction_violations.png samples/construction_clean.png \
  --rules rules/construction_ppe.yaml --probe-model tokimoa/shokuba-probe-2b --out out_reg_construction \
  || echo "=== REG construction FAILED ==="
echo "=== REG construction done ==="
echo "=== REG kitchen start ==="
$PY -m shokuba_lens.analyze --images samples/kitchen_clean.png \
  --rules rules/kitchen_hygiene.yaml --probe-model tokimoa/shokuba-probe-2b --out out_reg_kitchen \
  || echo "=== REG kitchen FAILED ==="
echo "=== REG kitchen done ==="
echo "ALL REG DONE"
