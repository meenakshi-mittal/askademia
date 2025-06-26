function injectAskademiaButton() {
    const replySidebar = document.querySelector('div[aria-label="Reply"]');
    console.log("Reply Sidebar:", replySidebar);
    if (!replySidebar) return;

    const questionSpan = replySidebar.querySelector('span[class^="questionText"]');
    console.log("Question Span:", questionSpan);
    if (!questionSpan || questionSpan.querySelector(".askademia-btn")) return;

    const button = document.createElement("button");
    button.innerText = "Askademia 💡";
    button.className = "askademia-btn";
    button.style.marginLeft = "8px";
    button.style.cursor = "pointer";
    button.title = "Ask Askademia";

    button.onclick = async () => {
        const question = questionSpan.innerText.trim();

        const response = await fetch("http://localhost:5000/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();
        const answer = data.response;

        const replyBox = document.querySelector('textarea[placeholder="Write your reply..."]');
        console.log("Reply Box:", replyBox);
        if (replyBox) {
            replyBox.value = answer;
            replyBox.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    questionSpan.appendChild(button);
}

const observer = new MutationObserver(() => {
    setTimeout(injectAskademiaButton, 50);
});

observer.observe(document.body, {
    childList: true,
    subtree: true,
});
