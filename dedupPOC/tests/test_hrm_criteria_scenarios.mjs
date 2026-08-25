/* Acceptance tests against "HRM DeDuping Selection Criteria" (the PDF the
 * built-in presets were written from). Two layers:
 *
 *   1. Spec lock — BUILTIN_PRESETS' match columns and rule chains are
 *      asserted to equal the PDF's Primary/First/Second Selection Criteria
 *      table, one dataset at a time, so a future edit that quietly drifts
 *      from the spec fails loudly here instead of only being noticed by a
 *      user's spreadsheet coming out wrong.
 *
 *   2. Scenarios — collapseRows run against small hand-built fixtures per
 *      dataset, proving (not just describing) that: rows are only collapsed
 *      when every concat field matches exactly, the First Selection
 *      Criterion decides when rows tie on the concat fields, and the Second
 *      Selection Criterion decides when they also tie on the first.
 *
 * Assessments carries a known deviation from the PDF: the shipped preset
 * runs an extra "oldest Assessment Date" rule between the count rule and the
 * Assessment ID rule that the PDF never specifies. Kept intentionally (see
 * chat history) rather than trimmed to the spec. Because Assessment Date is
 * itself one of the four concat/match fields, every row inside a duplicate
 * group already shares the same Assessment Date — so that middle rule can
 * never actually separate a tie; "assessments: the undocumented middle rule
 * always ties" below demonstrates that directly, so the dead code stays
 * visible rather than being forgotten.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { loadRules, loadPresets } from "./harness.mjs";

const R = loadRules();
const P = loadPresets();

function byLabel(label){
  const p = (P.BUILTIN_PRESETS || []).find(x => x.label === label);
  assert.ok(p, `no built-in preset named "${label}"`);
  return p;
}

function collapse(rows, keys, chain, tieCol = keys[0]){
  const cellAt = (i, c) => rows[i][c];
  return R.collapseRows({
    n: rows.length,
    cellAt,
    keys,
    norm: R.makeNorm(new Map(), {}),
    anyPfx: false,
    rules: R.buildRules(chain, cellAt, rows.length, true),
    wsBlank: true,
    tie: tieCol,
    sampleLimit: 30,
  });
}

/* Find the sample group whose first row carries `id` in `groupCol` — every
 * fixture below tags its scenario groups through the client-ID column, which
 * is always match field 0 and therefore always identical within a group. */
function groupFor(rows, out, groupCol, id){
  return out.samples.find(s => rows[s.idxs[0]][groupCol] === id);
}

/* ============================================================
   Spec lock — BUILTIN_PRESETS vs. the PDF's criteria table
   ============================================================ */

test("spec: Casenotes concat fields and tie-break order match the PDF", () => {
  const p = byLabel("Casenotes");
  assert.deepEqual(p.match, ["Client ID: HMIS ID", "Entry Date", "Case Note", "NoteWriter"]);
  assert.equal(p.rules.length, 2);
  assert.deepEqual(
    [p.rules[0].type, p.rules[0].parse, p.rules[0].dir, p.rules[0].field],
    ["minmax", "date", "min", "__PICK_LAST_DATE__"],
    "First Selection Criterion: oldest casenote (site picks which date column)"
  );
  assert.deepEqual(
    [p.rules[1].type, p.rules[1].parse, p.rules[1].dir, p.rules[1].field],
    ["minmax", "number", "min", "Casenote: Casenotes"],
    "Second Selection Criterion: lowest numbered casenote"
  );
});

test("spec: Assessments concat fields and First Selection Criterion match the PDF", () => {
  const p = byLabel("Assessments");
  assert.deepEqual(p.match, ["Client ID: HMIS ID", "Assessment Date", "Assessment Type", "Assessor"]);
  assert.deepEqual(
    [p.rules[0].type, p.rules[0].dir, p.rules[0].counts],
    ["count", "max", "above-zero"],
    "First Selection Criterion: highest count of >0 fields"
  );
  assert.deepEqual(p.rules[0].fields, [
    "Disabled", "DV Experience", "__PICK_EMPLOYMENT__", "Health Insurance",
    "Length of Stay", "Living Situation", "Monthly Expenses",
  ]);
});

