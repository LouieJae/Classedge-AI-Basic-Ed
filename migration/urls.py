from django.urls import path

from .views import actions, errors, job_detail, overview, sequence, settings as settings_views

app_name = "migration"

urlpatterns = [
    path("", sequence.SequenceView.as_view(), name="sequence"),
    path("overview/", overview.OverviewView.as_view(), name="overview"),
    path("actions/run-job/<str:app>/<str:model>/", sequence.RunJobView.as_view(), name="action-run-job"),
    path("status/<str:app>/<str:model>/", sequence.JobStatusView.as_view(), name="job-status"),
    path("rows/", overview.JobRowsFragment.as_view(), name="overview-rows"),
    path("job/<int:pk>/", job_detail.JobDetailView.as_view(), name="job-detail"),
    path("job/<int:pk>/fragment/", job_detail.JobDetailFragment.as_view(), name="job-detail-fragment"),
    path("errors/", errors.ErrorsView.as_view(), name="errors"),
    path("errors/<int:pk>/", errors.ErrorDetailView.as_view(), name="error-detail"),
    path("settings/", settings_views.SettingsView.as_view(), name="settings"),
    # Actions
    path("actions/start/", actions.StartPipelineView.as_view(), name="action-start"),
    path("actions/pause-all/", actions.PauseAllView.as_view(), name="action-pause-all"),
    path("actions/resume-all/", actions.ResumeAllView.as_view(), name="action-resume-all"),
    path("actions/toggle-dry-run/", actions.ToggleDryRunView.as_view(), name="action-toggle-dry-run"),
    path("actions/job/<int:pk>/pause/", actions.PauseJobView.as_view(), name="action-job-pause"),
    path("actions/job/<int:pk>/stop/", actions.StopJobView.as_view(), name="action-job-stop"),
    path("actions/job/<int:pk>/backfill-files/", actions.BackfillFilesView.as_view(), name="action-job-backfill-files"),
    path("actions/job/<int:pk>/resume/", actions.ResumeJobView.as_view(), name="action-job-resume"),
    path("actions/job/<int:pk>/restart/", actions.RestartJobView.as_view(), name="action-job-restart"),
    path("actions/job/<int:pk>/verify/", actions.VerifyJobView.as_view(), name="action-job-verify"),
    path("actions/errors/<int:pk>/retry/", actions.RetryErrorView.as_view(), name="action-error-retry"),
    path("actions/errors/<int:pk>/resolve/", actions.ResolveErrorView.as_view(), name="action-error-resolve"),
]
