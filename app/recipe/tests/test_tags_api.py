"""
Test for tags API
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAG_URL = reverse('recipes:tags-list')


def detail_tag(tag_id):
    """Return a tag object by its id"""
    return reverse('recipes:tags-detail', args=[tag_id])


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests"""

    def SetUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(TAG_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests"""
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='testpass123'
            )
        self.client.force_authenticate(self.user)

    def test_retrive_tags(self):
        """Test retrieving a list of tags"""

        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAG_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""

        user2 = create_user(email='user2@example.com', password='test@123')
        Tag.objects.create(user=user2, name='Fruits')
        tag = Tag.objects.create(user=self.user, name='comfort food')

        res = self.client.get(TAG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user=self.user, name='Butter chicken')
        payload = {'name': 'Indian food'}
        url = detail_tag(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting a tag"""
        tag = Tag.objects.create(user=self.user, name='chicken')

        url = detail_tag(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tag = Tag.objects.filter(user=self.user)
        self.assertFalse(tag.exists())

    def test_filter_Tags_assigned_to_recipe(self):
        """Test listing Tags to those assigned to recipe"""
        tag1 = Tag.objects.create(user=self.user, name="vegitable")
        tag2 = Tag.objects.create(user=self.user, name="non-veg")
        recipe = Recipe.objects.create(
            title="test",
            time_minutes=10,
            price=Decimal('4.99'),
            user=self.user,
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAG_URL, {'assigned_only': 1})
        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_Tag_unique(self):
        """Test filtering Tags by assigned recipe returns unique items"""
        tag1 = Tag.objects.create(user=self.user, name="Breakefast")
        Tag.objects.create(user=self.user, name="dinner")
        recipe1 = Recipe.objects.create(
            title="test1",
            time_minutes=10,
            price=Decimal('4.99'),
            user=self.user,
            )
        recipe2 = Recipe.objects.create(
            title="test2",
            time_minutes=10,
            price=Decimal(9.99),
            user=self.user,
        )
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag1)

        res = self.client.get(TAG_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
