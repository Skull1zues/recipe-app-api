"""
Test for recipe PI
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailsSerializer,
    )


RECIPE_URL = reverse('recipes:recipe-list')


def detail_url(recipe_id):
    """create and retuen a recipe details URL."""
    return reverse('recipes:recipe-detail', args=[recipe_id])

def image_upload_url(recipe_id):
    """create and return a recipe image upload URL."""
    return reverse('recipes:recipe-upload-image', args=[recipe_id])

def create_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.55'),
        'description': 'Sample recipe for testing',
        'link': 'http://example.com/recipe'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated recipe API access"""
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API"""
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test Authenticated API request"""
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_user(email='user@e.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrive_recipe(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list limited to the auth user"""
        user2 = create_user(
            email='otheruser@example.com',
            password='password123'
            )
        create_recipe(user=user2)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_details(self):
        """Test get recipe details by recipe id"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailsSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a new recipe"""
        payload = {
            'title': 'Test Recipe',
            'time_minutes': 10,
            'price': Decimal('5.99'),
        }
        res = self.client.post(RECIPE_URL, payload)  # /api/recipes/recipe

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_pertial_update(self):
        """Test updating a recipe with a partial update"""
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title='sample recipe',
            link=original_link
            )
        payload = {'title': 'New Recipe Title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update recipe"""
        recipe = create_recipe(
            user=self.user,
            title='sample recipe',
            link='www.google.com',
            description='Sample description'
        )

        payload = {
            'title': 'New Recipe Title',
            'link': 'www.g.com',
            'time_minutes': 15,
            'price': Decimal('5.90')
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test updating the user returns an error"""
        new_user = create_user(email='u2@gmail.com', password='testpass@123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_user_recipe(self):
        """Test trying to delete other user recipe delete"""
        new_user = create_user(email='u2@gmail.com', password='testpass@123')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def create_recipe_with_new_tags(self):
        """Test creating a recipe with a new tags"""
        payload = {
            'title': 'recipe1',
            'time_minutes': 30,
            'price': Decimal('5.90'),
            'tags': [{'name': 'tag1'}, {'name': 'tag2'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='jason')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exits = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exits)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags"""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'recipe1',
            'time_minutes': 30,
            'price': Decimal('5.90'),
            'tags': [{'name': 'Indian'}, {'name': 'tag2'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exits = recipe.tags.filter(
                name=tag['name'],
                user=self.user
                ).exists()
            self.assertTrue(exits)

    def test_create_tag_on_update(self):
        """Test creating tag when update"""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe"""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakefast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipe's tags"""
        tag = Tag.objects.create(user=self.user, name='Sweet')
        receipe = create_recipe(user=self.user)
        receipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(receipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(receipe.tags.count(), 0)

    def test_recipe_with_new_ingredients(self):
        """Test creating a api with new Ingredient"""

        payload1 = {
            'title': 'test recipe',
            'time_minutes': 30,
            'price': Decimal('5.90'),
            'ingredient': [{"name": "ingredient1"}, {"name": "ingredient2"}],
        }
        res = self.client.post(RECIPE_URL, payload1, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredient.count(), 2)
        for ingre in payload1['ingredient']:
            exits = recipe.ingredient.filter(
                name=ingre['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exits)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a recipe with existing tags"""
        ingredient = Ingredient.objects.create(user=self.user, name='Jeera')
        payload = {
            'title': 'recipe1',
            'time_minutes': 30,
            'price': Decimal('5.90'),
            'ingredient': [{'name': 'Jeera'}, {'name': 'rice'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredient.count(), 2)
        self.assertIn(ingredient, recipe.ingredient.all())
        for ingredient in payload['ingredient']:
            exits = recipe.ingredient.filter(
                name=ingredient['name'],
                user=self.user
                ).exists()
            self.assertTrue(exits)

    def test_create_ingredient_on_update(self):
        """Test creating tag when update"""
        recipe = create_recipe(user=self.user)

        payload_ingredient = {'ingredient': [{'name': 'Butter'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload_ingredient, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Butter')
        self.assertIn(new_ingredient, recipe.ingredient.all())

    def test_update_ingredient_assign_ingredient(self):
        """Test assigning an existing tag when updating a recipe"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingredient.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Paper')

        payload = {'ingredient': [{'name': 'Paper'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredient.all())
        self.assertNotIn(ingredient1, recipe.ingredient.all())

    def test_clear_recipe_ingredient(self):
        """Test clearing a recipe's tags"""
        ingredient = Ingredient.objects.create(user=self.user, name='Sweet')
        receipe = create_recipe(user=self.user)
        receipe.ingredient.add(ingredient)

        payload = {'ingredient': []}
        url = detail_url(receipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(receipe.ingredient.count(), 0)
