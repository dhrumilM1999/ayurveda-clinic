import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from conftest import client_for

BRANDING = "/api/v1/branding/"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (40, 20), (200, 40, 30, 255)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.mark.django_db
def test_login_screen_can_read_clinic_name_without_logging_in(org):
    org.name = "Vednath Ayurved"
    org.save()
    response = APIClient().get(BRANDING)
    assert response.status_code == 200
    assert response.data["name"] == "Vednath Ayurved"
    assert response.data["has_logo"] is False
    # Only public things are exposed
    assert set(response.data) == {"name", "short_name", "has_logo", "version"}


@pytest.mark.django_db
def test_logo_is_public_only_after_the_clinic_uploads_one(org, org_admin, branch_a):
    assert APIClient().get(BRANDING + "logo/").status_code == 404

    upload = SimpleUploadedFile("logo.png", _png(), content_type="image/png")
    assert client_for(org_admin, branch_a).post("/api/v1/organization/logo/", {"file": upload}, format="multipart").status_code == 200

    info = APIClient().get(BRANDING)
    assert info.data["has_logo"] is True
    picture = APIClient().get(BRANDING + "logo/")
    assert picture.status_code == 200
    assert b"".join(picture.streaming_content)[1:4] == b"PNG"  # the saved file is a real PNG picture


@pytest.mark.django_db
def test_branding_follows_the_clinic_name_when_it_is_changed(org, org_admin, branch_a):
    before = APIClient().get(BRANDING).data["version"]
    assert client_for(org_admin, branch_a).patch("/api/v1/organization/", {"name": "New Clinic"}, format="json").status_code == 200
    after = APIClient().get(BRANDING).data
    assert after["name"] == "New Clinic"
    assert after["version"] >= before  # the number only goes up, so the browser never shows an old logo
