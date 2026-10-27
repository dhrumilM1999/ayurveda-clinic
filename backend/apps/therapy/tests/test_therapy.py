from datetime import date, time, timedelta

import pytest

from apps.organizations.models import BranchFeatureFlag, Room
from apps.patients.models import Patient
from apps.therapy.models import TherapySession, TherapyType
from apps.therapy.services import load_sample_therapies
from conftest import client_for

DAY = date.today() + timedelta(days=1)


def switch_on(branch):
    BranchFeatureFlag.objects.update_or_create(branch=branch, code="panchakarma",
                                               defaults={"organization": branch.organization, "enabled": True})


@pytest.fixture
def on(branch_a):
    switch_on(branch_a)


@pytest.fixture
def patient(org):
    return Patient.objects.create(organization=org, uhid="9", first_name="Kiran", last_name="Shah", gender="female",
                                  mobile="9876500009")


@pytest.fixture
def room(org, branch_a):
    return Room.objects.create(organization=org, branch=branch_a, name="Therapy room 1", capacity=1)


@pytest.fixture
def abhyanga(org):
    load_sample_therapies(org)
    return TherapyType.objects.get(organization=org, name__startswith="Abhyanga")


def make_plan(client, patient, therapy, sessions=3, **extra):
    body = {"patient": str(patient.id), "title": "Detox course", "start_date": str(DAY),
            "items": [{"therapy": str(therapy.id), "stage": "purva", "sessions_planned": sessions}], **extra}
    res = client.post("/api/v1/therapy-plans/", body, format="json")
    assert res.status_code == 201, res.data
    return res.data


@pytest.mark.django_db
def test_module_is_off_until_switched_on(org, roles, branch_a, therapist):
    res = client_for(therapist, branch_a).get("/api/v1/therapy-sessions/")
    assert res.status_code == 403


@pytest.mark.django_db
def test_sample_list_is_added_once(on, org, roles, branch_a, doctor):
    c = client_for(doctor, branch_a)
    assert c.post("/api/v1/therapies/load-sample/").data["added"] > 20
    assert c.post("/api/v1/therapies/load-sample/").data["added"] == 0
    rows = c.get("/api/v1/therapies/").data
    assert any(r["stage"] == "pradhana" for r in rows) and any(r["stage"] == "paschat" for r in rows)


@pytest.mark.django_db
def test_plan_with_sessions_and_progress(on, org, roles, branch_a, doctor, therapist, room, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=2, consent_taken=True)
    assert plan["consent_on"] and plan["sessions_planned"] == 2 and plan["status"] == "planned"
    item = plan["items"][0]["id"]
    res = c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {
        "item": item, "dates": [str(DAY), str(DAY + timedelta(days=1))], "start_time": "10:00",
        "therapist": str(therapist.id), "room": str(room.id)}, format="json")
    assert res.status_code == 201 and len(res.data) == 2 and res.data[0]["end_time"] == "10:45:00"
    assert [r["session_no"] for r in res.data] == [1, 2]
    # The therapist records the sessions on their day (a later day is refused: see the test below)
    TherapySession.objects.filter(pk=res.data[0]["id"]).update(date=date.today())
    TherapySession.objects.filter(pk=res.data[1]["id"]).update(date=date.today(), start_time=time(12, 0), end_time=time(12, 45))
    t = client_for(therapist, branch_a)
    sid = res.data[0]["id"]
    done = t.post(f"/api/v1/therapy-sessions/{sid}/complete/", {"material_used": "Sesame oil", "quantity_ml": 150,
                                                                   "patient_response": "Felt relaxed"}, format="json")
    assert done.status_code == 200 and done.data["status"] == "done" and done.data["quantity_ml"] == 150
    assert c.get(f"/api/v1/therapy-plans/{plan['id']}/").data["status"] == "active"
    t.post(f"/api/v1/therapy-sessions/{res.data[1]['id']}/complete/", {}, format="json")
    assert c.get(f"/api/v1/therapy-plans/{plan['id']}/").data["status"] == "completed"


@pytest.mark.django_db
def test_no_double_booking_of_therapist_or_room(on, org, roles, branch_a, doctor, therapist, room, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=4)
    item = plan["items"][0]["id"]
    url = f"/api/v1/therapy-plans/{plan['id']}/schedule/"
    first = {"item": item, "dates": [str(DAY)], "start_time": "10:00", "therapist": str(therapist.id), "room": str(room.id)}
    assert c.post(url, first, format="json").status_code == 201
    # same therapist, overlapping time
    res = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "10:30", "therapist": str(therapist.id)}, format="json")
    assert res.status_code == 400 and "already booked" in str(res.data["therapist"])
    # same room, overlapping time, no therapist
    res = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "10:15", "room": str(room.id)}, format="json")
    assert res.status_code == 400 and "already in use" in str(res.data["room"])
    # right after it is free
    assert c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "10:45", "therapist": str(therapist.id),
                        "room": str(room.id)}, format="json").status_code == 201
    # a cancelled session frees the slot
    sid = TherapySession.objects.filter(start_time=time(10, 0)).first().id
    assert c.post(f"/api/v1/therapy-sessions/{sid}/cancel/").status_code == 200
    assert c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "10:00", "therapist": str(therapist.id)},
                  format="json").status_code == 201


