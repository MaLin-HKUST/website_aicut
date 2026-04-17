# rel0415-ui Release Gate

- Completed features: 10/10
- Build status: pass
- Playwright status: pass

## Build Output
```text
> build
> next build

   ▲ Next.js 15.4.6

   Creating an optimized production build ...
 ✓ Compiled successfully in 0ms
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/12) ...
   Generating static pages (3/12) 
   Generating static pages (6/12) 
   Generating static pages (9/12) 
 ✓ Generating static pages (12/12)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                      127 B        99.7 kB
├ ○ /_not-found                            990 B         101 kB
├ ○ /admin                               8.01 kB         115 kB
├ ○ /admin/tasks                         4.52 kB         112 kB
├ ƒ /api/proxy/[...path]                   127 B        99.7 kB
├ ○ /icon.svg                                0 B            0 B
├ ○ /login                                1.9 kB         109 kB
├ ○ /smart-cut                             163 B         118 kB
├ ƒ /smart-cut/[taskId]                    163 B         118 kB
├ ○ /tasks                               4.93 kB         112 kB
├ ○ /tts                                 5.58 kB         113 kB
└ ○ /welcome                             3.85 kB         111 kB
+ First Load JS shared by all            99.6 kB
  ├ chunks/4bd1b696-cf72ae8a39fa05aa.js  54.1 kB
  ├ chunks/964-7a34cadcb7695cec.js       43.5 kB
  └ other shared chunks (total)          1.93 kB


○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

## Playwright Output
```text
Running 7 tests using 4 workers

  ✓  2 [chromium] › tests/rel0415-live-routes.spec.ts:79:7 › rel0415 route loads: /login (3.2s)
  ✓  3 [chromium] › tests/rel0415-live-routes.spec.ts:79:7 › rel0415 route loads: /tts (3.6s)
  ✓  1 [chromium] › tests/rel0415-live-routes.spec.ts:79:7 › rel0415 route loads: /welcome (3.8s)
  ✓  4 [chromium] › tests/rel0415-live-routes.spec.ts:79:7 › rel0415 route loads: /smart-cut (3.8s)
  ✓  5 [chromium] › tests/rel0415-live-routes.spec.ts:79:7 › rel0415 route loads: /tasks (2.8s)
  ✓  6 [chromium] › tests/rel0415-user-navigation.spec.ts:111:5 › rel0415 user can navigate login welcome tts smart-cut and tasks (5.2s)
  ✓  7 [chromium] › tests/smart-cut.spec.ts:3:5 › user can enter smart cut workspace and submit preview/finalize actions (5.3s)

  7 passed (18.7s)
