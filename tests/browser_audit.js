// Page audit: paste into the browser console on the dashboard, or run from a browser tool.
// Goes through every range and every chart, and returns the problems it finds.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const problems = [];
  const stats = { cards: 0, charts: 0, tables: 0, tooltips: 0, ranges: 0 };
  const titleOf = (el) => el.closest("article")?.querySelector("h3")?.textContent ?? "page";
  const BAD = /\bNaN\b|\bundefined\b|\bnull\b|\bInfinity\b|\[object|\$-|\+-|--\d|%%|\$\$/;

  const pageChecks = (label) => {
    const text = document.body.innerText;
    const m = text.match(new RegExp(`.{0,40}(${BAD.source}).{0,40}`));
    if (m) problems.push(`${label}: bad text "${m[0]}"`);
    const doc = document.documentElement;
    if (doc.scrollWidth > doc.clientWidth + 1) problems.push(`${label}: page scrolls sideways (${doc.scrollWidth} > ${doc.clientWidth})`);
    document.querySelectorAll("article.card").forEach((a) => {
      const t = titleOf(a);
      if (a.scrollWidth > a.clientWidth + 1) problems.push(`${label}: "${t}" card overflows`);
      if (!a.querySelector("footer a")) problems.push(`${label}: "${t}" has no source link`);
      if (!a.querySelector(".takeaway")?.textContent.trim()) problems.push(`${label}: "${t}" has no summary`);
      const svg = a.querySelector(".chart-wrap svg");
      if (!svg) { problems.push(`${label}: "${t}" has no chart`); return; }
      const box = svg.getBoundingClientRect();
      if (box.width < 100 || box.height < 100) problems.push(`${label}: "${t}" chart is ${box.width}x${box.height}`);
      if (svg.querySelectorAll("path").length < 2) problems.push(`${label}: "${t}" chart has no marks`);
      const texts = [...svg.querySelectorAll("text")].map((x) => ({ t: x.textContent, r: x.getBoundingClientRect() })).filter((o) => o.r.width > 0);
      if (!texts.length) problems.push(`${label}: "${t}" chart has no labels`);
      for (const o of texts) {
        if (o.r.left < box.left - 2 || o.r.right > box.right + 2) problems.push(`${label}: "${t}" label "${o.t}" cut off at the side`);
        if (o.r.top < box.top - 4 || o.r.bottom > box.bottom + 4) problems.push(`${label}: "${t}" label "${o.t}" cut off at top or bottom`);
      }
      for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
        const A = texts[i].r, B = texts[j].r;
        if (A.left < B.right && B.left < A.right && A.top < B.bottom - 2 && B.top < A.bottom - 2) problems.push(`${label}: "${t}" labels overlap: ${texts[i].t} / ${texts[j].t}`);
      }
    });
  };

  const ranges = ["5 yrs", "10 yrs", "30 yrs", "All"];
  const button = (t) => [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === t);
  const original = document.querySelector('.segmented [aria-pressed="true"], .segmented [aria-checked="true"]')?.textContent.trim();
  for (const r of ranges) {
    button(r)?.click();
    await wait(900);
    stats.ranges++;
    pageChecks(r);
  }
  button(original ?? "10 yrs")?.click();
  await wait(700);

  const cards = [...document.querySelectorAll("article.card")];
  stats.cards = cards.length;
  for (const a of cards) {
    const t = titleOf(a);
    const svg = a.querySelector(".chart-wrap svg");
    if (svg) {
      stats.charts++;
      const host = svg.parentElement;
      const box = host.getBoundingClientRect();
      const xs = [0.2, 0.5, 0.8];
      for (const x of xs) {
        host.dispatchEvent(new MouseEvent("mousemove", { clientX: box.left + box.width * x, clientY: box.top + box.height * 0.4, bubbles: true }));
        await wait(60);
        const tip = a.querySelector(".tt");
        if (tip) {
          stats.tooltips++;
          if (BAD.test(tip.innerText)) problems.push(`"${t}" tooltip has bad text: ${tip.innerText.slice(0, 80)}`);
          const tb = tip.parentElement.getBoundingClientRect();
          if (tb.left < -1 || tb.right > innerWidth + 1) problems.push(`"${t}" tooltip runs off screen`);
        }
      }
      host.dispatchEvent(new MouseEvent("mouseout", { bubbles: true }));
    }
    const toggle = [...a.querySelectorAll("button")].find((b) => b.textContent === "Show table");
    if (toggle) {
      toggle.click();
      await wait(40);
      const rows = [...a.querySelectorAll("table tbody tr")];
      if (!rows.length) problems.push(`"${t}" table is empty`);
      else stats.tables++;
      const head = a.querySelectorAll("table thead th").length;
      for (const row of rows) {
        if (row.children.length !== head) { problems.push(`"${t}" table row has ${row.children.length} cells, header has ${head}`); break; }
        if (BAD.test(row.textContent)) { problems.push(`"${t}" table has bad text: ${row.textContent.slice(0, 80)}`); break; }
      }
      toggle.click();
      await wait(20);
    } else problems.push(`"${t}" has no table button`);
  }

  // Tile and nav links lead somewhere; the two tabs of data agree.
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    const id = a.getAttribute("href").slice(1);
    if (id && !document.getElementById(id)) problems.push(`link ${a.getAttribute("href")} goes nowhere`);
  });
  const dupes = [...document.querySelectorAll("[id]")].map((e) => e.id).filter((id, i, all) => all.indexOf(id) !== i);
  if (dupes.length) problems.push(`duplicate ids: ${[...new Set(dupes)].join(", ")}`);
  const links = [...new Set([...document.querySelectorAll('a[href^="http"]')].map((a) => a.href))];
  return { width: innerWidth, stats, problems: [...new Set(problems)], links };
})();
