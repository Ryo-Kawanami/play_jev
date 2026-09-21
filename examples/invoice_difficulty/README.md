# 請求書の難易度スコア評価

合成した日本語請求書を難易度1〜5に分け、Jev と `gpt-4o-mini` が文書の処理難易度を正しく順位付けできるか比較します。

## 実行

```bash
uv run python examples/invoice_difficulty/run.py
```

デフォルトでは各難易度20件、合計100件を生成します。結果は次に保存されます。

- `examples/invoice_difficulty/data/dataset.jsonl`
- `examples/invoice_difficulty/out/jev_results.jsonl`
- `examples/invoice_difficulty/out/llm_results.jsonl`
- `examples/invoice_difficulty/out/metrics.json`
- `docs/invoice-difficulty-results.md`

低コストでデータ生成だけ確認する場合:

```bash
uv run python examples/invoice_difficulty/run.py --per-level 2 --generate-only
```

Jevだけの評価:

```bash
uv run python examples/invoice_difficulty/run.py --skip-llm
```

難易度の正解値は、明細数、外貨、例外、矛盾など生成時に注入した難化要因から決めたルールスコアです。実運用の請求書性能を示すものではありません。
