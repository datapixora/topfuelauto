import requests
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.vin_report import VinReport

settings = get_settings()


def decode_vin(db: Session, vin: str) -> dict:
    cached = db.query(VinReport).filter(VinReport.vin == vin, VinReport.report_type == "decode").first()
    if cached:
        return {"status": "OK", "vin": vin, "results": cached.payload_json}

    url = f"{settings.nhtsa_api_base}/DecodeVinValuesExtended/{vin}?format=json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("Results", [{}])[0]
            db.add(VinReport(vin=vin, report_type="decode", payload_json=results))
            db.commit()
            return {"status": "OK", "vin": vin, "results": results}
        else:
            return {"status": "ERROR", "vin": vin, "message": "Decode service unavailable"}
    except Exception:
        return {"status": "ERROR", "vin": vin, "message": "Decode request failed"}


def history_vin(db: Session, vin: str) -> dict:
    placeholder = {"status": "NOT_CONFIGURED", "vin": vin, "message": "Provider not configured"}
    db.add(VinReport(vin=vin, report_type="history", payload_json=placeholder))
    db.commit()
    return placeholder