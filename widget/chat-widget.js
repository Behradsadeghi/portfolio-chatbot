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
      position: relative;
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

    /* ---- scroll-to-bottom (mesl-e fin.ai) ---- */
    .bsc-jump {
      position: absolute; left: 50%; bottom: 14px;
      transform: translateX(-50%) scale(.8);
      width: 30px; height: 30px; border-radius: 50%;
      border: 1px solid rgba(255,255,255,.14);
      background: rgba(60,60,66,.95);
      -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
      color: var(--white-2, hsl(0,0%,98%));
      cursor: pointer; display: flex; align-items: center;
      justify-content: center; opacity: 0; pointer-events: none;
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
      transition: opacity .2s ease, transform .2s ease;
    }
    .bsc-jump.bsc-show {
      opacity: 1; pointer-events: auto; transform: translateX(-50%) scale(1);
    }

    /* ---- history dropdown ---- */
    .bsc-titlebtn {
      display: flex; align-items: center; gap: 6px; flex: 1;
      background: none; border: none; padding: 0; cursor: pointer;
      font-family: inherit; text-align: left;
      color: var(--white-2, hsl(0,0%,98%));
      font-size: 14px; font-weight: 500;
    }
    .bsc-titlebtn svg { transition: transform .2s ease; flex-shrink: 0; }
    .bsc-root.bsc-hist .bsc-titlebtn svg { transform: rotate(180deg); }

    .bsc-history {
      position: absolute; top: 50px; left: 14px; right: 14px; z-index: 2;
      background: rgba(52,52,58,.97);
      -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 14px; padding: 6px;
      box-shadow: 0 12px 32px rgba(0,0,0,.5);
      max-height: 240px; overflow-y: auto;
      display: none;
    }
    .bsc-root.bsc-hist .bsc-history { display: block; }

    .bsc-hitem {
      display: flex; align-items: center; gap: 10px; width: 100%;
      background: none; border: none; cursor: pointer;
      padding: 9px 10px; border-radius: 9px; font-family: inherit;
      text-align: left; transition: background .13s ease;
    }
    .bsc-hitem:hover { background: rgba(255,255,255,.08); }
    .bsc-hdot {
      width: 20px; height: 20px; border-radius: 6px; flex-shrink: 0;
      background: var(--text-gradient-yellow,
        linear-gradient(to right, hsl(207,86%,57%), hsl(197,86%,57%)));
    }
    /* Radif-e "New conversation" bayad AZ NAZAR-E BASARI fargh dashte
       bashe ba goftogu-haye ghabli — vagarna ye morabba'-e abi-ye digeh-st
       va kasi motevajeh nemishe amal-esh fargh dare. */
    .bsc-hnew .bsc-hdot {
      background: none; border: 1px dashed rgba(255,255,255,.3);
      display: flex; align-items: center; justify-content: center;
      color: var(--light-gray, hsl(0,0%,84%));
    }
    .bsc-hsep {
      height: 1px; margin: 5px 8px;
      background: rgba(255,255,255,.09);
    }
    .bsc-hlabel {
      flex: 1; min-width: 0; font-size: 12.5px;
      color: var(--white-2, hsl(0,0%,98%));
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .bsc-hage {
      font-size: 11px; flex-shrink: 0;
      color: var(--light-gray-70, hsla(0,0%,84%,.7));
    }
    .bsc-hempty {
      padding: 12px 10px; font-size: 12px;
      color: var(--light-gray-70, hsla(0,0%,84%,.7));
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
        <button class="bsc-titlebtn" aria-label="Past conversations">
          <span>Ask about Behrad</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.4"
               stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <button class="bsc-collapse" aria-label="Close chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.2"
               stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>
      <div class="bsc-history"></div>
      <div class="bsc-log"></div>
      <button class="bsc-jump" aria-label="Scroll to latest">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.6"
             stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
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
  const titleBtn = root.querySelector(".bsc-titlebtn");
  const titleLabel = titleBtn.querySelector("span");
  const historyBox = root.querySelector(".bsc-history");
  const jumpBtn = root.querySelector(".bsc-jump");

  // --- conversation store ------------------------------------------------
  //
  // CHERA localStorage VA NA SERVER
  // -------------------------------
  // Server-e ma stateless-e va hich goftogu-ii ro zakhire nemikone -
  // in amdi-e: ye site-e portfolio nabayad chat-e bazdid-konande-ha ro
  // negah dare. Tariche mal-e KHOD-E user-e va tuye browser-esh mimune.
  //
  // Ma'ni-sh: history rooye device-e digeh nemiad. Baraye fin.ai un
  // moshkel-e (support-e chand-canale), baraye ma na.
  const STORE_KEY = "bsc:conversations";
  const MAX_STORED = 8;
  const MAX_HISTORY_TURNS = 6;

  function loadConversations() {
    // localStorage momkene khamush bashe (private mode, setting-e user).
    // Un vaght widget bayad kar kone, faghat bedun-e tariche.
    try {
      const raw = localStorage.getItem(STORE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveConversations(list) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(list.slice(0, MAX_STORED)));
    } catch (e) {
      /* quota por-e ya khamush-e - bikhial */
    }
  }

  let conversations = loadConversations();
  let current = null;

  function persist() {
    if (!current || !current.turns.length) return;
    conversations = conversations.filter((c) => c.id !== current.id);
    conversations.unshift(current);
    saveConversations(conversations);
  }

  function relativeAge(ts) {
    const mins = Math.floor((Date.now() - ts) / 60000);
    if (mins < 1) return "now";
    if (mins < 60) return mins + "m";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h";
    const days = Math.floor(hrs / 24);
    if (days < 30) return days + "d";
    return Math.floor(days / 30) + "mo";
  }

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

  // --- history dropdown --------------------------------------------------
  function renderHistory() {
    historyBox.innerHTML = "";

    // "New conversation" hamishe aval-e. Bedun-e in, ye bar ke goftogu
    // shoru she hich rah-i baraye shoru-e ye ta-ye taze nist.
    if (current && current.turns.length) {
      const fresh = document.createElement("button");
      fresh.className = "bsc-hitem bsc-hnew";

      const plus = document.createElement("div");
      plus.className = "bsc-hdot";
      plus.innerHTML =
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="3" stroke-linecap="round">' +
        '<line x1="12" y1="5" x2="12" y2="19"></line>' +
        '<line x1="5" y1="12" x2="19" y2="12"></line></svg>';

      const lbl = document.createElement("span");
      lbl.className = "bsc-hlabel";
      lbl.textContent = "New conversation";

      fresh.append(plus, lbl);
      fresh.onclick = () => {
        startNew();
        root.classList.remove("bsc-hist");
        open();
        input.focus();
      };
      historyBox.appendChild(fresh);

      const sep = document.createElement("div");
      sep.className = "bsc-hsep";
      historyBox.appendChild(sep);
    }

    const others = conversations.filter((c) => !current || c.id !== current.id);

    if (!others.length) {
      const p = document.createElement("div");
      p.className = "bsc-hempty";
      p.textContent = "No earlier conversations.";
      historyBox.appendChild(p);
      return;
    }

    others.forEach((conv) => {
      const btn = document.createElement("button");
      btn.className = "bsc-hitem";

      const dot = document.createElement("div");
      dot.className = "bsc-hdot";

      const label = document.createElement("span");
      label.className = "bsc-hlabel";
      label.textContent = conv.title;

      const age = document.createElement("span");
      age.className = "bsc-hage";
      age.textContent = relativeAge(conv.updatedAt);

      btn.append(dot, label, age);
      btn.onclick = () => openConversation(conv);
      historyBox.appendChild(btn);
    });
  }

  function openConversation(conv) {
    persist();
    current = conv;
    log.innerHTML = "";
    suggBox = null;
    conv.turns.forEach((t) => {
      if (t.role === "user") {
        addMessage(t.text, "bsc-user");
      } else {
        const el = addMessage("", "bsc-bot");
        renderAnswer(el, t.text, t.sources);
      }
    });
    root.classList.remove("bsc-hist");
    updatePlaceholder();
    log.scrollTop = log.scrollHeight;
  }

  function startNew() {
    persist();
    current = null;
    log.innerHTML = "";
    suggBox = null;
    greeted = false;
    updatePlaceholder();
  }

  // "Continue conversation" — mesl-e fin.ai. Ye signal-e kuchik vali
  // vazeh: goftogu tamum nashode, mituni edame bedi.
  function updatePlaceholder() {
    input.placeholder =
      current && current.turns.length
        ? "Continue conversation"
        : "Ask anything about Behrad…";
  }

  let greeted = false;
  function open() {
    if (root.classList.contains("bsc-open")) return;
    root.classList.add("bsc-open");
    if (!greeted && (!current || !current.turns.length)) {
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
    root.classList.remove("bsc-hist");
    if (suggBox) { suggBox.remove(); suggBox = null; }

    if (!current) {
      current = {
        id: "c_" + Date.now().toString(36),
        title: message,          // avvalin soal onvan mishe
        updatedAt: Date.now(),
        turns: [],
      };
    }

    // Tariche GHABL az ezafe kardan-e payam-e feli gerefte mishe —
    // vagarna soal ro do bar be model midim.
    const history = current.turns
      .slice(-MAX_HISTORY_TURNS)
      .map((t) => ({ role: t.role, text: t.text }));

    addMessage(message, "bsc-user");
    current.turns.push({ role: "user", text: message });
    current.updatedAt = Date.now();

    input.value = "";
    input.disabled = sendBtn.disabled = true;

    const pending = addTyping();

    try {
      const res = await fetch(API_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
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

      current.turns.push({
        role: "assistant",
        text: data.answer,
        sources: data.sources,
      });
      current.updatedAt = Date.now();
      persist();
    } catch (err) {
      console.error("[chat-widget]", err);
      pending.className = "bsc-msg bsc-err";
      pending.textContent =
        "Couldn't reach the assistant. It may be waking up — try again in a moment.";
      // soal-e nafrestade ro az tariche dar miarim, vagarna daf'e-ye
      // ba'd be onvan-e context-e ye javab-i ke hich vaght nayumad
      // ferestade mishe
      current.turns.pop();
    } finally {
      input.disabled = sendBtn.disabled = false;
      updatePlaceholder();
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
    root.classList.remove("bsc-open", "bsc-hist");
    input.blur();
  };

  titleBtn.onclick = () => {
    const opening = !root.classList.contains("bsc-hist");
    if (opening) renderHistory();
    root.classList.toggle("bsc-hist", opening);
  };

  // CHERA IN DEKME LAZEM-E
  // ----------------------
  // Vaghti user bala scroll karde ta ye javab-e ghadimi ro bekhune va
  // javab-e jadid miad, un motevajeh nemishe. Auto-scroll ham eshtebah-e:
  // matni ke dare mikhune ro mipare. Pas ye dekme neshun midim.
  jumpBtn.onclick = () => {
    log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
  };

  log.addEventListener("scroll", () => {
    const atBottom =
      log.scrollHeight - log.scrollTop - log.clientHeight < 40;
    jumpBtn.classList.toggle("bsc-show", !atBottom);
  });

  // click-e birun -> dropdown baste she
  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) root.classList.remove("bsc-hist");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (root.classList.contains("bsc-hist")) {
      root.classList.remove("bsc-hist");   // aval dropdown
    } else if (root.classList.contains("bsc-open")) {
      root.classList.remove("bsc-open");   // ba'd khod-e panel
      input.blur();
    }
  });

  window.addEventListener("beforeunload", persist);
})();
