from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.valid_payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '0123456789',
            'role': 'PATIENT'
        }

    def test_user_can_register_correctly(self):
        """Test creates a user with valid payload."""
        print("\n--> TEST: Registration with valid payload")
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')
        self.assertEqual(User.objects.get().role, 'PATIENT')
        print("    [OK] User created successfully")

    def test_user_cannot_register_missing_fields(self):
        """Test registration fails if mandatory fields are missing (username/password)."""
        print("\n--> TEST: Registration failure on missing fields")
        invalid_payload = self.valid_payload.copy()
        del invalid_payload['password']
        response = self.client.post(self.register_url, invalid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        print("    [OK] Missing fields rejected correctly")

    def test_password_is_hashed(self):
        """Test that the password is not stored in plain text."""
        print("\n--> TEST: Password hashing security")
        self.client.post(self.register_url, self.valid_payload)
        user = User.objects.get(username='testuser')
        self.assertNotEqual(user.password, 'securepassword123')
        self.assertTrue(user.check_password('securepassword123'))
        print("    [OK] Password is securely hashed")
