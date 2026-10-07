import math
from datetime import datetime
import requests
from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import EspecieProtegida
from .serializers import EspecieProtegidaSerializer

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    radio_tierra = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radio_tierra * c, 1)


def obtener_nombre_lugar_preciso(lat, lon, nombre_gbif=""):
    """
    Consulta a OpenStreetMap con zoom=17 (nivel sendero/parque/cerro)
    para obtener el nombre exacto del lugar en vez de solo la comuna.
    """
    try:
        url_rev = "https://nominatim.openstreetmap.org/reverse"
        headers_osm = {'User-Agent': 'CachuditoAppChile/1.0 (ignacio@cachudito.cl)'}
        resp = requests.get(
            url_rev,
            params={
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 17,  # <-- CLAVE: Zoom 17 lee parques, cerros, reservas y senderos
                'addressdetails': 1
            },
            headers=headers_osm,
            timeout=4
        )
        if resp.status_code == 200:
            datos = resp.json()
            addr = datos.get('address', {})

            # 1. Buscamos primero si cae dentro de un Parque, Reserva, Cerro o Campus
            hito_natural = (
                datos.get('name')
                or addr.get('nature_reserve')
                or addr.get('national_park')
                or addr.get('park')
                or addr.get('leisure')
                or addr.get('peak')
                or addr.get('beach')
                or addr.get('tourism')
                or addr.get('amenity')
            )

            # 2. Buscamos el barrio, sector rural o calle/sendero
            sector_barrio = (
                addr.get('suburb')
                or addr.get('neighbourhood')
                or addr.get('quarter')
                or addr.get('village')
                or addr.get('hamlet')
                or addr.get('road')
            )

            # 3. Buscamos la comuna
            comuna = (
                addr.get('city')
                or addr.get('town')
                or addr.get('municipality')
                or addr.get('county')
                or ""
            )

            # Armamos un nombre compuesto súper descriptivo (Ej: "Cerro Caracol • Pedro de Valdivia, Concepción")
            partes = []
            if hito_natural and hito_natural.lower() != comuna.lower():
                partes.append(hito_natural)
            if sector_barrio and sector_barrio.lower() != comuna.lower() and sector_barrio not in partes:
                partes.append(sector_barrio)

            if partes and comuna:
                return f"{' • '.join(partes[:2])}, {comuna}"
            elif partes:
                return " • ".join(partes[:2])
            elif datos.get('display_name'):
                # Si es zona silvestre sin calle, tomamos los primeros 2 fragmentos de OpenStreetMap
                fragmentos = [f.strip() for f in datos['display_name'].split(',')]
                return ", ".join(fragmentos[:2])

    except requests.RequestException:
        pass

    return nombre_gbif or f"Sector GPS ({lat}, {lon})"


