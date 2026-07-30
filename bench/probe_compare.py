"""probe単体のVLM比較: 「未着用者がいるか」をVLM別に直接測る（視覚弁別のボトルネック切り分け用）。

Usage: python -m bench.probe_compare --dataset <dir> --sample eval_sample.json \
           --models tokimoa/llm-jp-4-vl-9b-beta-mlx-4bit mlx-community/Qwen2.5-VL-7B-Instruct-4bit
"""
import argparse
import json
import re
from pathlib import Path

from shokuba_lens.analyze import probe, unload_vlm

Q = ("この画像に写っている人を数えてください。全体の人数、そのうちヘルメット（保護帽）を"
     "着用している人数、着用していない人数を「人数:N人、着用:N人、未着用:N人」の形式で答えてください。")


def pred_from_answer(ans):
    m = re.search(r"未着用[:：]\s*(\d+)", ans)
    if m:
        return 1 if int(m.group(1)) > 0 else 0
    return 1 if re.search(r"着用していない人が(いる|\d+人)", ans) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default="bench_out_probe")
    args = ap.parse_args()

    sample = json.load(open(args.sample))
    imgdir = Path(args.dataset) / "Images"
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    for model in args.models:
        tag = model.split("/")[-1]
        cache_p = outdir / f"probe_{tag}.json"
        cache = json.load(open(cache_p)) if cache_p.exists() else {}
        for i, (stem, gt) in enumerate(sample):
            if stem in cache:
                continue
            print(f"[{tag} {i+1}/{len(sample)}] {stem}", flush=True)
            cache[stem] = probe(imgdir / f"{stem}.png", Q, model)
            json.dump(cache, open(cache_p, "w"), ensure_ascii=False)
        unload_vlm()
        tp = fp = fn = tn = 0
        for stem, gt in sample:
            p = pred_from_answer(cache[stem])
            if p and gt: tp += 1
            elif p and not gt: fp += 1
            elif not p and gt: fn += 1
            else: tn += 1
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        print(json.dumps({"model": model, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                          "precision": round(prec, 3), "recall": round(rec, 3)},
                         ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
