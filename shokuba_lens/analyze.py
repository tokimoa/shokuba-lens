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
DEFAULT_LLM = "mlx-community/Qwen3-8B-4bit"

OBSERVE_PROMPT = (
    "この画像は職場の様子です。安全点検の下調べとして、画像に写っているものと"
    "状況を、位置関係（何がどこにあるか・何の前に何があるか）を含めて"
    "箇条書きで具体的に記述してください。通路や設備の上・前に物がある場合は、"
    "その位置関係を明記してください。危険箇所（開口部・火気・配線など）は、"
    "柵・カバーなどの保護設備が見えるかどうかも書いてください。"
    "人が写っている場合は、一人ずつヘルメット・保護具を着用しているかどうかを明記してください。"
    "推測や評価は書かず、見えている事実のみを書いてください。"
)

JUDGE_PROMPT = """あなたは職場の安全・整理整頓の点検担当です。
以下の「観察記録」を、次の1つの点検ルールと照合して判定してください。

# 点検ルール
{rule}

# 観察記録
{observations}

# 出力形式
次のJSONオブジェクトのみを出力してください（説明文は不要。キーはこの順で）:
{{"evidence": "観察記録から引用した、判定の決め手となる記述（「追加確認」の回答も含む。なければ空文字)",
  "reason": "evidenceがルールに違反しているかどうかの短い理由づけ",
  "judgement": "違反疑い|問題なし|判定不能",
  "suggestion": "違反疑いの場合の具体的な改善提案（それ以外は空文字）"}}

判定の規律:
- evidenceは観察記録に実際に書かれている記述の引用に限ります
- 観察記録にこのルールに関係する記述がなければ「判定不能」です。根拠のない推測で「違反疑い」にしないでください
- 設備や対策の記述が観察記録にないことは「存在しない」ことの証拠にはなりません（その場合は「判定不能」）
- ルールに複数の条件がある場合、どれか1つに違反する記述があれば「違反疑い」です
- ルールに数値基準（段数・高さなど）がある場合は厳密に適用し、基準の範囲内なら「問題なし」です
- judgementはreasonの結論と一致させてください"""


_VLM_CACHE = {}
_LLM_CACHE = {}


def load_vlm(vlm_model):
    """VLMを一度だけロードして使い回す（複数画像・動画フレームの連続処理用）。"""
    if vlm_model not in _VLM_CACHE:
        from mlx_vlm import load
        from mlx_vlm.utils import load_config

        model, processor = load(vlm_model, trust_remote_code=True)
        config = load_config(vlm_model, trust_remote_code=True)
        _VLM_CACHE[vlm_model] = (model, processor, config)
    return _VLM_CACHE[vlm_model]


def unload_vlm():
    """判定フェーズ前にVLMを解放してメモリを空ける。"""
    import gc

    _VLM_CACHE.clear()
    gc.collect()


def load_llm(llm_model):
    if llm_model not in _LLM_CACHE:
        from mlx_lm import load

        _LLM_CACHE[llm_model] = load(llm_model)
    return _LLM_CACHE[llm_model]


def _vlm_generate(image_path, prompt_text, vlm_model, max_tokens):
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template

    model, processor, config = load_vlm(vlm_model)
    prompt = apply_chat_template(processor, config, prompt_text, num_images=1)
    out = generate(model, processor, prompt, image=[str(image_path)],
                   max_tokens=max_tokens, temperature=0.0, repetition_penalty=1.1, verbose=False)
    text = out.text if hasattr(out, "text") else str(out)
    text = re.sub(r"<\|[a-z_]+\|>", " ", text)  # チャットテンプレートの残渣を除去
    return text.strip()


def observe(image_path, vlm_model, max_tokens=600):
    return _vlm_generate(image_path, OBSERVE_PROMPT, vlm_model, max_tokens)


def probe(image_path, question, vlm_model, max_tokens=200):
    """ルール連動の追加質問。自由記述の観察は不在事実（未着用など）を書き落とすため、
    直接質問で確認する。回答は観察記録に「追加確認」として追記され、判定の入力になる。"""
    prompt = (f"この画像について、見えている事実のみに基づいて次の質問に簡潔に答えてください。\n"
              f"質問: {question}")
    return _vlm_generate(image_path, prompt, vlm_model, max_tokens)


