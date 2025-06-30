let observer;

function injectUI(responseId) {
    const replySidebar = document.querySelector('div[aria-label="Reply"], div[aria-label="Thread"]');
    if (!replySidebar) return;

    const replyHeading = Array.from(replySidebar.querySelectorAll('h2')).find(h => h.textContent.trim() === 'Reply');
    if (!replyHeading) return;

    let headerContainer = replyHeading.parentElement.className.includes('askademia-header-container')
        ? replyHeading.parentElement
        : null;

    let buttonContainer;

    if (!headerContainer) {
        headerContainer = document.createElement('div');
        headerContainer.className = 'askademia-header-container';
        headerContainer.style.display = 'flex';
        headerContainer.style.justifyContent = 'space-between';
        headerContainer.style.alignItems = 'center';
        headerContainer.style.width = '100%';

        buttonContainer = document.createElement('div');
        buttonContainer.className = 'askademia-button-container';

        replyHeading.parentNode.insertBefore(headerContainer, replyHeading);
        headerContainer.appendChild(replyHeading);
        headerContainer.appendChild(buttonContainer);
    } else {
        buttonContainer = headerContainer.querySelector('.askademia-button-container');
    }

    if (!buttonContainer) return;

    if (!document.getElementById('askademia-styles')) {
        const styleSheet = document.createElement("style");
        styleSheet.id = 'askademia-styles';
        styleSheet.innerText = `
            .askademia-btn, .feedback-btn {
                margin-left: 8px; cursor: pointer; border: none; background-color: #007bff;
                color: white; padding: 4px 14px; border-radius: 14px; font-size: 12px;
                transition: background-color 0.2s, filter 0.2s;
            }
            .askademia-btn:hover, .feedback-btn:hover { filter: brightness(1.1); }
            .askademia-btn:active, .feedback-btn:active { filter: brightness(0.9); }
            .feedback-btn[disabled] { background-color: #6c757d; color: #f8f9fa; cursor: not-allowed; }
        `;
        document.head.appendChild(styleSheet);
    }

    const askademiaButton = buttonContainer.querySelector(".askademia-btn");

    if (responseId) {
        if (askademiaButton) {
            askademiaButton.remove();
        }

        if (!buttonContainer.querySelector(`.feedback-btn[data-response-id="${responseId}"]`)) {
            const newFeedbackButton = document.createElement("button");
            newFeedbackButton.innerText = "Feedback 📝";
            newFeedbackButton.className = "feedback-btn";
            newFeedbackButton.dataset.responseId = responseId;

            newFeedbackButton.onclick = (event) => {
                event.stopPropagation();
                if (observer) observer.disconnect();

                const existingForm = document.querySelector(".feedback-iframe");
                if (existingForm) existingForm.remove();

                const rect = newFeedbackButton.getBoundingClientRect();
                const iframe = document.createElement("iframe");
                iframe.className = "feedback-iframe";
                iframe.dataset.responseId = newFeedbackButton.dataset.responseId;
                iframe.style.position = "absolute";
                iframe.style.top = `${rect.bottom + window.scrollY + 5}px`;
                iframe.style.left = `${rect.right + window.scrollX - 300}px`;
                iframe.style.width = "300px";
                iframe.style.height = "300px";
                iframe.style.border = "none";
                iframe.style.zIndex = "10001";
                iframe.style.filter = "drop-shadow(0 4px 8px rgba(0,0,0,0.1))";

                iframe.srcdoc = `
                    <html>
                    <head>
                        <style>
                            body { margin: 0; font-family: sans-serif; font-size: 14px; }
                            .feedback-form { position: relative; background-color: white; padding: 15px; border-radius: 8px; }
                            .feedback-form::before { content: ''; position: absolute; top: -10px; left: 20px; border-width: 0 10px 10px 10px; border-style: solid; border-color: transparent transparent white transparent; }
                            .rating-stars span { cursor: pointer; font-size: 24px; color: #ddd; }
                            .rating-stars span.selected, .rating-stars span:hover { color: orange; }
                            textarea { width: 95%; height: 80px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; }
                            button { padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
                            .submit-feedback { background-color: #4CAF50; color: white; }
                            .close-feedback { background-color: #f44336; color: white; float: right; }
                        </style>
                    </head>
                    <body>
                        <div class="feedback-form">
                            <h3>Feedback</h3>
                            <div class="rating-stars">
                                <span data-value="1">☆</span><span data-value="2">☆</span><span data-value="3">☆</span><span data-value="4">☆</span><span data-value="5">☆</span>
                            </div>
                            <textarea class="feedback-text" placeholder="Optional feedback..."></textarea>
                            <button class="submit-feedback">Submit</button>
                            <button class="close-feedback">Close</button>
                        </div>
                        <script>
                            let rating = 0;
                            const stars = document.querySelectorAll(".rating-stars span");
                            stars.forEach(star => {
                                star.onclick = () => {
                                    rating = parseInt(star.dataset.value);
                                    stars.forEach((s, i) => s.style.color = i < rating ? 'orange' : '#ddd');
                                };
                            });
                            document.querySelector(".submit-feedback").onclick = () => {
                                const feedbackText = document.querySelector(".feedback-text").value;
                                window.parent.postMessage({ type: 'submit-feedback', rating, feedbackText }, '*');
                            };
                            document.querySelector(".close-feedback").onclick = () => {
                                window.parent.postMessage({ type: 'close-feedback' }, '*');
                            };
                            document.querySelector(".feedback-text").focus();
                        </script>
                    </body>
                    </html>
                `;
                document.body.appendChild(iframe);
            };
            buttonContainer.appendChild(newFeedbackButton);
        }
    } else if (!askademiaButton && !buttonContainer.querySelector(".feedback-btn")) {
        const newAskademiaButton = document.createElement("button");
        newAskademiaButton.innerText = "Askademia 💡";
        newAskademiaButton.className = "askademia-btn";
        newAskademiaButton.onclick = async () => {
            const questionSpan = replySidebar.querySelector('span[class^="questionText"]');
            const question = Array.from(questionSpan.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent.trim()).join(" ");
            const response = await fetch("http://127.0.0.1:5000/", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question })
            });
            try {
                const data = await response.json();
                const replyBox = document.querySelector('textarea[placeholder="Write your reply..."]');
                if (replyBox) {
                    replyBox.value = data.response;
                    replyBox.dispatchEvent(new Event('input', { bubbles: true }));
                    injectUI(data.response_id);
                }
            } catch (e) { console.error("Fetch or JSON parse error", e); }
        };
        buttonContainer.appendChild(newAskademiaButton);
    }
}

