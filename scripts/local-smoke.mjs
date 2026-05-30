import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
assert.match(readme, /PAPERCLIP-READINESS-DIGEST-DRYRUN-002/);
console.log("Skeleton smoke passed; executable implementation is assigned to VOL-137/VOL-138.");

