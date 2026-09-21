from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import Choice, TypeSafeClient


ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "out"
RANDOM_SEED = 20260921


SPAM_TEMPLATES = [
    "【緊急】お客様のアカウントで異常なログインを検知しました。{action}こちらから確認してください: {url}",
    "おめでとうございます！抽選で{amount}円分のギフト券が当選しました。本日中に受け取り手続きを完了してください: {url}",
    "未払い料金があります。サービス停止を避けるため、{deadline}までに次のページでお支払い情報を更新してください: {url}",
    "投資の専門家からのご案内です。元本保証で短期間に利益が出る限定案件です。詳細はこちら: {url}",
    "あなたのメールボックスの容量が上限に達しました。継続利用のため、今すぐ容量を確認してください: {url}",
    "特別キャンペーンのお知らせです。先着順で豪華賞品をプレゼントします。参加登録はこちら: {url}",
    "本人確認が完了していません。{deadline}までに本人確認書類を提出しない場合、アカウントを凍結します: {url}",
    "限定会員だけの高還元クーポンを獲得できます。今すぐログインしてクーポンを受け取ってください: {url}",
    "銀行口座への不正アクセスの疑いがあります。安全確認のため、以下のフォームに暗証情報を入力してください: {url}",
    "副業モニターを募集しています。スマホだけで月{amount}円以上可能です。詳しい条件はこちら: {url}",
]

HAM_TEMPLATES = [
    "件名: 定例会議の議事録\n本日の会議で決まった内容を共有します。次回までに担当箇所をご確認ください。",
    "ご注文の商品を発送しました。配送状況は注文履歴から確認できます。到着予定日は{date}です。",
    "来月のシステムメンテナンスは{date}の{time}から実施します。作業中は一時的に利用できません。",
    "先日の打ち合わせありがとうございました。合意した見積書を添付しますので、ご確認をお願いします。",
    "図書館からのお知らせです。貸出中の資料の返却期限は{date}です。延長はマイページから手続きできます。",
    "今月の利用明細が確定しました。請求額と内訳は公式アプリの明細画面でご確認ください。",
    "プロジェクトの進捗報告です。予定どおり設計工程が完了し、来週から実装に移行します。",
    "健康診断の予約日時のお知らせです。{date}の{time}に受付へお越しください。変更は窓口へご連絡ください。",
    "ご利用いただきありがとうございます。サービス改善のため、任意のアンケートへのご協力をお願いします。",
    "町内会からのお知らせです。次回の清掃活動は{date}の午前9時からです。参加できる方は集合場所へお越しください。",
]


