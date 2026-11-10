"""
FAQ matching engine.

How a question is answered:
  1. Preprocess the text with NLTK: lowercase, tokenize, drop punctuation and
     stop words, and lemmatize each word ("refunds" -> "refund").
  2. Repair words the bot does not know: fix typos ("pasword" -> "password")
     and look up synonyms in WordNet ("parcel" -> "package").
  3. Turn the question into a TF-IDF vector and compare it with every FAQ
     using cosine similarity.
  4. Reply with the answer of the most similar FAQ, or ask the user to
     rephrase when nothing is similar enough.

Run this file directly to chat in the terminal:  python chatbot.py
"""

import difflib
import json
import math
from pathlib import Path

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_FILE = Path(__file__).parent / "data" / "faqs.json"

ANSWER_THRESHOLD = 0.24   # minimum confidence needed to give an answer
SUGGEST_THRESHOLD = 0.10  # minimum confidence to offer a question as a suggestion
SPELLING_CUTOFF = 0.8     # how alike (0 to 1) a typo must be to a known word to be corrected


def ensure_nltk_data():
    """Download the NLTK resources on first run (tokenizer, stop words, WordNet)."""
    try:
        word_tokenize("test")
        stopwords.words("english")
        WordNetLemmatizer().lemmatize("tests")
    except LookupError:
        for package in ("punkt_tab", "stopwords", "wordnet"):
            nltk.download(package, quiet=True)


ensure_nltk_data()

# Words such as "not" and "when" are stop words in NLTK, but in a question they
# carry meaning ("coupon NOT working", "WHEN will my refund arrive"), so keep them.
KEEP_WORDS = {"not", "no", "how", "when", "where", "what", "why", "which", "who"}
STOP_WORDS = set(stopwords.words("english")) - KEEP_WORDS
lemmatizer = WordNetLemmatizer()


def lemmatize(word):
    """Reduce a word to its base form: "orders" -> "order", "cancelled" -> "cancel"."""
    return lemmatizer.lemmatize(lemmatizer.lemmatize(word), pos="v")


def preprocess(text):
    """Clean a sentence and return its important words in base form."""
    text = text.lower().replace("-", " ").replace("’", "'")
    words = []
    for token in word_tokenize(text):
        if token == "n't":  # the tokenizer splits "didn't" into "did" + "n't"
            token = "not"
        if not token.isalnum() or token in STOP_WORDS:
            continue  # skip punctuation and stop words
        words.append(lemmatize(token))
    return words


# Short messages that are conversation rather than questions: (trigger words, reply)
SMALL_TALK = [
    ({"hi", "hii", "hello", "hey", "namaste", "morning", "afternoon", "evening"},
     "Hello! I can answer questions about orders, shipping, returns, payments and your account. What would you like to know?"),
    ({"thanks", "thank", "thankyou", "thx"},
     "You're welcome! Is there anything else I can help you with?"),
    ({"bye", "goodbye", "cya"},
     "Goodbye! Thanks for stopping by."),
]
GREETING = SMALL_TALK[0][1]


