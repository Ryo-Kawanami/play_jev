# Spam classification evaluation

迷惑メールと正常メールを同数生成し、Jev の判定を正解ラベルと比較する小さな評価実験です。

```bash
uv run python examples/spam_eval/run.py
```

`.env` に `TYPESAFE_API_KEY` と `OPENAI_API_KEY` の両方を設定すると、Jev と `gpt-4o-mini` を同じデータセットで比較します。Jev だけ試す場合は `--skip-llm` を指定してください。

デフォルトでは、迷惑メール100件・正常メール100件を生成します。データセットは `examples/spam_eval/data/`、判定結果は `examples/spam_eval/out/` に保存されます。

API 利用量を抑えて試す場合:

```bash
uv run python examples/spam_eval/run.py --count 10
```

このデータセットは合成データです。実運用の性能評価には、個人情報を除いた実データと人手で確認したラベルを使ってください。