test("spec: Assessments' final rule is the PDF's Second Selection Criterion (lowest Assessment ID)", () => {
  const p = byLabel("Assessments");
  const last = p.rules[p.rules.length - 1];
  assert.deepEqual(
    [last.type, last.parse, last.dir, last.field],
    ["minmax", "number", "min", "Assessment: HMIS Assessment ID (yyyymmdd)"]
  );
});

test("spec: Assessments carries one extra rule beyond the PDF's two criteria (documented deviation)", () => {
  const p = byLabel("Assessments");
  assert.equal(p.rules.length, 3, "PDF specifies exactly two selection criteria for Assessments");
  const middle = p.rules[1];
  assert.deepEqual(
    [middle.type, middle.parse, middle.dir, middle.field],
    ["minmax", "date", "min", "Assessment Date"],
    "not present in the PDF; kept intentionally, see the file header comment"
  );
});

test("spec: HMIS Services concat fields and tie-break order match the PDF", () => {
  const p = byLabel("HMIS Services");
  assert.deepEqual(p.match, [
    "Client ID: HMIS ID", "Service Date", "__PICK_SERVICE_COMBINED__", "Created by User",
  ]);
  assert.equal(p.rules.length, 2);
  assert.deepEqual(
    [p.rules[0].parse, p.rules[0].dir, p.rules[0].field],
    ["date", "min", "HMIS Service: Created Date"],
    "First Selection Criterion: oldest created date"
  );
  assert.deepEqual(
    [p.rules[1].parse, p.rules[1].dir, p.rules[1].field],
    ["date", "min", "HMIS Service: Last Modified Date"],
    "Second Selection Criterion: oldest last-modified date"
  );
});

test("spec: HRM Services concat fields and tie-break order match the PDF", () => {
  const p = byLabel("HRM Services");
  assert.deepEqual(p.match, ["Client ID: HMIS ID", "Service Date", "Office Visit", "Comments"]);
  assert.equal(p.rules.length, 2);
  assert.deepEqual(
    [p.rules[0].parse, p.rules[0].dir, p.rules[0].field],
    ["date", "min", "HRM Service: Created Date"]
  );
  assert.deepEqual(
    [p.rules[1].parse, p.rules[1].dir, p.rules[1].field],
    ["date", "min", "HRM Service: Last Modified Date"]
  );
});

/* ============================================================
   Casenotes — Client ID, Entry Date, Case Note, NoteWriter
   then oldest [Last] Date, then lowest Casenote number
   ============================================================ */

{
  const CID = 0, ENTRY = 1, NOTE = 2, WRITER = 3, LASTDATE = 4, CNNUM = 5;
  const KEYS = [CID, ENTRY, NOTE, WRITER];
  const CHAIN = [
    { type: "minmax", parse: "date", dir: "min", field: LASTDATE, fmt: "ISO" },
    { type: "minmax", parse: "number", dir: "min", field: CNNUM, strip: "digits" },
  ];

  const ROWS = [
    // G1: dates differ — the earlier Last Date wins outright.
    ["G1", "2026-01-01", "Intake note", "jdoe", "2026-02-10", "CN-500"],
    ["G1", "2026-01-01", "Intake note", "jdoe", "2026-02-05", "CN-900"],
    // G2: Last Dates tie — the lower casenote number wins.
    ["G2", "2026-03-01", "Follow up", "asmith", "2026-04-01", "CN-777"],
    ["G2", "2026-03-01", "Follow up", "asmith", "2026-04-01", "CN-321"],
    // G3: NoteWriter differs — not a duplicate at all, despite everything else matching.
    ["G3", "2026-05-01", "Housing note", "bwong", "2026-06-01", "CN-100"],
    ["G3", "2026-05-01", "Housing note", "kchen", "2026-06-01", "CN-050"],
  ];

  test("casenotes: rows are duplicates only when all four concat fields match", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    assert.equal(out.stats.dupGroups, 2, "G1 and G2 collide; G3's two rows do not");
    assert.equal(out.keptIdx.length, 4, "both G1/G2 winners, plus both G3 rows survive untouched");
    assert.ok(out.keptIdx.includes(4) && out.keptIdx.includes(5), "G3 rows both kept, neither removed");
  });

  test("casenotes: the oldest Last Date wins when it differs", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G1");
    assert.equal(g.decidedBy, 0);
    assert.equal(ROWS[g.winner][LASTDATE], "2026-02-05", "the earlier of the two");
  });

  test("casenotes: a tied Last Date falls to the lowest casenote number", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G2");
    assert.equal(g.trail[0].outcome, "tied", "Last Dates are identical");
    assert.equal(g.decidedBy, 1);
    assert.equal(ROWS[g.winner][CNNUM], "CN-321", "321 < 777 once CN- is stripped");
  });
}