class FAQBot:
    def __init__(self, data_file=DATA_FILE):
        data = json.loads(Path(data_file).read_text(encoding="utf-8"))
        self.name = data["bot_name"]
        self.faqs = data["faqs"]

        # One document per FAQ: its question plus the other ways people ask it
        documents = []
        for faq in self.faqs:
            phrasings = [faq["question"], *faq.get("variations", [])]
            documents.append(" ".join(word for phrase in phrasings for word in preprocess(phrase)))

        # TF-IDF gives rare, informative words ("refund") more weight than common ones ("order")
        self.vectorizer = TfidfVectorizer(token_pattern=r"\S+", sublinear_tf=True)
        self.faq_vectors = self.vectorizer.fit_transform(documents)
        self.vocabulary = set(self.vectorizer.vocabulary_)

    def understand(self, message):
        """Preprocess a message and repair the words the bot does not know.

        Returns (words, coverage) where coverage is the share of words that
        the bot knows, after fixing typos and trying synonyms.
        """
        words, understood, total = [], 0.0, 0
        for word in preprocess(message):
            total += 1
            if word in self.vocabulary:
                words.append(word)
                understood += 1
            elif fixed := self.fix_spelling(word):
                words.append(fixed)
                understood += 1
            elif synonym := self.find_synonym(word):
                words.append(synonym)
                understood += 0.5  # a synonym is only a guess, so it counts half
        return words, (understood / total if total else 0.0)

    def fix_spelling(self, word):
        """Return the known word closest to a typo, e.g. "refnd" -> "refund"."""
        if len(word) < 4:
            return None
        candidates = [known for known in self.vocabulary if known[0] == word[0]]
        close = difflib.get_close_matches(word, candidates, n=1, cutoff=SPELLING_CUTOFF)
        return close[0] if close else None

    def find_synonym(self, word):
        """Return a WordNet synonym that the bot knows, e.g. "bill" -> "invoice".

        Only the two most common meanings of the word are checked; rarer
        meanings produce far-fetched matches.
        """
        for synset in wordnet.synsets(word)[:2]:
            for name in synset.lemma_names():
                candidate = lemmatize(name.lower())
                if candidate in self.vocabulary:
                    return candidate
        return None

    def rank(self, message):
        """Return [(faq_index, confidence)] for every FAQ, best match first."""
        words, coverage = self.understand(message)
        query_vector = self.vectorizer.transform([" ".join(words)])
        similarities = cosine_similarity(query_vector, self.faq_vectors)[0]

        # Lower the confidence when part of the question was not understood, so
        # that an off-topic question sharing one word with a FAQ is not answered.
        scores = similarities * math.sqrt(coverage)
        return sorted(enumerate(map(float, scores)), key=lambda item: item[1], reverse=True)

    def small_talk(self, message):
        """Reply to greetings, thanks and goodbyes; None for anything else."""
        words = [word.strip(".,!?") for word in message.lower().split()]
        if 0 < len(words) <= 6:
            for keywords, response in SMALL_TALK:
                if keywords & set(words):
                    return response
        return None

    def starter_questions(self, count=4):
        """One question from each of the first few categories, for the welcome screen."""
        seen, questions = set(), []
        for faq in self.faqs:
            if faq["category"] not in seen:
                seen.add(faq["category"])
                questions.append(faq["question"])
        return questions[:count]

    def reply(self, message):
        """Build the chatbot's response to one user message."""
        message = message.strip()
        if not message:
            return {"type": "fallback", "answer": "Please type a question.", "suggestions": self.starter_questions()}

        ranked = self.rank(message)
        best_index, best_score = ranked[0]

        if best_score < ANSWER_THRESHOLD:
            talk = self.small_talk(message)
            if talk:
                # Offer example questions after a greeting, but not after "thanks" or "bye"
                starters = self.starter_questions() if talk == GREETING else []
                return {"type": "smalltalk", "answer": talk, "suggestions": starters}

            # Not confident enough to answer: offer the closest questions instead
            close = [self.faqs[i]["question"] for i, score in ranked[:3] if score >= SUGGEST_THRESHOLD]
            answer = ("I'm not sure I understood that. Did you mean one of these?" if close else
                      "Sorry, I don't have an answer for that. I can help with orders, shipping, "
                      "returns, payments and account questions.")
            return {"type": "fallback", "answer": answer, "confidence": round(best_score, 2),
                    "suggestions": close or self.starter_questions()}

        faq = self.faqs[best_index]
        related = [self.faqs[i]["question"] for i, score in ranked[1:3] if score >= SUGGEST_THRESHOLD]
        return {
            "type": "answer",
            "answer": faq["answer"],
            "matched_question": faq["question"],
            "category": faq["category"],
            "confidence": round(best_score, 2),
            "suggestions": related,
        }


def main():
    bot = FAQBot()
    print(f"{bot.name}: Hi! Ask me anything about orders, shipping, returns or payments. Type 'quit' to exit.")
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.lower() in {"quit", "exit"}:
            break
        response = bot.reply(message)
        print(f"{bot.name}: {response['answer']}")
        if response["type"] == "answer":
            print(f"   (matched \"{response['matched_question']}\", confidence {response['confidence']:.2f})")
        elif response["type"] == "fallback":
            for question in response["suggestions"]:
                print(f"   - {question}")
    print(f"{bot.name}: Goodbye!")


if __name__ == "__main__":
    main()
