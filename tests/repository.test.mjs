import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("repository declares the second-slice mission", async () => {
  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
  assert.match(readme, /Second Slice Readiness Digest Dry-Run Repo/);
  assert.match(readme, /ops\/ci\/smoke_readiness_digest\.sh/);
  assert.match(readme, /CI portability only/);
});
