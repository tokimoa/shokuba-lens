"""shokuba-lens 動画対応: 動画からフレームを抽出し、フレーム毎の観察→時間集約の判定を行う。

動画 → ffmpegでフレーム抽出（既定0.5fps=2秒に1枚） → 各フレームをローカルVLMで観察
→ ローカルLLMがルール照合（フレーム毎） → ルール単位に時間集約したレポート

集約規則:
- いずれかのフレームで「違反疑い」 → 違反疑い（検出時刻を列挙）
- 違反疑いがなく、いずれかで「問題なし」 → 問題なし
- 全フレーム「判定不能」 → 判定不能（映っていない）

Usage:
    python -m shokuba_lens.video --video walkthrough.mp4 \
        --rules rules/5s_office.yaml --fps 0.5 --out out_video/
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .analyze import (DEFAULT_LLM, DEFAULT_VLM, SEV_MARK, SEV_ORDER, judge,
                      load_rules, observe, observe_with_probes, unload_vlm)


def extract_frames(video, outdir, fps, max_frames):
    """ffmpegでフレームをPNG抽出し、[(時刻秒, パス)]を返す。"""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpegが見つかりません。`brew install ffmpeg` 等で導入してください。")
    outdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", f"fps={fps}", "-frames:v", str(max_frames),
         str(outdir / "frame_%04d.png")],
        check=True)
    frames = sorted(outdir.glob("frame_*.png"))
    return [(round((i / fps), 1), p) for i, p in enumerate(frames)]


def fmt_time(sec):
    return f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"


def aggregate(per_frame, rules):
    """フレーム毎の判定をルール単位に集約する。"""
    agg = {}
    for r in rules:
        rid = r["id"]
        hits = []
        any_ok = False
        for t, verdicts in per_frame:
            for v in verdicts:
                if v["rule_id"] != rid:
                    continue
                if v["judgement"] == "違反疑い":
                    hits.append((t, v))
                elif v["judgement"] == "問題なし":
                    any_ok = True
        if hits:
            agg[rid] = {"judgement": "違反疑い", "hits": hits}
        elif any_ok:
            agg[rid] = {"judgement": "問題なし", "hits": []}
        else:
            agg[rid] = {"judgement": "判定不能", "hits": []}
    return agg


def render_video_markdown(agg, rules_by_id, domain, video_name, n_frames, fps):
    lines = [f"# 職場点検レポート（{domain}・動画）",
             f"対象: {video_name}（{n_frames}フレームを{fps}fpsで点検） / "
             f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')} / shokuba-lens（ローカルAI・映像は外部送信なし）", ""]
    flagged = [(rid, a) for rid, a in agg.items() if a["judgement"] == "違反疑い"]
    flagged.sort(key=lambda x: SEV_ORDER.get(rules_by_id[x[0]]["severity"], 9))
    if not flagged:
        lines.append("指摘事項はありませんでした。")
    for rid, a in flagged:
        r = rules_by_id[rid]
        times = "、".join(fmt_time(t) for t, _ in a["hits"])
        first = a["hits"][0][1]
        lines += [f"### {SEV_MARK[r['severity']]} {r['name']}（{r['severity']}）",
                  f"- 検出時刻: {times}",
                  f"- 根拠: {first['evidence']}",
                  f"- 提案: {first['suggestion']}", ""]
    ok = [rules_by_id[rid]["name"] for rid, a in agg.items() if a["judgement"] == "問題なし"]
    und = [rules_by_id[rid]["name"] for rid, a in agg.items() if a["judgement"] == "判定不能"]
    if ok:
        lines.append(f"問題なし: {'、'.join(ok)}")
    if und:
        lines.append(f"（判定不能: {'、'.join(und)} — 映像に映っていない可能性）")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="職場動画のローカルAI点検")
    ap.add_argument("--video", required=True)
    ap.add_argument("--rules", default="rules/5s_office.yaml")
    ap.add_argument("--fps", type=float, default=0.5, help="点検するフレームの抽出レート（既定: 2秒に1枚）")
    ap.add_argument("--max-frames", type=int, default=30)
    ap.add_argument("--vlm-model", default=DEFAULT_VLM)
    ap.add_argument("--llm-model", default=DEFAULT_LLM)
    ap.add_argument("--probe-model", default=None,
                    help="追加確認（probe）専用のVLM。静止画のanalyzeと同じく、"
                         "ルールのprobe質問をフレーム毎に投げて判定の入力に加える")
    ap.add_argument("--out", default="out_video")
    args = ap.parse_args()

    ruleset, rules, rules_by_id = load_rules(args.rules)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(args.video, Path(td), args.fps, args.max_frames)
        print(f"フレーム抽出: {len(frames)}枚（{args.fps}fps）", flush=True)

        observations = []
        for t, p in frames:
            print(f"[観察 {fmt_time(t)}] ...", flush=True)
            if args.probe_model:
                obs = observe_with_probes(p, rules, args.vlm_model, args.probe_model)
            else:
                obs = observe(p, args.vlm_model)
            observations.append((t, obs))
        unload_vlm()

    per_frame = []
    for t, obs in observations:
        print(f"[照合 {fmt_time(t)}] ...", flush=True)
        per_frame.append((t, judge(obs, rules, args.llm_model)))

    agg = aggregate(per_frame, rules)
    md = render_video_markdown(agg, rules_by_id, ruleset.get("domain", ""),
                               Path(args.video).name, len(per_frame), args.fps)
    (outdir / "report.md").write_text(md)
    (outdir / "report.json").write_text(json.dumps(
        {"aggregated": {k: {"judgement": v["judgement"],
                            "hits": [{"time": t, **h} for t, h in v["hits"]]}
                        for k, v in agg.items()},
         "per_frame": [{"time": t, "verdicts": v} for t, v in per_frame]},
        ensure_ascii=False, indent=1))
    print(f"レポート出力: {outdir}/report.md / report.json")


if __name__ == "__main__":
    main()
