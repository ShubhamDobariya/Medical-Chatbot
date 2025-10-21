const sendBtn = document.getElementById("send-btn");
const userInput = document.getElementById("user-input");
const chatBody = document.getElementById("chat-body");

//  Function to append message with profile image and formatting
function appendMessage(message, sender) {
  const msgContainer = document.createElement("div");
  msgContainer.classList.add("message-container", sender);

  // Profile image
  const profileImg = document.createElement("img");
  profileImg.classList.add("profile-img");
  profileImg.src =
    sender === "user" ? "static/images/user.png" : "static/images/bot.png";
  profileImg.alt = sender === "user" ? "User" : "Bot";

  // Message bubble
  const msgDiv = document.createElement("div");
  msgDiv.classList.add("message");
  msgDiv.classList.add(sender === "user" ? "user-message" : "bot-message");

  //  Allow Markdown formatting (bold, italic, line breaks)
  msgDiv.innerHTML = message
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
    .replace(/\*(.*?)\*/g, "<em>$1</em>") // Italic
    .replace(/\n/g, "<br>"); // Line breaks

  // Append based on sender
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

// Send button click
sendBtn.addEventListener("click", () => {
  const message = userInput.value.trim();
  if (!message) return;

  appendMessage(message, "user");
  userInput.value = "";

  // Send message to Flask backend
  const formData = new FormData();
  formData.append("msg", message);

  fetch("/get", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.text())
    .then((data) => {
      appendMessage(data, "bot");
    })
    .catch((err) => {
      appendMessage("Error: Cannot reach the server.", "bot");
      console.error(err);
    });
});

// Enter key sends message
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendBtn.click();
});
