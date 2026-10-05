from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import user_has_perm

from .services import money_today, next_patients, opd_counts


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
