import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from .models import Ballot
from .models import Candidate
from .models import Election
from .models import Position
from .models import UserProfile
from .models import Vote
from .rate_limit import throttle_request

User = get_user_model()


def _active_election_or_none(school_slug=None):
	elections = Election.objects.filter(status=Election.STATUS_OPEN).order_by("-created_at")
	if school_slug:
		elections = elections.filter(school_slug=school_slug)
	return elections.first()


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
						"photo": candidate.photo.name if candidate.photo else "",
						"symbol": candidate.symbol.name if candidate.symbol else "",
						"symbol_name": candidate.symbol_name,
					}
					for candidate in position.candidates.all().order_by("order", "id")
				],
			}
		)

	# Resolve logo URL: ImageField returns relative path; prefix with /media/
	logo_url = ""
	if election.logo:
		logo_url = f"/media/{election.logo}"

	return {
		"id": election.id,
		"title": election.title,
		"school_name": election.school_name,
		"school_slug": election.school_slug,
		"logo_url": logo_url,
		"positions": positions,
	}


@login_required
@require_GET
def kiosk_page(request, school_slug=None):
	# Enforce school constraints for non-superusers
	if not request.user.is_superuser:
		profile = getattr(request.user, "profile", None)
		if profile and profile.school_slug:
			if school_slug != profile.school_slug:
				return redirect("kiosk-school", school_slug=profile.school_slug)

	election = _active_election_or_none(school_slug=school_slug)
	return render(request, "voting/index.html", {
		"election": election,
		"school_slug": school_slug or "",
	})


@login_required
@require_GET
def api_current_election(request):
	school_slug = request.GET.get("school") or None
	if not request.user.is_superuser:
		profile = getattr(request.user, "profile", None)
		if profile and profile.school_slug:
			school_slug = profile.school_slug

	election = _active_election_or_none(school_slug=school_slug)
	if not election:
		return JsonResponse({"detail": "No active election."}, status=404)
	return JsonResponse(_serialize_election(election), status=200)


@login_required
@require_POST
def api_start_session(request):
	if throttle_request(request, "start_session", limit=20, window_seconds=60):
		return JsonResponse({"detail": "Too many start-session attempts."}, status=429)

	# Block locked invigilators
	profile = getattr(request.user, "profile", None)
	if profile and profile.is_locked:
		return JsonResponse(
			{"detail": "Your account has been locked by the administrator. No new ballots can be started."},
			status=423,
		)

	# Parse body (optional — may be empty JSON or contain school_slug)
	try:
		payload = json.loads(request.body.decode("utf-8")) if request.body else {}
	except json.JSONDecodeError:
		payload = {}

	school_slug = payload.get("school_slug") or None
	if not request.user.is_superuser:
		profile = getattr(request.user, "profile", None)
		if profile and profile.school_slug:
			school_slug = profile.school_slug

	election = _active_election_or_none(school_slug=school_slug)
	if not election:
		return JsonResponse({"detail": "Election is not open."}, status=400)
	if not election.is_active():
		return JsonResponse({"detail": f"Election is scheduled but not active yet. Starts at: {election.starts_at}"}, status=400)


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

	# Block locked invigilators
	profile = getattr(request.user, "profile", None)
	if profile and profile.is_locked:
		return JsonResponse(
			{"detail": "Your account has been locked by the administrator. Ballot submission is disabled."},
			status=423,
		)

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


