from django.test import TestCase
from django.contrib.auth.models import User
from gymApp.models import Profile, Membership, MembershipType, stripe
from datetime import datetime
from unittest.mock import patch

class UserProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_special$', password='12345')
        self.profile = Profile.objects.create(user=self.user)

    def test_profile_creation(self):
        self.assertEqual(self.profile.user.username, 'testuser_special$')
        self.assertTrue(self.profile.qr_code)  # Check if QR code is generated

    def test_qr_code_generation(self):
        self.profile.generate_qr_code()  # Ensure QR identifier is generated initially
        initial_identifier = self.profile.qr_identifier
        self.profile.qr_identifier = None  # Reset identifier to simulate new generation
        self.profile.generate_qr_code()
        self.assertNotEqual(initial_identifier, self.profile.qr_identifier)
        self.assertTrue(self.profile.qr_code.url.endswith('.png'))

    def test_profile_deletion(self):
        self.profile.delete()
        self.assertFalse(Profile.objects.filter(user=self.user).exists())


class MembershipTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testmember', password='12345')
        self.membership_type = MembershipType.objects.create(
            name="Basic",
            price_yen_male=1000,
            price_yen_female=1200,
            included_sessions=10,
            included_personal_trainings=5
        )
        self.membership = Membership.objects.create(user=self.user, membership_type=self.membership_type, start_date=datetime.today())

    def test_membership_creation(self):
        self.assertEqual(self.membership.user.username, 'testmember')
        self.assertEqual(self.membership.membership_type.name, "Basic")

    def test_prorate_sessions(self):
        join_date = datetime(2024, 5, 15)
        self.membership.prorate_sessions(join_date)
        expected_sessions = round(10 * (16 / 31))  # Assuming May has 31 days
        expected_personal_trainings = round(5 * (16 / 31))
        self.assertEqual(self.membership.remaining_sessions, expected_sessions)
        self.assertEqual(self.membership.remaining_personal_trainings, expected_personal_trainings)

    def test_different_months_proration(self):
        join_date_feb = datetime(2024, 2, 15)
        self.membership.prorate_sessions(join_date_feb)
        expected_sessions_feb = round(10 * (15 / 28))  # Assuming February has 28 days
        self.assertEqual(self.membership.remaining_sessions, expected_sessions_feb)

# class RenewalTest(TestCase):
#     def setUp(self):
#         self.user = User.objects.create_user(username='renewal_test', password='12345')
#         self.membership_type = MembershipType.objects.create(
#             name="Premium",
#             price_yen_male=2000,
#             price_yen_female=2200,
#             included_sessions=20
#         )
#         self.membership = Membership.objects.create(user=self.user, membership_type=self.membership_type, start_date=datetime.today(), end_date=datetime(2024, 5, 31))

#     def test_membership_renewal(self):
#         self.membership.renew_membership()
#         self.assertEqual(self.membership.end_date, datetime(2024, 6, 30))
#         self.assertEqual(self.membership.remaining_sessions, 20)
#         self.assertTrue(self.membership.is_active())


class StripeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='stripetest', password='12345')
        self.membership_type = MembershipType.objects.create(
            name="Standard",
            price_yen_male=1500,
            price_yen_female=1700,
            included_sessions=15
        )
        self.membership = Membership.objects.create(user=self.user, membership_type=self.membership_type, start_date=datetime.today())

    @patch('stripe.Subscription.retrieve')
    def test_stripe_subscription(self, mock_subscription_retrieve):
        mock_subscription_retrieve.return_value = {'status': 'active'}
        self.membership.stripe_subscription_id = 'sub_test'
        self.assertTrue(self.membership.check_stripe_subscription_status())
        self.assertIsNone(self.membership.end_date)

    @patch('stripe.Subscription.retrieve')
    def test_stripe_subscription_error(self, mock_subscription_retrieve):
        mock_subscription_retrieve.side_effect = stripe.error.StripeError('API connection error')
        self.membership.stripe_subscription_id = 'sub_test'
        self.assertFalse(self.membership.check_stripe_subscription_status())
        self.assertIsNotNone(self.membership.end_date)