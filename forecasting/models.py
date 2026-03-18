from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    gender = models.CharField(max_length=10, blank=True)
    dob = models.DateField(null=True, blank=True)
    is_server_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}"


class CovidDataset(models.Model):
    province_or_state = models.CharField(max_length=200)
    country_or_region = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    from_date = models.DateField()
    to_date = models.DateField()
    number_of_days = models.IntegerField()
    new_cases = models.IntegerField(default=0)
    death_cases = models.IntegerField(default=0)
    recovery_cases = models.IntegerField(default=0)
    ongoing_treatment_cases = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-from_date']

    def __str__(self):
        return f"{self.country_or_region} - {self.province_or_state}"


class PredictionResult(models.Model):
    MODEL_CHOICES = [
        ('LR', 'Linear Regression'),
        ('LASSO', 'LASSO Regression'),
        ('SVM', 'Support Vector Machine'),
        ('ES', 'Exponential Smoothing'),
    ]
    PREDICTION_TYPE = [
        ('new_cases', 'New Cases'),
        ('death_cases', 'Death Cases'),
        ('recovery_cases', 'Recovery Cases'),
    ]
    model_name = models.CharField(max_length=10, choices=MODEL_CHOICES)
    prediction_type = models.CharField(max_length=20, choices=PREDICTION_TYPE)
    country = models.CharField(max_length=200)
    prediction_date = models.DateField()
    predicted_value = models.FloatField()
    r2_score = models.FloatField(null=True, blank=True)
    mse = models.FloatField(null=True, blank=True)
    mae = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.model_name} | {self.country} | {self.prediction_date}"