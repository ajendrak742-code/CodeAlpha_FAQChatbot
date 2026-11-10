// FAQ Chatbot - front-end logic
// Sends each message to /api/chat and shows the reply as a chat bubble.

const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

const MIN_TYPING_TIME = 450;  // ms the "typing" dots stay visible, so replies do not flash in
let waiting = false;          // true while a reply is on its way

// Add one chat bubble. Options: meta (small grey line) and chips (clickable questions).
function addMessage(sender, text, { meta = "", chips = [] } = {}) {
  const message = document.createElement("div");
  message.className = `message ${sender}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;  // textContent keeps user input from being read as HTML
  message.appendChild(bubble);

  if (meta) {
    const metaEl = document.createElement("div");
    metaEl.className = "meta";
    metaEl.textContent = meta;
    message.appendChild(metaEl);
  }

  if (chips.length) {
    const chipsEl = document.createElement("div");
    chipsEl.className = "chips";
    for (const question of chips) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = question;
      chip.addEventListener("click", () => send(question));
      chipsEl.appendChild(chip);
    }
    message.appendChild(chipsEl);
  }

  messagesEl.appendChild(message);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return message;
}

function showTyping() {
  const typing = document.createElement("div");
  typing.className = "message bot typing";
  typing.innerHTML = '<div class="bubble"><span></span><span></span><span></span></div>';
  messagesEl.appendChild(typing);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return typing;
}

function showReply(reply) {
  let meta = "";
  if (reply.type === "answer") {
    meta = `Matched: "${reply.matched_question}" · ${reply.category} · similarity ${reply.confidence.toFixed(2)}`;
  }
  addMessage("bot", reply.answer, { meta, chips: reply.suggestions || [] });
}

async function send(text) {
  text = text.trim();
  if (!text || waiting) return;

  waiting = true;
  sendBtn.disabled = true;
  input.value = "";
  addMessage("user", text);
  const typing = showTyping();
  const started = Date.now();

  let reply;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (!response.ok) throw new Error("Server error");
    reply = await response.json();
  } catch {
    reply = { type: "error", answer: "I could not reach the server. Please check that it is running and try again." };
  }

  // Keep the typing dots up for a moment so the reply feels natural
  const elapsed = Date.now() - started;
  if (elapsed < MIN_TYPING_TIME) {
    await new Promise((resolve) => setTimeout(resolve, MIN_TYPING_TIME - elapsed));
  }

  typing.remove();
  showReply(reply);
  waiting = false;
  sendBtn.disabled = false;
  input.focus();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  send(input.value);
});

// Welcome message with a few questions to get started
addMessage("bot", `Hi, I'm ${BOT_NAME}! Ask me anything about your orders, delivery, returns, payments or account.`, {
  chips: STARTER_QUESTIONS,
});
