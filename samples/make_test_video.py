"""GT既知のテスト動画生成: 前半=クリーンなオフィス・後半=違反ありオフィス。

巡回撮影を模して、既存のGT既知シーン2枚を時間方向に並べたmp4を作る。
GT: 前半（0:00-0:05）は全ルール適合、後半（0:06-0:11）で
aisle_clear / fire_equipment_access / cable_management の3違反が映る。
動画パイプラインの時間集約（検出時刻が後半に出ること）を検証できる。

Usage: python samples/make_test_video.py  → samples/office_walkthrough.mp4
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent


def main():
    clean = HERE / "office_clean.png"
    viol = HERE / "office_violations.png"
    out = HERE / "office_walkthrough.mp4"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i in range(12):  # 1fps×12秒: 前半6枚=クリーン・後半6枚=違反
            src = clean if i < 6 else viol
            shutil.copy(src, td / f"frame_{i:04d}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1",
             "-i", str(td / "frame_%04d.png"), "-pix_fmt", "yuv420p", str(out)],
            check=True)
    print(f"saved {out}  GT: 0:00-0:05 クリーン / 0:06-0:11 違反3件")


if __name__ == "__main__":
    main()
