# Cujian Scheduler Release Gate Result

## Metadata
- Date: 2026-04-06T09:02:05.083759+00:00
- Executor: harness-runner
- Mode: auto
- Code Version: planning-stage
- Worker Image Tar: /Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz
- Fake TOS Root: /Volumes/XIAOMA-A-1T/docker_hub/FakeTos

## Summary
- Total Cases: 3
- P0 Total: 3
- P1 Total: 0
- P2 Total: 0
- Release Decision: PASS

## Commands
```bash
/Users/malin13/.pyenv/versions/3.10.18/bin/python -m pytest apps/api/tests/test_scheduler_domain.py apps/api/tests/test_scheduler_api.py -q
```

## Output
```
..............................                                           [100%]
=============================== warnings summary ===============================
apps/api/app/main.py:125
  /Users/malin13/Documents/trae_projects/website_aicut/apps/api/app/main.py:125: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

../../../.pyenv/versions/3.10.18/lib/python3.10/site-packages/fastapi/applications.py:4495
  /Users/malin13/.pyenv/versions/3.10.18/lib/python3.10/site-packages/fastapi/applications.py:4495: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
30 passed, 2 warnings in 1.82s
```

## Error
```

```

## Notes
- Pending features: F05, F06, F07, F08, F09, F10
- Execution record updated: no
- Cleanup verified: no