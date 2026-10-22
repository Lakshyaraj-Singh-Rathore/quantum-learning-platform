# Phase 6 — Gemini in the QML Lab

**Scope:** §2F. **Base:** `main @ 6dba64e`, 610 tracked files.
**Stopped at WP5.** WP6 (suggest-a-configuration) was not started — see §7.

---

## 1. What shipped

| WP | Deliverable | State |
| --- | --- | --- |
| 1 | `services/qml_ai.py` — prompt built from the stored payload, `MAX_PROMPT_CHARS` rejects rather than truncates, system instruction forbids invented values | **done** |
| 2 | `POST /qml/experiments/{id}/explain` — flag-gated, authenticated, 404→403 ownership, 503 on `GeminiUnavailable` | **done** |
| 3 | Unconfigured path automated to exhaustion | **done** |
| 4 | Configured path against a labelled fake; live call registered as **MT-010** | **done** |
| 5 | `QmlExplanationPanel` extending the Results view | **done** |
| 6 | Suggest-a-configuration | **not started, deliberately** (§7) |

**Files changed:** 4 backend (`services/qml_ai.py` new, `ai/gemini_client.py`,
`api/qml_lab.py`, + 2 test files), 4 frontend (`QmlExplanationPanel.tsx` new, `api/qml.ts`,
`pages/QmlLabPage.tsx`, `scripts/qml-task-check.mts`), 2 docs.

**Tracked files 610 → 614**, itemised — 4 added, 0 removed, 0 renamed:

| New file | |
| --- | --- |
| `backend/app/services/qml_ai.py` | the service |
| `backend/tests/test_qml_ai.py` | its 14 tests |
| `frontend/web/src/components/qml/QmlExplanationPanel.tsx` | the panel |
| `docs/qml/phase-6-report.md` | this report |

The other 7 changed files are edits in place.

### §4 allow-list justification

§4 does not list the AI paths, so each is justified:

| File | Why |
| --- | --- |
| `app/services/qml_ai.py` | **new**; the feature itself, mirroring `services/codelab_ai.py` |
| `app/api/qml_lab.py` | **append-only**: one route + two imports. No existing route altered |
| `app/ai/gemini_client.py` | **one signature, one literal** — `temperature` kwarg, default `1.0`. See below |
| `tests/test_qml_ai.py`, `tests/test_qml_api.py` | tests |

**`gemini_client.generate()` is the only shared file touched.** The change adds
`temperature: float = 1.0` and replaces the hardcoded `"temperature": 1.0` with it. All three
existing callers — `ai/chat.py:101`, `services/assignment_ai.py:326`, `services/codelab_ai.py:92`
— pass no `temperature` and are therefore bit-identical. The QML path passes `0.2`, because the
entire risk of this feature is confabulation and 1.0 is a strange default for it.

---

## 2. Gates

| Gate | Required | Measured |
| --- | --- | --- |
| `pytest` | grows from 1208 / 5, 0 regressions | **1230 passed, 5 skipped** (+22) ✅ |
| `ruff` | no new vs `origin/main`'s 79 | **79 → 79. New: 0. Fixed: 0** ✅ |
| `npm run typecheck` | 0 | **0** ✅ |
| `npm run build` | PASS | **✓ built in 8.48s** ✅ |
| Shared bundle | byte-identical | **640793 = 640793 bytes** ✅ (see §3) |
| `QmlLabPage` chunk | report it | **45740 → 49363 bytes** (+3623, +7.9%) ⚠️ §3 |
| `qml:tasks` | 48/48 | **55/55** — 48 unchanged + 7 new ⚠️ §3 |
| render · ui · circuit | 34 · 58 · 49, 0 fail | **34 · 58 · 49, 0 fail** ✅ |
| Goldens @ 1e-9 | 190 + 804 + 3306 | **190 + 804 + 3306** ✅ |
| a11y | 0 criticals | **0 criticals** ✅ |
| CSS rule diff | justify any change | **1 added / 0 changed / 0 removed** ✅ |
| §2A.6 flag states | 4 live, new route 404 when off | **4/4** ✅ |
| `requirements.txt` / pins / celery 8/15 / `qml_enabled=False` / `rag.py` | untouched | **all untouched** (0 diff lines each) ✅ |

