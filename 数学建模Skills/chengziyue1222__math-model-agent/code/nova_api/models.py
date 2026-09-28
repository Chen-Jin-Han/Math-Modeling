"""Strict public HTTP models; benchmark truth fields are intentionally absent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_EVALUATION_FIELDS = {"ground_truth", "fault_type", "expected_gate", "acceptable_first_experiments"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DecisionContext(StrictModel):
    forecast_horizon_hours: int = Field(default=24, ge=1, le=168)
    decision_use: str = Field(default="high_load_risk_assessment", min_length=1, max_length=100)


class StructuredData(StrictModel):
    timestamps: list[str] | None = Field(default=None, max_length=1000)
    actual_load: list[float] = Field(min_length=24, max_length=1000)
    predicted_load: list[float] = Field(min_length=24, max_length=1000)
    split_strategy: Literal["chronological", "random"] = "chronological"
    feature_origin_offsets: list[int] = Field(default_factory=list, max_length=1000)
    high_load_watch: bool = False
    rolling_fold_errors: list[float] = Field(default_factory=list, max_length=100)
    rolling_peak_errors: list[float] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_lengths(self) -> "StructuredData":
        if len(self.actual_load) != len(self.predicted_load):
            raise ValueError("actual_load and predicted_load must have equal length")
        if self.timestamps is not None and len(self.timestamps) != len(self.actual_load):
            raise ValueError("timestamps must match actual_load length")
        return self


class FileReference(StrictModel):
    file_url: str | None = None
    file_id: str | None = None
    content_type: str | None = None


class DiagnosisRequest(StrictModel):
    request_id: str | None = Field(default=None, max_length=128)
    domain: Literal["campus_load_forecast"] = "campus_load_forecast"
    mode: Literal["diagnose"] = "diagnose"
    decision_context: DecisionContext = Field(default_factory=DecisionContext)
    input_type: Literal["demo_case", "structured_data", "file_reference"]
    case_id: str | None = Field(default=None, max_length=128)
    data: StructuredData | None = None
    file_reference: FileReference | None = None
    metadata: dict[str, str] = Field(default_factory=dict, max_length=20)
    options: dict[str, Any] = Field(default_factory=dict, max_length=10)

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "DiagnosisRequest":
        if self.input_type == "demo_case" and self.case_id is None:
            raise ValueError("case_id is required for input_type=demo_case")
        if self.input_type == "structured_data" and self.data is None:
            raise ValueError("data is required for input_type=structured_data")
        if self.input_type == "file_reference":
            raise ValueError("FILE_REFERENCE_ADAPTER_PENDING_TENCENT_INTEGRATION")
        return self


class ErrorBody(StrictModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(StrictModel):
    error: ErrorBody
