import json
import csv
import requests
from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum

from .models import UserProfile, CovidDataset, PredictionResult
from .ml_models import run_all_models, get_best_model


SAMPLE_DATA = [
    ("Maharashtra", "India", 19.08, 72.88, "2020-04-01", "2020-04-08", 8, 10000, 1000, 3000, 6000),
    ("Delhi", "India", 28.71, 77.10, "2020-04-10", "2020-04-18", 8, 7000, 1000, 2000, 4000),
    ("Mumbai", "India", 19.08, 72.88, "2020-05-14", "2020-05-30", 16, 25000, 3000, 4000, 18000),
    ("Calcutta", "India", 22.57, 88.36, "2020-05-14", "2020-05-30", 16, 18000, 1000, 4000, 13000),
    ("Bangalore", "India", 12.97, 77.59, "2020-05-14", "2020-05-30", 16, 8000, 1000, 2000, 5000),
    ("Chennai", "India", 13.08, 80.27, "2020-04-22", "2020-04-30", 8, 10000, 1000, 3000, 6000),
    ("New York", "USA", 40.71, 74.01, "2020-05-14", "2020-05-30", 16, 12000, 2500, 2000, 7500),
    ("California", "USA", 36.77, 119.41, "2020-05-14", "2020-05-30", 16, 6000, 1500, 1200, 3300),
    ("Las Anges", "USA", 34.05, 118.24, "2020-05-14", "2020-05-30", 16, 5000, 300, 1200, 3500),
    ("Victoria", "Australia", -37.81, 144.96, "2020-04-22", "2020-04-30", 8, 600, 50, 300, 250),
    ("Colombia", "Canada", 49.28, -123.1, "2020-04-22", "2020-04-30", 8, 400, 100, 200, 100),
    ("New York", "USA", 40.71, 74.01, "2020-06-14", "2020-06-30", 16, 13000, 2500, 2000, 8500),
    ("California", "USA", 36.77, 119.41, "2020-06-14", "2020-06-30", 16, 16000, 1500, 1200, 13300),
    ("Maharashtra", "India", 19.08, 72.88, "2020-07-01", "2020-07-10", 10, 30000, 5000, 10000, 15000),
    ("Delhi", "India", 28.71, 77.10, "2020-07-01", "2020-07-10", 10, 20000, 3000, 8000, 9000),
]


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        login_type = request.POST.get('login_type', 'user')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = getattr(user, 'profile', None)
            if login_type == 'server' and (not profile or not profile.is_server_admin):
                messages.error(request, "You do not have Server Admin access.")
                return render(request, 'forecasting/login.html')
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'forecasting/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        country = request.POST.get('country', '').strip()
        state = request.POST.get('state', '').strip()
        city = request.POST.get('city', '').strip()
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'forecasting/register.html')
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'forecasting/register.html')
        user = User.objects.create_user(
            username=username, password=password, first_name=first_name
        )
        UserProfile.objects.create(
            user=user, mobile=mobile, country=country,
            state=state, city=city, is_server_admin=False
        )
        messages.success(request, "Account created! Please log in.")
        return redirect('login')
    return render(request, 'forecasting/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    profile = getattr(request.user, 'profile', None)
    is_admin = profile and profile.is_server_admin
    stats = CovidDataset.objects.aggregate(
        total_cases=Sum('new_cases'),
        total_deaths=Sum('death_cases'),
        total_recoveries=Sum('recovery_cases'),
    )
    recent_data = CovidDataset.objects.order_by('-uploaded_at')[:10]
    all_users = []
    if is_admin:
        all_users = User.objects.select_related('profile').filter(
            profile__is_server_admin=False
        ).order_by('-date_joined')
    context = {
        'is_admin': is_admin,
        'total_datasets': CovidDataset.objects.count(),
        'total_users': User.objects.filter(profile__is_server_admin=False).count(),
        'total_predictions': PredictionResult.objects.count(),
        'stats': stats,
        'recent_data': recent_data,
        'all_users': all_users,
    }
    return render(request, 'forecasting/dashboard.html', context)


@login_required
def browse_datasets(request):
    query = request.GET.get('q', '')
    datasets = CovidDataset.objects.all()
    if query:
        datasets = datasets.filter(country_or_region__icontains=query)
    return render(request, 'forecasting/datasets.html', {
        'datasets': datasets, 'query': query, 'total': datasets.count()
    })


@login_required
def add_dataset(request):
    if not getattr(request.user, 'profile', None) or not request.user.profile.is_server_admin:
        messages.error(request, "Admin access required.")
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            CovidDataset.objects.create(
                province_or_state=request.POST.get('province_or_state', ''),
                country_or_region=request.POST.get('country_or_region', ''),
                latitude=float(request.POST.get('latitude', 0)),
                longitude=float(request.POST.get('longitude', 0)),
                from_date=request.POST.get('from_date'),
                to_date=request.POST.get('to_date'),
                number_of_days=int(request.POST.get('number_of_days', 0)),
                new_cases=int(request.POST.get('new_cases', 0)),
                death_cases=int(request.POST.get('death_cases', 0)),
                recovery_cases=int(request.POST.get('recovery_cases', 0)),
                ongoing_treatment_cases=int(request.POST.get('ongoing_treatment_cases', 0)),
            )
            messages.success(request, "Record added successfully!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return redirect('browse_datasets')
    return render(request, 'forecasting/add_dataset.html')


@login_required
def load_sample_data(request):
    if not request.user.profile.is_server_admin:
        messages.error(request, "Admin access required.")
        return redirect('dashboard')
    count = 0
    for row in SAMPLE_DATA:
        _, created = CovidDataset.objects.get_or_create(
            province_or_state=row[0],
            country_or_region=row[1],
            from_date=row[4],
            defaults={
                'latitude': row[2], 'longitude': row[3],
                'to_date': row[5], 'number_of_days': row[6],
                'new_cases': row[7], 'death_cases': row[8],
                'recovery_cases': row[9], 'ongoing_treatment_cases': row[10],
            }
        )
        if created:
            count += 1
    messages.success(request, f"Loaded {count} sample records!")
    return redirect('browse_datasets')


@login_required
def prediction_view(request):
    countries = CovidDataset.objects.values_list(
        'country_or_region', flat=True
    ).distinct().order_by('country_or_region')
    results = None
    selected_country = None
    target_label = None
    forecast_dates = []
    best_model = None
    TARGET_MAP = {
        'new_cases': 'New Confirmed Cases',
        'death_cases': 'Death Cases',
        'recovery_cases': 'Recovery Cases',
    }
    if request.method == 'POST':
        selected_country = request.POST.get('country', '')
        target_col = request.POST.get('target', 'new_cases')
        target_label = TARGET_MAP.get(target_col, 'New Cases')
        qs = CovidDataset.objects.filter(
            country_or_region__icontains=selected_country
        ).order_by('from_date')
        if qs.count() < 5:
            messages.warning(request, "Not enough data for this country.")
        else:
            results = run_all_models(qs, target_col=target_col, forecast_days=10)
            best_model = get_best_model(results)
            last_entry = qs.last()
            start_date = last_entry.to_date if last_entry else date.today()
            forecast_dates = [
                (start_date + timedelta(days=i + 1)).strftime('%b %d')
                for i in range(10)
            ]
            if best_model and results.get(best_model):
                best = results[best_model]
                PredictionResult.objects.filter(
                    country=selected_country, model_name=best_model
                ).delete()
                for i, val in enumerate(best['forecast']):
                    PredictionResult.objects.create(
                        model_name=best_model,
                        prediction_type=target_col,
                        country=selected_country,
                        prediction_date=start_date + timedelta(days=i + 1),
                        predicted_value=val,
                        r2_score=best['metrics']['r2'],
                        mse=best['metrics']['mse'],
                        mae=best['metrics']['mae'],
                        rmse=best['metrics']['rmse'],
                    )
    context = {
        'countries': countries,
        'results': results,
        'selected_country': selected_country,
        'target_label': target_label,
        'forecast_dates_json': json.dumps(forecast_dates),
        'results_json': json.dumps(
            {k: v['forecast'] for k, v in results.items()} if results else {}
        ),
        'best_model': best_model,
        'target_map': TARGET_MAP,
    }
    return render(request, 'forecasting/prediction.html', context)


@login_required
def view_predictions(request):
    prediction_type = request.GET.get('type', 'new_cases')
    predictions = PredictionResult.objects.filter(
        prediction_type=prediction_type
    ).order_by('-created_at')[:50]
    return render(request, 'forecasting/predictions_list.html', {
        'predictions': predictions, 'prediction_type': prediction_type
    })


@login_required
def extract_predictions_csv(request, prediction_type):
    predictions = PredictionResult.objects.filter(
        prediction_type=prediction_type
    ).order_by('prediction_date')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="covid19_{prediction_type}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Model', 'Country', 'Date', 'Predicted Value', 'R2', 'MSE', 'MAE', 'RMSE'])
    for p in predictions:
        writer.writerow([
            p.get_model_name_display(), p.country, p.prediction_date,
            p.predicted_value, p.r2_score, p.mse, p.mae, p.rmse
        ])
    return response


@login_required
def charts_view(request):
    data = CovidDataset.objects.values('country_or_region').annotate(
        total_deaths=Sum('death_cases'),
        total_new=Sum('new_cases'),
        total_recovery=Sum('recovery_cases'),
    ).order_by('-total_deaths')[:15]
    labels = [d['country_or_region'] for d in data]
    deaths = [d['total_deaths'] or 0 for d in data]
    new_cases = [d['total_new'] or 0 for d in data]
    recoveries = [d['total_recovery'] or 0 for d in data]
    return render(request, 'forecasting/charts.html', {
        'labels_json': json.dumps(labels),
        'deaths_json': json.dumps(deaths),
        'new_cases_json': json.dumps(new_cases),
        'recoveries_json': json.dumps(recoveries),
    })


@login_required
def profile_view(request):
    profile = getattr(request.user, 'profile', None)
    return render(request, 'forecasting/profile.html', {'profile': profile})
@login_required
def fetch_live_data(request):
    """Fetch live COVID-19 data from disease.sh API"""
    if not request.user.profile.is_server_admin:
        messages.error(request, "Admin access required.")
        return redirect('dashboard')
    try:
        response = requests.get(
            'https://disease.sh/v3/covid-19/countries?sort=cases',
            timeout=10
        )
        data = response.json()
        count = 0
        for country in data[:20]:
            from datetime import date
            CovidDataset.objects.get_or_create(
                province_or_state=country.get('country', ''),
                country_or_region=country.get('country', ''),
                from_date='2024-01-01',
                defaults={
                    'latitude': country.get('countryInfo', {}).get('lat', 0),
                    'longitude': country.get('countryInfo', {}).get('long', 0),
                    'to_date': str(date.today()),
                    'number_of_days': 365,
                    'new_cases': country.get('todayCases', 0),
                    'death_cases': country.get('todayDeaths', 0),
                    'recovery_cases': country.get('recovered', 0),
                    'ongoing_treatment_cases': country.get('active', 0),
                }
            )
            count += 1
        messages.success(request, f"Loaded live data for {count} countries!")
    except Exception as e:
        messages.error(request, f"Could not fetch live data: {str(e)}")
    return redirect('browse_datasets')