def ejecutar_analisis_terreno(consulta_especie, nombre_ciudad):
    mes_actual = datetime.now().month

    # --- A. GEOCODIFICACIÓN DE COMUNAS Y CIUDADES CHILENAS (OpenStreetMap Chile) ---
    lat_ciudad, lon_ciudad = -36.82, -73.05  # Respaldo por defecto
    ciudad_oficial = f"{nombre_ciudad} (Ubicación aproximada)"
    try:
        url_geo = "https://nominatim.openstreetmap.org/search"
        headers_osm = {'User-Agent': 'CachuditoAppChile/1.0 (contacto@cachudito.cl)'}
        resp_geo = requests.get(
            url_geo,
            params={'q': f"{nombre_ciudad}, Chile", 'countrycodes': 'cl', 'format': 'json', 'limit': 1},
            headers=headers_osm,
            timeout=5
        )
        datos_geo = resp_geo.json()
        if datos_geo:
            lat_ciudad = round(float(datos_geo[0]['lat']), 4)
            lon_ciudad = round(float(datos_geo[0]['lon']), 4)
            partes_nombre = datos_geo[0]['display_name'].split(', ')
            ciudad_oficial = ", ".join(partes_nombre[:2])
    except (requests.RequestException, ValueError, KeyError):
        pass

    # --- B. CRUCE CON BASE DE DATOS LEGAL CHILENA + TRADUCTOR DE NOMBRES COMUNES ---
    especie_local = EspecieProtegida.objects.filter(
        Q(nombre_cientifico__icontains=consulta_especie) |
        Q(nombre_comun__icontains=consulta_especie)
    ).first()

    nombre_para_gbif = especie_local.nombre_cientifico if especie_local else consulta_especie
    nombre_comun_detectado = especie_local.nombre_comun if especie_local else consulta_especie.capitalize()

    # Si NO está en nuestra base SQL, le preguntamos a iNaturalist Chile para traducir nombres comunes (ej: "Boldo", "Peumo", "Loica")
    if not especie_local:
        try:
            resp_inat = requests.get(
                "https://api.inaturalist.org/v1/taxa",
                params={'q': consulta_especie, 'locale': 'es-CL', 'per_page': 1},
                timeout=4
            )
            resultados_inat = resp_inat.json().get('results', [])
            if resultados_inat:
                nombre_para_gbif = resultados_inat[0].get('name', nombre_para_gbif)
                nombre_comun_detectado = resultados_inat[0].get('preferred_common_name', nombre_comun_detectado).capitalize()
        except requests.RequestException:
            pass

    taxon_key = None
    nombre_cientifico_oficial = nombre_para_gbif
    familia_gbif = "No especificada"

    try:
        resp_match = requests.get(
            "https://api.gbif.org/v1/species/match",
            params={'name': nombre_para_gbif},
            timeout=5
        )
        datos_match = resp_match.json()
        if datos_match.get('matchType') != 'NONE':
            taxon_key = datos_match.get('usageKey')
            nombre_cientifico_oficial = datos_match.get('canonicalName') or datos_match.get('scientificName')
            familia_gbif = datos_match.get('family', 'No especificada')
    except requests.RequestException:
        pass

    if not especie_local and nombre_cientifico_oficial:
        especie_local = EspecieProtegida.objects.filter(
            nombre_cientifico__iexact=nombre_cientifico_oficial
        ).first()

    if especie_local:
        info_legal = {
            'registrada_en_rce': True,
            'nombre_cientifico': especie_local.nombre_cientifico,
            'nombre_comun': especie_local.nombre_comun,
            'familia': familia_gbif,
            'categoria_codigo': especie_local.categoria,
            'categoria_nombre': especie_local.get_categoria_display(),
            'origen': especie_local.get_origen_display(),
            'decreto': especie_local.decreto,
            'semaforo': especie_local.alerta_colecta,
        }
    else:
        info_legal = {
            'registrada_en_rce': False,
            'nombre_cientifico': nombre_cientifico_oficial,
            'nombre_comun': nombre_comun_detectado,
            'familia': familia_gbif,
            'categoria_codigo': 'NE',
            'categoria_nombre': 'No Evaluada / Sin restricción RCE en base local',
            'origen': 'Por confirmar',
            'decreto': 'Sin prohibición específica en nómina local. Colecta ética permitida fuera de SNASPE.',
            'semaforo': 'VERDE',
        }

    # --- C. BÚSQUEDA DE OCURRENCIAS CERCANAS EN GBIF Y CLUSTERING DE ZONAS ---
    zonas_calientes = []
    if taxon_key:
        # Reducimos caja de búsqueda a ~45-50 km (+/- 0.45 grados) para terreno local
        min_lat, max_lat = round(lat_ciudad - 0.45, 3), round(lat_ciudad + 0.45, 3)
        min_lon, max_lon = round(lon_ciudad - 0.45, 3), round(lon_ciudad + 0.45, 3)

        try:
            resp_occ = requests.get(
                "https://api.gbif.org/v1/occurrence/search",
                params={
                    'taxonKey': taxon_key,
                    'country': 'CL',
                    'decimalLatitude': f"{min_lat},{max_lat}",
                    'decimalLongitude': f"{min_lon},{max_lon}",
                    'hasCoordinate': 'true',
                    'limit': 200,
                },
                timeout=6
            )
            registros = resp_occ.json().get('results', [])

            # Cuadrícula fina de ~1.1 km (2 decimales: 0.01 grados)
            grupos = {}
            for reg in registros:
                lat_pto = reg.get('decimalLatitude')
                lon_pto = reg.get('decimalLongitude')
                if lat_pto is None or lon_pto is None:
                    continue

                clave_celda = (round(lat_pto, 2), round(lon_pto, 2))
                if clave_celda not in grupos:
                    grupos[clave_celda] = {
                        'total': 0,
                        'suma_lat': 0.0,
                        'suma_lon': 0.0,
                        'en_este_mes': 0,
                        'recientes': 0,
                        'localidades': [],
                    }

                grupos[clave_celda]['total'] += 1
                grupos[clave_celda]['suma_lat'] += lat_pto
                grupos[clave_celda]['suma_lon'] += lon_pto

                if reg.get('month') == mes_actual:
                    grupos[clave_celda]['en_este_mes'] += 1
                if (reg.get('year') or 0) >= 2018:
                    grupos[clave_celda]['recientes'] += 1

                # Priorizamos localidad específica antes que provincia/región
                loc = reg.get('locality') or reg.get('verbatimLocality')
                if loc and len(loc) > 12 and loc not in grupos[clave_celda]['localidades']:
                    grupos[clave_celda]['localidades'].append(loc)

            for _, datos_z in grupos.items():
                # Calculamos el centroide real (promedio exacto de las coordenadas del grupo)
                lat_real = round(datos_z['suma_lat'] / datos_z['total'], 4)
                lon_real = round(datos_z['suma_lon'] / datos_z['total'], 4)

                dist_km = calcular_distancia_km(lat_ciudad, lon_ciudad, lat_real, lon_real)

                puntaje_densidad = min(35, datos_z['total'] * 4)
                puntaje_estacional = min(12, datos_z['en_este_mes'] * 4)
                puntaje_reciente = min(8, datos_z['recientes'] * 2)
                probabilidad = min(96, 42 + puntaje_densidad + puntaje_estacional + puntaje_reciente)

                nombre_sector = (
                    datos_z['localidades'][0]
                    if datos_z['localidades']
                    else f"Sector GPS ({lat_real}, {lon_real})"
                )

                zonas_calientes.append({
                    'sector': nombre_sector,
                    'latitud': lat_real,
                    'longitud': lon_real,
                    'distancia_km': dist_km,
                    'total_registros': datos_z['total'],
                    'registros_mes_actual': datos_z['en_este_mes'],
                    'probabilidad_exito': probabilidad,
                })

            # Ordenamos por probabilidad, pero si empatan gana el más cercano a tu comuna
            zonas_calientes.sort(key=lambda z: (-z['probabilidad_exito'], z['distancia_km']))

            # Evitamos que dos círculos caigan pegados en el mismo cerro (mínimo 1.8 km de separación entre zonas)
            zonas_separadas = []
            for candidata in zonas_calientes:
                muy_cerca = any(
                    calcular_distancia_km(
                        candidata['latitud'], candidata['longitud'],
                        elegida['latitud'], elegida['longitud']
                    ) < 1.8
                    for elegida in zonas_separadas
                )
                if not muy_cerca:
                    zonas_separadas.append(candidata)
                if len(zonas_separadas) == 5:
                    break

            zonas_calientes = zonas_separadas
        except requests.RequestException:
            pass

    # --- D. CLIMA EN VIVO PARA LAS ZONAS TOP (Open-Meteo API) ---
    for zona in zonas_calientes:
        # 1. Traducimos coordenada a nombre de Parque, Caleta, Cerro o Barrio real
        zona['sector'] = obtener_nombre_lugar_preciso(
            zona['latitud'],
            zona['longitud'],
            zona['sector']
        )

        # 2. Clima actual en esa coordenada (Open-Meteo API)
        zona['clima'] = {'temperatura_c': '--', 'humedad': '--'}
        try:
            resp_clima = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': zona['latitud'],
                    'longitude': zona['longitud'],
                    'current': 'temperature_2m,relative_humidity_2m',
                },
                timeout=3
            )
            if resp_clima.status_code == 200:
                actual = resp_clima.json().get('current', {})
                zona['clima'] = {
                    'temperatura_c': actual.get('temperature_2m', '--'),
                    'humedad': actual.get('relative_humidity_2m', '--'),
                }
        except requests.RequestException:
            pass

    return {
        'ciudad_origen': {
            'nombre': ciudad_oficial,
            'latitud': lat_ciudad,
            'longitud': lon_ciudad,
        },
        'dictamen_legal': info_legal,
        'zonas_recomendadas': zonas_calientes,
    }

