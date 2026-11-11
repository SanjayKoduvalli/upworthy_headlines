/* Interactive copy of the Headline Labeler used to check the AI classifier (case study §3.4).
   Same flow as the real tool: one headline at a time, one question at a time (who it centers → tone → topic),
   the AI's answer hidden until you've given yours, then shown side by side, with a running agreement score.
   Data: the 100 validation headlines, with Sanjay's blind label and the classifier's (docs/validation/
   classifier_validation_items.json, embedded in the page). Nothing is saved; this copy runs entirely in the browser. */
(function () {
  const root = document.getElementById("labeler-demo");
  const dataEl = document.getElementById("labeler-demo-data");
  if (!root || !dataEl) return;
  const items = JSON.parse(dataEl.textContent);

  const STEPS = [
    { key: "g", q: "Who does the headline center?", opts: [["f", "A woman"], ["m", "A man"], ["b", "Both"], ["n", "No gendered person"]] },
    { key: "s", q: "What's its overall tone?", opts: [["+", "Positive"], ["0", "Neutral"], ["-", "Negative"]] },
    { key: "t", q: "What's it mainly about?", opts: [["POL", "Politics & world affairs"], ["RAC", "Race, religion & immigration"],
      ["GEN", "Gender equality & LGBTQ+"], ["HEA", "Health & medicine"], ["ECO", "Economy, work & inequality"], ["EDU", "Education"],
      ["FAM", "Children & family"], ["ENV", "Environment & climate"], ["CRI", "Crime, police & justice"], ["SCI", "Science & technology"],
      ["ENT", "Entertainment & media"], ["HUM", "Human interest & kindness"], ["", "Can't tell from the headline"]] },
  ];
  const NAME = {}; STEPS.forEach(s => s.opts.forEach(([v, l]) => { NAME[s.key + ":" + v] = l; }));
  const label = (k, v) => NAME[k + ":" + v] || v;

  // shuffle once per visit (Fisher–Yates), so each reader sees a different order
  const order = items.map((_, i) => i);
  for (let i = order.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }

  let pos = 0, step = 0, sel = 0, answers = {}, revealed = false;
  const score = { n: 0, g: 0, s: 0, t: 0 };

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  function matches(key, mine, item) {
    if (key === "t") return mine === "" ? item.ai.t.length === 0 : item.ai.t.includes(mine);
    return mine === item.ai[key];
  }

  function render() {
    const item = items[order[pos]];
    root.replaceChildren();
    const top = el("div", "ld-top");
    top.append(el("span", "ld-count", `Headline ${pos + 1} of ${items.length}`));
    const sc = el("span", "ld-score");
    sc.textContent = score.n ? `You vs. the AI so far: who ${pct(score.g)} · tone ${pct(score.s)} · topic ${pct(score.t)} (${score.n} headline${score.n > 1 ? "s" : ""})` : "Your agreement with the AI appears here";
    top.append(sc);
    root.append(top);

    const card = el("div", "ld-card");
    card.append(el("p", "ld-head", item.h));
    if (item.e) card.append(el("p", "ld-excerpt", item.e));
    root.append(card);

    if (!revealed) {
      const s = STEPS[step];
      const box = el("div", "ld-q");
      box.append(el("p", "ld-qtext", `${step + 1}/3 · ${s.q}`));
      const opts = el("div", "ld-opts" + (s.key === "t" ? " ld-grid" : ""));
      opts.setAttribute("role", "group"); opts.setAttribute("aria-label", s.q);
      s.opts.forEach(([v, l], i) => {
        const b = el("button", "ld-opt" + (i === sel ? " sel" : ""), l);
        b.type = "button";
        b.addEventListener("click", () => choose(v));
        opts.append(b);
      });
      box.append(opts);
      box.append(el("p", "ld-hint", "Click an answer, or use the arrow keys and Enter. The AI's answer stays hidden until you've answered all three."));
      root.append(box);
    } else {
      const res = el("div", "ld-reveal"); res.setAttribute("aria-live", "polite");
      const t = el("table", "ld-table");
      const head = t.createTHead().insertRow();
      ["", "You", "AI classifier", "Sanjay (blind)"].forEach(h => head.append(el("th", null, h)));
      const body = t.createTBody();
      STEPS.forEach(s => {
        const r = body.insertRow();
        r.append(el("th", null, { g: "Who", s: "Tone", t: "Topic" }[s.key]));
        const ok = matches(s.key, answers[s.key], item);
        const you = el("td", ok ? "ok" : "miss", (ok ? "✓ " : "✗ ") + label(s.key, answers[s.key]));
        r.append(you);
        const ai = s.key === "t" ? (item.ai.t.length ? item.ai.t.map(x => label("t", x)).join(" + ") : label("t", "")) : label(s.key, item.ai[s.key]);
        r.append(el("td", null, ai));
        r.append(el("td", null, label(s.key, item.human[s.key])));
      });
      res.append(t);
      res.append(el("p", "ld-hint", "Topic counts as a match when your topic is among the AI's tags. Press Enter or click Next for another headline."));
      const next = el("button", "btn small primary ld-next", "Next headline");
      next.type = "button"; next.addEventListener("click", advance);
      res.append(next);
      root.append(res);
      next.focus({ preventScroll: true });
    }
  }

  const pct = (k) => Math.round((100 * k) / score.n) + "%";

  function choose(v) {
    answers[STEPS[step].key] = v;
    if (step < STEPS.length - 1) { step += 1; sel = 0; render(); return; }
    const item = items[order[pos]];
    score.n += 1;
    ["g", "s", "t"].forEach(k => { if (matches(k, answers[k], item)) score[k] += 1; });
    revealed = true; render();
  }

  function advance() { pos = (pos + 1) % items.length; step = 0; sel = 0; answers = {}; revealed = false; render(); }

  root.addEventListener("keydown", (e) => {
    if (revealed) { if (e.key === "Enter") { e.preventDefault(); advance(); } return; }
    const n = STEPS[step].opts.length, grid = STEPS[step].key === "t" ? 2 : 1;
    const moves = { ArrowRight: 1, ArrowDown: grid, ArrowLeft: -1, ArrowUp: -grid };
    if (e.key in moves) { e.preventDefault(); sel = (sel + moves[e.key] + n) % n; render(); root.querySelector(".ld-opt.sel")?.focus({ preventScroll: true }); }
    else if (e.key === "Enter" && !(e.target instanceof HTMLButtonElement)) { e.preventDefault(); choose(STEPS[step].opts[sel][0]); }
  });

  render();
})();
