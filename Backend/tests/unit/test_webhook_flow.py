from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.supabase_client import get_db

client = TestClient(app)

# Mock Supabase Client
mock_db = MagicMock()
mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

# Override dependency
app.dependency_overrides[get_db] = lambda: mock_db

def test_webhook_verification_fails_invalid_token():
    response = client.get("/webhook?hub.mode=subscribe&hub.challenge=1158201444&hub.verify_token=WRONG_TOKEN")
    assert response.status_code == 403

def test_webhook_post_returns_200_instantly():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123", "phone_number_id": "123"},
                    "messages": [{"from": "111", "id": "wamid", "text": {"body": "test"}}]
                },
                "field": "messages"
            }]
        }]
    }
    
    response = client.post("/webhook", json=payload)
    # Even if DB is not mocked, our robust dependencies catch the logic fault and safely return 200 OK 
    # internally flagged as "Ignored/Error reading tenant context" to avoid dropping the Meta API webhook setup.
    assert response.status_code == 200
