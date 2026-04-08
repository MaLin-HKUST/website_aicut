# Current Grounded Status

## Part 2: A-machine scheduler center

- `apps/scheduler/` contains scheduler-center service logic.
- The active root `docker-compose.yml` does not yet represent the target A-machine architecture.
- Planning/deployment compose examples exist under `HarnessPlan/cujian_scheduler2/`, but they are not the active product deployment path.
- At least one compose example references `apps/api/Dockerfile.prod`, which does not exist in the main repo.

## Part 3: Worker gateway

- `worker/`, `apps/models/`, `apps/services/`, and `configs/` contain gateway-oriented code.
- The current test/runtime configuration still defaults to SQLite.
- PostgreSQL-backed integration with the shared A-machine scheduler database is not yet proven.
- The desired final architecture is gateway + algorithm image separation, not the combined experimental image as the final production shape.
