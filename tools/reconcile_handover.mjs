// Independent reader for the synthetic Airworthiness+ reconciliation format.
// Requires Node 24 and Info-ZIP. Never extracts archive files onto the filesystem.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { performance } from 'node:perf_hooks';
import { DatabaseSync } from 'node:sqlite';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const parse = bytes => JSON.parse(bytes.toString('utf8'));

function requireEvidence(condition, message) {
    if (!condition) throw new Error(message);
}

function loadArchive(path, expectedDigest) {
    const archive = resolve(path);
    const unzip = (...args) => execFileSync('unzip', args, { maxBuffer: 16 * 1024 * 1024 });
    const names = unzip('-Z1', archive).toString('utf8').trimEnd().split('\n');
    requireEvidence(new Set(names).size === names.length, 'Duplicate archive member');
    requireEvidence(names.includes('manifest.json'), 'Missing manifest');
    const read = name => unzip('-p', archive, name);
    const raw = read('manifest.json');
    requireEvidence(digest(raw) === expectedDigest, 'Manifest digest differs');
    const manifest = parse(raw);
    requireEvidence(manifest.format === 'Airworthiness+ Records Export' && manifest.version === 1,
        'Unsupported archive format or version');
    const entries = Object.entries(manifest.files);
    requireEvidence(entries.length === names.length - 1, 'Archive members differ from manifest');
    const members = new Map();
    for (const [name, hash] of entries) {
        requireEvidence(/^(README\.txt|people\.json|(records|history)\/[a-z0-9_]+\.(csv|json))$/.test(name)
            && names.includes(name), `Invalid or missing member ${name}`);
        const body = read(name);
        requireEvidence(digest(body) === hash, `Altered archive member ${name}`);
        members.set(name, body);
    }
    return { manifest, members };
}

function readTrial({ manifest, members }, wanted) {
    const owner = manifest.organisation.id;
    const aircraftId = wanted.aircraft_id;
    requireEvidence(owner === wanted.source_organisation_id && manifest.aircraft?.id === aircraftId,
        'Wrong organisation or aircraft');
    const history = {};
    function rows(table) {
        const body = members.get(`records/${table}.json`);
        const events = members.get(`history/${table}.json`);
        requireEvidence(body && events, `Missing records or history for ${table}`);
        const records = parse(body);
        const index = new Map(records.map(record => [record.id, record]));
        requireEvidence(index.size === records.length, `Duplicate record in ${table}`);
        requireEvidence(records.every(record => record.organisation_id === owner), `Wrong owner in ${table}`);
        history[table] = parse(events);
        return index;
    }
    const aircraft = rows('aircraft_aircraft').get(aircraftId);
    const defect = rows('defects_defect').get(wanted.defect_id);
    const task = rows('programme_task').get(wanted.inspection_id);
    const programme = rows('programme_programme').get(task?.programme_id);
    const counter = rows('aircraft_counter').get(task?.counter_id);
    const readings = rows('aircraft_utilisationentry');
    const corrected = readings.get(wanted.corrected_reading_id);
    const original = readings.get(corrected?.supersedes_id);
    const completions = [...rows('programme_workdone').values()]
        .filter(row => row.task_id === task?.id)
        .sort((a, b) => a.dated.localeCompare(b.dated) || a.hours - b.hours);
    const completion = completions.at(-1);
    requireEvidence(aircraft && task && defect && original && corrected && completion
        && aircraft.registration === manifest.aircraft.registration && defect.aircraft_id === aircraftId
        && programme?.aircraft_id === aircraftId && counter?.aircraft_id === aircraftId
        && completions.every(row => row.aircraft_id === aircraftId)
        && original.counter_id === counter.id && corrected.counter_id === counter.id,
    'Missing selected record or broken dependency');
    requireEvidence(defect.decision === 'Deferred' && defect.closed_on === null,
        'Selected defect is not open and deferred');
    requireEvidence(Number.isInteger(task.interval_days) && task.interval_days > 0
        && ['hours', 'cycles', 'months'].every(unit => task[`interval_${unit}`] === null),
    'Unsupported inspection interval');
    requireEvidence(completion.instruction_reference && completion.instruction_revision
        && completion.completion_measurements, 'Inspection completion evidence is incomplete');
    const due = new Date(`${completion.dated}T00:00:00Z`);
    due.setUTCDate(due.getUTCDate() + task.interval_days);
    const actual = {
        source_organisation_id: owner, aircraft_id: aircraft.id, defect_id: defect.id,
        defect_limit_on: defect.limit_on, inspection_id: task.id, inspection_source: task.source,
        completion_id: completion.id, instruction_reference: completion.instruction_reference,
        instruction_revision: completion.instruction_revision,
        completion_measurements: completion.completion_measurements, next_due: due.toISOString().slice(0, 10),
        original_reading_id: original.id, corrected_reading_id: corrected.id,
        original_hours: original.hours, corrected_hours: corrected.hours,
    };
    requireEvidence(Object.keys(actual).length === Object.keys(wanted).length,
        'Wrong number of reconciliation fields');
    const changed = Object.keys(actual).filter(key => actual[key] !== wanted[key]);
    requireEvidence(changed.length === 0, `Reconciliation differs for ${changed.join(', ')}`);
    return { actual, aircraft, defect, task, programme, counter, completion, original, corrected, history };
}

function store(path, owner, aircraft, manifestDigest, evidence) {
    const database = new DatabaseSync(path);
    try {
        database.exec(`CREATE TABLE IF NOT EXISTS aircraft_transfer (
            owner TEXT, aircraft TEXT, manifest_digest TEXT, evidence TEXT,
            PRIMARY KEY(owner, aircraft)) STRICT`);
        const payload = JSON.stringify(evidence);
        const result = database.prepare('INSERT OR IGNORE INTO aircraft_transfer VALUES (?, ?, ?, ?)')
            .run(owner, aircraft, manifestDigest, payload);
        const existing = database.prepare('SELECT * FROM aircraft_transfer WHERE owner = ? AND aircraft = ?')
            .get(owner, aircraft);
        requireEvidence(existing.manifest_digest === manifestDigest && existing.evidence === payload,
            'Existing snapshot differs and needs reconciliation');
        return result.changes === 1;
    } finally {
        database.close();
    }
}

try {
    const began = performance.now();
    const [archivePath, expectedDigest, comparisonPath, databasePath] = process.argv.slice(2);
    requireEvidence(databasePath, 'Usage: node tools/reconcile_handover.mjs ARCHIVE DIGEST COMPARISON SQLITE');
    const comparison = parse(readFileSync(comparisonPath));
    requireEvidence(comparison.format === 'Airworthiness+ Aircraft Handover Reconciliation'
        && comparison.version === 1, 'Unsupported reconciliation format or version');
    const values = readTrial(loadArchive(archivePath, expectedDigest), comparison.records);
    const imported = store(databasePath, values.actual.source_organisation_id, values.actual.aircraft_id,
        expectedDigest, values);
    console.log(JSON.stringify({ imported, seconds: (performance.now() - began) / 1000,
        checked: values.actual, rekeyed: 0, missing_or_changed: 0, issuer_trust: 'Unverified',
        signing_time: 'Unverified', maintenance_authority: 'Unverified' }, null, 2));
} catch (error) {
    console.error(error.message);
    process.exitCode = 1;
}
