from typing import Optional

from pydantic import BaseModel, Field


class CurLoadRequest(BaseModel):
    role_arn: str = Field(..., description="Full ARN of the customer's cross-account role, e.g. arn:aws:iam::123456789012:role/CurReaderRole")
    external_id: str = Field(..., description="External ID configured on the trust policy of role_arn")
    s3_uri: str = Field(
        ...,
        description=(
            "Bucket (or bucket/prefix) containing the CUR report, e.g. "
            "s3://my-cur-bucket/cur-reports/my-report, my-cur-bucket/cur-reports/my-report, "
            "or just my-cur-bucket. The s3:// scheme and the prefix are both optional -- "
            "when the prefix is omitted, the report's location for the requested month is "
            "auto-discovered by scanning the bucket."
        ),
    )
    month: str = Field(..., description="Billing period to load, formatted YYYY-MM")
    region: Optional[str] = Field(None, description="Bucket region; auto-detected if omitted")
    session_name: str = Field("cur-dashboard-session", description="RoleSessionName used for sts:AssumeRole")


class ServiceCost(BaseModel):
    service: str
    cost: float


class DailyCost(BaseModel):
    date: str
    cost: float


class AccountCost(BaseModel):
    account_id: str
    cost: float


class CurLoadResponse(BaseModel):
    billing_period: str
    currency: Optional[str] = None
    total_cost: float
    cost_by_service: list[ServiceCost]
    cost_by_day: list[DailyCost]
    cost_by_account: list[AccountCost]
    file_format: str
    part_file_count: int
    load_time_ms: float
