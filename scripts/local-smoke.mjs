import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
const evidence = await readFile(
  new URL("../docs/second-slice-github-dry-run-repo-evidence.md", import.meta.url),
  "utf8",
);

assert.match(readme, /Second Slice Readiness Digest Dry-Run Repo/);
assert.match(readme, /ops\/ci\/smoke_readiness_digest\.sh/);
assert.match(evidence, /Issue: VOL-150/);
assert.match(evidence, /bounded readiness digest smoke passed/);
console.log("Repository smoke passed for the externalized second-slice dry-run repo.");