# 3. Vista de la Página Web (Renderiza el Template con Tailwind y Leaflet)
def pagina_buscador(request):
    especie_q = request.GET.get('especie', 'Luma apiculata').strip()
    ciudad_q = request.GET.get('ciudad', 'Concepción').strip()

    resultado = ejecutar_analisis_terreno(especie_q, ciudad_q)

    contexto = {
        'especie_buscada': especie_q,
        'ciudad_buscada': ciudad_q,
        'resultado': resultado,
    }
    return render(request, 'buscador/index.html', contexto)


# 4. Vistas de la API REST (Django REST Framework)
class EspecieProtegidaViewSet(viewsets.ModelViewSet):
    queryset = EspecieProtegida.objects.all().order_by('nombre_cientifico')
    serializer_class = EspecieProtegidaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['categoria', 'origen']
    search_fields = ['nombre_cientifico', 'nombre_comun']


@api_view(['GET'])
def api_analizar_terreno(request):
    """Endpoint JSON: /api/analizar/?especie=Queule&ciudad=Concepcion"""
    especie_q = request.query_params.get('especie', 'Gomortega keule')
    ciudad_q = request.query_params.get('ciudad', 'Concepción')
    datos = ejecutar_analisis_terreno(especie_q, ciudad_q)
    return Response(datos)