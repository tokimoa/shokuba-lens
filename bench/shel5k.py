"""SHEL5K（CC BY 4.0）によるヘルメット違反検出の画像単位ベンチマーク。

SHEL5Kのボックスラベル（head / person_no_helmet = 未着用者あり）から
画像単位GT「ヘルメット未着用者がいるか」を導出し、shokuba-lensの
observe→judge（helmet_requiredルールのみ）の指摘と突き合わせる。

Usage:
    python -m bench.shel5k --dataset ".../Safety Helmet Wearing Dataset" \
        --sample eval_sample.json --out bench_out/
sampleは [(画像stem, gt(0/1)), ...] のJSON。
"""
import argparse
import json
from pathlib import Path

import yaml

from shokuba_lens.analyze import judge, observe, probe, unload_vlm, DEFAULT_LLM, DEFAULT_VLM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--rules", default="rules/construction_ppe.yaml")
    ap.add_argument("--rule-id", default="helmet_required")
    ap.add_argument("--vlm-model", default=DEFAULT_VLM)
    ap.add_argument("--llm-model", default=DEFAULT_LLM)
    ap.add_argument("--out", default="bench_out")
    args = ap.parse_args()

    sample = json.load(open(args.sample))
    rules = [r for r in yaml.safe_load(open(args.rules))["rules"] if r["id"] == args.rule_id]
    assert rules, f"rule {args.rule_id} not found"
    imgdir = Path(args.dataset) / "Images"
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    obs_cache = outdir / "observations.json"
    obs = json.load(open(obs_cache)) if obs_cache.exists() else {}
    for i, (stem, gt) in enumerate(sample):
        if stem in obs:
            continue
        print(f"[観察 {i+1}/{len(sample)}] {stem}", flush=True)
        obs[stem] = observe(imgdir / f"{stem}.png", args.vlm_model)
        json.dump(obs, open(obs_cache, "w"), ensure_ascii=False)

    probe_cache = outdir / "probes.json"
    probes = json.load(open(probe_cache)) if probe_cache.exists() else {}
    rule = rules[0]
    if rule.get("probe"):
        for i, (stem, gt) in enumerate(sample):
            if stem in probes:
                continue
            print(f"[追加確認 {i+1}/{len(sample)}] {stem}", flush=True)
            probes[stem] = probe(imgdir / f"{stem}.png", rule["probe"], args.vlm_model)
            json.dump(probes, open(probe_cache, "w"), ensure_ascii=False)
    unload_vlm()
    for stem in list(obs):
        if stem in probes:
            obs[stem] = obs[stem] + f"\n\n追加確認（{rule['name']}）: {rule['probe']} → {probes[stem]}"

    results = []
    tp = fp = fn = tn = 0
    for i, (stem, gt) in enumerate(sample):
        print(f"[照合 {i+1}/{len(sample)}] {stem}", flush=True)
        try:
            v = judge(obs[stem], rules, args.llm_model)[0]
        except ValueError as e:
            print(f"  判定失敗（判定不能扱い）: {e}", flush=True)
            v = {"judgement": "判定不能", "evidence": "", "reason": "judge-error"}
        pred = 1 if v["judgement"] == "違反疑い" else 0
        if pred and gt:
            tp += 1
        elif pred and not gt:
            fp += 1
        elif not pred and gt:
            fn += 1
        else:
            tn += 1
        results.append({"image": stem, "gt": gt, "pred": pred,
                        "judgement": v["judgement"], "evidence": v.get("evidence", ""),
                        "reason": v.get("reason", ""), "verify_note": v.get("verify_note", ""),
                        "observation": obs[stem]})

    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    acc = (tp + tn) / len(sample)
    summary = {"n": len(sample), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
               "precision": round(prec, 3), "recall": round(rec, 3), "accuracy": round(acc, 3),
               "vlm": args.vlm_model, "llm": args.llm_model}
    print(json.dumps(summary, ensure_ascii=False))
    json.dump({"summary": summary, "results": results},
              open(outdir / "shel5k_results.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
