import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .appointment_workflow import AppointmentAssetWorkflow, ConfirmationRequest, ConfirmationResult, UploadRequest, UploadTicket
from .infrai_storage import InfraiError, InfraiStorage

BUCKET = os.environ.get("INFRAI_UPLOAD_BUCKET", "appointment-assets")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    storage = InfraiStorage()
    bucket_created = False
    try:
        await storage.create_bucket(BUCKET)
        bucket_created = True
        app.state.storage = storage
        app.state.workflow = AppointmentAssetWorkflow(storage, BUCKET)
        yield
    finally:
        try:
            if bucket_created:
                await storage.delete_bucket(BUCKET)
        finally:
            await storage.close()


app = FastAPI(title="Appointment asset uploads", lifespan=lifespan)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_request: Request, error: InfraiError) -> JSONResponse:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"detail": {"code": error.code, "message": str(error)}})


@app.post("/appointments/upload-ticket", response_model=UploadTicket)
async def upload_ticket(request: UploadRequest) -> UploadTicket:
    return await app.state.workflow.issue_upload(request)


@app.post("/appointments/confirm-upload", response_model=ConfirmationResult)
async def confirm_upload(request: ConfirmationRequest) -> ConfirmationResult:
    return await app.state.workflow.confirm_upload(request)
