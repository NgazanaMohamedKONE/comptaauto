from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Entreprise
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email','username','role','is_active')
    list_filter = ('role',)
    fieldsets = UserAdmin.fieldsets + (('Infos',{'fields':('role','telephone')}),)
@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom','secteur','formule','statut','date_inscription')
    list_filter = ('formule','statut')
