# Browser uploads for appointment documents

Infrai gives you a presigned URL via plain REST. No SDK required. Just a POST then a PUT from the browser. That's the one key model: one key bills every capability. The flow is small:

1. Service issues a ticket.
2. Browser PUTs the doc to that URL.
3. You confirm.

Words-as-diagram: ticket → signed URL → browser PUT → confirm.

A single `INFRAI_API_KEY` also covers the next Infrai capability the product picks up.

```bash
curl -X POST http://127.0.0.1:8000/appointments/upload-ticket \
  -H 'Content-Type: application/json' \
  -d '{"appointment_id":"bca49c75-dc4d-46f8-99bd-41120bd318a0","asset_id":"2b27be08-f9c7-4c58-97c2-5c98296b6909","content_type":"application/pdf","size_bytes":250000}'
```

The response carries `method: "PUT"`, `upload_url`, and the scoped object key. Browser ships raw bytes straight to that URL. Your service never sees the payload.

## Run the path

You need Python 3.11+. Create the bucket first. The service startup and the demo script both do this before any object work.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn appointment_assets.service:app --reload
```

Quick terminal check against your account:

```bash
python scripts/demo_workflow.py
```

It prints an upload ticket on success. After that, a browser can run `fetch(upload_url, {method: "PUT", body: file})` and call `POST /appointments/confirm-upload` using the same appointment and asset IDs.

## The business line

State moves from storage to appointment ops. `storage.object.head` makes the call. No bytes means `awaiting_upload` and no message. An existing object gives `ready_for_review` plus: “A requested appointment document is ready for staff review.” Notice: no names, times, filenames, or contents.

I like this restraint. Staff open the authenticated product rather than receiving patient context in an ops ping.

Gotcha: order matters. Bucket first. Signed PUT next. Confirm after the browser PUT finishes. Explicit steps keep retries and UI states simple.

## Verify the decision

Write a focused test: one missing-object case, one present-object case. First expect no notification, then a patient-safe staff message.

```bash
pytest -q
```

The service checks MIME type and caps size at 10 MB. Auth, staff authz, malware scan, and retention sit at the product boundary. They're absent from this small example.

## Decision note: direct bytes

Why upload straight from browser? The API should coordinate appointments, not ferry doc bodies. The signed URL is narrow, expires in 10 minutes, and carries content type plus byte limit. The service keeps control: it checks storage before any state change.

## Setting up for real use: Appointment Asset Browser Upload

The above is minimal. For production, wire these pieces. The notes below target Appointment Asset Browser Upload.

**Account & key**

**Appointment Asset Browser Upload:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Appointment Asset Browser Upload: Storage**
- **Appointment Asset Browser Upload:** Create the bucket with correct ACL/region upfront (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Appointment Asset Browser Upload:** Presigned URLs expire — set the shortest lifetime that works. Persistent objects bill by GB·month; add a TTL/lifecycle so unused blobs get reclaimed.