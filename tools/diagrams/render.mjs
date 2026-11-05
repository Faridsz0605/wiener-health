// Renders docs/diagrams/*.svg from specs/*.json with a hand-drawn (Excalidraw-like) look.
// Output is deterministic: every shape gets a fixed seed derived from its position in the spec.
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import rough from "roughjs";

const HERE = new URL(".", import.meta.url).pathname;
const OUT = join(HERE, "../../docs/diagrams");
const FONT = "Excalifont, Virgil, 'Comic Sans MS', cursive";
const INK = "#1e1e1e";
const gen = rough.generator();

const round = (d) => d.replace(/-?\d+\.\d+/g, (n) => String(Math.round(Number(n) * 10) / 10));
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// toPaths() drops dash options, so dashing is applied on the SVG element.
function paths(drawable, dashed = false) {
  const dash = dashed ? ' stroke-dasharray="8 6"' : "";
  return gen
    .toPaths(drawable)
    .map((p) => `<path d="${round(p.d)}" stroke="${p.stroke}" stroke-width="${p.strokeWidth}" fill="${p.fill ?? "none"}"${dash}/>`)
    .join("");
}

function text(x, y, label, size = 16, anchor = "middle") {
  const lines = label.split("\n");
  const top = y - ((lines.length - 1) * size * 1.25) / 2;
  const spans = lines
    .map((l, i) => `<tspan x="${x}" y="${(top + i * size * 1.25).toFixed(1)}">${esc(l)}</tspan>`)
    .join("");
  const attrs = `font-family="${FONT}" font-size="${size}" text-anchor="${anchor}" dominant-baseline="middle"`;
  // White halo drawn first keeps labels readable over hachure and arrows.
  return `<text ${attrs} fill="#fff" stroke="#fff" stroke-width="4">${spans}</text><text ${attrs} fill="${INK}">${spans}</text>`;
}

// Point where the segment from the box center towards (tx, ty) leaves the box.
function exitPoint(n, tx, ty) {
  const cx = n.x + n.w / 2;
  const cy = n.y + n.h / 2;
  const dx = tx - cx;
  const dy = ty - cy;
  const s = Math.min(Math.abs(n.w / 2 / dx || Infinity), Math.abs(n.h / 2 / dy || Infinity));
  return [cx + dx * s, cy + dy * s];
}

function arrow(a, b, edge, seed) {
  const [x1, y1] = exitPoint(a, b.x + b.w / 2, b.y + b.h / 2);
  const [x2, y2] = exitPoint(b, a.x + a.w / 2, a.y + a.h / 2);
  const opts = { seed, stroke: INK, strokeWidth: 1.5, roughness: 1 };
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const head = (da) => gen.line(x2, y2, x2 - 14 * Math.cos(ang + da), y2 - 14 * Math.sin(ang + da), opts);
  let out = paths(gen.line(x1, y1, x2, y2, opts), edge.dashed) + paths(head(0.45)) + paths(head(-0.45));
  if (edge.label) out += text((x1 + x2) / 2, (y1 + y2) / 2 - 10, edge.label, 13);
  return out;
}

function render(spec) {
  let seed = 1;
  const shape = (s, opts) => {
    const o = { seed: seed++, stroke: INK, strokeWidth: 1.5, fillStyle: "hachure", hachureGap: 8, ...opts };
    return s.shape === "ellipse"
      ? gen.ellipse(s.x + s.w / 2, s.y + s.h / 2, s.w, s.h, o)
      : gen.rectangle(s.x, s.y, s.w, s.h, o);
  };
  const nodes = Object.fromEntries(spec.nodes.map((n) => [n.id, n]));
  const body = [
    text(spec.width / 2, 30, spec.title, 24),
    ...(spec.groups ?? []).map(
      (g) =>
        paths(shape(g, { stroke: g.fill, strokeWidth: 3 }), true) +
        text(g.x + 12, g.y + 18, g.label, 15, "start"),
    ),
    ...spec.edges.map((e) => arrow(nodes[e.from], nodes[e.to], e, seed++)),
    ...spec.nodes.map((n) => paths(shape(n, { fill: n.fill })) + text(n.x + n.w / 2, n.y + n.h / 2, n.label, n.size ?? 15)),
    ...(spec.notes ?? []).map((n) => text(n.x, n.y, n.text, 13, "start")),
  ];
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${spec.width} ${spec.height}" width="${spec.width}" height="${spec.height}"><rect width="100%" height="100%" fill="#ffffff"/>${body.join("")}</svg>\n`;
}

mkdirSync(OUT, { recursive: true });
for (const file of readdirSync(join(HERE, "specs")).filter((f) => f.endsWith(".json")).sort()) {
  const spec = JSON.parse(readFileSync(join(HERE, "specs", file), "utf8"));
  writeFileSync(join(OUT, file.replace(/\.json$/, ".svg")), render(spec));
  console.log(`docs/diagrams/${file.replace(/\.json$/, ".svg")}`);
}