### Flag states, live

```
QML_ENABLED=true   /features                        -> 200 {"qml_enabled":true}
QML_ENABLED=true   /qml/describe                    -> 401
QML_ENABLED=true   POST /qml/experiments/1/explain  -> 401     <-- new
QML_ENABLED=false  /features                        -> 200 {"qml_enabled":false}
QML_ENABLED=false  /qml/describe                    -> 404
QML_ENABLED=false  POST /qml/experiments/1/explain  -> 404     <-- new
```

The new route is in `QML_PATHS`, so the existing flag-off sweep now covers it too.

### CSS

```
baseline rules 1803   ours 1804
ADDED 1   CHANGED 0   REMOVED 0
  + @layer utilities .whitespace-pre-wrap
```

One Tailwind utility, used by the offline-explanation block. No existing rule changed.

---

## 3. Three numbers that moved, and why

**Shared bundle — held at byte-identical, but only after measuring.** The first build came out
**640802 bytes against main's 640793: +9.** Normalising every content hash showed the divergence
was not a hash cascade but one extra export alias in the shared chunk's export map. Cause: the
panel imported the lucide `Info` icon, which no other module uses, so the shared chunk had to
export one more binding. Swapping it out returned the bundle to **640793 — exactly main**. The
`EmptyState` now ships with no icon, and the reason is a comment at that line. A 9-byte regression
is not important in itself; being unable to explain it would have been.

**`QmlLabPage` 45740 → 49363 bytes (+3623, +7.9%).** Entirely the new panel: the component, its
grounding table, and the `useMutation` wiring. It is confined to the lazy chunk. For context the
growth is a third of Phase 5c's (+53%), and the shared bundle is unchanged.

**`qml:tasks` 48 → 55.** The gate said "stays 48/48". All 48 pre-existing assertions still pass
unchanged; the 7 new ones cover the explanation panel. Flagging the number rather than quietly
reporting 55/55 as if it were the stated gate.

---

## 4. Grounding, and how it is enforced rather than requested

§2F.2 calls grounding structural. Three mechanisms, only one of which depends on the model:

1. **`build_prompt` renders every figure from the stored result.** The model is never asked to
   recall a number. Asserted on hand-read literals from the captured payload — `0.7778`,
   `0.6923`, `0.8182`, `[[5, 4], [0, 9]]`, `0.9048` for classification; `0.5954`, `0.6679`,
   `0.1582` and the signed `-2.0602` for regression. Asserting via the module's own `_fmt` would
   have restated the implementation, so the literals are hardcoded.
2. **`grounded_on` returns the same facts to the client**, and the panel prints them beneath the
   prose. A fabricated number sits directly under the true one.
3. **The system instruction forbids introducing values.** This is the only part that relies on
   the model complying, which is exactly why MT-010 exists.

**Metric vocabularies are disjoint, asserted in both directions:** a regression prompt contains
none of `accuracy`/`precision`/`recall`/`f1`/`confusion`, and a classification prompt contains
none of `r2`/`mae`/`rmse`, over the **whole** prompt.

> An earlier version of that test read
> `assert "accuracy" not in prompt.lower().split("TASK")[0]`. Lowercasing first meant it split on
> `- task: regression` in line 3 and inspected **45 of 847 characters** — it would have passed on
> a prompt full of accuracies. Found by printing what the assertion actually looked at, before
> the mutation campaign, not by it.

**Over-length rejects, never truncates.** The tail of the prompt is the baseline and the epoch
history, so truncation would remove the evidence and keep the confidence. 422, with the real
runs measured at well inside the 8,000-character budget.

---

## 5. Mutation testing

**Service and prompt — 6 mutants, 6 caught, 0 survivors:**

