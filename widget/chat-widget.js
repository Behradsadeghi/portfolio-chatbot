/*
 * chat-widget.js
 *
 * Widget-e chat baraye behradsadeghi.github.io
 * Zaher: elgu-ye fin.ai — pill-e hamishe-peyda paiin-e safhe, va ye
 * panel-e sheeshe-i (glassmorphism) ke bala-ye un baz mishe.
 *
 * CHERA IN ELGU VA NA HOBAB-E GOOSHE
 * ----------------------------------
 * Hobab-e goosheh bayad kashf beshe — kasi ke nemidune unja chizi
 * hast, click nemikone. Pill-e hamishe-peyda khodesh da'vat-e:
 * "Ask anything" ro mibini va mifahmi mituni soal beporsi.
 *
 * Trade-off: ye navar-e daemi paiin-e safhe fazaa migire. Fin.ai
 * ghabulesh karde chon chat mahsul-e asli-shun-e. Injaa ham chatbot
 * hamun chizi-e ke mikhay dide beshe, pas manteghi-e.
 *
 * CHERA RANG-HA AZ CSS-E KHOD-E SITE MIAN
 * ---------------------------------------
 * Site palette-e khodesh ro tuye :root ta'rif karde. Age injaa rang-e
 * delkhah bezanam, har vaght theme-e site avaz she widget jaa mimune.
 * Ba var(--..., fallback) az hamun estefade mikonim.
 *
 * (Nokte: esm-e var-ha tuye un CSS "yellow"-e vali rang-eshun aslan
 *  abi-e — hsl(207,86%,57%). Esm-e ghalat az template-e asli munde.)
 *
 * Estefade — ghabl az </body>:
 *   <script src="assets/js/chat-widget.js"
 *           data-api="https://portfolio-chatbot-tdnm.onrender.com"></script>
 */

