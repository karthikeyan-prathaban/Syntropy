# AA go-live and DPDP compliance

This is the non-code track. The application is already built so that Account
Aggregator is one adapter behind `app/ingestion/`, which means nothing here
blocks shipping: statement upload delivers real transactions today, and the AA
adapter switches on once a licence is in place.

## 1. The licence decision

Setu will not grant production access without a regulated-entity licence,
because only a regulated entity can be a Financial Information User under the
RBI's AA framework. The sandbox returns dummy data only.

| Route | Capital requirement | Realistic timeline | Who owns the customer |
| --- | --- | --- | --- |
| SEBI Registered Investment Adviser (non-individual) | ₹50 lakh net worth | 6–9 months | You |
| Partner with an existing regulated FIU | None | 1–3 months | The partner |
| NBFC registration | ₹2 crore net owned funds | 12–18 months | You |

**Recommendation: SEBI RIA.** A personal finance product is advisory in
substance, and the advisory purpose maps directly onto purpose code `101`
already sent in `app/services/setu_client.py`. The partnership route reaches
real data fastest but the partner owns the consent relationship, which makes it
hard to migrate away later.

Non-individual RIA also requires a principal officer with the required
post-graduate qualification and NISM Series X-A and X-B certification, plus a
compliance officer. Budget for those hires before the capital.

## 2. Setu Bridge checklist

Work through these in order; each one gates the next.

1. **Licence submission.** Upload the SEBI registration certificate to Setu
   Bridge. Nothing else is reviewed until this clears.
2. **Use case and consent copy.** Sahamati reviews the stated purpose and the
   exact wording shown on the consent screen. The purpose declared must match
   purpose code `101` and must match what the product actually does with the
   data. Over-claiming here is the most common rejection.
3. **Consent parameters.** Confirm the fetch type, frequency, and data life
   requested are the minimum the product needs. The current consent is
   `PERIODIC` over `DEPOSIT` — justify both.
4. **Production callback URL.** Register the production
   `REDIRECT_URL` and the webhook endpoint `POST /api/v1/webhooks/setu`. Set
   `SETU_WEBHOOK_SECRET`; the handler rejects every unsigned event, so an
   unset secret means no data refreshes at all.
5. **KYC.** Company incorporation documents, PAN, GST, and authorised
   signatory identity.
6. **ReBIT certification.** Setu runs this through Aujas. It covers encryption
   at rest and in transit, key management, and audit logging.
7. **Central Registry onboarding.** Setu handles the submission.

## 3. DPDP Act 2023 posture

Processing financial data makes NOVAA a Data Fiduciary. The duties and their
current implementation status:

| Duty | Status | Where |
| --- | --- | --- |
| Consent records with purpose and timestamp | Done | `ConsentRecord` table |
| PII encrypted at rest | Done | AES-256-GCM in `app/core/crypto.py` |
| Erasure on request | Done | `DELETE /api/v1/me/data` |
| Data minimisation in logs | Done | `SensitiveDataSanitizerFilter` |
| Retention limit | Done | `enforce_retention` cron in `app/workers/tasks.py` |
| Breach notification within 72 hours | **Outstanding** | Needs a documented runbook |
| Named grievance officer | **Outstanding** | Needs a person and a published contact |
| Consent withdrawal | Done | `POST /api/v1/consent/{id}/revoke` |

### Retention policy

Enforced daily at 05:30 by the `enforce_retention` cron job:

- Uploaded statement files are deleted from object storage 90 days after a
  successful parse. The derived transactions are what the product needs; the
  source PDF is not, and the upload record is kept so the audit trail survives.
- Webhook payloads are deleted after 180 days. They exist for audit, not
  analysis.

Still policy rather than code:

- Transactions and derived analytics: retained while the account is active,
  purged 30 days after account closure.
- Revoked consents: keep the consent record for the statutory audit period, but
  purge the financial data fetched under it immediately.

### Before go-live

- Publish a privacy notice stating the purpose, the categories of data, the
  retention periods above, and the erasure route.
- Name a grievance officer and publish an email address that is monitored.
- Write the breach runbook: who declares an incident, who notifies the Data
  Protection Board, and what the 72-hour clock starts on.
- Confirm `ENABLE_DEMO_ROUTES=false` and that `ENCRYPTION_KEY` is stored in a
  secrets manager, not an environment file. The application refuses to start in
  production if either is wrong, but the key still needs somewhere safe to live.
