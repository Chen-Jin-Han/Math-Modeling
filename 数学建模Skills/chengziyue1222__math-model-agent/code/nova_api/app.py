"""FastAPI app that delegates every diagnostic decision to Nova Core."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nova_core.enums import ExperimentType, GateDecisionValue

from .models import DiagnosisRequest, ErrorResponse
from .security import require_api_key
from .services import DiagnosisApiService, TraceabilityFailure

NOVA_PROTOCOL_VERSION = "0.2"
API_VERSION = "0.1"


def _error(status: int, code: str, message: str, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "request_id": request_id}})


def create_app(service: DiagnosisApiService | None = None) -> FastAPI:
    app = FastAPI(title="Nova Core Trustworthy Diagnosis API", version=API_VERSION, openapi_url="/openapi.json", docs_url=None, redoc_url=None)
    api_service = service or DiagnosisApiService()

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(422, "INVALID_REQUEST", "Request schema validation failed.")

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return _error(exc.status_code, detail.get("code", "HTTP_ERROR"), detail.get("message", "HTTP error."))

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"service": "nova_api", "status": "ok", "version": API_VERSION, "protocol_version": NOVA_PROTOCOL_VERSION}

    @app.get("/v1/protocol", tags=["protocol"])
    def protocol() -> dict[str, Any]:
        return {"protocol_version": NOVA_PROTOCOL_VERSION, "supported_domains": ["campus_load_forecast"], "experiments": [item.value for item in ExperimentType], "gate_statuses": [item.value for item in GateDecisionValue], "file_reference_status": "FILE_REFERENCE_ADAPTER_PENDING_TENCENT_INTEGRATION"}

    @app.post("/v1/diagnosis/run", tags=["diagnosis"], responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def run_diagnosis(payload: DiagnosisRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
        try:
            return api_service.run(payload)
        except TraceabilityFailure as exc:
            return _error(500, "TRACEABILITY_FAILED", str(exc), payload.request_id)
        except ValueError as exc:
            message = str(exc)
            code, status = ("UNSUPPORTED_DOMAIN", 422) if "Unknown demo case" in message or "PENDING" in message else ("INVALID_DATA", 422)
            return _error(status, code, message, payload.request_id)
        except Exception:
            return _error(500, "EXECUTION_FAILED", "Nova Core execution failed.", payload.request_id)

    @app.get("/v1/diagnosis/runs/{run_id}", tags=["diagnosis"], responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    def get_run(run_id: str, full: bool = False, _: None = Depends(require_api_key)) -> dict[str, Any]:
        result = api_service.get(run_id, full=full)
        if result is None:
            return _error(404, "RUN_NOT_FOUND", "No completed run exists for this run_id.")
        return result

    return app


app = create_app()
