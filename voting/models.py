import secrets

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify


class Election(models.Model):
	STATUS_DRAFT = "draft"
	STATUS_OPEN = "open"
	STATUS_CLOSED = "closed"
	STATUS_CHOICES = (
		(STATUS_DRAFT, "Draft"),
		(STATUS_OPEN, "Open"),
		(STATUS_CLOSED, "Closed"),
	)

	title = models.CharField(max_length=200)
	school_name = models.CharField(max_length=200)
	school_slug = models.SlugField(
		max_length=100,
		blank=True,
		db_index=True,
		help_text="Auto-generated from school name. Used in kiosk URL: /vote/<slug>/",
	)
	logo = models.ImageField(
		upload_to="elections/logos/",
		blank=True,
		help_text="Optional school logo shown in the kiosk header.",
	)
	status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
	starts_at = models.DateTimeField(null=True, blank=True)
	ends_at = models.DateTimeField(null=True, blank=True)
	results_published = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("-created_at",)

	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		"""Auto-populate school_slug from school_name if not set."""
		if not self.school_slug and self.school_name:
			base_slug = slugify(self.school_name)
			self.school_slug = base_slug or "school"
		super().save(*args, **kwargs)

	def is_active(self):
		now = timezone.now()
		if self.status != self.STATUS_OPEN:
			return False
		if self.starts_at and now < self.starts_at:
			return False
		if self.ends_at and now > self.ends_at:
			return False
		return True


class Position(models.Model):
	election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="positions")
	name = models.CharField(max_length=140)
	icon = models.CharField(max_length=16, blank=True)
	order = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ("order", "id")
		constraints = [
			models.UniqueConstraint(fields=("election", "name"), name="uniq_position_name_per_election"),
			models.UniqueConstraint(fields=("election", "order"), name="uniq_position_order_per_election"),
		]

	def __str__(self):
		return f"{self.election.title}: {self.name}"


class Candidate(models.Model):
	position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="candidates")
	name = models.CharField(max_length=140)
	class_name = models.CharField(max_length=80, blank=True)
	motto = models.CharField(max_length=255, blank=True)
	photo = models.ImageField(upload_to="candidates/photos", blank=True, null=True)
	symbol = models.ImageField(upload_to="candidates/symbols", blank=True, null=True)
	symbol_name = models.CharField(max_length=50, blank=True, help_text="Text to display alongside the symbol (e.g. 'Globe')")
	order = models.PositiveIntegerField(default=0)
	is_nota = models.BooleanField(default=False)

	class Meta:
		ordering = ("order", "id")
		constraints = [
			models.UniqueConstraint(fields=("position", "order"), name="uniq_candidate_order_per_position"),
		]

	def __str__(self):
		return f"{self.position.name}: {self.name}"


class Ballot(models.Model):
	STATUS_STARTED = "started"
	STATUS_SUBMITTED = "submitted"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = (
		(STATUS_STARTED, "Started"),
		(STATUS_SUBMITTED, "Submitted"),
		(STATUS_CANCELLED, "Cancelled"),
	)

	election = models.ForeignKey(Election, on_delete=models.PROTECT, related_name="ballots")
	started_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="started_ballots",
	)
	session_token = models.CharField(max_length=64, unique=True, db_index=True)
	receipt_token = models.CharField(max_length=12, unique=True, db_index=True)
	status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_STARTED)
	created_at = models.DateTimeField(auto_now_add=True)
	submitted_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ("-created_at",)

	def __str__(self):
		return f"Ballot {self.receipt_token} ({self.status})"

	@staticmethod
	def generate_session_token():
		return secrets.token_urlsafe(32)

	@staticmethod
	def generate_receipt_token():
		return secrets.token_hex(4).upper()


class Vote(models.Model):
	ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="votes")
	position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="votes")
	candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name="votes")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=("ballot", "position"), name="uniq_vote_per_position_per_ballot"),
		]
		indexes = [
			models.Index(fields=("ballot", "position")),
			models.Index(fields=("position", "candidate")),
		]

	def __str__(self):
		return f"{self.ballot.receipt_token}: {self.position.name} -> {self.candidate.name}"


# ── User Profile (lock / unlock invigilators) ─────────────────────────────
class UserProfile(models.Model):
	"""One-to-one extension of the built-in User, adds invigilator lock state."""

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="profile",
	)
	is_locked = models.BooleanField(
		default=False,
		help_text="When True, this user cannot start or submit ballots.",
	)
	locked_at = models.DateTimeField(null=True, blank=True)
	locked_reason = models.CharField(max_length=255, blank=True)
	school_name = models.CharField(
		max_length=200,
		blank=True,
		help_text="The school this invigilator is assigned to (blank for superusers/all schools).",
	)
	school_slug = models.SlugField(
		max_length=100,
		blank=True,
		help_text="The school slug this invigilator is assigned to.",
	)
	exclude_votes = models.BooleanField(
		default=False,
		help_text="Exclude votes cast during sessions started by this invigilator from final results counting.",
	)

	class Meta:
		verbose_name = "User Profile"
		verbose_name_plural = "User Profiles"

	def __str__(self):
		status = "🔒 LOCKED" if self.is_locked else "✅ Active"
		return f"{self.user.username} [{status}]"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def _auto_create_user_profile(sender, instance, created, **kwargs):
	"""Automatically create a UserProfile whenever a new User is saved."""
	if created:
		UserProfile.objects.get_or_create(user=instance)
