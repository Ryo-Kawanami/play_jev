from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import Score, TypeSafeClient


ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "out"
DOCS = ROOT.parent.parent / "docs"
SEED = 20260921
LEVELS = (1, 2, 3, 4, 5)


def make_invoice(level: int, index: int, rng: random.Random) -> dict[str, object]:
    invoice_id = f"invoice-{level}-{index:03d}"
    vendor = rng.choice(["青空システムズ株式会社", "みなと物流株式会社", "北極星デザイン合同会社"])
    customer = rng.choice(["さくら商事株式会社", "東都マーケティング株式会社", "山手製作所"])
    currency = "JPY"
    factors: list[str] = []
    lines = [
        ("業務委託費", 1, 120000),
        ("保守サポート", 1, 45000),
    ]
    if level >= 2:
        lines.extend([("追加作業", 2, 18000), ("資料作成", 3, 12000)])
        factors.extend(["many_line_items", "discount"])
    if level >= 3:
        lines.append(("緊急対応費", 1, 30000))
        factors.extend(["multiple_tax_rates", "credit_note", "payment_terms"])
    if level >= 4:
        currency = "USD"
        factors.extend(["multi_currency", "contract_reference", "long_notes"])
    if level >= 5:
        factors.extend(["ambiguous_exception", "contradiction", "duplicate_line"])
        lines.append(("業務委託費（再計上分）", 1, 120000))

    subtotal = sum(quantity * unit_price for _, quantity, unit_price in lines)
    discount = 0 if level == 1 else 5000 + level * 1000
    tax_rate = 0.10 if level < 3 else 0.10
    tax = round((subtotal - discount) * tax_rate)
    total = subtotal - discount + tax
    issue_date = "2026年9月1日"
    due_date = "2026年9月30日" if level < 4 else "2026年9月15日"

    line_text = "\n".join(
        f"- {name}: {quantity} × {unit_price:,}円"
        for name, quantity, unit_price in lines
    )
    sections = [
        f"請求書番号: {invoice_id.upper()}",
        f"発行者: {vendor}",
        f"請求先: {customer}",
        f"発行日: {issue_date}",
        f"支払期限: {due_date}",
        "",
        "明細:",
        line_text,
        "",
        f"小計: {subtotal:,}円",
        f"値引き: -{discount:,}円",
        f"消費税: {tax:,}円（10%）",
        f"請求合計: {total:,}円",
        "",
        "振込先: 東都銀行 本店営業部 普通 1234567",
        "支払条件: 請求書受領月の翌月末払い。振込手数料はお客様負担です。",
    ]
    if level >= 4:
        sections.extend([
            "契約参照: 基本契約書 第7条および個別発注書A-19に基づく請求です。",
            "海外作業分はUSD建てですが、本請求書では参考換算額を円で記載しています。換算レートは1 USD = 148.20円です。",
            "備考: 月次作業、追加作業、過去月の調整分を含みます。詳細は別紙の作業報告書を参照してください。",
        ])
    if level >= 5:
        sections.extend([
            "例外: 契約書には支払期限を翌月末とする記載もありますが、個別発注書の期限を優先します。",
            "確認事項: 明細の「業務委託費（再計上分）」は前月請求との重複の可能性があります。",
            f"注記: 上記の請求合計は計算上 {total:,}円ですが、経理確認欄には {total + 1000:,}円と記載されています。",
        ])
    if level == 2:
        sections.append("備考: 今月の定例作業と追加作業をまとめて請求しています。")
    if level == 3:
        sections.append("備考: 返品分のクレジットは次回請求で相殺予定です。")

    return {
        "id": invoice_id,
        "difficulty": level,
        "factors": factors,
        "invoice_text": "\n".join(sections),
        "expected_fields": {
            "invoice_number": invoice_id.upper(),
            "vendor": vendor,
            "customer": customer,
            "currency": currency,
            "total_jpy": total,
        },
    }


def make_dataset(per_level: int) -> list[dict[str, object]]:
    rng = random.Random(SEED)
    rows = [make_invoice(level, index, rng) for level in LEVELS for index in range(1, per_level + 1)]
    rng.shuffle(rows)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def parse_score(value: object) -> int:
    score = int(round(float(value)))
    if score not in LEVELS:
        raise ValueError(f"score must be 1..5, got {value!r}")
    return score


def score_with_jev(dataset: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    with TypeSafeClient() as client:
        for number, item in enumerate(dataset, start=1):
            started = time.perf_counter()
            response = client.system_one(
                state={"invoice": item["invoice_text"]},
                questions={
                    "difficulty": Score(
                        instructions=(
                            "この請求書を自動処理システムが正確に読み取り、金額・日付・条件・例外を確認する難しさを評価してください。"
                            "文書の長さだけでなく、情報の分散、計算、曖昧さ、矛盾、追加確認の必要性を考慮してください。"
                        ),
                        criteria=[
                            "1: 単純で情報が明確",
                            "2: 軽微な揺れや明細増加がある",
                            "3: 複数の計算や条件確認が必要",
                            "4: 複数の例外や文書間参照が必要",
                            "5: 矛盾・欠落・曖昧さがあり追加確認が必要",
                        ],
                    )
                },
            )
            answer = response.scores["difficulty"]
            predicted = parse_score(answer.score)
            results.append({
                "id": item["id"],
                "truth": item["difficulty"],
                "predicted": predicted,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            })
            print(f"[Jev {number}/{len(dataset)}] {item['id']}: {predicted}")
    return results


def score_with_llm(dataset: list[dict[str, object]], model: str) -> tuple[list[dict[str, object]], dict[str, int]]:
    from openai import OpenAI

    client = OpenAI()
    results = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    for number, item in enumerate(dataset, start=1):
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=20,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        'Rate invoice processing difficulty from 1 to 5. '
                        'Return only JSON: {"score": 1}. '
                        "1 means simple and clear; 5 means contradictions, ambiguity, or manual review are required."
                    ),
                },
                {"role": "user", "content": item["invoice_text"]},
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        predicted = parse_score(payload.get("score"))
        if response.usage:
            usage["prompt_tokens"] += response.usage.prompt_tokens
            usage["completion_tokens"] += response.usage.completion_tokens
        results.append({
            "id": item["id"],
            "truth": item["difficulty"],
            "predicted": predicted,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        })
        print(f"[{model} {number}/{len(dataset)}] {item['id']}: {predicted}")
    return results, usage


def rank_correlation(truth: list[int], predicted: list[int]) -> float:
    def ranks(values: list[int]) -> list[float]:
        ordered = sorted(values)
        rank_by_value = {
            value: ordered.index(value) + (ordered.count(value) + 1) / 2
            for value in set(values)
        }
        return [rank_by_value[value] for value in values]

    a, b = ranks(truth), ranks(predicted)
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
    return numerator / denominator if denominator else 0.0


def evaluate(results: list[dict[str, object]]) -> dict[str, object]:
    truth = [int(row["truth"]) for row in results]
    predicted = [int(row["predicted"]) for row in results]
    errors = [prediction - actual for actual, prediction in zip(truth, predicted)]
    latencies = [float(row["latency_ms"]) for row in results]
    mae = statistics.mean(abs(error) for error in errors)
    rmse = math.sqrt(statistics.mean(error * error for error in errors))
    return {
        "total": len(results),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "exact_match": round(sum(error == 0 for error in errors) / len(errors), 4),
        "within_one": round(sum(abs(error) <= 1 for error in errors) / len(errors), 4),
        "mean_bias": round(statistics.mean(errors), 4),
        "spearman_like_correlation": round(rank_correlation(truth, predicted), 4),
        "by_difficulty": {
            str(level): {
                "count": sum(actual == level for actual in truth),
                "mae": round(statistics.mean(abs(error) for actual, error in zip(truth, errors) if actual == level), 4),
                "mean_predicted": round(statistics.mean(prediction for actual, prediction in zip(truth, predicted) if actual == level), 4),
            }
            for level in LEVELS
        },
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p95": round(sorted(latencies)[max(0, math.ceil(len(latencies) * 0.95) - 1)], 1),
        },
        "throughput_requests_per_second": round(len(results) / (sum(latencies) / 1000), 2),
    }


def write_report(reports: dict[str, dict[str, object]], per_level: int, llm_model: str) -> None:
    blocks = []
    for name, metrics in reports.items():
        latency = metrics["latency_ms"]
        blocks.append(
            f"""## {name}

| 指標 | 値 |
|---|---:|
| MAE | {metrics['mae']:.4f} |
| RMSE | {metrics['rmse']:.4f} |
| Exact match | {metrics['exact_match']:.4f} |
| Within ±1 | {metrics['within_one']:.4f} |
| 平均バイアス | {metrics['mean_bias']:.4f} |
| 順位相関 | {metrics['spearman_like_correlation']:.4f} |
| 平均レイテンシー | {latency['mean']} ms |
| P95 | {latency['p95']} ms |
| スループット | {metrics['throughput_requests_per_second']} 件/秒 |

### 難易度別

| 正解難易度 | 件数 | MAE | 平均予測 |
|---:|---:|---:|---:|
""" + "\n".join(
                f"| {level} | {values['count']} | {values['mae']:.4f} | {values['mean_predicted']:.2f} |"
                for level, values in metrics["by_difficulty"].items()
            ) + "\n"
        )
    report = f"""# 請求書難易度スコア評価

実行日時: {time.strftime('%Y-%m-%d %H:%M:%S %z')}  
データ: 合成請求書（難易度1〜5、各{per_level}件、合計{per_level * 5}件）  
比較モデル: TypeSafe Jev / {llm_model}

{''.join(blocks)}
> 難易度の正解値は、請求書生成時に注入した難化要因からルールで決めています。実運用文書の客観的な難易度を直接測定したものではありません。
"""
    DOCS.mkdir(exist_ok=True)
    (DOCS / "invoice-difficulty-results.md").write_text(report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-level", type=int, default=20, help="難易度ごとの件数")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()
    if args.per_level < 1:
        parser.error("--per-level は1以上にしてください")

    load_dotenv()
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    dataset = make_dataset(args.per_level)
    write_jsonl(DATA / "dataset.jsonl", dataset)
    if args.generate_only:
        print(f"generated {len(dataset)} invoices at {DATA / 'dataset.jsonl'}")
        return
    if not os.getenv("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY を .env に設定してください")

    jev_results = score_with_jev(dataset)
    reports = {"Jev": evaluate(jev_results)}
    write_jsonl(OUT / "jev_results.jsonl", jev_results)
    if not args.skip_llm:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("比較には OPENAI_API_KEY を .env に設定してください")
        llm_results, usage = score_with_llm(dataset, args.llm_model)
        reports[args.llm_model] = evaluate(llm_results)
        reports[args.llm_model]["token_usage"] = usage
        write_jsonl(OUT / "llm_results.jsonl", llm_results)
    (OUT / "metrics.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    write_report(reports, args.per_level, args.llm_model if not args.skip_llm else "比較なし")
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
