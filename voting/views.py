import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from .models import Ballot
from .models import Candidate
from .models import Election
from .models import Position
from .models import Vote
from .rate_limit import throttle_request


def _active_election_or_none():
	elections = Election.objects.filter(status=Election.STATUS_OPEN).order_by("-created_at")
	for election in elections:
		if election.is_active():
			return election
	return None


def _serialize_election(election):
	positions = []
	for position in election.positions.prefetch_related("candidates").all().order_by("order", "id"):
		positions.append(
			{
				"id": position.id,
				"position": position.name,
				"icon": position.icon,
				"candidates": [
					{
						"id": candidate.id,
						"name": candidate.name,
						"class": candidate.class_name,
						"motto": candidate.motto,
						"photo": candidate.photo,
						"symbol": candidate.symbol,
					}
					for candidate in position.candidates.all().order_by("order", "id")
				],
			}
		)

	return {
		"id": election.id,
		"title": election.title,
		"school_name": election.school_name,
		"positions": positions,
	}


@login_required
@require_GET
def kiosk_page(request):
	election = _active_election_or_none()
	return render(request, "voting/index.html", {"election": election})


@login_required
@require_GET
def api_current_election(request):
	election = _active_election_or_none()
	if not election:
		return JsonResponse({"detail": "No active election."}, status=404)
	return JsonResponse(_serialize_election(election), status=200)


@login_required
@require_POST
def api_start_session(request):
	if throttle_request(request, "start_session", limit=20, window_seconds=60):
		return JsonResponse({"detail": "Too many start-session attempts."}, status=429)

	election = _active_election_or_none()
	if not election:
		return JsonResponse({"detail": "Election is not open."}, status=400)

	ballot = Ballot.objects.create(
		election=election,
		started_by=request.user,
		session_token=Ballot.generate_session_token(),
		receipt_token=Ballot.generate_receipt_token(),
	)
	request.session["active_ballot_id"] = ballot.id

	return JsonResponse(
		{
			"ballot_id": ballot.id,
			"session_token": ballot.session_token,
			"election": _serialize_election(election),
		},
		status=201,
	)


@login_required
@require_POST
def api_save_selection(request):
	if throttle_request(request, "save_selection", limit=120, window_seconds=60):
		return JsonResponse({"detail": "Too many vote updates."}, status=429)

	try:
		payload = json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON payload.")

	ballot_id = payload.get("ballot_id")
	position_id = payload.get("position_id")
	candidate_id = payload.get("candidate_id")

	if not all([ballot_id, position_id, candidate_id]):
		return JsonResponse({"detail": "ballot_id, position_id and candidate_id are required."}, status=400)

	try:
		ballot = Ballot.objects.select_related("election").get(id=ballot_id)
	except Ballot.DoesNotExist:
		return JsonResponse({"detail": "Ballot not found."}, status=404)

	if request.session.get("active_ballot_id") != ballot.id:
		return JsonResponse({"detail": "This ballot session is not active on kiosk."}, status=403)

	if ballot.status != Ballot.STATUS_STARTED:
		return JsonResponse({"detail": "Ballot is already submitted or cancelled."}, status=400)

	if not ballot.election.is_active():
		return JsonResponse({"detail": "Election is no longer active."}, status=400)

	try:
		position = Position.objects.get(id=position_id, election=ballot.election)
	except Position.DoesNotExist:
		return JsonResponse({"detail": "Position does not belong to active election."}, status=400)

	try:
		candidate = Candidate.objects.get(id=candidate_id, position=position)
	except Candidate.DoesNotExist:
		return JsonResponse({"detail": "Candidate does not belong to selected position."}, status=400)

	Vote.objects.update_or_create(
		ballot=ballot,
		position=position,
		defaults={"candidate": candidate},
	)

	return JsonResponse({"detail": "Selection saved."}, status=200)


@login_required
@require_POST
def api_submit_ballot(request):
	if throttle_request(request, "submit_ballot", limit=30, window_seconds=60):
		return JsonResponse({"detail": "Too many submit attempts."}, status=429)

	try:
		payload = json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON payload.")

	ballot_id = payload.get("ballot_id")
	if not ballot_id:
		return JsonResponse({"detail": "ballot_id is required."}, status=400)

	try:
		ballot = Ballot.objects.select_related("election").get(id=ballot_id)
	except Ballot.DoesNotExist:
		return JsonResponse({"detail": "Ballot not found."}, status=404)

	if request.session.get("active_ballot_id") != ballot.id:
		return JsonResponse({"detail": "This ballot session is not active on kiosk."}, status=403)

	if ballot.status != Ballot.STATUS_STARTED:
		return JsonResponse({"detail": "Ballot was already submitted."}, status=409)

	if not ballot.election.is_active():
		return JsonResponse({"detail": "Election is no longer active."}, status=400)

	position_count = ballot.election.positions.count()
	vote_count = ballot.votes.count()
	if vote_count != position_count:
		return JsonResponse(
			{"detail": "All positions must be voted before submit.", "expected": position_count, "current": vote_count},
			status=400,
		)

	with transaction.atomic():
		ballot = Ballot.objects.select_for_update().get(id=ballot.id)
		if ballot.status != Ballot.STATUS_STARTED:
			return JsonResponse({"detail": "Ballot was already submitted."}, status=409)

		ballot.status = Ballot.STATUS_SUBMITTED
		ballot.submitted_at = timezone.now()
		ballot.save(update_fields=["status", "submitted_at"])

	request.session.pop("active_ballot_id", None)
	return JsonResponse({"receipt_token": ballot.receipt_token}, status=200)
