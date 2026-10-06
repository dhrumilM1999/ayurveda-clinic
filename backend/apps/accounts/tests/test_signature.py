import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from conftest import client_for


def png_bytes():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (60, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.django_db
def test_admin_uploads_and_removes_a_doctor_signature(org_admin, doctor, branch_a):
    client = client_for(org_admin, branch_a)
    url = f"/api/v1/staff/{doctor.id}/signature/"
    res = client.post(url, {"file": SimpleUploadedFile("sign.png", png_bytes(), content_type="image/png")}, format="multipart")
    assert res.status_code == 200, res.data
    assert client.get(f"/api/v1/staff/{doctor.id}/").data["has_signature"] is True
    bad = client.post(url, {"file": SimpleUploadedFile("sign.png", b"not an image", content_type="image/png")}, format="multipart")
    assert bad.status_code == 400
    assert client.delete(url).status_code == 204
    doctor.refresh_from_db()
    assert not doctor.signature


@pytest.mark.django_db
def test_others_cannot_change_a_signature(receptionist, doctor, branch_a):
    url = f"/api/v1/staff/{doctor.id}/signature/"
    res = client_for(receptionist, branch_a).post(url, {"file": SimpleUploadedFile("s.png", png_bytes())}, format="multipart")
    assert res.status_code == 403
