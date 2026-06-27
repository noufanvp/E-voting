"""
Admin Portal Views — superuser-only election management module.

Provides full CRUD for Elections, Positions, and Candidates,
including image upload handling for logos, candidate photos, and symbols.
"""
import json
import os
import uuid

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Ballot, Candidate, Election, Position, UserProfile, Vote


# ── Helpers ──────────────────────────────────────────────────────────────────

def _superuser_required(view_fn):
    """Decorator: login + superuser check."""
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "portal/403.html", status=403)
        return view_fn(request, *args, **kwargs)
    _wrapped.__name__ = view_fn.__name__
    return _wrapped


def _save_upload(file_obj, folder):
    """Save an uploaded file and return the storage-assigned name.
    When Cloudinary is active, the returned name includes the version (e.g. v1782546959/...),
    which is required to correctly generate Cloudinary delivery URLs later.
    """
    if not file_obj:
        return None
    ext = os.path.splitext(file_obj.name)[1].lower() or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    rel_path = f"{folder}/{filename}"
    # IMPORTANT: use the return value — Cloudinary storage returns a versioned name
    saved_name = default_storage.save(rel_path, ContentFile(file_obj.read()))
    return saved_name



def _delete_media(path):
    """Delete a media-uploaded file (skip if it's a legacy static path).
    Safe to call with any path format — versioned Cloudinary paths, local paths, or empty values.
    """
    if not path:
        return
    path_str = getattr(path, "name", str(path))
    if not path_str:
        return
    # Skip static git-tracked assets — they must never be deleted
    if path_str.startswith("voting/"):
        return
    try:
        default_storage.delete(path_str)
    except Exception:
        # Silently ignore deletion errors — the DB record will still be removed
        pass