(function () {
  "use strict";

  const script = document.currentScript;
  const API_URL = (script.getAttribute("data-api") || "").replace(/\/$/, "");
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
    .bsc-root {
      position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%);
      z-index: 9999; width: 520px; max-width: calc(100vw - 32px);
      font-family: var(--ff-poppins, 'Poppins', system-ui, sans-serif);
      display: flex; flex-direction: column; align-items: stretch; gap: 10px;
      pointer-events: none;
    }
    .bsc-root > * { pointer-events: auto; }

    /* ---- panel (glass card above the bar) ---- */
    .bsc-panel {
      background: rgba(44, 44, 49, 0.72);
      -webkit-backdrop-filter: blur(24px) saturate(140%);
      backdrop-filter: blur(24px) saturate(140%);
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-radius: 22px;
      box-shadow: 0 18px 50px rgba(0, 0, 0, .45);
      display: flex; flex-direction: column; overflow: hidden;
      height: 0; opacity: 0;
      transition: height .32s cubic-bezier(.4,0,.2,1), opacity .22s ease;
    }
    .bsc-root.bsc-open .bsc-panel {
      height: min(440px, calc(100vh - 160px)); opacity: 1;
    }

    .bsc-head {
      display: flex; align-items: center; gap: 10px;
      padding: 14px 16px; flex-shrink: 0;
    }
    .bsc-mark {
      width: 26px; height: 26px; border-radius: 8px; flex-shrink: 0;
      background: var(--text-gradient-yellow,
        linear-gradient(to right, hsl(207,86%,57%), hsl(197,86%,57%)));
      display: flex; align-items: center; justify-content: center;
      color: #fff; font-size: 12px; font-weight: 600;
    }
    .bsc-title {
      color: var(--white-2, hsl(0,0%,98%));
      font-size: 14px; font-weight: 500; flex: 1;
    }
    .bsc-collapse {
      background: none; border: none; cursor: pointer; padding: 4px;
      color: var(--light-gray, hsl(0,0%,84%)); display: flex;
      border-radius: 6px; transition: background .15s ease;
    }
    .bsc-collapse:hover { background: rgba(255,255,255,.08); }

    /* ---- messages ---- */
    .bsc-log {
      flex: 1; overflow-y: auto; padding: 4px 18px 16px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255,255,255,.18) transparent;
    }
    .bsc-log::-webkit-scrollbar { width: 6px; }
    .bsc-log::-webkit-scrollbar-thumb {
      background: rgba(255,255,255,.18); border-radius: 3px;
    }

    .bsc-msg {
      font-size: 13.5px; line-height: 1.62; margin-bottom: 16px;
      white-space: pre-wrap; animation: bsc-in .28s ease both;
    }
    @keyframes bsc-in {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: none; }
    }

    /* Bot: matn-e khali, bedun-e hobab — hamun kari ke fin.ai mikone.
       Javab-e boland tuye hobab khafe mishe; bedun-e hobab khunda-tare. */
    .bsc-bot { color: var(--white-2, hsl(0,0%,98%)); }

    /* User: hobab-e kuchik-e rast-chin, ta marz-e goftogu vazeh bashe */
    .bsc-user {
      background: rgba(255,255,255,.13);
      color: var(--white-2, hsl(0,0%,98%));
      padding: 9px 14px; border-radius: 16px;
      margin-left: auto; width: fit-content; max-width: 78%;
    }

    .bsc-err { color: hsl(0, 60%, 72%); }

    .bsc-sources {
      margin-top: 9px; font-size: 11px; line-height: 1.7;
      color: var(--light-gray-70, hsla(0,0%,84%,.7));
    }
    .bsc-sources a {
      color: var(--orange-yellow-crayola, hsl(207,86%,57%));
      text-decoration: none;
    }
    .bsc-sources a:hover { text-decoration: underline; }

    /* ---- typing dots ---- */
    .bsc-dots { display: flex; gap: 4px; padding: 4px 0; }
    .bsc-dots i {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--light-gray-70, hsla(0,0%,84%,.7));
      animation: bsc-blink 1.3s infinite both;
    }
    .bsc-dots i:nth-child(2) { animation-delay: .18s; }
    .bsc-dots i:nth-child(3) { animation-delay: .36s; }
    @keyframes bsc-blink {
      0%, 60%, 100% { opacity: .25; }
      30%           { opacity: 1; }
    }

    /* ---- suggestions ---- */
    .bsc-sugg { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 14px; }
    .bsc-sugg button {
      background: rgba(255,255,255,.07);
      border: 1px solid rgba(255,255,255,.1);
      color: var(--light-gray, hsl(0,0%,84%));
      border-radius: 15px; padding: 7px 13px; font-size: 12px;
      cursor: pointer; font-family: inherit;
      transition: background .15s ease, border-color .15s ease;
    }
    .bsc-sugg button:hover {
      background: rgba(255,255,255,.13);
      border-color: rgba(255,255,255,.2);
    }

    /* ---- input bar (hamishe peyda) ---- */
    .bsc-bar {
      display: flex; align-items: center; gap: 8px;
      background: rgba(44, 44, 49, .88);
      -webkit-backdrop-filter: blur(24px) saturate(140%);
      backdrop-filter: blur(24px) saturate(140%);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 999px; padding: 7px 8px 7px 20px;
      box-shadow: 0 8px 28px rgba(0,0,0,.4);
      transition: border-color .2s ease;
    }
    .bsc-bar:focus-within {
      border-color: var(--orange-yellow-crayola, hsl(207,86%,57%));
    }
    .bsc-bar input {
      flex: 1; background: none; border: none; outline: none;
      color: var(--white-2, hsl(0,0%,98%));
      font-size: 14px; font-family: inherit; min-width: 0;
    }
    .bsc-bar input::placeholder {
      color: var(--light-gray-70, hsla(0,0%,84%,.7));
    }
    .bsc-send {
      width: 36px; height: 36px; border-radius: 50%; border: none;
      flex-shrink: 0; cursor: pointer; display: flex;
      align-items: center; justify-content: center; color: #fff;
      background: var(--text-gradient-yellow,
        linear-gradient(to right, hsl(207,86%,57%), hsl(197,86%,57%)));
      transition: transform .15s ease, opacity .15s ease;
    }
    .bsc-send:hover:not(:disabled) { transform: scale(1.06); }
    .bsc-send:disabled { opacity: .45; cursor: not-allowed; }

    @media (max-width: 560px) {
      .bsc-root { left: 12px; right: 12px; bottom: 12px;
                  transform: none; width: auto; max-width: none; }
      .bsc-root.bsc-open .bsc-panel { height: min(60vh, 400px); }
    }

    @media (prefers-reduced-motion: reduce) {
      .bsc-panel, .bsc-msg, .bsc-send { transition: none; animation: none; }
    }
  `;
  document.head.appendChild(style);

  // --- markup ------------------------------------------------------------
  const root = document.createElement("div");
  root.className = "bsc-root";
  root.innerHTML = `
    <div class="bsc-panel">
      <div class="bsc-head">
        <div class="bsc-mark">B</div>
        <div class="bsc-title">Ask about Behrad</div>
        <button class="bsc-collapse" aria-label="Close chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.2"
               stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>
      <div class="bsc-log"></div>
    </div>

    <div class="bsc-bar">
      <input type="text" placeholder="Ask anything about Behrad…"
             maxlength="500" autocomplete="off"
             aria-label="Ask a question about Behrad">
      <button class="bsc-send" aria-label="Send">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.4"
             stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      </button>
    </div>
  `;
  document.body.appendChild(root);

  const log = root.querySelector(".bsc-log");
  const input = root.querySelector(".bsc-bar input");
  const sendBtn = root.querySelector(".bsc-send");
  const collapseBtn = root.querySelector(".bsc-collapse");

  // --- helpers -----------------------------------------------------------

  // CHERA textContent VA NA innerHTML
  // ---------------------------------
  // Matn az ye LLM miad. Age un ro be onvan HTML render konim, har tag-i
  // toosh bashe ejra mishe — rah-e classic-e XSS. textContent hame chi ro
  // matn-e khoshk hesab mikone.
  function addMessage(text, cls) {
    const el = document.createElement("div");
    el.className = "bsc-msg " + cls;
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function addTyping() {
    const el = document.createElement("div");
    el.className = "bsc-msg bsc-bot";
    el.innerHTML = '<div class="bsc-dots"><i></i><i></i><i></i></div>';
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  /*
   * CHERA SHOMARE-HA AZ MATN PAK MISHAN
   * -----------------------------------
   * Model javab ro ba [1] [2] mide, vali un shomare-ha be passage-haii
   * eshare mikonan ke BAZDID-KONANDE HICH VAGHT NEMIBINE. Tuye maghale-ye
   * elmi citation kar mikone chon list-e marja' zir-e safhe-st; injaa un
   * rabt vojud nadare — faghat noise-e basari-e.
   *
   * VALI AZ MODEL MIGIRIMESHUN, chon:
   *   - model ro majbur mikonan har claim ro be ye manba' vasl kone
   *     (khod-e in hallucination ro kam mikone)
   *   - ba unha mifahmim kodum chunk VAGHEAN be kar umad — 8 ta
   *     mifrestim, shayad 2 tash estefade beshe
   *   - baraye debug: javab-e ghalat az kodum chunk umad?
   *
   * Pas: model shomare bede -> ma filter konim -> az matn pakesh konim.
   */
  const CITE_RE = /\s*\[(\d+)\]/g;

  function renderAnswer(el, text, sources) {
    const cited = new Set();
    let m;
    CITE_RE.lastIndex = 0;
    while ((m = CITE_RE.exec(text)) !== null) cited.add(m[1]);

    // matn-e tamiz: shomare-ha + faseleye ghabl-eshun bardashte mishe
    el.textContent = text.replace(CITE_RE, "").replace(/\s+([.,;:!?])/g, "$1");

    if (!sources || !sources.length) return;
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
        a.textContent = s.title;
        box.appendChild(a);
      } else {
        box.appendChild(document.createTextNode(s.title));
      }
    });
    el.appendChild(box);
  }

  let suggBox = null;
  function renderSuggestions() {
    suggBox = document.createElement("div");
    suggBox.className = "bsc-sugg";
    SUGGESTIONS.forEach((text) => {
      const b = document.createElement("button");
      b.textContent = text;
      b.onclick = () => send(text);
      suggBox.appendChild(b);
    });
    log.appendChild(suggBox);
    log.scrollTop = log.scrollHeight;
  }

  let greeted = false;
  function open() {
    if (root.classList.contains("bsc-open")) return;
    root.classList.add("bsc-open");
    if (!greeted) {
      addMessage(
        "Hi — I can answer questions about Behrad's background, experience, and projects, using what's on this site.",
        "bsc-bot"
      );
      renderSuggestions();
      greeted = true;
    }
  }

  async function send(message) {
    open();
    if (suggBox) { suggBox.remove(); suggBox = null; }

    addMessage(message, "bsc-user");
    input.value = "";
    input.disabled = sendBtn.disabled = true;

    const pending = addTyping();

    try {
      const res = await fetch(API_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (res.status === 429) {
        pending.className = "bsc-msg bsc-err";
        pending.textContent =
          "That's a lot of questions at once — give it a minute.";
        return;
      }
      if (!res.ok) throw new Error("HTTP " + res.status);

      const data = await res.json();
      pending.className = "bsc-msg bsc-bot";
      renderAnswer(pending, data.answer, data.sources);
    } catch (err) {
      console.error("[chat-widget]", err);
      pending.className = "bsc-msg bsc-err";
      pending.textContent =
        "Couldn't reach the assistant. It may be waking up — try again in a moment.";
    } finally {
      input.disabled = sendBtn.disabled = false;
      input.focus();
      log.scrollTop = log.scrollHeight;
    }
  }

  // --- wiring ------------------------------------------------------------
  input.addEventListener("focus", open);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const msg = input.value.trim();
      if (msg) send(msg);
    }
  });

  sendBtn.onclick = () => {
    const msg = input.value.trim();
    if (msg) send(msg);
    else open();
  };

  collapseBtn.onclick = () => {
    root.classList.remove("bsc-open");
    input.blur();
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && root.classList.contains("bsc-open")) {
      root.classList.remove("bsc-open");
      input.blur();
    }
  });
})();
