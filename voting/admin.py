from django.contrib import admin

from .models import Ballot
from .models import Candidate
from .models import Election
from .models import Position
from .models import Vote


class CandidateInline(admin.TabularInline):
	model = Candidate
	extra = 0
	fields = ("order", "name", "class_name", "motto", "photo", "is_nota")
	ordering = ("order", "id")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
	list_display = ("name", "election", "order")
	list_filter = ("election",)
	search_fields = ("name", "election__title")
	ordering = ("election", "order")
	inlines = (CandidateInline,)


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
	list_display = ("title", "school_name", "status", "starts_at", "ends_at")
	list_filter = ("status",)
	search_fields = ("title", "school_name")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
	list_display = ("name", "position", "class_name", "order", "is_nota")
	list_filter = ("position__election", "position")
	search_fields = ("name", "position__name")
	ordering = ("position", "order")


class VoteInline(admin.TabularInline):
	model = Vote
	extra = 0
	fields = ("position", "candidate", "created_at")
	readonly_fields = ("position", "candidate", "created_at")
	can_delete = False


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
	list_display = ("receipt_token", "election", "status", "created_at", "submitted_at")
	list_filter = ("election", "status")
	search_fields = ("receipt_token", "session_token")
	readonly_fields = (
		"election",
		"started_by",
		"session_token",
		"receipt_token",
		"status",
		"created_at",
		"submitted_at",
	)
	inlines = (VoteInline,)

	def has_add_permission(self, request):
		return False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
	list_display = ("ballot", "position", "candidate", "created_at")
	readonly_fields = ("ballot", "position", "candidate", "created_at")
	list_filter = ("position__election", "position")

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False