def _election_stats(election):
    """Return dict of stats for an election."""
    positions = election.positions.prefetch_related("candidates").all()
    candidate_count = sum(p.candidates.count() for p in positions)
    
    exclude_user_ids = UserProfile.objects.filter(exclude_votes=True).values_list("user_id", flat=True)
    TEST_USERNAMES = ["testuser", "micestest"]
    
    ballot_count = election.ballots.filter(
        status=Ballot.STATUS_SUBMITTED
    ).exclude(
        started_by__username__in=TEST_USERNAMES
    ).exclude(
        started_by_id__in=exclude_user_ids
    ).count()
    
    return {
        "position_count": positions.count(),
        "candidate_count": candidate_count,
        "ballot_count": ballot_count,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

@_superuser_required
def portal_home(request):
    elections = (
        Election.objects
        .prefetch_related("positions__candidates", "ballots")
        .order_by("-created_at")
    )
    elections_data = []
    for e in elections:
        stats = _election_stats(e)
        logo_url = e.logo_url if e.logo else None
        elections_data.append({
            "obj": e,
            "stats": stats,
            "logo_url": logo_url,
            "kiosk_url": f"/vote/{e.school_slug}/" if e.school_slug else None,
        })

    context = {
        "elections_data": elections_data,
        "total_elections": len(elections_data),
        "active_count": sum(1 for ed in elections_data if ed["obj"].status == Election.STATUS_OPEN),
    }
    return render(request, "portal/home.html", context)


# ── Election CRUD ─────────────────────────────────────────────────────────────

@_superuser_required
def portal_election_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        school_name = request.POST.get("school_name", "").strip()
        school_slug = request.POST.get("school_slug", "").strip()
        status = request.POST.get("status", Election.STATUS_DRAFT)
        starts_at = request.POST.get("starts_at") or None
        ends_at = request.POST.get("ends_at") or None
        logo_file = request.FILES.get("logo")

        errors = {}
        if not title:
            errors["title"] = "Election title is required."
        if not school_name:
            errors["school_name"] = "School name is required."

        if errors:
            return render(request, "portal/election_form.html", {
                "errors": errors, "form": request.POST, "is_create": True,
            })

        with transaction.atomic():
            election = Election(
                title=title,
                school_name=school_name,
                school_slug=school_slug or slugify(school_name) or "school",
                status=status,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            if logo_file:
                logo_path = _save_upload(logo_file, "elections/logos")
                election.logo = logo_path
            election.save()

        return redirect("portal-positions", election_id=election.id)

    return render(request, "portal/election_form.html", {"is_create": True, "form": {}})


@_superuser_required
def portal_election_edit(request, election_id):
    election = get_object_or_404(Election, id=election_id)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        school_name = request.POST.get("school_name", "").strip()
        school_slug = request.POST.get("school_slug", "").strip()
        status = request.POST.get("status", election.status)
        starts_at = request.POST.get("starts_at") or None
        ends_at = request.POST.get("ends_at") or None
        results_published = request.POST.get("results_published") == "on"
        logo_file = request.FILES.get("logo")
        remove_logo = request.POST.get("remove_logo") == "on"

        errors = {}
        if not title:
            errors["title"] = "Election title is required."
        if not school_name:
            errors["school_name"] = "School name is required."

        if errors:
            return render(request, "portal/election_form.html", {
                "errors": errors, "election": election, "is_create": False,
                "form": request.POST,
            })

        with transaction.atomic():
            election.title = title
            election.school_name = school_name
            election.school_slug = school_slug or slugify(school_name) or "school"
            election.status = status
            election.starts_at = starts_at
            election.ends_at = ends_at
            election.results_published = results_published

            if remove_logo and election.logo:
                _delete_media(str(election.logo))
                election.logo = None
            elif logo_file:
                old_logo = str(election.logo) if election.logo else None
                logo_path = _save_upload(logo_file, "elections/logos")
                election.logo = logo_path
                if old_logo:
                    _delete_media(old_logo)

            election.save()

        return redirect("portal-home")

    logo_url = election.logo_url if election.logo else None
    return render(request, "portal/election_form.html", {
        "election": election,
        "is_create": False,
        "logo_url": logo_url,
        "form": {
            "title": election.title,
            "school_name": election.school_name,
            "school_slug": election.school_slug,
            "status": election.status,
            "starts_at": election.starts_at.strftime("%Y-%m-%dT%H:%M") if election.starts_at else "",
            "ends_at": election.ends_at.strftime("%Y-%m-%dT%H:%M") if election.ends_at else "",
            "results_published": election.results_published,
        },
    })


@_superuser_required
@require_POST
def portal_election_delete(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    if election.logo:
        _delete_media(str(election.logo))
    # Cascade deletes positions/candidates/votes via FK
    election.delete()
    return redirect("portal-home")


@_superuser_required
@require_POST
def portal_election_status(request, election_id):
    """AJAX: toggle election status."""
    election = get_object_or_404(Election, id=election_id)
    try:
        body = json.loads(request.body)
        new_status = body.get("status")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if new_status not in (Election.STATUS_DRAFT, Election.STATUS_OPEN, Election.STATUS_CLOSED):
        return JsonResponse({"error": "Invalid status"}, status=400)

    election.status = new_status
    election.save(update_fields=["status"])
    return JsonResponse({"status": election.status})


# ── Positions ──────────────────────────────────────────────────────────────────

@_superuser_required
def portal_positions(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    positions = election.positions.prefetch_related("candidates").order_by("order", "id")
    return render(request, "portal/positions.html", {
        "election": election,
        "positions": positions,
    })


@_superuser_required
@require_POST
def portal_position_create(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    name = request.POST.get("name", "").strip()
    icon = request.POST.get("icon", "").strip()

    if not name:
        return redirect("portal-positions", election_id=election_id)

    # Next order value
    last_order = election.positions.order_by("-order").values_list("order", flat=True).first()
    next_order = (last_order or 0) + 1

    Position.objects.create(election=election, name=name, icon=icon, order=next_order)
    return redirect("portal-positions", election_id=election_id)


@_superuser_required
def portal_position_edit(request, position_id):
    position = get_object_or_404(Position, id=position_id)
    if request.method == "POST":
        position.name = request.POST.get("name", position.name).strip()
        position.icon = request.POST.get("icon", position.icon).strip()
        position.save(update_fields=["name", "icon"])
        return redirect("portal-positions", election_id=position.election_id)

    return render(request, "portal/position_edit.html", {"position": position})


@_superuser_required
@require_POST
def portal_position_delete(request, position_id):
    position = get_object_or_404(Position, id=position_id)
    election_id = position.election_id
    # Best-effort cleanup of candidate media files — never block deletion on errors
    try:
        for candidate in position.candidates.all():
            _delete_media(candidate.photo)
            _delete_media(candidate.symbol)
    except Exception:
        pass
    position.delete()
    return redirect("portal-positions", election_id=election_id)


@_superuser_required
@require_POST
def portal_positions_reorder(request):
    """AJAX: accept ordered list of position IDs and update their order."""
    try:
        body = json.loads(request.body)
        ordered_ids = body.get("order", [])
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    with transaction.atomic():
        for idx, pos_id in enumerate(ordered_ids):
            Position.objects.filter(id=pos_id).update(order=idx)

    return JsonResponse({"ok": True})


# ── Candidates ────────────────────────────────────────────────────────────────

@_superuser_required
def portal_candidate_create(request, position_id):
    position = get_object_or_404(Position, id=position_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        class_name = request.POST.get("class_name", "").strip()
        motto = request.POST.get("motto", "").strip()
        is_nota = request.POST.get("is_nota") == "on"
        symbol_name = request.POST.get("symbol_name", "").strip()
        photo_file = request.FILES.get("photo")
        symbol_file = request.FILES.get("symbol")

        errors = {}
        if not name:
            errors["name"] = "Candidate name is required."

        if errors:
            return render(request, "portal/candidate_form.html", {
                "position": position,
                "errors": errors,
                "form": request.POST,
                "is_create": True,
            })

        # Next order value
        last_order = position.candidates.order_by("-order").values_list("order", flat=True).first()
        next_order = (last_order or 0) + 1

        photo_path = _save_upload(photo_file, "candidates/photos") or ""
        symbol_path = _save_upload(symbol_file, "candidates/symbols") or ""

        Candidate.objects.create(
            position=position,
            name=name,
            class_name=class_name,
            motto=motto,
            photo=photo_path,
            symbol=symbol_path,
            symbol_name=symbol_name,
            order=next_order,
            is_nota=is_nota,
        )
        return redirect("portal-positions", election_id=position.election_id)

    return render(request, "portal/candidate_form.html", {
        "position": position,
        "is_create": True,
        "form": {},
    })


@_superuser_required
def portal_candidate_edit(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    position = candidate.position

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        class_name = request.POST.get("class_name", "").strip()
        motto = request.POST.get("motto", "").strip()
        is_nota = request.POST.get("is_nota") == "on"
        symbol_name = request.POST.get("symbol_name", "").strip()
        photo_file = request.FILES.get("photo")
        symbol_file = request.FILES.get("symbol")
        remove_photo = request.POST.get("remove_photo") == "on"
        remove_symbol = request.POST.get("remove_symbol") == "on"

        errors = {}
        if not name:
            errors["name"] = "Candidate name is required."

        if errors:
            return render(request, "portal/candidate_form.html", {
                "candidate": candidate,
                "position": position,
                "errors": errors,
                "form": request.POST,
                "is_create": False,
            })

        candidate.name = name
        candidate.class_name = class_name
        candidate.motto = motto
        candidate.symbol_name = symbol_name
        candidate.is_nota = is_nota

        if remove_photo:
            _delete_media(candidate.photo)
            candidate.photo = ""
        elif photo_file:
            _delete_media(candidate.photo)
            candidate.photo = _save_upload(photo_file, "candidates/photos") or ""

        if remove_symbol:
            _delete_media(candidate.symbol)
            candidate.symbol = ""
        elif symbol_file:
            _delete_media(candidate.symbol)
            candidate.symbol = _save_upload(symbol_file, "candidates/symbols") or ""

        candidate.save()
        return redirect("portal-positions", election_id=position.election_id)

    # Build preview URLs for existing images
    def image_url(path):
        if not path:
            return None
        path_str = getattr(path, "name", str(path))
        if not path_str:
            return None
        if path_str.startswith("voting/"):
            return f"/static/{path_str}"
        return getattr(path, "url", f"/media/{path_str}")

    return render(request, "portal/candidate_form.html", {
        "candidate": candidate,
        "position": position,
        "is_create": False,
        "photo_url": image_url(candidate.photo),
        "symbol_url": image_url(candidate.symbol),
        "form": {
            "name": candidate.name,
            "class_name": candidate.class_name,
            "motto": candidate.motto,
            "symbol_name": candidate.symbol_name,
            "is_nota": candidate.is_nota,
        },
    })


@_superuser_required
@require_POST
def portal_candidate_delete(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    election_id = candidate.position.election_id
    _delete_media(candidate.photo)
    _delete_media(candidate.symbol)
    candidate.delete()
    return redirect("portal-positions", election_id=election_id)


# ── Invigilators Management ──

@_superuser_required
def portal_invigilators(request):
    invigilators = User.objects.filter(is_superuser=False).select_related("profile").order_by("username")
    return render(request, "portal/invigilators.html", {
        "invigilators": invigilators,
    })


@_superuser_required
def portal_invigilator_create(request):
    schools = Election.objects.values_list("school_name", flat=True).distinct()
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        
        school_select = request.POST.get("school_select", "").strip()
        school_custom = request.POST.get("school_custom", "").strip()
        school_name = school_custom if school_select == "__custom__" else school_select
        
        errors = {}
        if not username:
            errors["username"] = "Username is required."
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Username is already taken."
            
        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
            
        if not school_name:
            errors["school"] = "School assignment is required."
            
        if errors:
            return render(request, "portal/invigilator_form.html", {
                "errors": errors,
                "form": request.POST,
                "is_create": True,
                "schools": schools,
            })
            
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                is_staff=False,
                is_superuser=False,
            )
            if full_name:
                parts = full_name.split(" ", 1)
                user.first_name = parts[0]
                if len(parts) > 1:
                    user.last_name = parts[1]
                user.save()
                
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.school_name = school_name
            profile.school_slug = slugify(school_name) or "school"
            profile.exclude_votes = request.POST.get("exclude_votes") == "on"
            profile.save()
            
        return redirect("portal-invigilators")
        
    return render(request, "portal/invigilator_form.html", {
        "is_create": True,
        "form": {},
        "schools": schools,
    })


@_superuser_required
def portal_invigilator_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id, is_superuser=False)
    profile = getattr(user_obj, "profile", None)
    if not profile:
        profile, _ = UserProfile.objects.get_or_create(user=user_obj)
        
    schools = Election.objects.values_list("school_name", flat=True).distinct()
    
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        password = request.POST.get("password", "").strip()
        
        school_select = request.POST.get("school_select", "").strip()
        school_custom = request.POST.get("school_custom", "").strip()
        school_name = school_custom if school_select == "__custom__" else school_select
        
        errors = {}
        if password and len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
            
        if not school_name:
            errors["school"] = "School assignment is required."
            
        if errors:
            return render(request, "portal/invigilator_form.html", {
                "errors": errors,
                "user_obj": user_obj,
                "profile": profile,
                "is_create": False,
                "schools": schools,
                "form": request.POST,
            })
            
        with transaction.atomic():
            if full_name:
                parts = full_name.split(" ", 1)
                user_obj.first_name = parts[0]
                user_obj.last_name = parts[1] if len(parts) > 1 else ""
            else:
                user_obj.first_name = ""
                user_obj.last_name = ""
                
            if password:
                user_obj.set_password(password)
                
            user_obj.save()
            
            profile.school_name = school_name
            profile.school_slug = slugify(school_name) or "school"
            profile.exclude_votes = request.POST.get("exclude_votes") == "on"
            profile.save()
            
        return redirect("portal-invigilators")
        
    full_name = user_obj.get_full_name() or user_obj.username
    return render(request, "portal/invigilator_form.html", {
        "user_obj": user_obj,
        "profile": profile,
        "is_create": False,
        "schools": schools,
        "form": {
            "username": user_obj.username,
            "full_name": full_name,
            "school_select": profile.school_name,
            "exclude_votes": profile.exclude_votes,
        },
    })


@_superuser_required
@require_POST
def portal_invigilator_delete(request, user_id):
    user_obj = get_object_or_404(User, id=user_id, is_superuser=False)
    user_obj.delete()
    return redirect("portal-invigilators")