window.addEventListener('message', async (event) => {
    const iframe = document.querySelector(".feedback-iframe");
    if (!iframe) return;

    const responseId = iframe.dataset.responseId;

    const closeAndRestore = () => {
        iframe.remove();
        if (observer) observer.observe(document.body, { childList: true, subtree: true });
    };

    if (event.data.type === 'submit-feedback') {
        await fetch("http://127.0.0.1:5000/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                response_id: responseId,
                rating: event.data.rating,
                feedback_text: event.data.feedbackText
            })
        });

        const feedbackButton = document.querySelector(`.feedback-btn[data-response-id="${responseId}"]`);
        if (feedbackButton) {
            feedbackButton.innerText = "Submitted ✔";
            feedbackButton.disabled = true;
        }

        closeAndRestore();
    } else if (event.data.type === 'close-feedback') {
        closeAndRestore();
    }
});

const observerCallback = () => {
    if (document.querySelector('.feedback-iframe')) return;
    setTimeout(() => injectUI(null), 200);
};
observer = new MutationObserver(observerCallback);
observer.observe(document.body, { childList: true, subtree: true });

document.addEventListener('click', (e) => {
    const iframe = document.querySelector('.feedback-iframe');
    if (iframe && !iframe.contains(e.target) && !e.target.closest('.feedback-btn')) {
        iframe.remove();
        if (observer) observer.observe(document.body, { childList: true, subtree: true });
    }
});

injectUI(null);