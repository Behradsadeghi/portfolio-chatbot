/*
 * chat-widget.js
 *
 * Widget-e float-e goshe-ye site. Ye file, bedun-e dependency.
 *
 * CHERA VANILLA JS VA NA REACT
 * ----------------------------
 * Site-e to HTML-e static-e. Ezafe kardan-e React ya'ni build step,
 * bundler, va sad-ha KB JavaScript - baraye ye hobab-e chat.
 *
 * CHERA HAME-YE CSS DAKHEL-E JS
 * -----------------------------
 * Ta faghat YE khat be index.html ezafe beshe. Har class ba pishvand-e
 * `bsc-` shoru mishe ta ba style-haye site ghati nashe.
 *
 * Estefade - in ro ghabl az </body> tuye index.html bezar:
 *   <script src="assets/js/chat-widget.js"
 *           data-api="https://YOUR-BACKEND-URL"></script>
 */

(function () {
  "use strict";

  const script = document.currentScript;
  const API_URL = script.getAttribute("data-api");
  if (!API_URL) {
    console.error("[chat-widget] data-api attribute missing");
    return;
  }

  const SUGGESTIONS = [
    "What is he working on now?",
    "Does he have production ML experience?",
    "How can I contact him?",
  ];

  // --- styles ------------------------------------------------------------
  const style = document.createElement("style");
  style.textContent = `
    .bsc-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9998;
      width: 56px; height: 56px; border-radius: 50%; border: none;
      background: linear-gradient(135deg, #FFDB70, #FFBB5C);
      color: #1c1c22; font-size: 24px; cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,.4);
      display: flex; align-items: center; justify-content: center;
      transition: transform .2s ease;
    }
    .bsc-btn:hover { transform: scale(1.08); }

    .bsc-panel {
      position: fixed; bottom: 92px; right: 24px; z-index: 9999;
      width: 360px; max-width: calc(100vw - 32px);
      height: 480px; max-height: calc(100vh - 140px);
      background: #2b2b2f; border: 1px solid #383838; border-radius: 14px;
      box-shadow: 0 8px 32px rgba(0,0,0,.5);
      display: none; flex-direction: column; overflow: hidden;
      font-family: 'Poppins', system-ui, sans-serif;
    }
    .bsc-panel.bsc-open { display: flex; }

    .bsc-head {
      padding: 14px 16px; border-bottom: 1px solid #383838;
      color: #fafafa; font-size: 14px; font-weight: 600;
      display: flex; justify-content: space-between; align-items: center;
    }
    .bsc-head span { color: #d6d6d6; font-weight: 400; font-size: 12px; }
    .bsc-close {
      background: none; border: none; color: #d6d6d6;
      font-size: 20px; cursor: pointer; line-height: 1;
    }

    .bsc-log { flex: 1; overflow-y: auto; padding: 14px; }

    .bsc-msg {
      margin-bottom: 12px; padding: 10px 12px; border-radius: 10px;
      font-size: 13px; line-height: 1.55; white-space: pre-wrap;
    }
    .bsc-user { background: #FFDB70; color: #1c1c22; margin-left: 32px; }
    .bsc-bot  { background: #383838; color: #fafafa; margin-right: 16px; }
    .bsc-err  { background: #4a2b2b; color: #ffb4b4; margin-right: 16px; }

    .bsc-sources {
      margin-top: 8px; padding-top: 8px; border-top: 1px solid #4a4a4a;
      font-size: 11px; color: #b0b0b0;
    }
    .bsc-sources a { color: #FFDB70; text-decoration: none; }

    .bsc-sugg { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 14px 10px; }
    .bsc-sugg button {
      background: #383838; color: #d6d6d6; border: 1px solid #4a4a4a;
      border-radius: 14px; padding: 6px 10px; font-size: 11px; cursor: pointer;
      font-family: inherit;
    }
    .bsc-sugg button:hover { background: #454545; }

    .bsc-form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #383838; }
    .bsc-form input {
      flex: 1; background: #383838; border: 1px solid #4a4a4a; border-radius: 8px;
      padding: 9px 12px; color: #fafafa; font-size: 13px; font-family: inherit;
    }
    .bsc-form input:focus { outline: none; border-color: #FFDB70; }
    .bsc-form button {
      background: #FFDB70; border: none; border-radius: 8px;
      padding: 0 16px; color: #1c1c22; font-weight: 600; cursor: pointer;
      font-family: inherit; font-size: 13px;
    }
    .bsc-form button:disabled { opacity: .5; cursor: not-allowed; }

    @media (max-width: 480px) {
      .bsc-panel { right: 16px; left: 16px; width: auto; bottom: 84px; }
    }
  `;
  document.head.appendChild(style);

  // --- markup ------------------------------------------------------------
  const btn = document.createElement("button");
  btn.className = "bsc-btn";
  btn.setAttribute("aria-label", "Open chat");
  btn.textContent = "💬";

  const panel = document.createElement("div");
  panel.className = "bsc-panel";
  panel.innerHTML = `
    <div class="bsc-head">
      <div>Ask about Behrad <span>· AI assistant</span></div>
      <button class="bsc-close" aria-label="Close chat">×</button>
    </div>
    <div class="bsc-log"></div>
    <div class="bsc-sugg"></div>
    <form class="bsc-form">
      <input type="text" placeholder="Ask a question…" maxlength="500" autocomplete="off">
      <button type="submit">Send</button>
    </form>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  const log = panel.querySelector(".bsc-log");
  const sugg = panel.querySelector(".bsc-sugg");
  const form = panel.querySelector(".bsc-form");
  const input = form.querySelector("input");
  const sendBtn = form.querySelector("button");

  // --- helpers -----------------------------------------------------------

  // CHERA textContent VA NA innerHTML
  // ---------------------------------
  // Javab az ye LLM miad. Age un matn ro be onvan HTML render konim,
  // har tag-i toosh bashe ejra mishe. In rah-e classic-e XSS-e.
  // textContent hame chi ro matn-e khoshk hesab mikone.
  function addMessage(text, cls) {
    const el = document.createElement("div");
    el.className = "bsc-msg " + cls;
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function addSources(el, sources) {
    if (!sources || !sources.length) return;
    // faghat un-haii ke to javab cite shodan
    const cited = new Set(
      (el.textContent.match(/\[(\d+)\]/g) || []).map((m) => m.replace(/\D/g, ""))
    );
    const used = sources.filter((s) => cited.has(String(s.n)));
    if (!used.length) return;

    const box = document.createElement("div");
    box.className = "bsc-sources";
    box.appendChild(document.createTextNode("Sources: "));
    used.forEach((s, i) => {
      if (i) box.appendChild(document.createTextNode(" · "));
      if (s.url) {
        const a = document.createElement("a");
        a.href = s.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = `[${s.n}] ${s.title}`;
        box.appendChild(a);
      } else {
        box.appendChild(document.createTextNode(`[${s.n}] ${s.title}`));
      }
    });
    el.appendChild(box);
  }

  function renderSuggestions() {
    sugg.innerHTML = "";
    SUGGESTIONS.forEach((text) => {
      const b = document.createElement("button");
      b.textContent = text;
      b.onclick = () => {
        input.value = text;
        form.requestSubmit();
      };
      sugg.appendChild(b);
    });
  }

  async function send(message) {
    addMessage(message, "bsc-user");
    sugg.innerHTML = "";
    input.value = "";
    input.disabled = sendBtn.disabled = true;

    const pending = addMessage("…", "bsc-bot");

    try {
      const res = await fetch(API_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (res.status === 429) {
        pending.className = "bsc-msg bsc-err";
        pending.textContent = "Too many questions at once — give it a minute.";
        return;
      }
      if (!res.ok) throw new Error("HTTP " + res.status);

      const data = await res.json();
      pending.textContent = data.answer;
      addSources(pending, data.sources);
    } catch (err) {
      console.error("[chat-widget]", err);
      pending.className = "bsc-msg bsc-err";
      pending.textContent =
        "Couldn't reach the assistant. Please try again in a moment.";
    } finally {
      input.disabled = sendBtn.disabled = false;
      input.focus();
      log.scrollTop = log.scrollHeight;
    }
  }

  // --- wiring ------------------------------------------------------------
  let greeted = false;
  btn.onclick = () => {
    panel.classList.toggle("bsc-open");
    if (panel.classList.contains("bsc-open")) {
      if (!greeted) {
        addMessage(
          "Hi — ask me anything about Behrad's background, experience, or projects.",
          "bsc-bot"
        );
        renderSuggestions();
        greeted = true;
      }
      input.focus();
    }
  };

  panel.querySelector(".bsc-close").onclick = () =>
    panel.classList.remove("bsc-open");

  form.onsubmit = (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (msg) send(msg);
  };
})();
