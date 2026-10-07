import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from buscador.models import EspecieProtegida

especies_iniciales = [
   # 🔴 ALERTA ROJA (CR, EN, MN - Prohibida su colecta/corta)
    {
        'nombre_cientifico': 'Gomortega keule',
        'nombre_comun': 'Queule',
        'categoria': 'MN',
        'origen': 'E',
        'decreto': 'DS 13/1995 MINAGRI (Monumento Natural) / DS 151/2007 (En Peligro)'
    },
    {
        'nombre_cientifico': 'Araucaria araucana',
        'nombre_comun': 'Araucaria / Pehuén',
        'categoria': 'MN',
        'origen': 'N',
        'decreto': 'DS 43/1990 MINAGRI (Monumento Natural) / EN en Cordillera de Nahuelbuta'
    },
    {
        'nombre_cientifico': 'Pitavia punctata',
        'nombre_comun': 'Pitao',
        'categoria': 'MN',
        'origen': 'E',
        'decreto': 'DS 13/1995 MINAGRI (Monumento Natural) / DS 151/2007 (En Peligro)'
    },
    {
        'nombre_cientifico': 'Berberidopsis corallina',
        'nombre_comun': 'Michay rojo / Voqui fuco',
        'categoria': 'EN',
        'origen': 'E',
        'decreto': 'DS 151/2007 MINSEGPRES (1° Proceso RCE - En Peligro)'
    },
    {
        'nombre_cientifico': 'Nothofagus alessandrii',
        'nombre_comun': 'Ruil',
        'categoria': 'MN',
        'origen': 'E',
        'decreto': 'DS 13/1995 MINAGRI (Monumento Natural) / DS 151/2007 (En Peligro)'
    },

    # 🟡 ALERTA AMARILLA (VU, NT - Colecta restringida / Precaución)
    {
        'nombre_cientifico': 'Beilschmiedia berteroana',
        'nombre_comun': 'Belloto del sur',
        'categoria': 'MN',
        'origen': 'E',
        'decreto': 'DS 13/1995 MINAGRI (Monumento Natural) / En Peligro'
    },
    {
        'nombre_cientifico': 'Lapageria rosea',
        'nombre_comun': 'Copihue',
        'categoria': 'VU',
        'origen': 'E',
        'decreto': 'DS 129/1971 MINAGRI (Prohíbe arranque y comercialización de plantas/flores)'
    },
    {
        'nombre_cientifico': 'Puya chilensis',
        'nombre_comun': 'Chagual / Cardón',
        'categoria': 'LC',
        'origen': 'E',
        'decreto': 'DS 42/2011 MMA (Preocupación Menor,NT en zonas específicas)'
    },
    {
        'nombre_cientifico': 'Austrocedrus chilensis',
        'nombre_comun': 'Ciprés de la cordillera',
        'categoria': 'NT',
        'origen': 'N',
        'decreto': 'DS 42/2011 MMA (Casi Amenazada)'
    },

    # 🟢 ALERTA VERDE (LC o Introducidas - Herborización permitida fuera de SNASPE)
    {
        'nombre_cientifico': 'Luma apiculata',
        'nombre_comun': 'Arrayán / Palo colorado',
        'categoria': 'LC',
        'origen': 'N',
        'decreto': 'Preocupación Menor (LC). Colecta ética permitida fuera de áreas protegidas.'
    },
    {
        'nombre_cientifico': 'Ugni molinae',
        'nombre_comun': 'Murta / Murtilla',
        'categoria': 'LC',
        'origen': 'N',
        'decreto': 'Preocupación Menor (LC). Colecta permitida fuera de parques nacionales.'
    },
    {
        'nombre_cientifico': 'Nolana paradoxa',
        'nombre_comun': 'Suspiro de mar',
        'categoria': 'LC',
        'origen': 'E',
        'decreto': 'Endémica costera abundante (LC). Permitido herborizar con criterio.'
    },
    {
        'nombre_cientifico': 'Ulex europaeus',
        'nombre_comun': 'Espinillo / Chacay',
        'categoria': 'LC',
        'origen': 'I',
        'decreto': 'Especie exótica invasora. Extracción y herborización totalmente libre.'
    },
]

creadas = 0
for datos in especies_iniciales:
    obj, created = EspecieProtegida.objects.update_or_create(
        nombre_cientifico=datos['nombre_cientifico'],
        defaults=datos
    )
    if created:
        creadas += 1

print(f"✅ Base de datos legal lista: {creadas} especies nuevas cargadas ({EspecieProtegida.objects.count()} en total).")