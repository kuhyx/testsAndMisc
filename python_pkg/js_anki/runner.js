// Evaluates each card example and reports its JSON.stringify'd return value.
// Input (stdin): [{"id": "...", "code": "<function body with return>"}]
// Output (stdout): [{"id": "...", "ok": true, "value": "..."} | {"ok": false, "error": "..."}]
"use strict";

const chunks = [];
process.stdin.on("data", (c) => chunks.push(c));
process.stdin.on("end", () => {
  const items = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const out = items.map(({ id, code }) => {
    try {
      const result = new Function(code)();
      const value = result === undefined ? "undefined" : JSON.stringify(result);
      return { id, ok: true, value };
    } catch (err) {
      return { id, ok: false, error: String(err) };
    }
  });
  process.stdout.write(JSON.stringify(out));
});
