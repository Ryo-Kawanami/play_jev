# play_jev

TypeSafe の Jev を試すための最小サンプルです。

## セットアップ

```bash
cp .env.example .env
# .env に TYPESAFE_API_KEY を設定
uv sync
```

## 最小サンプル

```bash
uv run python jev_example.py
```

## スパム判定の評価実験

迷惑メールと正常メールを同数生成し、Jev と安価な `gpt-4o-mini` の判定を同じ正解ラベルと比較します。デフォルトは各100件です。

```bash
uv run python examples/spam_eval/run.py
```

精度、混同行列、平均・中央値・P95レイテンシー、スループットを表示し、結果を `docs/spam-eval-results.md` に保存します。API利用量を抑える場合は `--count 10` を指定してください。Jev だけの場合は `--skip-llm` を指定します。

詳細は [examples/spam_eval/README.md](examples/spam_eval/README.md) を参照してください。

## 請求書の難易度評価

複雑な合成請求書を難易度1〜5で採点し、Jev と `gpt-4o-mini` のスコア誤差・順位相関・速度を比較します。

```bash
uv run python examples/invoice_difficulty/run.py
```

詳細は [examples/invoice_difficulty/README.md](examples/invoice_difficulty/README.md) を参照してください。
