from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Ballot
from .models import Candidate
from .models import Election
from .models import Position
from .models import Vote


class VotingFlowTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = get_user_model().objects.create_user(username="operator", password="StrongPass123!")

		self.election = Election.objects.create(
			title="Test Election",
			school_name="Test School",
			status=Election.STATUS_OPEN,
			starts_at=timezone.now(),
		)
		self.position = Position.objects.create(election=self.election, name="President", icon="👑", order=1)
		self.candidate_1 = Candidate.objects.create(position=self.position, name="A", class_name="10-A", order=1)
		self.candidate_2 = Candidate.objects.create(position=self.position, name="B", class_name="10-B", order=2)

		self.client.login(username="operator", password="StrongPass123!")

	def test_start_session(self):
		response = self.client.post(reverse("api-start-session"), data="{}", content_type="application/json")
		self.assertEqual(response.status_code, 201)
		payload = response.json()
		self.assertIn("ballot_id", payload)

	def test_vote_validation_candidate_position_mismatch(self):
		second_position = Position.objects.create(election=self.election, name="Vice", icon="🌟", order=2)
		wrong_candidate = Candidate.objects.create(position=second_position, name="Wrong", class_name="9-A", order=1)

		start = self.client.post(reverse("api-start-session"), data="{}", content_type="application/json").json()
		response = self.client.post(
			reverse("api-save-selection"),
			data={
				"ballot_id": start["ballot_id"],
				"position_id": self.position.id,
				"candidate_id": wrong_candidate.id,
			},
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 400)

	def test_duplicate_submit_prevention(self):
		start = self.client.post(reverse("api-start-session"), data="{}", content_type="application/json").json()
		self.client.post(
			reverse("api-save-selection"),
			data={
				"ballot_id": start["ballot_id"],
				"position_id": self.position.id,
				"candidate_id": self.candidate_1.id,
			},
			content_type="application/json",
		)

		first_submit = self.client.post(
			reverse("api-submit-ballot"),
			data={"ballot_id": start["ballot_id"]},
			content_type="application/json",
		)
		second_submit = self.client.post(
			reverse("api-submit-ballot"),
			data={"ballot_id": start["ballot_id"]},
			content_type="application/json",
		)

		self.assertEqual(first_submit.status_code, 200)
		self.assertEqual(second_submit.status_code, 403)

	def test_election_closed_behavior(self):
		self.election.status = Election.STATUS_CLOSED
		self.election.save(update_fields=["status"])
		response = self.client.post(reverse("api-start-session"), data="{}", content_type="application/json")
		self.assertEqual(response.status_code, 400)

	def test_anonymous_ballot_storage(self):
		start = self.client.post(reverse("api-start-session"), data="{}", content_type="application/json").json()
		self.client.post(
			reverse("api-save-selection"),
			data={
				"ballot_id": start["ballot_id"],
				"position_id": self.position.id,
				"candidate_id": self.candidate_2.id,
			},
			content_type="application/json",
		)
		self.client.post(
			reverse("api-submit-ballot"),
			data={"ballot_id": start["ballot_id"]},
			content_type="application/json",
		)

		ballot = Ballot.objects.get(id=start["ballot_id"])
		vote = Vote.objects.get(ballot=ballot, position=self.position)

		self.assertTrue(ballot.receipt_token)
		self.assertEqual(ballot.status, Ballot.STATUS_SUBMITTED)
		self.assertEqual(vote.candidate_id, self.candidate_2.id)
		self.assertNotIn("student", ballot.__dict__)


class InvigilatorSecurityTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.superuser = get_user_model().objects.create_superuser(username="admin_user", password="SuperPassword123")
		
		# Create invigilators
		self.invigilator_a = get_user_model().objects.create_user(username="inv_a", password="InvPassword123")
		self.invigilator_a.profile.school_name = "School A"
		self.invigilator_a.profile.school_slug = "school-a"
		self.invigilator_a.profile.save()

		self.invigilator_b = get_user_model().objects.create_user(username="inv_b", password="InvPassword123")
		self.invigilator_b.profile.school_name = "School B"
		self.invigilator_b.profile.school_slug = "school-b"
		self.invigilator_b.profile.save()

		# Create elections for both schools
		self.election_a = Election.objects.create(
			title="Election A",
			school_name="School A",
			school_slug="school-a",
			status=Election.STATUS_OPEN,
			starts_at=timezone.now(),
		)
		self.election_b = Election.objects.create(
			title="Election B",
			school_name="School B",
			school_slug="school-b",
			status=Election.STATUS_OPEN,
			starts_at=timezone.now(),
		)

	def test_invigilator_kiosk_access_and_redirection(self):
		# Log in as inv_a
		self.client.login(username="inv_a", password="InvPassword123")
		
		# Try to access school-a kiosk
		response = self.client.get(reverse("kiosk-school", kwargs={"school_slug": "school-a"}))
		self.assertEqual(response.status_code, 200)

		# Try to access school-b kiosk -> should redirect to school-a
		response = self.client.get(reverse("kiosk-school", kwargs={"school_slug": "school-b"}))
		self.assertRedirects(response, reverse("kiosk-school", kwargs={"school_slug": "school-a"}))

		# Try to access root kiosk -> should redirect to school-a
		response = self.client.get(reverse("kiosk"))
		self.assertRedirects(response, reverse("kiosk-school", kwargs={"school_slug": "school-a"}))

	def test_invigilator_api_start_session_enforcement(self):
		# Log in as inv_a
		self.client.login(username="inv_a", password="InvPassword123")

		# Start session without slug or with school-b slug -> should still create Ballot for school-a (election_a)
		response = self.client.post(
			reverse("api-start-session"),
			data='{"school_slug": "school-b"}',
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 201)
		payload = response.json()
		ballot = Ballot.objects.get(id=payload["ballot_id"])
		self.assertEqual(ballot.election, self.election_a)

	def test_superuser_global_access(self):
		# Log in as superuser
		self.client.login(username="admin_user", password="SuperPassword123")

		# Should access school-a directly without redirect
		response = self.client.get(reverse("kiosk-school", kwargs={"school_slug": "school-a"}))
		self.assertEqual(response.status_code, 200)

		# Should access school-b directly without redirect
		response = self.client.get(reverse("kiosk-school", kwargs={"school_slug": "school-b"}))
		self.assertEqual(response.status_code, 200)

	def test_exclude_votes_from_results(self):
		# Create an invigilator with exclude_votes = True
		test_inv = get_user_model().objects.create_user(username="test_inv", password="Password123")
		test_inv.profile.school_name = "School A"
		test_inv.profile.school_slug = "school-a"
		test_inv.profile.exclude_votes = True
		test_inv.profile.save()

		# Log in as test_inv
		self.client.login(username="test_inv", password="Password123")

		# Start a session
		response = self.client.post(
			reverse("api-start-session"),
			data='{}',
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 201)
		ballot_id = response.json()["ballot_id"]

		# Create a position and candidate under self.election_a
		pos = Position.objects.create(election=self.election_a, name="President", icon="👑", order=1)
		cand = Candidate.objects.create(position=pos, name="Candidate A", order=1)

		# Save selection
		self.client.post(
			reverse("api-save-selection"),
			data={
				"ballot_id": ballot_id,
				"position_id": pos.id,
				"candidate_id": cand.id,
			},
			content_type="application/json",
		)

		# Submit ballot
		self.client.post(
			reverse("api-submit-ballot"),
			data={"ballot_id": ballot_id},
			content_type="application/json",
		)

		# Get results page
		# Log in as superuser to view results page
		self.client.login(username="admin_user", password="SuperPassword123")
		response = self.client.get(reverse("results", kwargs={"election_id": self.election_a.id}))
		self.assertEqual(response.status_code, 200)

		# Total submitted should be 0 because it's excluded
		self.assertEqual(response.context["total_submitted"], 0)


# Create your tests here.
