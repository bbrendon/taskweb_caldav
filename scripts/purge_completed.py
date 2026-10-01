"""
Delete completed tasks finished more than N days ago (default 60), without keeping them.
To keep a copy first, use archive_completed.py --apply --remove instead.

"Finished" is the COMPLETED timestamp; tasks marked completed without one fall back
to LAST-MODIFIED. Open tasks and repeating "after done" tasks are never deleted.
A completed task that still has open subtasks is skipped. Completed subtasks of a
deleted task are deleted with it.

    python scripts/purge_completed.py                 # preview only
    python scripts/purge_completed.py --apply         # fresh full backup, then delete
    python scripts/purge_completed.py --days 90
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backup_calendar import main as backup  # noqa: E402
from completed_common import connect, delete_selected, finished_at, select_old_completed  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=60)
    ap.add_argument('--apply', action='store_true', help='delete (after a fresh backup)')
    args = ap.parse_args()

    svc = connect()
    sel = select_old_completed(svc, args.days)
    all_tasks = svc.tasks()

    print(f'Completed tasks finished before {sel.cutoff.date()} ({args.days} days ago): {len(sel.tasks)} to delete')
    if sel.pulled_in:
        print(f'  plus {len(sel.pulled_in)} recently completed subtasks of those')
    if sel.without_completed_date:
        print(f'  {sel.without_completed_date} had no completion date (used last-modified instead)')
    kept_done = sum(1 for t in all_tasks if not t.is_open) - len(sel.everything)
    print(f'Keeping: {sum(t.is_open for t in all_tasks)} open tasks, {kept_done} completed tasks')
    for t in sel.skipped:
        print(f'  skipped (has open subtasks): {t.title}')
    print()
    for t in sel.everything:
        when = finished_at(t)
        print(f'  {str(when.date()) if when else "?":10}  {t.title}')

    if not args.apply:
        print('\nPreview only. Nothing was deleted. Run with --apply to delete.')
        return 0

    print('\nTaking a fresh backup first...')
    if backup() != 0:
        print('Backup failed; not deleting.', file=sys.stderr)
        return 1
    deleted, errors = delete_selected(svc, sel)
    for e in errors:
        print(f'  FAILED: {e}', file=sys.stderr)
    print(f'\nDeleted {len(deleted)}, failed {len(errors)}.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
