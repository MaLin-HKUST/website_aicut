# rel0415-ui Current Status

- The redesign is anchored to the screenshot set under `HarnessPlan/rel0415/page-pic/`.
- The rel0415 frontend now shares one screenshot-led Chinese shell across `welcome`, `tts`, `smart-cut`, and `tasks`.
- The login page has been restored to the Chinese dual-panel layout while preserving existing auth redirects.
- User-facing Playwright coverage now exercises route smoke, login-to-workspace navigation, and the Smart Cut task flow.
- The release gate passes on build and the rel0415 Playwright suite; admin and backend contracts remain intentionally out of scope.