@require_GET
def results_page(request, election_id):
	election = get_object_or_404(Election, id=election_id)

	# Access control: unpublished results are staff/superuser only
	if not election.results_published:
		if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
			return HttpResponseForbidden(
				"<h2 style='font-family:sans-serif;text-align:center;margin-top:80px'>"
				"🔒 Results have not been published yet.</h2>"
			)

	# Test accounts — their votes are excluded from official results
	TEST_USERNAMES = ["testuser", "micestest"]
	exclude_user_ids = UserProfile.objects.filter(exclude_votes=True).values_list("user_id", flat=True)

	# Count only ballots that have actual votes in this election (excludes stale/orphaned ballots)
	total_submitted = (
		Vote.objects.filter(position__election=election)
		.exclude(ballot__started_by__username__in=TEST_USERNAMES)
		.exclude(ballot__started_by_id__in=exclude_user_ids)
		.values("ballot_id")
		.distinct()
		.count()
	)

	positions_data = []
	for position in election.positions.prefetch_related("candidates").order_by("order", "id"):
		vote_counts = (
			Vote.objects.filter(position=position)
			.exclude(ballot__started_by__username__in=TEST_USERNAMES)
			.exclude(ballot__started_by_id__in=exclude_user_ids)
			.values("candidate_id")
			.annotate(count=Count("id"))
		)
		counts_map = {vc["candidate_id"]: vc["count"] for vc in vote_counts}
		total_votes = sum(counts_map.values())

		candidates_data = []
		for candidate in position.candidates.order_by("order", "id"):
			votes = counts_map.get(candidate.id, 0)
			pct = round((votes / total_votes * 100) if total_votes else 0, 1)
			candidates_data.append({
				"id": candidate.id,
				"name": candidate.name,
				"photo": candidate.photo,
				"symbol": candidate.symbol,
				"class_name": candidate.class_name,
				"votes": votes,
				"pct": pct,
			})

		# Sort descending by votes to find winner
		candidates_data.sort(key=lambda c: c["votes"], reverse=True)
		winner_votes = candidates_data[0]["votes"] if candidates_data else 0
		for c in candidates_data:
			c["is_winner"] = (c["votes"] == winner_votes and winner_votes > 0)

		positions_data.append({
			"name": position.name,
			"icon": position.icon,
			"total_votes": total_votes,
			"candidates": candidates_data,
		})

	context = {
		"election": election,
		"positions": positions_data,
		"total_submitted": total_submitted,
		"is_superuser": request.user.is_authenticated and request.user.is_superuser,
	}
	return render(request, "voting/results.html", context)


@login_required
@require_POST
def api_publish_results(request, election_id):
	if not request.user.is_superuser:
		return JsonResponse({"detail": "Superuser access required."}, status=403)

	election = get_object_or_404(Election, id=election_id)
	election.results_published = not election.results_published
	election.save(update_fields=["results_published"])
	return JsonResponse({"published": election.results_published}, status=200)


@login_required
@require_GET
def api_list_invigilators(request):
	"""Return list of all non-superuser users with their lock status (superuser only)."""
	if not request.user.is_superuser:
		return JsonResponse({"detail": "Superuser access required."}, status=403)

	users = (
		User.objects
		.filter(is_superuser=False)
		.select_related("profile")
		.order_by("username")
	)

	data = []
	for u in users:
		profile = getattr(u, "profile", None)
		if profile is None:
			profile, _ = UserProfile.objects.get_or_create(user=u)
		data.append({
			"id": u.id,
			"username": u.username,
			"full_name": u.get_full_name() or u.username,
			"is_staff": u.is_staff,
			"is_active": u.is_active,
			"is_locked": profile.is_locked,
			"locked_reason": profile.locked_reason,
			"locked_at": profile.locked_at.isoformat() if profile.locked_at else None,
			"school_name": profile.school_name,
			"school_slug": profile.school_slug,
			"exclude_votes": profile.exclude_votes,
		})

	return JsonResponse({"users": data}, status=200)


@login_required
@require_POST
def api_toggle_user_lock(request, user_id):
	"""Lock or unlock a specific invigilator user (superuser only)."""
	if not request.user.is_superuser:
		return JsonResponse({"detail": "Superuser access required."}, status=403)

	target_user = get_object_or_404(User, id=user_id)

	if target_user.is_superuser:
		return JsonResponse({"detail": "Cannot lock a superuser account."}, status=400)

	try:
		payload = json.loads(request.body.decode("utf-8"))
	except json.JSONDecodeError:
		payload = {}

	reason = payload.get("reason", "Locked by administrator for result publishing")

	profile, _ = UserProfile.objects.get_or_create(user=target_user)
	profile.is_locked = not profile.is_locked
	if profile.is_locked:
		profile.locked_at = timezone.now()
		profile.locked_reason = reason
	else:
		profile.locked_at = None
		profile.locked_reason = ""
	profile.save()

	return JsonResponse({
		"user_id": target_user.id,
		"username": target_user.username,
		"is_locked": profile.is_locked,
	}, status=200)
