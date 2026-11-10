"""
Measures how often the chatbot picks the right FAQ.

data/test_queries.json holds questions worded differently from the stored
FAQs, plus a few off-topic questions that the bot should decline to answer.
These questions were also used to choose the thresholds in chatbot.py.

Run:  python evaluate.py
"""

import json
from pathlib import Path

from chatbot import FAQBot

TEST_FILE = Path(__file__).parent / "data" / "test_queries.json"


def main():
    bot = FAQBot()
    queries = json.loads(TEST_FILE.read_text(encoding="utf-8"))["queries"]

    correct = 0
    misses = []
    for item in queries:
        response = bot.reply(item["query"])
        got = response.get("matched_question")  # None when the bot declined to answer
        if got == item["expected"]:
            correct += 1
        else:
            misses.append((item["query"], item["expected"], got, response.get("confidence")))

    on_topic = sum(1 for q in queries if q["expected"])
    print(f"FAQs in knowledge base : {len(bot.faqs)}")
    print(f"Test questions         : {len(queries)} ({on_topic} on-topic, {len(queries) - on_topic} off-topic)")
    print(f"Correct                : {correct} / {len(queries)} ({correct / len(queries):.0%})")

    if misses:
        print("\nMisses:")
        for query, expected, got, score in misses:
            print(f"  \"{query}\"")
            print(f"      expected: {expected or '(decline to answer)'}")
            print(f"      got     : {got or '(declined)'}  [confidence {score}]")


if __name__ == "__main__":
    main()
