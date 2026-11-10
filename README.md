# FAQ Chatbot

A chatbot that answers customer questions by finding the most similar question in a list of FAQs, using NLP preprocessing, TF-IDF and cosine similarity.

Built for **Task 2** of the CodeAlpha Artificial Intelligence internship.

The knowledge base is 37 FAQs for *BrightCart*, a fictional online electronics store (orders, shipping, returns, payments, accounts, warranty, offers and support). The store, its policies and contact details are invented sample data.

## Features

- Matches a question to the right FAQ even when it is worded differently
- Fixes typos (`"wher is my ordr"` still finds the order-tracking answer)
- Understands synonyms through WordNet (`"bill"` → `"invoice"`, `"parcel"` → `"package"`)
- Says so when it is not sure, and suggests the closest questions instead of guessing
- Replies to greetings, thanks and goodbyes
- Web chat interface with suggested questions, plus a terminal mode
- Evaluation script that measures accuracy on 104 test questions

## How it works

```
"i didnt get my refnd"
      │
      ▼  1. Preprocess (NLTK): lowercase, tokenize, remove stop words, lemmatize
["not", "get", "refnd"]
      │
      ▼  2. Repair unknown words: spelling correction, then WordNet synonyms
["not", "get", "refund"]
      │
      ▼  3. TF-IDF vector  →  cosine similarity with every FAQ
"When will I get my refund?"   similarity 0.69   ← best match
      │
      ▼  4. Above the confidence threshold?  yes → reply with that FAQ's answer
                                             no  → "Did you mean…?" with the closest questions
```

1. **Preprocessing.** Each sentence is lowercased and tokenized with NLTK. Punctuation and stop
   words are removed and every word is lemmatized (`"refunds"` → `"refund"`, `"cancelled"` → `"cancel"`).
   Negations and question words are kept because they change the meaning of a question.
2. **Knowledge base.** Every FAQ has a main question and a few alternative phrasings. Together they
   form one document per FAQ, and all documents are converted to TF-IDF vectors.
3. **Matching.** The user's question is vectorized the same way and compared with every FAQ using
   cosine similarity. The FAQ with the highest score wins.
4. **Unknown words.** A word the bot has never seen is first compared with known words to fix typos,
   then looked up in WordNet for a known synonym. If neither works, the confidence is lowered, so an
   off-topic question that happens to share one word with a FAQ is not answered.
5. **Confidence threshold.** If the best score is below the threshold, the bot does not answer and
   offers the closest questions as suggestions.

## Results

`evaluate.py` asks the bot 104 test questions that are worded differently from the stored FAQs
(90 on-topic, 14 off-topic that it should decline):

```
Correct: 91 / 104 (88%)
```

These questions were also used to choose the thresholds, so accuracy on completely new questions
will be somewhat lower. Most misses are confusions between closely related FAQs, for example
"What is your return policy?" and "How do I return a product?".

## Run it

Requires Python 3.10 or newer. The first run downloads the NLTK data it needs (a few MB).

```bash
git clone https://github.com/ajendrak742-code/CodeAlpha_FAQChatbot.git
cd CodeAlpha_FAQChatbot

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

python app.py         # web chat at http://127.0.0.1:5001
python chatbot.py     # or chat in the terminal
python evaluate.py    # accuracy report
```

## Use your own FAQs

Edit `data/faqs.json`. Each entry has a `category`, a `question`, a list of `variations` (other ways
people ask the same thing) and the `answer`. Restart the app to load the changes. Adding more
variations is the easiest way to improve matching.

## Project structure

```
chatbot.py             Matching engine: preprocessing, TF-IDF, cosine similarity, replies
app.py                 Flask server for the web chat
evaluate.py            Accuracy test
data/faqs.json         The FAQ knowledge base
data/test_queries.json Test questions with the expected FAQ for each
templates/index.html   Chat page
static/                Styling and front-end logic
```

## Tech stack

Python · NLTK · scikit-learn · Flask · HTML · CSS · JavaScript
