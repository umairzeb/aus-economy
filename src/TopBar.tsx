// One sticky bar for getting around: section links (current one highlighted) and the chart time range.
import { useEffect, useRef, useState } from "react";
import { RangeBar, type Range } from "./range";

export const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "going", label: "How it's going" },
  { id: "earn", label: "How we earn" },
  { id: "budget", label: "Government money" },
  { id: "you", label: "What it means for me" },
  { id: "business", label: "For business" },
];

export function TopBar({ range, onRange }: { range: Range; onRange: (r: Range) => void }) {
  const [active, setActive] = useState(SECTIONS[0].id);
  const navRef = useRef<HTMLElement>(null);

  // On narrow screens the links scroll sideways: keep the current one in view.
  useEffect(() => {
    const nav = navRef.current;
    const link = nav?.querySelector<HTMLElement>('[aria-current]');
    if (nav && link) nav.scrollTo({ left: link.offsetLeft - nav.clientWidth / 2 + link.offsetWidth / 2, behavior: "smooth" });
  }, [active]);

  useEffect(() => {
    // A section counts as current once its top passes the upper part of the screen.
    const obs = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (hit) setActive(hit.target.id);
      },
      { rootMargin: "-90px 0px -55% 0px" },
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  return (
    <div className="topbar">
      <nav ref={navRef} className="topbar-nav" aria-label="Sections">
        {SECTIONS.map((s) => (
          <a key={s.id} href={`#${s.id}`} aria-current={active === s.id ? "location" : undefined}>{s.label}</a>
        ))}
      </nav>
      <RangeBar range={range} onChange={onRange} />
    </div>
  );
}
