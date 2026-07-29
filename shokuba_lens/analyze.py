"""shokuba-lens: 職場写真をローカルAIで点検し、改善提案レポートを生成する。

カメラ/スマホの写真 → ローカルVLM（状況記述） → ローカルLLM（業務ルール照合）
→ Markdownレポート + JSON。すべて手元のマシンで完結し、画像は外部に送信しない。

Usage:
    python -m shokuba_lens.analyze --images office1.jpg office2.jpg \
        --rules rules/5s_office.yaml --out out/
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import yaml

DEFAULT_VLM = "tokimoa/llm-jp-4-vl-9b-beta-mlx-4bit"
DEFAULT_LLM = "Qwen/Qwen3-4B"

OBSERVE_PROMPT = (
    "この画像は職場の様子です。安全点検の下調べとして、画像に写っているものと"
    "状況を、位置関係（何がどこにあるか・何の前に何があるか）を含めて"
    "箇条書きで具体的に記述してください。通路や設備の上・前に物がある場合は、"
    "その位置関係を明記してください。推測や評価は書かず、見えている事実のみを書いてください。"
)

JUDGE_PROMPT = """あなたは職場の安全・整理整頓（5S）の点検担当です。
以下の「観察記録」を「点検ルール」と照合し、ルールごとに判定してください。

# 点検ルール
{rules}

# 観察記録
{observations}

# 出力形式
次のJSON配列のみを出力してください（説明文は不要）:
[{{"rule_id": "ルールID", "judgement": "違反疑い|問題なし|判定不能",
   "evidence": "観察記録内の根拠（判定不能なら空文字）",
   "suggestion": "違反疑いの場合の具体的な改善提案（それ以外は空文字）"}}]

観察記録に関連する記述がないルールは「判定不能」としてください。根拠のない推測で「違反疑い」にしないでください。
ルールに数値基準（段数・距離など）がある場合は厳密に適用し、基準の範囲内であれば「問題なし」としてください。"""


def observe(image_path, vlm_model, max_tokens=600):
    from mlx_vlm import generate, load
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config

    model, processor = load(vlm_model, trust_remote_code=True)
    config = load_config(vlm_model, trust_remote_code=True)
    prompt = apply_chat_template(processor, config, OBSERVE_PROMPT, num_images=1)
    out = generate(model, processor, prompt, image=[str(image_path)],
                   max_tokens=max_tokens, temperature=0.0, repetition_penalty=1.1, verbose=False)
    text = out.text if hasattr(out, "text") else str(out)
    text = re.sub(r"<\|[a-z_]+\|>", " ", text)  # チャットテンプレートの残渣を除去
    del model
    import gc

    gc.collect()
    return text.strip()


def judge(observations, rules, llm_model, max_tokens=1200):
    from mlx_lm import load
    from mlx_lm.generate import generate
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(llm_model)
    rules_text = "\n".join(
        f"- {r['id']}（{r['name']}・重大度{r['severity']}）: {r['description']}" for r in rules
    )
    prompt = JUDGE_PROMPT.format(rules=rules_text, observations=observations)
    msgs = [{"role": "user", "content": prompt}]
    p = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                      enable_thinking=False)
    out = generate(model, tokenizer, prompt=p, max_tokens=max_tokens,
                   sampler=make_sampler(temp=0.0))
    m = re.search(r"\[.*\]", out, re.DOTALL)
    if not m:
        raise ValueError(f"判定のJSONが取得できませんでした: {out[:200]}")
    return json.loads(m.group(0))


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEV_MARK = {"critical": "🟥", "high": "🟧", "medium": "🟨", "low": "⬜"}


def render_markdown(results, rules_by_id, domain):
    lines = [f"# 職場点検レポート（{domain}）",
             f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')} / shokuba-lens（ローカルAI・画像は外部送信なし）", ""]
    for img_name, verdicts in results.items():
        lines.append(f"## 📷 {img_name}")
        flagged = [v for v in verdicts if v["judgement"] == "違反疑い"]
        flagged.sort(key=lambda v: SEV_ORDER.get(rules_by_id[v["rule_id"]]["severity"], 9))
        if not flagged:
            lines.append("指摘事項はありませんでした。")
        for v in flagged:
            r = rules_by_id[v["rule_id"]]
            lines += [f"### {SEV_MARK[r['severity']]} {r['name']}（{r['severity']}）",
                      f"- 根拠: {v['evidence']}",
                      f"- 提案: {v['suggestion']}", ""]
        undetermined = [rules_by_id[v["rule_id"]]["name"] for v in verdicts if v["judgement"] == "判定不能"]
        if undetermined:
            lines.append(f"（判定不能: {'、'.join(undetermined)} — 撮影範囲外の可能性）")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="職場写真のローカルAI点検")
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--rules", default="rules/5s_office.yaml")
    ap.add_argument("--vlm-model", default=DEFAULT_VLM)
    ap.add_argument("--llm-model", default=DEFAULT_LLM)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    ruleset = yaml.safe_load(open(args.rules))
    rules = ruleset["rules"]
    rules_by_id = {r["id"]: r for r in rules}
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    results = {}
    for img in args.images:
        name = Path(img).name
        print(f"[観察] {name} ...", flush=True)
        obs = observe(img, args.vlm_model)
        print(f"[照合] {name} ...", flush=True)
        verdicts = judge(obs, rules, args.llm_model)
        results[name] = verdicts
        (outdir / f"{Path(img).stem}_observations.txt").write_text(obs)

    md = render_markdown(results, rules_by_id, ruleset.get("domain", ""))
    (outdir / "report.md").write_text(md)
    (outdir / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"レポート出力: {outdir}/report.md / report.json")


if __name__ == "__main__":
    main()
