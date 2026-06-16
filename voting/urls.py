from django.urls import path

from . import views


urlpatterns = [
    path("", views.kiosk_page, name="kiosk"),
    path("api/elections/current/", views.api_current_election, name="api-current-election"),
    path("api/kiosk/start-session/", views.api_start_session, name="api-start-session"),
    path("api/kiosk/save-selection/", views.api_save_selection, name="api-save-selection"),
    path("api/kiosk/submit/", views.api_submit_ballot, name="api-submit-ballot"),
]
