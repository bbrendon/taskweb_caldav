"""
Delete completed tasks finished more than N days ago (default 60).

"Finished" is the COMPLETED timestamp; tasks marked completed without one fall back
to LAST-MODIFIED. Open tasks and repeating "after done" tasks are never deleted.
A completed task that still has open subtasks is skipped (the subtasks would be
orphaned), and reported.

    python scripts/purge_completed.py                 # preview only
    python scripts/purge_completed.py --apply         # fresh backup, then delete
    python scripts/purge_completed.py --days 90
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from backup_calendar import load_env, main as backup  # noqa: E402
from dateutil.parser import isoparse  # noqa: E402
from task_caldav_lib import CalDAVService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=60)
    ap.add_argument('--apply', action='store_true', help='delete (after a fresh backup)')
    args = ap.parse_args()

    load_env(ROOT / '.env')
    svc = CalDAVService(
        os.environ['CALDAV_URL'], os.environ['CALDAV_USERNAME'], os.environ['CALDAV_PASSWORD'],
        os.environ.get('CALDAV_CALENDAR', 'Tasks'), tz='America/Los_Angeles',
    )
    svc.refresh()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    tasks = svc.tasks()

    purge, skipped, no_date = [], [], 0
    for t in tasks:
        if t.status not in ('COMPLETED', 'CANCELLED') or t.recur_after:
            continue
        stamp = t.completed_at or t.last_modified
        if not stamp:
            continue
        finished = isoparse(stamp)
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        if finished >= cutoff:
            continue
        if any(c.is_open for c in svc.descendants(t.uid)):
            skipped.append(t)
            continue
        no_date += not t.completed_at
        purge.append((finished, t))
    purge.sort(key=lambda x: x[0])

    kept_done = sum(1 for t in tasks if not t.is_open) - len(purge)
    print(f'Completed tasks finished before {cutoff.date()} ({args.days} days ago): {len(purge)} to delete')
    if purge:
        print(f'  oldest finished {purge[0][0].date()}, newest {purge[-1][0].date()}')
        print(f'  {no_date} of them had no completion date (used last-modified instead)')
    print(f'Keeping: {sum(t.is_open for t in tasks)} open tasks, {kept_done} completed tasks')
    for t in skipped:
        print(f'  skipped (has open subtasks): {t.title}')
    print()
    for finished, t in purge:
        print(f'  {finished.date()}  {t.title}')

    if not args.apply:
        print('\nPreview only. Nothing was deleted. Run with --apply to delete.')
        return 0

    print('\nTaking a fresh backup first...')
    if backup() != 0:
        print('Backup failed; not deleting.', file=sys.stderr)
        return 1
    failed = 0
    deleted: set[str] = set()
    for _, t in purge:
        if t.uid in deleted:  # already removed along with its parent
            continue
        try:
            # children='delete' only ever removes completed descendants: open ones were skipped above
            deleted.update(svc.delete(t.uid, children='delete'))
        except Exception as e:
            failed += 1
            print(f'  FAILED: {t.title}: {e}', file=sys.stderr)
    print(f'\nDeleted {len(deleted)}, failed {failed}.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