[2m[WebServer] [22m(node:23438) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m(node:23582) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
(node:23586) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23586) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23587) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23587) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23584) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23585) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23585) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:23584) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m(node:23787) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22mTypeError: fetch failed
[2m[WebServer] [22m    at async handler (app/api/proxy/[...path]/route.ts:27:19)
[2m[WebServer] [22m[0m [90m 25 |[39m   }
[2m[WebServer] [22m [90m 26 |[39m
[2m[WebServer] [22m[31m[1m>[22m[39m[90m 27 |[39m   [36mconst[39m response [33m=[39m [36mawait[39m fetch(url[33m,[39m init)[33m;[39m
[2m[WebServer] [22m [90m    |[39m                   [31m[1m^[22m[39m
[2m[WebServer] [22m [90m 28 |[39m   [36mreturn[39m [36mnew[39m [33mResponse[39m(response[33m.[39mbody[33m,[39m {
[2m[WebServer] [22m [90m 29 |[39m     status[33m:[39m response[33m.[39mstatus[33m,[39m
[2m[WebServer] [22m [90m 30 |[39m     statusText[33m:[39m response[33m.[39mstatusText[33m,[39m[0m {
[2m[WebServer] [22m  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8000
[2m[WebServer] [22m      at <unknown> (Error: connect ECONNREFUSED 127.0.0.1:8000) {
[2m[WebServer] [22m    errno: [33m-61[39m,
[2m[WebServer] [22m    code: [32m'ECONNREFUSED'[39m,
[2m[WebServer] [22m    syscall: [32m'connect'[39m,
[2m[WebServer] [22m    address: [32m'127.0.0.1'[39m,
[2m[WebServer] [22m    port: [33m8000[39m
[2m[WebServer] [22m  }
[2m[WebServer] [22m}
[2m[WebServer] [22mTypeError: fetch failed
[2m[WebServer] [22m    at async handler (app/api/proxy/[...path]/route.ts:27:19)
[2m[WebServer] [22m[0m [90m 25 |[39m   }
[2m[WebServer] [22m [90m 26 |[39m
[2m[WebServer] [22m[31m[1m>[22m[39m[90m 27 |[39m   [36mconst[39m response [33m=[39m [36mawait[39m fetch(url[33m,[39m init)[33m;[39m
[2m[WebServer] [22m [90m    |[39m                   [31m[1m^[22m[39m
[2m[WebServer] [22m [90m 28 |[39m   [36mreturn[39m [36mnew[39m [33mResponse[39m(response[33m.[39mbody[33m,[39m {
[2m[WebServer] [22m [90m 29 |[39m     status[33m:[39m response[33m.[39mstatus[33m,[39m
[2m[WebServer] [22m [90m 30 |[39m     statusText[33m:[39m response[33m.[39mstatusText[33m,[39m[0m {
[2m[WebServer] [22m  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8000
[2m[WebServer] [22m      at <unknown> (Error: connect ECONNREFUSED 127.0.0.1:8000) {
[2m[WebServer] [22m    errno: [33m-61[39m,
[2m[WebServer] [22m    code: [32m'ECONNREFUSED'[39m,
[2m[WebServer] [22m    syscall: [32m'connect'[39m,
[2m[WebServer] [22m    address: [32m'127.0.0.1'[39m,
[2m[WebServer] [22m    port: [33m8000[39m
[2m[WebServer] [22m  }
[2m[WebServer] [22m}
[2m[WebServer] [22m(node:23788) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22m(node:23789) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
[2m[WebServer] [22mTypeError: fetch failed
[2m[WebServer] [22m    at async handler (app/api/proxy/[...path]/route.ts:27:19)
[2m[WebServer] [22m[0m [90m 25 |[39m   }
[2m[WebServer] [22m [90m 26 |[39m
[2m[WebServer] [22m[31m[1m>[22m[39m[90m 27 |[39m   [36mconst[39m response [33m=[39m [36mawait[39m fetch(url[33m,[39m init)[33m;[39m
[2m[WebServer] [22m [90m    |[39m                   [31m[1m^[22m[39m
[2m[WebServer] [22m [90m 28 |[39m   [36mreturn[39m [36mnew[39m [33mResponse[39m(response[33m.[39mbody[33m,[39m {
[2m[WebServer] [22m [90m 29 |[39m     status[33m:[39m response[33m.[39mstatus[33m,[39m
[2m[WebServer] [22m [90m 30 |[39m     statusText[33m:[39m response[33m.[39mstatusText[33m,[39m[0m {
[2m[WebServer] [22m  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8000
[2m[WebServer] [22m      at <unknown> (Error: connect ECONNREFUSED 127.0.0.1:8000) {
[2m[WebServer] [22m    errno: [33m-61[39m,
[2m[WebServer] [22m    code: [32m'ECONNREFUSED'[39m,
[2m[WebServer] [22m    syscall: [32m'connect'[39m,
[2m[WebServer] [22m    address: [32m'127.0.0.1'[39m,
[2m[WebServer] [22m    port: [33m8000[39m
[2m[WebServer] [22m  }
[2m[WebServer] [22m}
[2m[WebServer] [22mTypeError: fetch failed
[2m[WebServer] [22m    at async handler (app/api/proxy/[...path]/route.ts:27:19)
[2m[WebServer] [22m[0m [90m 25 |[39m   }
[2m[WebServer] [22m [90m 26 |[39m
[2m[WebServer] [22m[31m[1m>[22m[39m[90m 27 |[39m   [36mconst[39m response [33m=[39m [36mawait[39m fetch(url[33m,[39m init)[33m;[39m
[2m[WebServer] [22m [90m    |[39m                   [31m[1m^[22m[39m
[2m[WebServer] [22m [90m 28 |[39m   [36mreturn[39m [36mnew[39m [33mResponse[39m(response[33m.[39mbody[33m,[39m {
[2m[WebServer] [22m [90m 29 |[39m     status[33m:[39m response[33m.[39mstatus[33m,[39m
[2m[WebServer] [22m [90m 30 |[39m     statusText[33m:[39m response[33m.[39mstatusText[33m,[39m[0m {
[2m[WebServer] [22m  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8000
[2m[WebServer] [22m      at <unknown> (Error: connect ECONNREFUSED 127.0.0.1:8000) {
[2m[WebServer] [22m    errno: [33m-61[39m,
[2m[WebServer] [22m    code: [32m'ECONNREFUSED'[39m,
[2m[WebServer] [22m    syscall: [32m'connect'[39m,
[2m[WebServer] [22m    address: [32m'127.0.0.1'[39m,
[2m[WebServer] [22m    port: [33m8000[39m
[2m[WebServer] [22m  }
[2m[WebServer] [22m}
[2m[WebServer] [22m(node:23790) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
[2m[WebServer] [22m(Use `node --trace-warnings ...` to show where the warning was created)
```
