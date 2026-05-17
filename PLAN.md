# Security Hardening Plan

1. Add shared ownership helpers for session-scoped job and batch access.
2. Enforce ownership on download, job-config, get-job, cancel, delete, and history-clear routes.
3. Enforce ownership on batch status and batch cancel flows.
4. Enforce ownership on YouTube upload against both session token and job ownership.
5. Validate with static checks and targeted endpoint tests.
