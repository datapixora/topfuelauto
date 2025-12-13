from pydantic import BaseModel


class VinDecodeResponse(BaseModel):
    status: str
    vin: str
    results: dict | None = None
    message: str | None = None


class VinHistoryResponse(BaseModel):
    status: str
    vin: str
    message: str