def observe_with_probes(image_path, rules, vlm_model):
    """観察+ルール毎の追加質問をまとめた観察記録を返す。"""
    text = observe(image_path, vlm_model)
    for r in rules:
        if r.get("probe"):
            ans = probe(image_path, r["probe"], vlm_model)
            text += f"\n\n追加確認（{r['name']}）: {r['probe']} → {ans}"
    return text


VERIFY_PROMPT = """次の点検判定が正しいかを検証してください。

# 点検ルール
{rule}

# 判定（違反疑い）
- 根拠(evidence): {evidence}
- 理由(reason): {reason}

# 検証の観点
1. evidenceとreasonを合わせて見たとき、ルール違反の状態（未着用・放置・カバーなし等）を示す観察記述に基づいていますか？
2. 適合を示す記述（「カバー付き」「着用している」「施錠済み」など）だけを根拠に違反としていませんか？
3. 「記述がない・見つからない」ことだけを根拠にしていませんか？（不在の記述は違反の証拠になりません）

# 出力形式（JSONのみ）
{{"verdict": "支持|棄却", "why": "1文の理由"}}"""


def judge(observations, rules, llm_model, max_tokens=800):
    """ルール毎に個別のLLMコールで判定し、「違反疑い」のみ検証コールで敵対的に再確認する。

    ルール毎の個別判定は複数ルール同時照合のコンテキスト干渉（別ルールの根拠取り違え・
    条件無視・自己矛盾）を構造的に排除する。検証コールは「適合を示す根拠からの違反判定」
    「不在の記述を根拠にした違反判定」の2大誤検知パターンを棄却する。
    """
    from mlx_lm.generate import generate
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load_llm(llm_model)

    def ask(prompt, max_tok):
        msgs = [{"role": "user", "content": prompt}]
        p = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                          enable_thinking=False)
        out = generate(model, tokenizer, prompt=p, max_tokens=max_tok,
                       sampler=make_sampler(temp=0.0))
        m = re.search(r"\{.*\}", out, re.DOTALL)
        if not m:
            raise ValueError(f"判定のJSONが取得できませんでした: {out[:200]}")
        return json.loads(m.group(0))

    verdicts = []
    for r in rules:
        rule_text = f"{r['id']}（{r['name']}・重大度{r['severity']}）: {r['description']}"
        v = ask(JUDGE_PROMPT.format(rule=rule_text, observations=observations), max_tokens)
        v["rule_id"] = r["id"]
        if v.get("judgement") == "違反疑い":
            check = ask(VERIFY_PROMPT.format(rule=rule_text,
                                             evidence=v.get("evidence", ""),
                                             reason=v.get("reason", "")), 200)
            if check.get("verdict") != "支持":
                v["judgement"] = "判定不能"
                v["suggestion"] = ""
                v["verify_note"] = check.get("why", "")
        verdicts.append(v)
    return verdicts


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


def load_rules(path):
    ruleset = yaml.safe_load(open(path))
    rules = ruleset["rules"]
    return ruleset, rules, {r["id"]: r for r in rules}


def main():
    ap = argparse.ArgumentParser(description="職場写真のローカルAI点検")
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--rules", default="rules/5s_office.yaml")
    ap.add_argument("--vlm-model", default=DEFAULT_VLM)
    ap.add_argument("--llm-model", default=DEFAULT_LLM)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    ruleset, rules, rules_by_id = load_rules(args.rules)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # 観察→判定の順にフェーズをまとめ、モデルロードを各1回にする
    observations = {}
    for img in args.images:
        name = Path(img).name
        print(f"[観察] {name} ...", flush=True)
        observations[name] = observe_with_probes(img, rules, args.vlm_model)
        (outdir / f"{Path(img).stem}_observations.txt").write_text(observations[name])
    unload_vlm()

    results = {}
    for name, obs in observations.items():
        print(f"[照合] {name} ...", flush=True)
        results[name] = judge(obs, rules, args.llm_model)

    md = render_markdown(results, rules_by_id, ruleset.get("domain", ""))
    (outdir / "report.md").write_text(md)
    (outdir / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"レポート出力: {outdir}/report.md / report.json")


if __name__ == "__main__":
    main()
