from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active_student', 'is_staff')
    list_filter = ('role', 'is_active_student', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    fieldsets = UserAdmin.fieldsets + (
        ('COURSE profile', {'fields': ('role', 'phone', 'phone_verified', 'country', 'city', 'is_active_student', 'must_change_password')}),
    )
