import os
import django
import random

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import Client

def generate_data():
    streets = ["Moi Avenue", "Kenyatta Avenue", "Waiyaki Way", "Ngong Road", "Thika Road", "Langata Road", "Tom Mboya St", "Jogoo Road"]
    cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika"]
    
    clients = Client.objects.all()
    count = 0
    
    print("Generating random contacts for all clients...")
    
    for client in clients:
        # Generate a fake Kenyan phone number (e.g., 0712345678)
        phone = f"07{random.randint(10000000, 99999999)}"
        
        # Generate a fake address (e.g., 45 Ngong Road, Nairobi)
        address = f"{random.randint(1, 500)} {random.choice(streets)}, {random.choice(cities)}"

        # Generate a fake email address (e.g., brw_1001@example.com)
        email = f"{client.client_id.lower()}@gmail.com"
        
        client.phone_number = phone
        client.address = address
        client.email = email
        client.save()
        
        count += 1
        
    print(f"✅ Successfully added contacts to {count} clients!")

if __name__ == '__main__':
    generate_data()