# shokuba-lens 🔍

職場の写真をローカルAIで点検し、改善提案レポートを生成するリファレンス実装です。

```
カメラ/スマホの写真・動画 → ローカルVLM（状況を観察） → ローカルLLM（ルール毎に照合＋検証）
→ Markdownレポート + JSON（指摘・根拠・改善提案。動画は検出時刻つき）
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

# 動画の点検（ffmpegが必要。既定は2秒に1フレームを抽出し、ルール毎に検出時刻を集約）
python -m shokuba_lens.video \
  --video walkthrough.mp4 --rules rules/5s_office.yaml --fps 0.5 --out out_video/
```

既定モデルはVLM=[llm-jp-4-vl-9b-beta-mlx-4bit](https://huggingface.co/tokimoa/llm-jp-4-vl-9b-beta-mlx-4bit)（国産VLM・約6GB）、判定LLM=Qwen3-8B（4bit・約4.6GB）です。観察が終わるとVLMを解放してから判定に入るため、ピークメモリは観察フェーズの約6GBのままです。`--vlm-model` / `--llm-model`でmlx-vlm/mlx-lm対応の任意のモデルに差し替えられます。

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

GT既知の模式図テスト（4ドメイン×違反版/クリーン版の8枚・仕込んだ違反12件）では、検出10〜12/12・誤検知0〜4件の範囲で判定構成により揺れます（判定=Qwen3-14Bで11/12・誤検知0が最も安定。残る見逃しはVLM観察の言い回し曖昧性に起因）。`samples/`に再現手順を同梱しているので、モデルを差し替えて再実測できます。判定不能（撮影範囲外）も無理に判定せず明示します。

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

数値基準（「3段まで」「高さ1.5m以内」等）をdescriptionに書けば、判定時に厳密に適用されます。同梱ルールセットは5種です:

| ファイル | ドメイン |
|---|---|
| `rules/5s_office.yaml` | オフィス5S |
| `rules/5s_warehouse.yaml` | 倉庫 |
| `rules/kitchen_hygiene.yaml` | 厨房・食品衛生 |
| `rules/construction_ppe.yaml` | 建設現場（ヘルメット・開口部・資材） |
| `rules/clear_desk.yaml` | 情報セキュリティ（クリアデスク・クリアスクリーン） |

書き方のコツ（開発時の実測より）: 違反条件を文の先頭に書いてください。「Aを放置しない（Bは施錠保管）」のように禁止事項を先に置くと、複数条件ルールの判定が安定します。

## 実写ベンチマーク

実写での精度は公開データセットで実測しています。ヘルメット検査（未着用者がいる画像の指摘）の画像単位評価です。チェックポイント選択用の検証データと最終評価データは分離しています。

| 評価データ | 構成 | precision | recall | F1 |
|---|---|---|---|---|
| [SHEL5K](https://data.mendeley.com/datasets/9rcv8mm682/4) テスト400枚 | **[shokuba-probe-2b](https://huggingface.co/tokimoa/shokuba-probe-2b)**（probe） | **0.938** | **0.755** | **0.837** |
| 〃 | ベースQwen3-VL-2B（未チューニング） | 0.589 | 0.465 | 0.520 |
| 〃 | 汎用VLM（llm-jp-4-vl 9B）probe | 0.57前後 | 0.95前後 | 0.72前後 |
| Construction Site Safety 144枚（学習と別データセット） | shokuba-probe-2b | 0.684 | 0.629 | 0.655 |

- 汎用VLMは「見逃さないが数え過ぎる」（クリーン画像でも未着用と誤報告しがち）、shokuba-probe-2bは点検データでの学習によりバランス型です
- 別データセットでは精度が下がります（分布依存）。汎化は継続学習で強化していく予定で、モデルは同名のまま更新します
- 再現手順は `bench/` に同梱（`bench/shel5k.py`）。モデル差し替えで再実測できます

## ルール連動の追加確認（probe）

自由記述の観察は「未着用」「放置」のような不在の事実を書き落とします。ルールYAMLに `probe:` を書くと、観察後にVLMへ直接質問し、回答を観察記録に追記します:

```yaml
- id: helmet_required
  name: ヘルメット着用
  description: 作業エリア内の作業者は全員ヘルメット（保護帽）を着用する
  severity: critical
  probe: この画像に写っている人を数えてください。全体の人数、ヘルメットを着用している人数、していない人数を「人数:N人、着用:N人、未着用:N人」の形式で答えてください。
```

probeの書き方も実測で効果が分かれます: 数えさせる形式が最も見逃しに強く、「確認できない場合はそう答えて」と逃げ道を与えると大半が「確認できない」に流れ、位置の特定まで求めると「全員着用」に振れます。

## 設計メモ

- **観察と判定の2段分離**: VLMには「見えている事実の記述」だけをさせ、ルール照合と判定は別のLLMが行います。VLMに直接判定させるより、根拠の追跡と誤判定の抑制がしやすい構成です
- **ルール毎の個別判定**: 全ルールを1コールで判定させると、別ルールの根拠の取り違え・条件の無視・自己矛盾（根拠は適合を示すのに違反判定）が起きます。1コール1ルールに分離すると、この種のコンテキスト干渉が構造的に起きません
- **違反疑いの敵対的検証**: 「違反疑い」フラグにのみ検証コールを追加し、①適合を示す根拠からの違反判定②「記述がない」ことを根拠にした違反判定、の2大誤検知パターンを棄却します（棄却されたものは判定不能に降格し、`verify_note`に理由が残ります）
- **判定の規律**: 観察に記述がないルールは「判定不能」とし、根拠のない推測で違反にしません。数値基準は厳密適用します。判定書式はevidence→reason→judgementの順で、結論を最後に書かせます
- **動画の時間集約**: フレーム毎の判定をルール単位に集約し、1フレームでも違反疑いがあれば検出時刻つきで報告します。GT既知テスト動画（前半クリーン・後半違反3件）で、検出時刻が後半のみに正しく局在することを確認済みです
- **プロンプトの落とし穴（開発時の実測より）**: 観察プロンプトへルール一覧を注入したところ、VLMが同一行を繰り返す縮退ループに陥りました。観察指示はシンプルに保ち、位置関係と保護設備の有無だけ促すのが安定です
- **検証器の落とし穴（開発時の実測より）**: 検証をevidence欄だけで行うと、判定の決め手が追加確認の回答にある場合に正しい指摘まで棄却します（SHEL5K実測でrecall 0.9→0.2まで落ちた原因）。検証はevidenceとreasonを合わせて評価させています

## 関連

- 議事録の一気通貫: [jp-jitsumu-whisper](https://huggingface.co/tokimoa/jp-jitsumu-whisper-ggml)（音声認識）+ [jp-minutes-extractor](https://huggingface.co/tokimoa/jp-minutes-extractor-1.7b-GGUF)
- 帳票読取: [jp-invoice-reader-2b](https://huggingface.co/tokimoa/jp-invoice-reader-2b)
- 検証済みMLX変換モデル: [huggingface.co/tokimoa](https://huggingface.co/tokimoa)

## License

Apache-2.0

---
Developed by [tokimoa](https://tokimoa.jp) — データを外に出さないAI活用を支援しています
