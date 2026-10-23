# Runbook: periodic worker (offer maintenance)

## Purpose

Run the Procrastinate worker that also defers periodic tasks, including
`offer-maintenance` (2x/day at 08:00 and 20:00).

## Prerequisites

- PostgreSQL reachable via `DATABASE_URL`.
- Migrations applied (periodic defers table present).

## Start the worker with periodic enabled

```bash
procrastinate --app=app.jobs.app.app worker --periodic
```

Or via the helper:

```bash
python -m procrastinate --app=app.jobs.app.app worker --periodic
```

## Notes

- `--periodic` makes the worker process responsible for deferring periodic tasks.
  Run exactly one worker instance with `--periodic` to avoid duplicate defers.
- Other worker instances (without `--periodic`) can run concurrently for throughput.
- Maintenance task: `run_maintenance_task` (`periodic_id=offer-maintenance`).
- Failures are isolated per source; inspect logs for `[ALERT]` lines.

## Rollback

Stop the periodic worker; periodic defers stop. Existing queued jobs still process.