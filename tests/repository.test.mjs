import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("repository declares the second-slice mission", async () => {
  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
  assert.match(readme, /Second-slice executable repository/);
  assert.match(readme, /VOL-137/);
  assert.match(readme, /VOL-142/);
});

