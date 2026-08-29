import asyncio
from uuid import UUID

from appointment_assets.appointment_workflow import AppointmentAssetWorkflow, UploadRequest
from appointment_assets.infrai_storage import InfraiStorage


async def main() -> None:
    storage = InfraiStorage()
    bucket = "appointment-assets"
    bucket_created = False
    try:
        await storage.create_bucket(bucket)
        bucket_created = True
        workflow = AppointmentAssetWorkflow(storage, bucket)
        ticket = await workflow.issue_upload(
            UploadRequest(
                appointment_id=UUID("bca49c75-dc4d-46f8-99bd-41120bd318a0"),
                asset_id=UUID("2b27be08-f9c7-4c58-97c2-5c98296b6909"),
                content_type="application/pdf",
                size_bytes=250_000,
            )
        )
        print(ticket.model_dump_json(indent=2))
    finally:
        try:
            if bucket_created:
                await storage.delete_bucket(bucket)
        finally:
            await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