| Mutant | Caught by |
| --- | --- |
| M1 drop the TEST METRICS block | 2 grounding tests |
| M2 `_fmt` rounds to 2dp | 4 tests (prompt, offline, fake transport) |
| M3 over-length truncates instead of raising | the rejection test |
| M4 offline path degrades to `"AI unavailable."` | 2 unconfigured tests |
| M5 explain reverts to `temperature=1.0` | the fake-transport test |
| M6 `grounded_on` returns `{}` | 2 tests |

**Route — 2 mutants, 2 caught:** removing the ownership helper fails the cross-user 403 test;
removing the `GeminiUnavailable` handler fails the 503 test.

**UI — 2 mutants, 1 initially SURVIVED.**

- F1 (render prose inside a `<dl>` with `tabular-nums`) → caught by 2 assertions.
- **F2 (delete the evaluation metrics from the grounding table) → passed.** The assertion was
  `grounding.includes("0.7778")`, and the *baseline* block also renders `0.7778`
  (`test_accuracy`). The test was green because a different table happened to contain the same
  string. Re-pointed at `0.6923` and `0.8182`, which appear only in the evaluation block; F2 now
  fails as it should.

That survivor is the same family as Phase 3's and Phase 5's: **a value that is not unique to the
thing under test is not evidence about that thing.** Previously it was zeros; here it was a
duplicated float.

---

## 6. What these tests do **not** prove

Said plainly, per §8 and the `.apply()` standard from 5b:

- **The live Gemini call has never executed.** `GEMINI_API_KEY` is absent here and
  `is_configured()` also requires an importable SDK. Every "configured path" test runs against a
  fake function substituted with `monkeypatch`, named as a fake in the test name.
- **Nothing proves Gemini obeys the system instruction.** The prompt is provably grounded; the
  *reply* is not verified against it by any code. That is MT-010, and it is marked blocking.
- The platform already carries an untested live Gemini path (tutor, Code Lab, Smart Composer).
  This phase adds a fourth caller — it does not add the first instance of that risk.
- **No browser has rendered the panel.** As in 5c, every frontend claim is server-side rendering:
  no layout, no CSS cascade, no hover or focus, no portal, no `useMutation` ever actually
  dispatched. The idle state is SSR-observable; the loading, configured and unconfigured states
  are asserted by rendering their presentational components directly.
- Carried forward unchanged: no target-machine numbers, no Redis/Celery broker, no docker, no
  GPU, nothing OOM-killed, Linux not Windows. **MT-001 still blocks Phase 8.**

---

## 7. WP6 not started — the stopping point

WP1–WP5 are complete and green, so WP6 was permitted. It was not started, and the reason is the
instruction's own: *"An impossible suggestion that is rejected or regenerated beats one that is
surfaced and 422s on click."*

Doing it properly means a second service path, a second route, server-side validation through
`limits.check()` **and** `supports{}` for four algorithms, a regeneration loop, UI, and a mutation
campaign against suggestions that are invalid in each of the distinct ways (over a per-algorithm
cap, a task-mismatched dataset, `n_hidden` on a non-hybrid, `diff_method` on a closed-form fit).
That is a phase's worth of work, and a half-built version of it is precisely the defect class
§2F.3 names. Reporting the stopping point instead, as instructed.

**Carried into Phase 7 unchanged**, along with: the `QmlLabPage` chunk now at 49363 bytes, and
the un-rendered UI, which is larger after this phase than before it.

---

## 8. §8A split

**Automated: 187.** 165 before this phase, +22: `tests/test_qml_ai.py` (14) and
`tests/test_qml_api.py` (+8 — 7 explain-route tests plus the flag-off sweep gaining the new
path). Frontend: `qml:tasks` 48 → 55.

**Deferred: 5, by ID.** MT-006 (visual half, unchanged from 5c), MT-007, MT-008, MT-009, and
**MT-010** (new — the live Gemini call). MT-001…MT-005 remain the laptop pre-enablement set.
No ID was reused or renumbered.
