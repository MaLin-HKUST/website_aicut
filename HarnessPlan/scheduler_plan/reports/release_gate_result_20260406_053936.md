# Scheduler Release Gate Result

## Metadata
- Date: 2026-04-06T05:39:36.550504+00:00
- Version: scheduler-harness-v1
- Executor: harness-runner
- Harness mode: harness

## Summary
- Total test functions: 30
- Passed: 30
- Failed: 0

### Case Coverage by Priority
- P0 (阻断级): 50 cases mapped
- P1 (关键级): 14 cases mapped
- P2 (加固级): 2 cases mapped
- Total: 66 cases mapped

## Release Decision: PASS

All P0 and P1 cases are passing. System meets release criteria.

## Verification Evidence

### Commands Executed
```bash
cd /Users/malin13/Documents/trae_projects/website_aicut
python -m pytest apps/api/tests/test_scheduler_domain.py apps/api/tests/test_scheduler_api.py -v
```

### Test Output Summary
```
apps/api/tests/test_scheduler_domain.py::test_error_alarm_and_workspace_retention_cases PASSED [ 80%]
apps/api/tests/test_scheduler_domain.py::test_idempotent_abandon_and_boundary_recovery_rules PASSED [ 83%]
apps/api/tests/test_scheduler_api.py::test_user_resume_and_abandon_flow PASSED [ 86%]
apps/api/tests/test_scheduler_api.py::test_user_create_dispatch_worker_reconcile_and_release PASSED [ 90%]
apps/api/tests/test_scheduler_api.py::test_multistep_suspend_resume_timeout_and_worker_swap PASSED [ 93%]
apps/api/tests/test_scheduler_api.py::test_error_and_alarm_endpoints PASSED [ 96%]
apps/api/tests/test_scheduler_api.py::test_idempotent_edges_and_visibility PASSED [100%]

=============================== warnings summary ===============================
apps/api/app/main.py:114
  /Users/malin13/Documents/trae_projects/website_aicut/apps/api/app/main.py:114: DeprecationWarning: 
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
======================== 30 passed, 2 warnings in 1.44s ========================

```

## Case Catalog Reference
- Catalog file: /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/scheduler_plan/case_catalog.yaml
- All 66 release gate cases mapped to pytest functions

## Notes
- Remaining risks: None identified
- Next recommended feature: See feature_list.json
- See claude-progress.txt for session history