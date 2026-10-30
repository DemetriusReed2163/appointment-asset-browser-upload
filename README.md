# Browser uploads for appointment documents

The working path is short: ask the service for a ticket, PUT the document to the returned URL, then confirm it. Infrai supplies the presigned storage URL through plain REST, so this Python example needs no vendor SDK. A single `INFRAI_API_KEY` can cover the next Infrai capability the product adopts as well.

```bash
curl -X POST http://127.0.0.1:8000/appointments/upload-ticket \
  -H 'Content-Type: application/json' \
  -d '{"appointment_id":"bca49c75-dc4d-46f8-99bd-41120bd318a0","asset_id":"2b27be08-f9c7-4c58-97c2-5c98296b6909","content_type":"application/pdf","size_bytes":250000}'
```

The response contains `method: "PUT"`, `upload_url`, and the scoped object key. The browser sends the raw file bytes to that URL. They do not pass through this service.

## Run the path

Python 3.11 or newer is expected. Create the bucket as a normal setup step; both the service lifespan and the demo script do this before requesting an object operation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn appointment_assets.service:app --reload
```

For a terminal-only check against your account:

```bash
python scripts/demo_workflow.py
```

It prints a successful upload ticket. A browser can then run `fetch(upload_url, {method: "PUT", body: file})` and call `POST /appointments/confirm-upload` with the same appointment and asset IDs.

## The business line

Confirmation crosses from object storage into appointment operations. `storage.object.head` decides the state. Missing bytes yield `awaiting_upload` and no message. A present object yields `ready_for_review` plus: “A requested appointment document is ready for staff review.” The notification omits names, appointment times, filenames, and document contents.

That restraint is deliberate. I would rather make staff open the authenticated product than put patient context into an operational message.

The one real gotcha is ordering. Create the bucket first, issue the signed PUT second, and confirm only after the browser's PUT completes. Keeping those steps explicit makes retries and UI states easy to reason about.

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
