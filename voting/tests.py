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

# Create your tests here.
