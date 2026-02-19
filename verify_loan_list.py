
import os
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import Loan, Client as ClientModel, User

def verify_loan_list():
    print("--- Verifying Loan List Syntax ---")
    
    # DEBUG: Check file content
    try:
        with open('core/templates/loan_list.html', 'r', encoding='utf-8') as f:
            content = f.read()
            print("--- FILE CONTENT START ---")
            print(content[:1000]) # Print first 1000 chars
            print("--- FILE CONTENT END ---")
            if "status_filter=='Active'" in content:
                print("DETECTED ERROR IN FILE CONTENT: status_filter=='Active' found!")
            else:
                print("File content looks correct (no status_filter=='Active').")
    except Exception as e:
        print(f"Could not read file: {e}")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='test_admin')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()
        
    client, _ = ClientModel.objects.get_or_create(
        client_id="TEST_002",
        defaults={'name': "List Test Client", 'monthly_income': 5000, 'phone_number': '1234567890'}
    )
    if not client.phone_number:
         client.phone_number = '1234567890'
         client.save()
    
    # 2. Access View
    c = Client()
    c.force_login(user)
    
    url = reverse('loan_list')
    print(f"Accessing {url}...")
    
    try:
        response = c.get(url, HTTP_HOST='127.0.0.1')
    except Exception as e:
        print(f"\nFAILED: Exception encountered: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
    
    if response.status_code != 200:
        print(f"FAILED: Status Code {response.status_code}")
        # Print content if error to verify standard django error page content if needed
        # print(response.content.decode('utf-8')[:500])
        import sys
        sys.exit(1)

    print("\nSUCCESS: Loan List loaded without Syntax Error!")

if __name__ == "__main__":
    verify_loan_list()
