from django.contrib import admin
from .models import EspecieProtegida

@admin.register(EspecieProtegida)
class EspecieProtegidaAdmin(admin.ModelAdmin):
    list_display = ('nombre_cientifico', 'nombre_comun','categoria', 'origen')
    search_fields = ('nombre_cientifico', 'nombre_comun')
    list_filter = ('categoria', 'origen')