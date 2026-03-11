from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# If you are NOT using a custom user model, import it from django.contrib.auth.models
from .models import User 


admin.site.register(User, UserAdmin)

# ... (keep your other admin.site.register(Loan), etc. down here) ..