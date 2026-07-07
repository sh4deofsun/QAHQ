from .test_task_lifecycle import ROBOT_XML


def test_ci_xml_upload(client, admin_headers):
    r = client.post(
        "/api/results/upload",
        files={"file": ("output.xml", ROBOT_XML.encode(), "application/xml")},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["passed"] == 1
    assert body["failed"] == 1


def test_invalid_xml_rejected(client, admin_headers):
    r = client.post(
        "/api/results/upload",
        files={"file": ("output.xml", b"not xml", "application/xml")},
        headers=admin_headers,
    )
    assert r.status_code == 400
