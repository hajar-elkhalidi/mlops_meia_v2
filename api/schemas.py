from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    surface_m2: float = Field(gt=0, le=10_000)
    bedrooms: int = Field(ge=0, le=50)
    bathrooms: int = Field(ge=0, le=50)
    floor: int = Field(ge=0, le=200)
    rooms: int = Field(ge=0, le=100)

    city: str = Field(min_length=1)
    property_type: str = Field(min_length=1)
    localisation: str = Field(min_length=1)


class PredictionResponse(BaseModel):
    predicted_price_mad: float

    model_name: str
    model_version: str
    model_type: str

    city: str
    localisation: str
    localisation_grouped: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    model_version: str | None = None
    model_type: str | None = None
    tracking_uri: str


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    alias: str
    tracking_uri: str
