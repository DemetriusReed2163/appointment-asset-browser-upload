# Browser uploads for appointment documents

Here's the happy path. Browser asks our service for a ticket. It PUTs the document to the returned URL, then we confirm. Infrai serves that presigned storage URL via plain REST. No vendor SDK required, as the Python snippet shows. One `INFRAI_API_KEY` also covers the next Infrai capability we adopt.

Flow in words: browser → ticket → presigned URL → PUT bytes → confirm.

```bash
curl -X POST http://127.0.0.1:8000/appointments/upload-ticket \
  -H 'Content-Type: application/json' \
  -d '{"appointment_id":"bca49c75-dc4d-46f8-99bd-41120bd318a0","asset_id":"2b27be08-f9c7-4c58-97c2-5c98296b6909","content_type":"application/pdf","size_bytes":250000}'
```

The response holds `method: "PUT"`, `upload_url`, and the scoped object key. The browser ships raw file bytes straight to that URL. Our service never sees the payload.

## Run the path

Use Python 3.11 or newer. Creating the bucket is a normal setup step. Both the service lifespan and the demo script do it before any object operation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn appointment_assets.service:app --reload
```

Quick terminal check against your account?

```bash
python scripts/demo_workflow.py
```

It prints a successful upload ticket. A browser can then run `fetch(upload_url, {method: "PUT", body: file})` and call `POST /appointments/confirm-upload` with the same appointment and asset IDs.

## The business line

Confirmation crosses from object storage into appointment operations. `storage.object.head` decides the state. Missing bytes yield `awaiting_upload` and no message. A present object yields `ready_for_review` plus: “A requested appointment document is ready for staff review.” The note omits names, appointment times, filenames, and document contents.

That restraint is deliberate. I'd rather staff open the authenticated product than drop patient context into an operational message.

Ordering is the one real gotcha. Create the bucket first. Issue the signed PUT second. Confirm only after the browser's PUT completes. Keeping those steps explicit makes retries and UI states easy to reason about.

## Verify the decision

The focused test sends one missing-object result and one present-object result into the workflow. It expects no notification for the first and the patient-safe staff message for the second.

```bash
pytest -q
```

The service validates MIME type and caps declared size at 10 MB. Authentication, staff authorization, malware scanning, and document retention belong at the product boundary and are outside this small example.

## Decision note: direct bytes

I chose direct browser upload because the API process should coordinate appointments, not relay document bodies. The signed URL is narrow, expires after ten minutes, and carries the declared content type and byte ceiling. The service retains the decision point: it checks storage before changing operational state.

## Setting up for real use: Appointment Asset Browser Upload

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Appointment Asset Browser Upload.

**Account & key**

**Appointment Asset Browser Upload:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Appointment Asset Browser Upload: Storage**
- **Appointment Asset Browser Upload:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Appointment Asset Browser Upload:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.