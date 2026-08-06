import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the Antarctic Atlas landing page", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Antarctic Research Atlas<\/title>/i);
  assert.match(html, /See Antarctica/);
  assert.match(html, /Research Universe/);
  assert.match(html, /Antarctic System/);
  assert.match(html, /Mini Research Lab/);
  assert.match(html, /https:\/\/antarctic-research-atlas\.streamlit\.app\//);
});

test("source keeps the current product identity and navigation", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /Antarctic Atlas/);
  assert.match(page, /href="#explore"/);
  assert.match(page, /href="#about"/);
  assert.match(layout, /title:\s*"Antarctic Research Atlas"/);
  assert.match(
    layout,
    /interactive, visual atlas for exploring Antarctic Ice Sheet science/i,
  );
  assert.match(packageJson, /"name": "antarctic-atlas-site"/);
  assert.doesNotMatch(page, /Your site is taking shape|Codex is working/);
});
