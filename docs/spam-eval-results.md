# Spam 評価実験の結果

実行日時: 2026-09-21 20:53:34 +0900  
データ: 合成メール（spam 100 件 / not_spam 100 件、合計 200 件）  
比較モデル: TypeSafe Jev / gpt-4o-mini

## Jev

| 指標 | 値 |
|---|---:|
| Accuracy | 1.0000 |
| Spam precision | 1.0000 |
| Spam recall | 1.0000 |
| Spam F1 | 1.0000 |
| 平均レイテンシー | 236.6 ms |
| 中央値 | 223.6 ms |
| P95 | 307.6 ms |
| 実効スループット | 4.23 件/秒 |

混同行列: `spam→spam=100`, `spam→not_spam=0`, `not_spam→spam=0`, `not_spam→not_spam=100`
## gpt-4o-mini

| 指標 | 値 |
|---|---:|
| Accuracy | 1.0000 |
| Spam precision | 1.0000 |
| Spam recall | 1.0000 |
| Spam F1 | 1.0000 |
| 平均レイテンシー | 668.1 ms |
| 中央値 | 626.0 ms |
| P95 | 892.3 ms |
| 実効スループット | 1.5 件/秒 |

混同行列: `spam→spam=100`, `spam→not_spam=0`, `not_spam→spam=0`, `not_spam→not_spam=100`



> このデータセットは評価コードの動作確認用に生成した合成データです。実運用の性能を表すものではありません。
