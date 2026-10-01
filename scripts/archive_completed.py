"""
Archive completed tasks finished more than N days ago (default 60) to files,
and optionally remove them from the server.

Writes to archive/ (gitignored):
  completed-<timestamp>.ics   every archived task with all its original properties
                              (importable into any CalDAV client)
  completed-<timestamp>.csv   readable summary: title, completed, due, tags, repeat, notes

    python scripts/archive_completed.py                    # preview only
    python scripts/archive_completed.py --apply            # write the archive, keep tasks on the server
    python scripts/archive_completed.py --apply --remove   # write the archive, verify it, then delete
    python scripts/archive_completed.py --days 365 --out ~/TaskArchive
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from completed_common import ROOT, connect, delete_selected, finished_at, select_old_completed  # noqa: E402
from icalendar import Calendar  # noqa: E402


def repeat_text(t) -> str:
    return f'after done {t.recur_after}' if t.recur_after else (t.rrule or '')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=60)
    ap.add_argument('--out', type=Path, default=ROOT / 'archive')
    ap.add_argument('--apply', action='store_true', help='write the archive files')
    ap.add_argument('--remove', action='store_true', help='with --apply: delete archived tasks from the server')
    args = ap.parse_args()
    if args.remove and not args.apply:
        ap.error('--remove needs --apply')

    svc = connect()
    sel = select_old_completed(svc, args.days)
    tasks = sel.everything

    print(f'Completed tasks finished before {sel.cutoff.date()} ({args.days} days ago): {len(sel.tasks)}')
    if sel.pulled_in:
        print(f'  plus {len(sel.pulled_in)} recently completed subtasks of those (they go with their parent)')
    if sel.without_completed_date:
        print(f'  {sel.without_completed_date} had no completion date (used last-modified instead)')
    for t in sel.skipped:
        print(f'  skipped (has open subtasks): {t.title}')
    print()
    for t in tasks:
        when = finished_at(t)
        print(f'  {str(when.date()) if when else "?":10}  {t.title}')

    if not args.apply:
        print(f'\nPreview only. Nothing was written. --apply writes the archive; add --remove to also delete.')
        return 0
    if not tasks:
        print('\nNothing to archive.')
        return 0

    # ---- write the archive
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    ics_path, csv_path = out / f'completed-{stamp}.ics', out / f'completed-{stamp}.csv'

    archive = Calendar()
    archive.add('PRODID', '-//TaskWeb archive//EN')
    archive.add('VERSION', '2.0')
    seen_tz = set()
    for t in tasks:
        for comp in Calendar.from_ical(svc.raw(t.uid)).subcomponents:
            if comp.name == 'VTIMEZONE':
                tzid = str(comp.get('TZID'))
                if tzid in seen_tz:
                    continue
                seen_tz.add(tzid)
            if comp.name in ('VTODO', 'VTIMEZONE'):
                archive.add_component(comp)
    ics_path.write_bytes(archive.to_ical())

    with csv_path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['title', 'completed', 'due', 'tags', 'priority', 'repeat', 'place', 'parent_uid', 'notes', 'uid'])
        for t in tasks:
            w.writerow([t.title, t.completed_at or '', t.due or '', ', '.join(t.tags), t.priority or '',
                        repeat_text(t), t.location, t.parent_uid or '', t.notes, t.uid])

    # ---- verify before anything is deleted
    archived = {str(c.get('UID')) for c in Calendar.from_ical(ics_path.read_bytes()).walk('VTODO')}
    missing = [t.title for t in tasks if t.uid not in archived]
    if missing:
        print(f'\nArchive check FAILED; {len(missing)} tasks missing from {ics_path}. Nothing deleted.', file=sys.stderr)
        return 1
    print(f'\nArchived {len(tasks)} tasks:\n  {ics_path}\n  {csv_path}')

    if not args.remove:
        print('Tasks were left on the server. Rerun with --apply --remove to delete them.')
        return 0

    deleted, errors = delete_selected(svc, sel)
    for e in errors:
        print(f'  FAILED: {e}', file=sys.stderr)
    print(f'Removed {len(deleted)} from the server, failed {len(errors)}.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
