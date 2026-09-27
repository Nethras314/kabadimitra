# Recycler Verification

> Phase 4 deliverable. A recycler is never auto-verified.

## 1. Model

Verification is stored on `recycler_authorizations`: authorization number,
issuing authority, type, issue/expiry date, verification source/date, and
`status` (`verified | pending | expiring | expired | suspended`).

## 2. Effective verification

`app/recyclers.py:effective_verification()` derives the **effective** status:

- `verified` only if some authorization has `status = verified` **and** its
  `expiry_date` is today or later (or null).
- a `verified` authorization whose expiry date has passed resolves to `expired`.
- otherwise the latest authorization's stored status is used.

**Expired authorizations exclude the recycler from matching** (FR-VERIF-04).

## 3. Endpoints

| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| POST | `/api/v1/recycler/organizations` | `platform_admin`/`recycler` | onboard org + facility + authorization |
| GET | `/api/v1/recycler/organizations` | `platform_admin` | list all |
| GET | `/api/v1/recycler/organizations/{id}` | `platform_admin` | detail + effective status |
| GET | `/api/v1/recycler/verified` | authenticated | verified, non-expired recyclers (for matching) |

## 4. Open items

- Scheduled status flip (`verified -> expiring -> expired`) as expiry approaches
  (a worker/trigger in a later phase).
- Document/evidence storage and review workflow for `pending` applications.
