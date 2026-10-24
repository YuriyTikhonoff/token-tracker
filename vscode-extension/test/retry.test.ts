import assert from "node:assert/strict";
import { test } from "node:test";

import { isStale, retryDelaySeconds } from "../src/retry";

test("retries come quickly at first, then back off, then hand over to the regular poll", () => {
  assert.deepEqual([1, 2, 3, 4].map(retryDelaySeconds), [5, 10, 20, 30]);
  assert.equal(retryDelaySeconds(5), null);
  assert.equal(retryDelaySeconds(0), null);
});

test("one failed read is not stale, two in a row are", () => {
  assert.equal(isStale(0), false);
  assert.equal(isStale(1), false);
  assert.equal(isStale(2), true);
});
