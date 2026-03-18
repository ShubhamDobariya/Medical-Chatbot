const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatBody = document.getElementById("chat-body");

// Configure marked.js
marked.setOptions({ breaks: true, gfm: true });

// ── Append message ────────────────────────────────────────
function appendMessage(message, sender) {
  const msgContainer = document.createElement("div");
  msgContainer.classList.add("message-container", sender);

  const profileImg = document.createElement("img");
  profileImg.classList.add("profile-img");
  profileImg.src =
    sender === "user" ? "static/images/user.png" : "static/images/bot.png";
  profileImg.alt = sender === "user" ? "User" : "Bot";

  const msgDiv = document.createElement("div");
  msgDiv.classList.add("message");
  msgDiv.classList.add(sender === "user" ? "user-message" : "bot-message");

  //  Use marked.parse for bot (renders tables, bold, bullets)
  // Plain text for user messages
  if (sender === "bot") {
    msgDiv.innerHTML = marked.parse(message);
  } else {
    msgDiv.textContent = message;
  }

  if (sender === "user") {
    msgContainer.appendChild(msgDiv);
    msgContainer.appendChild(profileImg);
  } else {
    msgContainer.appendChild(profileImg);
    msgContainer.appendChild(msgDiv);
  }

  chatBody.appendChild(msgContainer);
  chatBody.scrollTop = chatBody.scrollHeight;
}

// ── Typing indicator ──────────────────────────────────────
function showTyping() {
  const container = document.createElement("div");
  container.classList.add("message-container");
  container.id = "typing-container";

  const img = document.createElement("img");
  img.src = "static/images/bot.png";
  img.classList.add("profile-img");
  img.alt = "Bot";

  const indicator = document.createElement("div");
  indicator.classList.add("typing-indicator");
  indicator.innerHTML = "<span></span><span></span><span></span>";

  container.appendChild(img);
  container.appendChild(indicator);
  chatBody.appendChild(container);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("typing-container");
  if (el) el.remove();
}

// ── Send message ──────────────────────────────────────────
sendBtn.addEventListener("click", () => {
  const message = userInput.value.trim();
  if (!message) return;

  appendMessage(message, "user");
  userInput.value = "";
  showTyping(); // show typing dots

  const formData = new FormData();
  formData.append("msg", message);

  fetch("/get", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.text())
    .then((data) => {
      hideTyping(); // remove typing dots
      appendMessage(data, "bot"); // render bot reply
    })
    .catch((err) => {
      hideTyping();
      appendMessage("⚠️ Error: Cannot reach the server.", "bot");
      console.error(err);
    });
});

// ── Enter key sends message
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

// ── Welcome message on page load
window.addEventListener("load", () => {
  const welcomeMsg =
    "Hello! 👋 I'm your Medical Assistant. How can I help you with your medical question today? 😊";
  appendMessage(welcomeMsg, "bot");
});
