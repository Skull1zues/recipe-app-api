"""
Tests for the ingredient API.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)
from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse('recipes:ingredients-list')


def detail_url(id):
    """Create and return an ingredient detail url"""
    return reverse('recipes:ingredients-detail', args=[id])


def create_user(email='user@example.com', password='Test@123'):
    """Create a test user."""
    return get_user_model().objects.create_user(email, password)


class PublicIngredientApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required."""
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredentsApiTest(TestCase):
    """Test authenticated API requests."""

    def setUp(self) -> None:
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrive_ingredients(self):
        """Test retrieving a list of ingredients."""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENT_URL)

        Ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(Ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limited_to_user(self):
        """Test that ingredients returned are for the authenticated user."""
        user2 = create_user(email='user2@example.com', password='Test@123')
        Ingredient.objects.create(user=user2, name='Salt')
        ingredient = Ingredient.objects.create(user=self.user, name='Veggie')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredent(self):
        """Test updating an existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Veggie')

        payload = {'name': 'Coriender'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredent(self):
        """Test deleting an existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Veggie')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredient = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredient.exists())

    def test_filter_ingredients_assigned_to_recipe(self):
        """Test listing ingredient to those assigned to recipe"""
        in1 = Ingredient.objects.create(user=self.user, name="rice")
        in2 = Ingredient.objects.create(user=self.user, name="dal")
        recipe = Recipe.objects.create(
            title="test",
            time_minutes=10,
            price=Decimal('4.99'),
            user=self.user,
        )
        recipe.ingredient.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})
        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtering ingredients by assigned recipe returns unique items"""
        in1 = Ingredient.objects.create(user=self.user, name="rice")
        Ingredient.objects.create(user=self.user, name="dal")
        recipe1 = Recipe.objects.create(
            title="test1",
            time_minutes=10,
            price=Decimal('4.99'),
            user=self.user,
            )
        recipe2 =Recipe.objects.create(
            title="test2",
            time_minutes=10,
            price=Decimal(9.99),
            user=self.user,
        )
        recipe1.ingredient.add(in1)
        recipe2.ingredient.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)

