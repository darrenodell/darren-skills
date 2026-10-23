#!/usr/bin/env python3
"""Decide which scheduled reports may be checked now. No network or state writes."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

RETRY_SECONDS = 180
DONE = {'primary_verified', 'secondary_reported', 'released', 'cancelled'}


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return parsed.astimezone(timezone.utc)


def plan(state, now):
    now = instant(now) if isinstance(now, str) else now
    deadline = state.get('watch_end_at_utc')
    if deadline and now >= instant(deadline):
        return {'expired': True, 'ready_event_ids': [], 'next_checks': []}
    ready, checks = [], []
    for event in state['events']:
        if event['status'] in DONE:
            continue
        due = instant(event.get('scheduled_at_utc') or event['due_et'])
        attempt = event.get('last_attempt_at_utc')
        attempt = instant(attempt) if attempt else None
        next_at = due
        if attempt and attempt >= due:
            next_at = max(due, attempt + timedelta(seconds=RETRY_SECONDS))
        event_id = event.get('id') or event['name']
        if next_at <= now:
            ready.append(event_id)
        checks.append({'event_id': event_id, 'check_at_utc': next_at.isoformat(),
                       'retry_seconds': RETRY_SECONDS if attempt and attempt >= due else None})
    return {'expired': False, 'ready_event_ids': ready, 'next_checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--now', help='Timezone-aware ISO timestamp; default current UTC')
    args = parser.parse_args()
    try:
        result = plan(json.loads(args.state.read_text()), args.now or datetime.now(timezone.utc))
    except (KeyError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
