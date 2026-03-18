from django.contrib import admin
from .models import UserProfile, CovidDataset, PredictionResult

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'country', 'city', 'is_server_admin']

@admin.register(CovidDataset)
class CovidDatasetAdmin(admin.ModelAdmin):
    list_display = ['country_or_region', 'province_or_state', 'from_date', 'new_cases', 'death_cases', 'recovery_cases']
    list_filter = ['country_or_region']
    search_fields = ['country_or_region', 'province_or_state']

@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'prediction_type', 'country', 'prediction_date', 'predicted_value']