def make_dataset(count: int) -> list[dict[str, object]]:
    rng = random.Random(RANDOM_SEED)
    dataset: list[dict[str, object]] = []
    dates = ["9月25日", "10月1日", "10月12日", "11月5日"]
    times = ["9:00", "13:30", "18:00"]
    amounts = ["3万円", "5万円", "10万円", "30万円"]
    deadlines = ["本日23:59", "24時間以内", "9月30日", "至急"]
    urls = ["https://example.invalid/verify", "https://example.invalid/claim"]

    for label, templates in (("spam", SPAM_TEMPLATES), ("not_spam", HAM_TEMPLATES)):
        for index in range(count):
            template = templates[index % len(templates)]
            text = template.format(
                action=rng.choice(["至急、", "ただちに、", "安全のため、"]),
                amount=rng.choice(amounts),
                deadline=rng.choice(deadlines),
                url=rng.choice(urls),
                date=rng.choice(dates),
                time=rng.choice(times),
            )
            dataset.append({"id": f"{label}-{index + 1:03d}", "label": label, "text": text})

    rng.shuffle(dataset)
    return dataset


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def classify_jev(dataset: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    with TypeSafeClient() as client:
        for number, item in enumerate(dataset, start=1):
            started = time.perf_counter()
            response = client.system_one(
                state={"email": item["text"]},
                questions={
                    "classification": Choice(
                        instructions="このメールは迷惑メールですか？広告・詐欺・不審なリンクなど、受信者が望まないメールを spam としてください。通常の業務連絡やサービス通知は not_spam としてください。",
                        criteria={"spam": None, "not_spam": None},
                    )
                },
            )
            answer = response.choices["classification"]
            results.append(
                {
                    **item,
                    "predicted": answer.choice,
                    "confidence": getattr(answer, "confidence", None),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
            print(f"[{number}/{len(dataset)}] {item['id']}: {answer.choice}")
    return results


def classify_llm(dataset: list[dict[str, object]], model: str) -> tuple[list[dict[str, object]], dict[str, int]]:
    from openai import OpenAI

    results = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    client = OpenAI()
    for number, item in enumerate(dataset, start=1):
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=8,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": 'Classify each email as exactly "spam" or "not_spam". Return only JSON: {"label":"spam"} or {"label":"not_spam"}.',
                },
                {"role": "user", "content": item["text"]},
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        predicted = payload.get("label")
        if predicted not in {"spam", "not_spam"}:
            raise ValueError(f"{model} returned an invalid label: {predicted!r}")
        if response.usage:
            usage["prompt_tokens"] += response.usage.prompt_tokens
            usage["completion_tokens"] += response.usage.completion_tokens
        results.append({**item, "predicted": predicted, "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
        print(f"[{model} {number}/{len(dataset)}] {item['id']}: {predicted}")
    return results, usage


def evaluate(results: list[dict[str, object]]) -> dict[str, object]:
    tp = sum(r["label"] == r["predicted"] == "spam" for r in results)
    tn = sum(r["label"] == r["predicted"] == "not_spam" for r in results)
    fp = sum(r["label"] == "not_spam" and r["predicted"] == "spam" for r in results)
    fn = sum(r["label"] == "spam" and r["predicted"] == "not_spam" for r in results)
    total = len(results)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    latencies = [float(r["latency_ms"]) for r in results]
    total_latency = sum(latencies) / 1000
    return {
        "total": total,
        "correct": tp + tn,
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision_spam": precision,
        "recall_spam": recall,
        "f1_spam": f1,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1),
            "min": round(min(latencies), 1),
            "max": round(max(latencies), 1),
        },
        "sequential_request_time_seconds": round(total_latency, 2),
        "throughput_requests_per_second": round(len(results) / total_latency, 2) if total_latency else 0.0,
        "confusion_matrix": {"true_spam_predicted_spam": tp, "true_spam_predicted_not_spam": fn, "true_not_spam_predicted_spam": fp, "true_not_spam_predicted_not_spam": tn},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="ラベルごとの件数")
    parser.add_argument("--skip-llm", action="store_true", help="gpt-4o-mini との比較を行わない")
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count は1以上にしてください")

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY を .env に設定してください")

    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    dataset = make_dataset(args.count)
    write_jsonl(DATA / "dataset.jsonl", dataset)
    if args.generate_only:
        print(f"generated {len(dataset)} emails at {DATA / 'dataset.jsonl'}")
        return
    jev_results = classify_jev(dataset)
    reports = {"Jev": evaluate(jev_results)}
    write_jsonl(OUT / "jev_results.jsonl", jev_results)
    llm_error = None
    if not args.skip_llm:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("比較には OPENAI_API_KEY を .env に設定してください（Jev だけなら --skip-llm）")
        try:
            llm_results, usage = classify_llm(dataset, args.llm_model)
            reports[args.llm_model] = evaluate(llm_results)
            reports[args.llm_model]["token_usage"] = usage
            write_jsonl(OUT / "llm_results.jsonl", llm_results)
        except Exception as error:
            llm_error = f"{type(error).__name__}: {error}"
            print(f"LLM comparison failed: {llm_error}")
    (OUT / "metrics.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    write_report(reports, args.count, args.llm_model if not args.skip_llm else "比較なし", llm_error)
    print(json.dumps(reports, ensure_ascii=False, indent=2))


def write_report(reports: dict[str, dict[str, object]], count: int, llm_model: str, llm_error: str | None = None) -> None:
    sections = []
    for name, metrics in reports.items():
        latency = metrics["latency_ms"]
        matrix = metrics["confusion_matrix"]
        sections.append(f"""## {name}

| 指標 | 値 |
|---|---:|
| Accuracy | {metrics['accuracy']:.4f} |
| Spam precision | {metrics['precision_spam']:.4f} |
| Spam recall | {metrics['recall_spam']:.4f} |
| Spam F1 | {metrics['f1_spam']:.4f} |
| 平均レイテンシー | {latency['mean']} ms |
| 中央値 | {latency['median']} ms |
| P95 | {latency['p95']} ms |
| 実効スループット | {metrics['throughput_requests_per_second']} 件/秒 |

混同行列: `spam→spam={matrix['true_spam_predicted_spam']}`, `spam→not_spam={matrix['true_spam_predicted_not_spam']}`, `not_spam→spam={matrix['true_not_spam_predicted_spam']}`, `not_spam→not_spam={matrix['true_not_spam_predicted_not_spam']}`
""")
    error_section = f"\n## 比較実行エラー\n\n`{llm_error}`\n" if llm_error else ""
    report = f"""# Spam 評価実験の結果

実行日時: {time.strftime('%Y-%m-%d %H:%M:%S %z')}  
データ: 合成メール（spam {count} 件 / not_spam {count} 件、合計 {count * 2} 件）  
比較モデル: TypeSafe Jev / {llm_model}

{''.join(sections)}
{error_section}

> このデータセットは評価コードの動作確認用に生成した合成データです。実運用の性能を表すものではありません。
"""
    docs = ROOT.parent.parent / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "spam-eval-results.md").write_text(report)


if __name__ == "__main__":
    main()
