
const $ = (id) => document.getElementById(id);

let latest = null;

const GREETING = "🌻 Good Morning, Sanskar Family!";

function setStatus(message, isError = false) {
    $("status").textContent = message;
    $("status").style.color = isError ? "#b33d32" : "";
}

function showQuote(item) {
    latest = item;

    $("theme").textContent = item.theme;
    $("quote").textContent = `"${item.quote}"`;
    $("hindiLine").textContent = item.hindiLine;
    $("closing").textContent = `✨ ${item.closing}`;

    $("result").classList.remove("hidden");
}

function getCompleteMessage(item) {
    return `${GREETING}

${item.theme}

"${item.quote}"

${item.hindiLine}

✨ ${item.closing}`;
}

async function generateQuote() {
    const button = $("generateBtn");

    button.disabled = true;
    button.textContent = "Creating your morning message...";

    setStatus("AI is creating a fresh message for Sanskar Family.");

    try {
        const response = await fetch("/api/generate-quote", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                topic: $("topic").value.trim(),
                context: $("context").value.trim()
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        showQuote(data);
        setStatus("Your Sanskar Family morning message is ready! 🌻");


    } catch (error) {
        setStatus(error.message, true);

    } finally {
        button.disabled = false;
        button.innerHTML = 'Generate morning message <span>→</span>';
    }
}

async function loadHistory() {
    try {
        const response = await fetch("/api/quotes");
        const items = await response.json();

        const container = $("history");
        container.innerHTML = "";

        if (!items.length) {
            container.innerHTML =
                '<p class="muted">Your generated messages will appear here.</p>';
            return;
        }

        items.slice(0, 8).forEach(item => {
            const card = document.createElement("div");
            card.className = "history-item";

            const title = document.createElement("strong");
            title.textContent = item.theme || "Morning message";

            const preview = document.createElement("p");
            preview.textContent = item.quote;

            const meta = document.createElement("small");
            meta.textContent = new Date(item.createdAt).toLocaleString();

            card.append(title, preview, meta);

            card.addEventListener("click", () => {
                showQuote(item);
                $("result").scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            });

            container.appendChild(card);
        });

    } catch {
        $("history").innerHTML =
            '<p class="muted">Could not load message history.</p>';
    }
}

$("generateBtn").addEventListener("click", generateQuote);
$("anotherBtn").addEventListener("click", generateQuote);

$("copyBtn").addEventListener("click", async () => {
    if (!latest) return;

    try {
        await navigator.clipboard.writeText(
            getCompleteMessage(latest)
        );

        $("copyBtn").textContent = "Copied!";

        setTimeout(() => {
            $("copyBtn").textContent = "Copy message";
        }, 1500);

    } catch {
        setStatus("Clipboard access was blocked by your browser.", true);
    }
});


