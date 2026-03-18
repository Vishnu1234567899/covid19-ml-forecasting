import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Lasso
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from statsmodels.tsa.holtwinters import SimpleExpSmoothing


def prepare_data(queryset, target_col):
    records = list(queryset.values(
        'from_date', 'new_cases', 'death_cases', 'recovery_cases'
    ).order_by('from_date'))
    if len(records) < 5:
        return None, None, None
    df = pd.DataFrame(records)
    df['day_index'] = range(len(df))
    X = df[['day_index']].values
    y = df[target_col].values.astype(float)
    return X, y, df


def split_data(X, y, test_ratio=0.15):
    split = int(len(X) * (1 - test_ratio))
    return X[:split], X[split:], y[:split], y[split:]


def compute_metrics(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    n = len(y_true)
    p = 1
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else r2
    return {
        'r2': round(float(r2), 4),
        'adj_r2': round(float(adj_r2), 4),
        'mse': round(float(mse), 4),
        'mae': round(float(mae), 4),
        'rmse': round(float(rmse), 4),
    }


def forecast_next_n_days(model, last_day_index, n=10, scaler=None):
    future_indices = np.array([[last_day_index + i + 1] for i in range(n)])
    if scaler:
        future_indices = scaler.transform(future_indices)
    preds = model.predict(future_indices)
    return [max(0, round(float(v), 2)) for v in preds]


def run_linear_regression(queryset, target_col='new_cases', forecast_days=10):
    X, y, df = prepare_data(queryset, target_col)
    if X is None:
        return None
    X_train, X_test, y_train, y_test = split_data(X, y)
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred)
    forecast = forecast_next_n_days(model, len(X) - 1)
    return {
        'model': 'LR', 'model_name': 'Linear Regression',
        'target': target_col, 'metrics': metrics,
        'forecast': forecast, 'train_size': len(X_train), 'test_size': len(X_test),
    }


def run_lasso(queryset, target_col='new_cases', forecast_days=10):
    X, y, df = prepare_data(queryset, target_col)
    if X is None:
        return None
    X_train, X_test, y_train, y_test = split_data(X, y)
    model = Lasso(alpha=0.1, max_iter=10000)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred)
    forecast = forecast_next_n_days(model, len(X) - 1)
    return {
        'model': 'LASSO', 'model_name': 'LASSO Regression',
        'target': target_col, 'metrics': metrics,
        'forecast': forecast, 'train_size': len(X_train), 'test_size': len(X_test),
    }


def run_svm(queryset, target_col='new_cases', forecast_days=10):
    X, y, df = prepare_data(queryset, target_col)
    if X is None:
        return None
    X_train, X_test, y_train, y_test = split_data(X, y)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    model = SVR(kernel='rbf', C=100, gamma=0.1, epsilon=0.1)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    metrics = compute_metrics(y_test, y_pred)
    forecast = forecast_next_n_days(model, len(X) - 1, scaler=scaler)
    return {
        'model': 'SVM', 'model_name': 'Support Vector Machine',
        'target': target_col, 'metrics': metrics,
        'forecast': forecast, 'train_size': len(X_train), 'test_size': len(X_test),
    }


def run_exponential_smoothing(queryset, target_col='new_cases', forecast_days=10):
    X, y, df = prepare_data(queryset, target_col)
    if X is None:
        return None
    _, _, y_train, y_test = split_data(X, y)
    y_train_safe = np.clip(y_train, 1, None)
    model = SimpleExpSmoothing(y_train_safe).fit(optimized=True)
    y_pred = model.fittedvalues[-len(y_test):] if len(y_test) > 0 else []
    if len(y_pred) > 0 and len(y_test) > 0:
        metrics = compute_metrics(y_test[:len(y_pred)], y_pred)
    else:
        metrics = {'r2': 0, 'adj_r2': 0, 'mse': 0, 'mae': 0, 'rmse': 0}
    forecast_raw = model.forecast(forecast_days)
    forecast = [max(0, round(float(v), 2)) for v in forecast_raw]
    return {
        'model': 'ES', 'model_name': 'Exponential Smoothing',
        'target': target_col, 'metrics': metrics,
        'forecast': forecast, 'train_size': len(y_train), 'test_size': len(y_test),
    }


def run_all_models(queryset, target_col='new_cases', forecast_days=10):
    results = {}
    lr = run_linear_regression(queryset, target_col, forecast_days)
    if lr:
        results['LR'] = lr
    lasso = run_lasso(queryset, target_col, forecast_days)
    if lasso:
        results['LASSO'] = lasso
    svm = run_svm(queryset, target_col, forecast_days)
    if svm:
        results['SVM'] = svm
    es = run_exponential_smoothing(queryset, target_col, forecast_days)
    if es:
        results['ES'] = es
    return results


def get_best_model(results):
    if not results:
        return None
    best = max(results.values(), key=lambda r: r['metrics'].get('r2', -999))
    return best['model']