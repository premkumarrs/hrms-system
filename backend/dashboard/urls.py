from django.urls import path

from .views import (
    dashboard_stats,
    dashboard_analytics,
    dashboard_insights,
    report_attendance,
    report_leave,
    report_project_headcount,
    report_attrition,
    report_payroll,
)

urlpatterns = [

    path('dashboard/stats/', dashboard_stats),
    path('dashboard/analytics/', dashboard_analytics),
    path('dashboard/insights/', dashboard_insights),

    path('reports/attendance/', report_attendance),
    path('reports/leave/', report_leave),
    path('reports/project-headcount/', report_project_headcount),
    path('reports/attrition/', report_attrition),
    path('reports/payroll/', report_payroll),
]
