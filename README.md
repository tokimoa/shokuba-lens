# shokuba-lens 🔍

職場の写真をローカルAIで点検し、改善提案レポートを生成するリファレンス実装です。

```
カメラ/スマホの写真 → ローカルVLM（状況を観察） → ローカルLLM（業務ルールと照合）
→ Markdownレポート + JSON（指摘・根拠・改善提案）
```

すべて手元のマシンで完結し、**画像は外部に送信しません**。大規模GPUも不要で、Apple Silicon Mac（16GB以上推奨）で動作します。安全・整理整頓（5S）チェックを題材にしていますが、ルールはYAMLで自由に差し替えられます。

## 使い方

```bash
git clone https://github.com/tokimoa/shokuba-lens
cd shokuba-lens
pip install -r requirements.txt   # mlx-vlm>=0.6.8 / mlx-lm / pyyaml / pillow

python -m shokuba_lens.analyze \
  --images office1.jpg office2.jpg \
  --rules rules/5s_office.yaml \
  --out out/
# → out/report.md（人が読む用） / out/report.json（システム連携用）
```

既定モデルはVLM=[llm-jp-4-vl-9b-beta-mlx-4bit](https://huggingface.co/tokimoa/llm-jp-4-vl-9b-beta-mlx-4bit)（国産VLM・約6GB）、判定LLM=Qwen3-4Bです。`--vlm-model` / `--llm-model`でmlx-vlm/mlx-lm対応の任意のモデルに差し替えられます。

## 出力例（実出力）

正解既知のテストシーン（違反3件を意図的に配置した平面図。`samples/make_test_scene.py`で生成）に対する実際の出力です。

> ### 🟥 消防設備前の空間確保（critical）
> - 根拠: 消火器の前には青い椅子が置かれている。
> - 提案: 消火器の前には物を置かないよう、椅子を移動させ、消火器の前を確保してください。
>
> ### 🟧 通路の確保（high）
> - 根拠: 机の正面に通路が通っており、その奥には段ボール箱が置かれている。
> - 提案: 段ボール箱を移動させ、通路を確保してください。
>
> ### 🟧 ケーブルの安全（high）
> - 根拠: 床を横切る電源ケーブルがあり、その上部にはカバーが設置されていない。
> - 提案: 床を横切る電源ケーブルは保護カバーで覆うか床下・壁沿いに配線してください。

このテストでは仕込んだ違反3件をすべて指摘し、ルール適合の項目（書類の2段積み=基準3段以内）を正しく「問題なし」とし、違反のないクリーン版シーンでは指摘ゼロでした。判定不能（撮影範囲外）も無理に判定せず明示します。

## ルールのカスタマイズ

`rules/*.yaml`に自社のルールを書くだけです。

```yaml
domain: オフィス
rules:
  - id: aisle_clear
    name: 通路の確保
    description: 通路・動線上に箱、荷物、椅子などの障害物を置かない
    severity: high   # critical / high / medium / low
```

数値基準（「3段まで」等）をdescriptionに書けば、判定時に厳密に適用されます。`rules/5s_warehouse.yaml`に倉庫版のサンプルもあります。

## 設計メモ

- **観察と判定の2段分離**: VLMには「見えている事実の記述」だけをさせ、ルール照合と判定は別のLLMが行います。VLMに直接判定させるより、根拠の追跡と誤判定の抑制がしやすい構成です
- **判定の規律**: 観察に記述がないルールは「判定不能」とし、根拠のない推測で違反にしません。数値基準は厳密適用します
- **プロンプトの落とし穴（開発時の実測より）**: 観察プロンプトへルール一覧を注入したところ、VLMが同一行を繰り返す縮退ループに陥りました。観察指示はシンプルに保ち、位置関係の明記だけ促すのが安定です

## 関連

- 議事録の一気通貫: [jp-jitsumu-whisper](https://huggingface.co/tokimoa/jp-jitsumu-whisper-ggml)（音声認識）+ [jp-minutes-extractor](https://huggingface.co/tokimoa/jp-minutes-extractor-1.7b-GGUF)
- 帳票読取: [jp-invoice-reader-2b](https://huggingface.co/tokimoa/jp-invoice-reader-2b)
- 検証済みMLX変換モデル: [huggingface.co/tokimoa](https://huggingface.co/tokimoa)

## License

Apache-2.0

---
Developed by [tokimoa](https://tokimoa.jp) — データを外に出さないAI活用を支援しています
