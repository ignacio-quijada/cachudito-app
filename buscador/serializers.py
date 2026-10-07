from rest_framework import serializers
from .models import EspecieProtegida

class EspecieProtegidaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='get_categoria_display', read_only=True)
    origen_nombre = serializers.CharField(source='get_origen_display', read_only=True)
    semaforo = serializers.ReadOnlyField(source='alerta_colecta')

    class Meta:
        model = EspecieProtegida
        fields = [
            'id',
            'nombre_cientifico',
            'nombre_comun',
            'categoria',
            'categoria_nombre',
            'origen',
            'origen_nombre',
            'decreto',
            'semaforo',
        ]