@pytest.mark.django_db
def test_cannot_book_more_than_planned(on, org, roles, branch_a, doctor, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=1)
    res = c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {
        "item": plan["items"][0]["id"], "dates": [str(DAY), str(DAY + timedelta(days=1))], "start_time": "09:00"}, format="json")
    assert res.status_code == 400 and "1 more" in str(res.data)
    assert TherapySession.objects.count() == 0  # nothing half-booked


@pytest.mark.django_db
def test_moving_a_session_is_checked_too(on, org, roles, branch_a, doctor, therapist, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=2)
    url = f"/api/v1/therapy-plans/{plan['id']}/schedule/"
    item = plan["items"][0]["id"]
    a = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "09:00", "therapist": str(therapist.id)}, format="json").data[0]
    b = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "11:00", "therapist": str(therapist.id)}, format="json").data[0]
    assert c.patch(f"/api/v1/therapy-sessions/{b['id']}/", {"start_time": "09:30", "end_time": "10:15"}, format="json").status_code == 400
    assert c.patch(f"/api/v1/therapy-sessions/{a['id']}/", {"start_time": "09:10"}, format="json").status_code == 200


@pytest.mark.django_db
def test_cancel_plan_frees_sessions_and_branch_isolation(on, org, roles, branch_a, branch_b, doctor, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=2)
    c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {"item": plan["items"][0]["id"], "dates": [str(DAY)],
                                                            "start_time": "09:00"}, format="json")
    assert c.post(f"/api/v1/therapy-plans/{plan['id']}/cancel/").data["status"] == "cancelled"
    assert not TherapySession.objects.filter(status="scheduled").exists()
    # another branch does not see this branch's plans
    switch_on(branch_b)
    assert client_for(doctor, branch_b).get("/api/v1/therapy-plans/").data["count"] == 0


@pytest.mark.django_db
def test_pharmacist_cannot_see_therapy(on, org, roles, branch_a, pharmacist):
    assert client_for(pharmacist, branch_a).get("/api/v1/therapy-plans/").status_code == 403


@pytest.mark.django_db
def test_therapy_plan_prints_as_pdf_in_the_patient_language(on, org, roles, branch_a, doctor, therapist, room, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=2, consent_taken=True)
    c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {"item": plan["items"][0]["id"], "dates": [str(DAY)],
                                                            "start_time": "10:00", "therapist": str(therapist.id)}, format="json")
    for lang in ("en", "gu", "hi"):
        res = c.get(f"/api/v1/documents/therapy-plan/{plan['id']}/?lang={lang}&preview=1")
        assert res.status_code == 200 and res["Content-Type"] == "application/pdf" and res.content[:4] == b"%PDF", lang
    assert client_for(therapist, branch_a).get(f"/api/v1/documents/therapy-plan/{plan['id']}/?preview=1").status_code == 200


@pytest.mark.django_db
def test_plan_can_be_linked_to_the_check_up_of_the_same_patient_only(on, org, roles, branch_a, doctor, patient, abhyanga):
    from apps.emr.models import Visit

    other = Patient.objects.create(organization=org, uhid="10", first_name="Anil", last_name="Mehta", gender="male", mobile="9876500010")
    visit = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=date.today())
    c = client_for(doctor, branch_a)
    item = [{"therapy": str(abhyanga.id), "stage": "purva", "sessions_planned": 2}]
    ok = c.post("/api/v1/therapy-plans/", {"patient": str(patient.id), "visit": str(visit.id), "title": "A", "start_date": str(DAY),
                                           "items": item}, format="json")
    assert ok.status_code == 201 and str(ok.data["visit"]) == str(visit.id)
    bad = c.post("/api/v1/therapy-plans/", {"patient": str(other.id), "visit": str(visit.id), "title": "B", "start_date": str(DAY),
                                            "items": item}, format="json")
    assert bad.status_code == 400 and "another patient" in str(bad.data)


