import os

from dotenv import load_dotenv
from typesafe_sdk import Choice, TypeSafeClient


load_dotenv()

if not os.getenv("TYPESAFE_API_KEY"):
    raise SystemExit("TYPESAFE_API_KEY を設定してください")


with TypeSafeClient() as client:
    response = client.system_one(
        state={"text": "請求が二重になっています。確認してください。"},
        questions={
            "category": Choice(
                instructions="この問い合わせのカテゴリは？",
                criteria={
                    "billing": None,
                    "technical": None,
                    "other": None,
                },
            ),
        },
    )

print(response.choices["category"].choice)