/* ============================================================
   Assessments — Client ID, Assessment Date, Assessment Type, Assessor
   then highest count of >0 fields, then (undocumented) oldest
   Assessment Date, then lowest Assessment ID
   ============================================================ */

{
  const CID = 0, ADATE = 1, ATYPE = 2, ASSESSOR = 3;
  const DISABLED = 4, DV = 5, EMP = 6, HEALTH = 7, LOS = 8, LIVING = 9, MONTHLY = 10;
  const ASSESSID = 11;
  const KEYS = [CID, ADATE, ATYPE, ASSESSOR];
  const CHAIN = [
    { type: "count", dir: "max", counts: "above-zero",
      fields: [DISABLED, DV, EMP, HEALTH, LOS, LIVING, MONTHLY] },
    { type: "minmax", parse: "date", dir: "min", field: ADATE, fmt: "ISO" },
    { type: "minmax", parse: "number", dir: "min", field: ASSESSID, strip: "digits" },
  ];

  const ROWS = [
    // G1: row 0 has five fields above zero, row 1 only one — count decides
    // immediately, even though row 1 has the lower Assessment ID.
    ["G1", "2026-01-01", "Intake", "assessorA", "1", "1", "0", "1", "1", "0", "1", "A-9999"],
    ["G1", "2026-01-01", "Intake", "assessorA", "1", "0", "0", "0", "0", "0", "0", "A-1111"],
    // G2: both rows have exactly three fields above zero — the count ties,
    // and since Assessment Date is itself a match field it also ties, so
    // the lowest Assessment ID decides.
    ["G2", "2026-02-01", "Annual", "assessorB", "1", "1", "1", "0", "0", "0", "0", "A-500"],
    ["G2", "2026-02-01", "Annual", "assessorB", "0", "0", "1", "1", "0", "1", "0", "A-200"],
  ];

  test("assessments: rows are duplicates only when all four concat fields match", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    assert.equal(out.stats.dupGroups, 2);
  });

  test("assessments: the highest count of >0 fields wins, ahead of the Assessment ID", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G1");
    assert.equal(g.decidedBy, 0);
    assert.equal(ROWS[g.winner][ASSESSID], "A-9999",
      "wins on count (5 > 1) despite having the higher Assessment ID");
  });

  test("assessments: a count tie falls through to the lowest Assessment ID", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G2");
    assert.equal(g.trail[0].outcome, "tied", "both rows have exactly 3 fields above zero");
    assert.equal(g.decidedBy, 2, "level 1 (the extra date rule) is skipped over, not what decided it");
    assert.equal(ROWS[g.winner][ASSESSID], "A-200", "200 < 500");
  });

  test("assessments: the undocumented middle rule always ties, because Assessment Date is a match field", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G2");
    assert.equal(g.trail[1].outcome, "tied",
      "every row in a group already shares one Assessment Date value by construction, " +
      "so this rule can never separate a tie in real data");
  });
}

/* ============================================================
   HMIS Services — Client ID, Service Date, Service Combined,
   Created by User, then oldest Created Date, then oldest
   Last Modified Date
   ============================================================ */

