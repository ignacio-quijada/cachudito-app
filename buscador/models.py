from django.db import models

class EspecieProtegida(models.Model):
    CATEGORIAS_RCE = [
        ('CR', 'En Peligro Crítico'),
        ('EN', 'En Peligro'),
        ('VU', 'Vulnerable'),
        ('NT', 'Casi Amenazada'),
        ('LC', 'Preocupación Menor'),
        ('MN', 'Monumento Natural'),
    ]

    ORIGEN_ESPECIE = [
        ('E', 'Endémica'),
        ('N', 'Nativa'),
        ('I', 'Introducida')
    ]

    nombre_cientifico = models.CharField(max_length=200, unique=True, db_index=True)
    nombre_comun = models.CharField(max_length=200, blank=True, null=True)
    categoria = models.CharField(max_length=2, choices=CATEGORIAS_RCE, default='LC')
    origen = models.CharField(max_length=1, choices=ORIGEN_ESPECIE, default='N')
    decreto = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: DS 13/1995 MINAGRI")

    class Meta:
        verbose_name = 'Especie Protegida'
        verbose_name_plural = 'Especies Protegidas'

    def __str__(self):
        return f"{self.nombre_cientifico}({self.get_categoria_display()})"

    @property
    def alerta_colecta(self):
        if self.categoria in ['CR', 'EN', 'MN']:
            return 'ROJA'
        elif self.categoria in ['VU', 'NT']:
            return 'AMARILLA'
        else:
            return 'VERDE'