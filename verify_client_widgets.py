
import os
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import User

def verify_client_widgets():
    print("--- Verifying Client Form Widgets ---")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='test_admin')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()
        
    # 2. Access View
    c = Client()
    c.force_login(user)
    
    url = reverse('create_client')
    print(f"Accessing {url}...")
    
    response = c.get(url, HTTP_HOST='127.0.0.1')
    
    if response.status_code != 200:
        print(f"FAILED: Status Code {response.status_code}")
        return

    content = response.content.decode('utf-8')
    
    # 3. Verify Address Widget
    # We expect <input ... name="address" ...> NOT <textarea ... name="address" ...>
    # The default TextInput widget renders as <input type="text" ...>
    
    if '<input' in content and 'name="address"' in content:
        # Check if they are part of the same tag. Use regex or simple string search if contiguous.
        # Django rendering usually: <input type="text" name="address" ...>
        # Let's check for 'name="address"' and ensure it's inside an input tag context or check for absence of textarea with that name
        
        if '<textarea' in content and 'name="address"' in content:
             # Check if 'name="address"' follows '<textarea'
             # Splitting by name="address"
             parts = content.split('name="address"')
             # Check the part before. 
             last_tag_start = parts[0].rfind('<')
             tag_start = parts[0][last_tag_start:]
             
             if 'textarea' in tag_start:
                 print("  [FAIL] Address field is still a TEXTAREA.")
                 import sys
                 sys.exit(1)
        
        print("  [OK] Address field is NOT a textarea (likely input).")
        
        if 'type="email"' in content and 'name="email"' in content:
            print("  [OK] Email field found as email input.")
            
        print("\nSUCCESS: Client Widgets Verified.")
        
    else:
        print("  [FAIL] Address input field not found.")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    try:
        verify_client_widgets()
    except Exception:
        import traceback
        import sys
        traceback.print_exc()
        sys.exit(1)
