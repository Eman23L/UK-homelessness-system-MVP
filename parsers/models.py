from pydantic import BaseModel, Field, field_validator
from datetime import date
from pathlib import Path
from typing import Optional


class HomelessSupportService(BaseModel):
    name: str = Field(..., description="Official name of the service or centre")
    description: str = Field("", description="Cleaned summary of what the service does")
    service_type: str = Field("", description="e.g. advice centre, hostel, day centre")
    provider_name: str = Field(..., description="Source provider, e.g. shelter, crisis, homeless_england")
    website_url: str = Field("", description="External website URL for the service or organisation")
    phone_number: str = Field("", description="Main contact number")
    email_address: str = Field("", description="General contact email")
    physical_address: str = Field("", description="Full street address where confidently known")
    postcode: str = Field("", description="UK postcode if found")
    opening_times: str = Field("", description="Formatted opening hours")
    eligibility: str = Field("", description="Who the service is for, if available")
    notes: str = Field("", description="Extra notes, caveats, or data-quality context")
    latitude: Optional[float] = Field(None, description="Latitude for map display")
    longitude: Optional[float] = Field(None, description="Longitude for map display")
    source_url: str = Field(..., description="The source page URL")
    date_collected: str = Field(default_factory=lambda: str(date.today()))
    verification_status: str = Field("unverified", description="Verification status")

    @field_validator("postcode")
    @classmethod
    def normalize_postcode(cls, v: str) -> str:
        if not v:
            return ""
        return v.upper().strip()

    def to_json_file(self, folder_path: str, filename: str) -> None:
        out_dir = Path(folder_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{filename}.json"
        file_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")