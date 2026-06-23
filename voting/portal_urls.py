from django.urls import path

from . import portal_views

urlpatterns = [
    path("", portal_views.portal_home, name="portal-home"),
    # Elections
    path("elections/new/", portal_views.portal_election_create, name="portal-election-create"),
    path("elections/<int:election_id>/edit/", portal_views.portal_election_edit, name="portal-election-edit"),
    path("elections/<int:election_id>/delete/", portal_views.portal_election_delete, name="portal-election-delete"),
    # Positions
    path("elections/<int:election_id>/positions/", portal_views.portal_positions, name="portal-positions"),
    path("elections/<int:election_id>/positions/new/", portal_views.portal_position_create, name="portal-position-create"),
    path("positions/<int:position_id>/edit/", portal_views.portal_position_edit, name="portal-position-edit"),
    path("positions/<int:position_id>/delete/", portal_views.portal_position_delete, name="portal-position-delete"),
    path("positions/reorder/", portal_views.portal_positions_reorder, name="portal-positions-reorder"),
    # Candidates
    path("positions/<int:position_id>/candidates/new/", portal_views.portal_candidate_create, name="portal-candidate-create"),
    path("candidates/<int:candidate_id>/edit/", portal_views.portal_candidate_edit, name="portal-candidate-edit"),
    path("candidates/<int:candidate_id>/delete/", portal_views.portal_candidate_delete, name="portal-candidate-delete"),
    # Invigilators
    path("invigilators/", portal_views.portal_invigilators, name="portal-invigilators"),
    path("invigilators/new/", portal_views.portal_invigilator_create, name="portal-invigilator-create"),
    path("invigilators/<int:user_id>/edit/", portal_views.portal_invigilator_edit, name="portal-invigilator-edit"),
    path("invigilators/<int:user_id>/delete/", portal_views.portal_invigilator_delete, name="portal-invigilator-delete"),
    # AJAX helpers
    path("elections/<int:election_id>/status/", portal_views.portal_election_status, name="portal-election-status"),
]
