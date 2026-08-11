# Restore Procedure

Restore is a deliberate, risky operation. Always verify the backup file exists
and ideally restore into a throwaway database first.

## Steps

1. Stop writes by stopping the backend:

   ```bash
   docker compose -f /srv/yoga-sys/compose.prod.yml stop backend
   ```

2. Restore into the running database:

   ```bash
   docker compose -f /srv/yoga-sys/compose.prod.yml exec -T postgres \
     pg_restore -U yoga -d yoga_sys --clean --if-exists \
     < /srv/yoga-sys/backups/yoga_sys_<STAMP>.dump
   ```

   If the container's PostgreSQL does not exist yet (fresh server), use:

   ```bash
   gunzip -c backup.dump.gz | docker compose -f /srv/yoga-sys/compose.prod.yml \
     exec -T postgres pg_restore -U yoga -d yoga_sys --clean --if-exists
   ```

3. Start the backend again (migrations run only on demand):

   ```bash
   docker compose -f /srv/yoga-sys/compose.prod.yml start backend
   ```

4. Smoke check:

   ```bash
   curl -s https://yoga.tuitukj.com/healthz
   ```

## Important

- Never restore over a database that has newer migrations unless you also run
  `alembic upgrade head` afterwards.
- Always snapshot a fresh backup immediately before a restore.
