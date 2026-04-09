from __future__ import annotations

import csv
import re
from pathlib import Path

INPUT_PATH = Path("all_questions.csv")
OUTPUT_PATH = Path("all_questions_clean.csv")

PHONE_PATTERNS = [
    re.compile(r"\+994[\s\-]?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", re.IGNORECASE),
    re.compile(r"\b0\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", re.IGNORECASE),
]
SHORTCODE_PATTERN = re.compile(
    r"(?i)\b(əlaqə|qaynar xətt|qaynar|telefon|tel|nömrə|zəng|sms|whatsapp|watsap)\b[^\n]{0,25}\b(\d{4})\b"
)
KNOWN_SHORTCODES = {"1114", "5666"}


def _clean_contacts(text: str) -> str:
    cleaned = text
    for pattern in PHONE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = SHORTCODE_PATTERN.sub(r"\1", cleaned)
    for shortcode in KNOWN_SHORTCODES:
        cleaned = re.sub(rf"\b{shortcode}\b", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()


def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = []
        for row in reader:
            question = _clean_contacts((row.get("question") or "").strip())
            reply = _clean_contacts((row.get("reply") or "").strip())
            if not question or not reply:
                continue
            rows.append({"question": question, "reply": reply})

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=["question", "reply"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"written={len(rows)} file={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
