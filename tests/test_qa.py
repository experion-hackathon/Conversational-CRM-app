def test_ask_about_unrecognized_customer_is_not_identified(logged_in_client):
    response = logged_in_client.post("/qa", json={"question": "what did we discuss last time with Nobody Inc"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "not_identified"


def test_ask_empty_question_is_400(logged_in_client):
    response = logged_in_client.post("/qa", json={"question": "   "})
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_QUESTION"


def test_ask_against_empty_thread_is_no_history(logged_in_client):
    response = logged_in_client.post("/qa", json={"question": "what did we discuss last time with Globex"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "no_history"


def test_ask_last_discussed_after_capture(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met with Acme, discussed renewal pricing"})
    response = logged_in_client.post("/qa", json={"question": "what did we discuss last time with Acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "answered"
    assert body["account_id"] == "ACC-ACME"
    assert body["answer_text"]


def test_ask_open_commitments_when_none_exist(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met with Acme, just a casual chat"})
    response = logged_in_client.post("/qa", json={"question": "what did I commit to for Acme"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "no_open_commitments"


def test_ask_open_commitments_when_some_exist(logged_in_client):
    logged_in_client.post(
        "/interactions",
        json={"raw_text": "met with Acme, they want a demo of module X by Friday"},
    )
    response = logged_in_client.post("/qa", json={"question": "what did I commit to for Acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "answered"
    assert "demo" in body["answer_text"].lower()


def test_ask_attendees_when_none_captured(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met with Acme, no names mentioned"})
    response = logged_in_client.post("/qa", json={"question": "who attended from Acme's side"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "no_attendees_captured"


def test_ask_attendees_when_captured(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met Priya and Arjun from Acme"})
    response = logged_in_client.post("/qa", json={"question": "who attended from Acme's side"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "answered"
    assert "Priya" in body["answer_text"] and "Arjun" in body["answer_text"]


def test_ask_with_account_id_hint_skips_name_resolution(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met with Initech, discussed the contract"})
    response = logged_in_client.post("/qa", json={"question": "what did we discuss last time", "account_id": "ACC-INITECH"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "answered"
    assert response.json()["account_id"] == "ACC-INITECH"


def test_ask_with_invalid_account_id_hint_is_not_identified(logged_in_client):
    # DAT-4: an explicit but invalid hint fails closed rather than silently
    # falling back to resolving the account from the question's own text.
    logged_in_client.post("/interactions", json={"raw_text": "met with Acme, discussed pricing"})
    response = logged_in_client.post("/qa", json={"question": "what did we discuss last time with Acme", "account_id": "ACC-DOES-NOT-EXIST"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "not_identified"
