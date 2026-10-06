from datetime import date, timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import accessible_branches, user_has_perm
from apps.audit.services import log_action

from .exports import to_excel, to_pdf
from .reports import REPORTS, build
from .services import money_today, next_patients, opd_counts

MAX_DAYS = 3 * 366  # longer reports would be slow; P2 will build them in the background
NOTES = {
    "gst": "Prices include GST. GST is shown as CGST + SGST (same state). Please confirm with your CA before filing.",
    "follow_ups": "Patients whose follow-up date has passed and who have not had a check-up since (any branch).",
    "by_doctor": "Pharmacy bills count for the doctor of the prescription. Billed = bills minus returns / cancellations.",
}


class TodayDashboardView(APIView):
    """GET /dashboard/today/ - the dashboard of the current branch in OPD words."""

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True  # needs the branch; dashboard.view is checked below

    def get(self, request):
        if not user_has_perm(request.user, "dashboard.view", request.branch):
            self.permission_denied(request)
        day = timezone.localdate()
        user, branch = request.user, request.branch
        data = {"date": str(day), "is_doctor": user.is_doctor}
        if user_has_perm(user, "appointments.view", branch):
            data["opd"] = opd_counts(branch, day)
            if user.is_doctor:
                data["my_opd"] = opd_counts(branch, day, doctor=user)
                data["next_patients"] = next_patients(branch, day, user)
        if user_has_perm(user, "billing.view", branch):
            data["money"] = {k: str(v) if not isinstance(v, int) else v for k, v in money_today(branch, day).items()}
        return Response(data)


def _date(raw, name, default):
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: "Date must look like 2026-10-05."})


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


class ReportView(APIView):
    """
    GET /reports/<code>/  codes: collection, by_doctor, by_branch, patients, follow_ups, gst
      ?date_from=2026-10-01&date_to=2026-10-31   (default: this month)
      ?branch=<id> | all                           (default: the current branch; "all" = every branch you may see)
      ?group=day|month                             (collection and patients)
      ?export=xlsx|pdf                             (download; written to the audit log)
    Needs "reports.view" plus the module's own permission (bills: billing.view, patients: patients.view...)
    in every branch included.
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True

    def get(self, request, code):
        info = REPORTS.get(code)
        if info is None:
            raise ValidationError({"detail": "Unknown report."})
        user = request.user
        p = request.query_params

        def allowed(branch):
            return user_has_perm(user, "reports.view", branch) and user_has_perm(user, info["needs"], branch)

        choice = p.get("branch") or str(request.branch.id)
        if choice == "all":
            branches = [b for b in accessible_branches(user).order_by("name") if allowed(b)]
        else:
            branches = [b for b in accessible_branches(user).filter(id=choice) if allowed(b)] if _is_uuid(choice) else []
        if not branches:
            raise PermissionDenied("You may not see this report for this branch.")

        today = timezone.localdate()
        date_from = _date(p.get("date_from"), "date_from", today.replace(day=1))
        date_to = _date(p.get("date_to"), "date_to", today)
        if date_from > date_to:
            raise ValidationError({"date_to": "The end date is before the start date."})
        if (date_to - date_from) > timedelta(days=MAX_DAYS):
            raise ValidationError({"date_to": "Please choose at most 3 years."})
        group = p.get("group", "day")
        if group not in ("day", "month"):
            raise ValidationError({"group": "Choose day or month."})

        report = build(code, branches, date_from, date_to, group)
        branch_names = ", ".join(b.name for b in branches) if choice != "all" else "All branches"
        subtitle = f"{branch_names} · {date_from:%d-%m-%Y} to {date_to:%d-%m-%Y}"
        audit = {"report": code, "date_from": str(date_from), "date_to": str(date_to),
                 "branches": [str(b.id) for b in branches]}

        export = p.get("export")
        if export in ("xlsx", "pdf"):
            log_action(request, "export", object_type="report", object_repr=info["title"],
                       changes={**audit, "format": export})
            name = f"{code}-{date_from}-to-{date_to}.{export}"
            if export == "xlsx":
                content = to_excel(report, title=info["title"], subtitle=subtitle)
                kind = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                content = to_pdf(report, title=info["title"], subtitle=subtitle, organization=user.organization,
                                 notes=NOTES.get(code, ""))
                kind = "application/pdf"
            response = HttpResponse(content, content_type=kind)
            response["Content-Disposition"] = f'attachment; filename="{name}"'
            return response
        if export:
            raise ValidationError({"export": "Choose xlsx or pdf."})

        if code == "follow_ups":  # a list of patients: record who looked at it
            log_action(request, "view", object_type="report", object_repr=info["title"], changes=audit)
        return Response({
            "code": code, "title": info["title"], "subtitle": subtitle, "notes": NOTES.get(code, ""),
            "date_from": str(date_from), "date_to": str(date_to), "group": group,
            "branches": [{"id": str(b.id), "name": b.name} for b in branches],
            "columns": report["columns"],
            "rows": [{k: _json(v) for k, v in row.items()} for row in report["rows"]],
            "totals": {k: _json(v) for k, v in report["totals"].items()} if report["totals"] else None,
        })


def _is_uuid(raw):
    import uuid

    try:
        uuid.UUID(raw)
        return True
    except ValueError:
        return False
