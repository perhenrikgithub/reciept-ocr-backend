import ast
import json
from typing import NamedTuple
import pytesseract
import openai
from PIL import Image


class Item(NamedTuple):
    start_text: str
    end_text: str


STORE_DICT = {
    "rema 1000": Item(start_text="serienr", end_text="sum "),
    "coop obs": Item(start_text="ref", end_text="totalt "),
    "coop extra": Item(start_text="salgskvittering", end_text="totalt "),
    "unknown": Item(start_text="unknown", end_text="unknown "),
}


def _export_image_text(image_path: str) -> str:
    image = Image.open(f"src/receipts/{image_path}")
    return pytesseract.image_to_string(image, lang="nor").lower()


def _make_gpt_prompt(image_path: str) -> str:
    lines = _export_image_text(image_path).split("\n")

    store = lines[0]
    if "extra" in store:
        store = "coop extra"
    elif "obs" in store:
        store = "coop obs"
    elif "rema" in store:
        store = "rema 1000"
    else:
        store = "unknown"

    store = STORE_DICT[store]

    start_index = 0
    end_index = len(lines)

    for i, line in enumerate(lines):
        if not start_index and line.startswith(store.start_text):
            start_index = i + 1
        elif line.startswith(store.end_text):
            end_index = i
            break

    return ", ".join(
        line
        for line in lines[start_index:end_index]
        if not line.startswith("pant")
    )


def make_gpt_request(image_path: str) -> None:
    message_prefix = (
        "Lag et JSON-datasett fra følgende matvarer. Svaret skal være på "
        "formatet {'matvare': {'antall': int, 'vekt': str, 'kategori': str}, "
        "...}. Defaultverdi for antall skal være 1, vekt skal være 'N/A' og "
        "kategori skal være innenfor kjøleskap, tørrvare eller fryser. Rett "
        "opp i skrivefeil og generaliser navnet på matvaren."
    )
    prompt = _make_gpt_prompt(image_path)

    # TODO: Add API key
    openai.api_key = ""
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"{message_prefix}:\n{prompt}"}],
        temperature=0.0,
    )
    result_str = completion.choices[0].message.content  # type: ignore
    result = ast.literal_eval(
        result_str[result_str.find("{") : result_str.rfind("}") + 1]
    )
    _dump_gpt_request(result)


def _dump_gpt_request(new_articles: dict[str, str | int]) -> None:
    with open("src/db/articles.json", encoding="utf-8") as file:
        articles = json.load(file)

    articles.update(new_articles)
    _write_to_json(articles)


def _write_to_json(articles: dict[str, str | int]) -> None:
    with open("src/db/articles.json", "w", encoding="utf-8") as file:
        json.dump(articles, file)


def main() -> None:
    _write_to_json({})  # Reset articles.json
    test_receipts = {
        "rema": "rema_1000.jpg",
        # "obs": "coop_obs.jpeg",
        "extra": "coop_extra.jpg",
    }
    for value in test_receipts.values():
        print(make_gpt_request(value))


if __name__ == "__main__":
    main()
