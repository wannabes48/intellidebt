from django import forms
from .models import Client, Loan, Payment

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['client_id', 'name', 'age', 'gender', 'phone_number', 'address', 'email', 'employment_type', 'monthly_income', 'num_dependents']
        widgets = {
            'client_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., BRW_1001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], attrs={'class': 'form-select'}),
            'employment_type': forms.Select(choices=[('Salaried', 'Salaried'), ('Self-Employed', 'Self-Employed'), ('Business', 'Business')], attrs={'class': 'form-select'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control'}),
            'num_dependents': forms.NumberInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        # Notice: 'due_date' has been removed, and we include the new ML fields
        fields = ['loan_id', 'client', 'amount', 'tenure', 'interest_rate', 'loan_type', 'collateral_value']
        widgets = {
            'loan_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., LN_1001'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'tenure': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Months (e.g., 12, 24)'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'loan_type': forms.Select(choices=[('Personal', 'Personal'), ('Home', 'Home'), ('Auto', 'Auto'), ('Business', 'Business')], attrs={'class': 'form-select'}),
            'collateral_value': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount_paid', 'reference_number']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }