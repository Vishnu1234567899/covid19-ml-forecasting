from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('datasets/', views.browse_datasets, name='browse_datasets'),
    path('datasets/add/', views.add_dataset, name='add_dataset'),
    path('datasets/load-sample/', views.load_sample_data, name='load_sample_data'),
    path('prediction/', views.prediction_view, name='prediction'),
    path('predictions/view/', views.view_predictions, name='view_predictions'),
    path('predictions/export/<str:prediction_type>/', views.extract_predictions_csv, name='extract_predictions'),
    path('charts/', views.charts_view, name='charts'),
    path('profile/', views.profile_view, name='profile'),
    path('datasets/fetch-live/', views.fetch_live_data, name='fetch_live_data'),
]