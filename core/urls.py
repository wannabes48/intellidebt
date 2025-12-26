from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('loans/', views.loan_list, name='loan_list'),
    path('settings/', views.settings_view, name='settings'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('create-loan/', views.create_loan, name='create_loan'),
    path('create-client/', views.create_client, name='create_client'),
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('run-reminders/', views.trigger_reminders, name='trigger_reminders'),
    path('loan/<int:loan_id>/pay/', views.add_payment, name='add_payment'),
    path('loan/<int:loan_id>/settlement/', views.generate_settlement, name='generate_settlement'),
]