@pytest.mark.django_db
def test_undo_a_therapy_session_step_by_step(on, org, roles, branch_a, doctor, therapist, patient, abhyanga):
    from django.utils import timezone

    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=1)
    sid = c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {"item": plan["items"][0]["id"], "dates": [str(date.today())],
                                                                  "start_time": "10:00", "therapist": str(therapist.id)},
                 format="json").data[0]["id"]
    t = client_for(therapist, branch_a)
    assert t.post(f"/api/v1/therapy-sessions/{sid}/start/").data["undo_to"] == "scheduled"
    done = t.post(f"/api/v1/therapy-sessions/{sid}/complete/", {"material_used": "Oil", "quantity_ml": 100}, format="json")
    assert done.data["status"] == "done" and done.data["undo_to"] == "in_progress"
    assert c.get(f"/api/v1/therapy-plans/{plan['id']}/").data["status"] == "completed"
    back = t.post(f"/api/v1/therapy-sessions/{sid}/undo/")
    assert back.data["status"] == "in_progress" and back.data["quantity_ml"] == 100  # what was written is kept
    assert c.get(f"/api/v1/therapy-plans/{plan['id']}/").data["status"] == "active"
    assert t.post(f"/api/v1/therapy-sessions/{sid}/undo/").data["status"] == "scheduled"
    # Did not come, then undo
    assert t.post(f"/api/v1/therapy-sessions/{sid}/missed/").data["status"] == "missed"
    assert t.post(f"/api/v1/therapy-sessions/{sid}/undo/").data["status"] == "scheduled"
    # too late
    TherapySession.objects.filter(pk=sid).update(updated_at=timezone.now() - timedelta(minutes=61))
    assert t.post(f"/api/v1/therapy-sessions/{sid}/undo/").status_code == 400


@pytest.mark.django_db
def test_a_missed_session_can_be_moved_to_a_new_day(on, org, roles, branch_a, doctor, therapist, room, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=2)
    url = f"/api/v1/therapy-plans/{plan['id']}/schedule/"
    item = plan["items"][0]["id"]
    a = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "09:00", "therapist": str(therapist.id),
                     "room": str(room.id)}, format="json").data[0]
    b = c.post(url, {"item": item, "dates": [str(DAY)], "start_time": "11:00", "therapist": str(therapist.id)}, format="json").data[0]
    assert c.post(f"/api/v1/therapy-sessions/{a['id']}/missed/").status_code == 200
    new_day = DAY + timedelta(days=2)
    # the therapist is busy with the other session at 11:00
    res = c.post(f"/api/v1/therapy-sessions/{a['id']}/reschedule/", {"date": str(DAY), "start_time": "11:10"}, format="json")
    assert res.status_code == 400 and "already booked" in str(res.data["therapist"])
    # a day that has passed is refused
    res = c.post(f"/api/v1/therapy-sessions/{a['id']}/reschedule/",
                 {"date": str(date.today() - timedelta(days=1)), "start_time": "10:00"}, format="json")
    assert res.status_code == 400 and "passed" in str(res.data["date"])
    res = c.post(f"/api/v1/therapy-sessions/{a['id']}/reschedule/", {"date": str(new_day), "start_time": "10:00"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "scheduled" and res.data["date"] == str(new_day) and res.data["start_time"].startswith("10:00")
    assert str(res.data["therapist"]) == str(therapist.id)  # kept
    # a session that is done or cancelled cannot be moved
    assert c.post(f"/api/v1/therapy-sessions/{b['id']}/cancel/").status_code == 200
    assert c.post(f"/api/v1/therapy-sessions/{b['id']}/reschedule/", {"date": str(new_day), "start_time": "15:00"}, format="json").status_code == 400


@pytest.mark.django_db
def test_a_session_of_a_later_day_cannot_be_started_or_finished_today(on, org, roles, branch_a, doctor, therapist, patient, abhyanga):
    c = client_for(doctor, branch_a)
    plan = make_plan(c, patient, abhyanga, sessions=1)
    s = c.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {"item": plan["items"][0]["id"], "dates": [str(DAY)],
                                                               "start_time": "09:00"}, format="json").data[0]
    for step in ("start", "complete"):
        res = c.post(f"/api/v1/therapy-sessions/{s['id']}/{step}/")
        assert res.status_code == 400 and "later day" in str(res.data)
    assert TherapySession.objects.get(pk=s["id"]).status == "scheduled"


@pytest.mark.django_db
def test_only_people_who_do_therapy_are_listed_as_therapists(on, org, roles, branch_a, doctor, therapist, receptionist):
    names = {x["name"] for x in client_for(receptionist, branch_a).get("/api/v1/therapy-sessions/options/").data["therapists"]}
    assert names == {therapist.full_name}  # not the receptionist who books, not the doctor
