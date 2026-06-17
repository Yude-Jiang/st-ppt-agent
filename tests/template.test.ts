import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

describe("template baseline files", () => {
  it("contains metadata and firebase blueprint", () => {
    const root = process.cwd();
    const metadataPath = path.join(root, "metadata.json");
    const blueprintPath = path.join(root, "firebase-blueprint.json");

    assert.equal(fs.existsSync(metadataPath), true);
    assert.equal(fs.existsSync(blueprintPath), true);
  });
});
