import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auction import BidfaxTestParseResponse


class DummyProvider:
    def fetch_list_page(self, url: str, proxy_url=None, proxy_id=None, fetch_mode: str = "http", timeout: float = 10.0):
        from app.services.sold_results.fetch_diagnostics import FetchDiagnostics

        return FetchDiagnostics(
            html="<html>ok</html>",
            status_code=200,
            latency_ms=5,
            fetch_mode=fetch_mode,
            final_url=url,
            error=None,
            proxy_exit_ip=None,
            browser_version=None,
        )

    def parse_list_page(self, html: str, url: str):
        return [
            {
                "vin": "1FADP5AU1FL123456",
                "sold_price": 10000,
                "lot_id": "1",
                "sold_at": None,
                "sale_status": "sold",
            }
        ]


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    # Bypass admin auth/db for the endpoint
    from app.core.security import get_current_admin
    from app.core.database import get_db
    from types import SimpleNamespace

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(email="test@example.com")
    app.dependency_overrides[get_db] = lambda: None

    monkeypatch.setattr("app.services.proxy_service.list_enabled_proxies", lambda db: [])
    monkeypatch.setattr("app.services.proxy_service.get_proxy", lambda db, proxy_id: None)
    monkeypatch.setattr("app.services.proxy_service.check_proxy", lambda db, proxy: {"ok": True})
    monkeypatch.setattr("app.routers.admin_auction.BidfaxHtmlProvider", DummyProvider)
    yield
    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "proxy_id,fetch_mode",
    [
        (None, "http"),
        ("", "http"),
        (None, "browser"),
    ],
)
def test_test_parse_handles_proxy_and_modes(proxy_id, fetch_mode):
    client = TestClient(app)
    resp = client.post(
        "/api/v1/admin/data-engine/bidfax/test-parse",
        json={"url": "https://example.com", "proxy_id": proxy_id, "fetch_mode": fetch_mode},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    parsed = BidfaxTestParseResponse(**data)
    assert parsed.debug.request_id
    assert parsed.http.status == 200