{
  const CID = 0, SVCDATE = 1, SVCCOMB = 2, CREATEDBY = 3, CREATED = 4, MODIFIED = 5;
  const KEYS = [CID, SVCDATE, SVCCOMB, CREATEDBY];
  const CHAIN = [
    { type: "minmax", parse: "date", dir: "min", field: CREATED, fmt: "ISO" },
    { type: "minmax", parse: "date", dir: "min", field: MODIFIED, fmt: "ISO" },
  ];

  const ROWS = [
    // G1: Created dates differ.
    ["G1", "2026-01-15", "Bus pass", "uintake1", "2026-01-10", "2026-01-20"],
    ["G1", "2026-01-15", "Bus pass", "uintake1", "2026-01-05", "2026-01-25"],
    // G2: Created dates tie — Last Modified decides.
    ["G2", "2026-02-15", "Meal voucher", "uintake2", "2026-02-01", "2026-02-20"],
    ["G2", "2026-02-15", "Meal voucher", "uintake2", "2026-02-01", "2026-02-10"],
    // G3: Created-by-User differs — not a duplicate.
    ["G3", "2026-03-15", "Clothing", "uintake3", "2026-03-01", "2026-03-05"],
    ["G3", "2026-03-15", "Clothing", "uintake4", "2026-03-01", "2026-03-05"],
  ];

  test("hmis services: rows are duplicates only when all four concat fields match", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    assert.equal(out.stats.dupGroups, 2);
    assert.ok(out.keptIdx.includes(4) && out.keptIdx.includes(5), "both G3 rows survive, unmatched");
  });

  test("hmis services: the oldest Created Date wins when it differs", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G1");
    assert.equal(g.decidedBy, 0);
    assert.equal(ROWS[g.winner][CREATED], "2026-01-05");
  });

  test("hmis services: a tied Created Date falls to the oldest Last Modified Date", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G2");
    assert.equal(g.trail[0].outcome, "tied");
    assert.equal(g.decidedBy, 1);
    assert.equal(ROWS[g.winner][MODIFIED], "2026-02-10");
  });
}

/* ============================================================
   HRM Services — Client ID, Service Date, Office Visit, Comments,
   then oldest Created Date, then oldest Last Modified Date
   ============================================================ */

{
  const CID = 0, SVCDATE = 1, VISIT = 2, COMMENTS = 3, CREATED = 4, MODIFIED = 5;
  const KEYS = [CID, SVCDATE, VISIT, COMMENTS];
  const CHAIN = [
    { type: "minmax", parse: "date", dir: "min", field: CREATED, fmt: "ISO" },
    { type: "minmax", parse: "date", dir: "min", field: MODIFIED, fmt: "ISO" },
  ];

  const ROWS = [
    // G1: Created dates differ.
    ["G1", "2026-01-15", "Yes", "walk-in", "2026-01-10", "2026-01-20"],
    ["G1", "2026-01-15", "Yes", "walk-in", "2026-01-05", "2026-01-25"],
    // G2: Created dates tie — Last Modified decides.
    ["G2", "2026-02-15", "No", "phone check-in", "2026-02-01", "2026-02-20"],
    ["G2", "2026-02-15", "No", "phone check-in", "2026-02-01", "2026-02-10"],
    // G3: Comments differ — not a duplicate.
    ["G3", "2026-03-15", "Yes", "referred to shelter", "2026-03-01", "2026-03-05"],
    ["G3", "2026-03-15", "Yes", "referred to clinic", "2026-03-01", "2026-03-05"],
  ];

  test("hrm services: rows are duplicates only when all four concat fields match", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    assert.equal(out.stats.dupGroups, 2);
    assert.ok(out.keptIdx.includes(4) && out.keptIdx.includes(5), "both G3 rows survive, unmatched");
  });

  test("hrm services: the oldest Created Date wins when it differs", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G1");
    assert.equal(g.decidedBy, 0);
    assert.equal(ROWS[g.winner][CREATED], "2026-01-05");
  });

  test("hrm services: a tied Created Date falls to the oldest Last Modified Date", () => {
    const out = collapse(ROWS, KEYS, CHAIN);
    const g = groupFor(ROWS, out, CID, "G2");
    assert.equal(g.trail[0].outcome, "tied");
    assert.equal(g.decidedBy, 1);
    assert.equal(ROWS[g.winner][MODIFIED], "2026-02-10");
  });
}
