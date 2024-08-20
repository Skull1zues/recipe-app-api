"""
URL mapping for the recipe API
"""
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from recipe import views


router = DefaultRouter()
router.register('recipe', views.RecipeViewSet, 'recipe')
router.register('tags', views.TagViewSet, 'tags')
router.register('ingredients', views.IngredientViewSet, 'ingredients')

app_name = 'recipes'

urlpatterns = [
    path('', include(router.urls)),
]
