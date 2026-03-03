# geo/services/location_resolver.py
import json
from django.db import connection
from django.core.cache import cache


def normalize_coordinates(lat: float, lng: float, precision: int = 4):
    return round(lat, precision), round(lng, precision)


def resolve_ward_from_location(lat: float, lng: float):
    """
    Returns ward + municipal corporation for given GPS location
    """

    lat_n, lng_n = normalize_coordinates(lat, lng)
    cache_key = f"geo:ward:{lat_n}:{lng_n}"

    # 1️⃣ Try Redis first
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 2️⃣ Fallback to PostGIS
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                w.id   AS ward_id,
                w.name AS ward_name,
                mc.id  AS corp_id,
                mc.name AS corp_name
            FROM ward w
            JOIN municipal_corporation mc
              ON mc.id = w.municipal_corp_id
            WHERE ST_Contains(
                w.geometry,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            LIMIT 1;
            """,
            [lng, lat]
        )

        row = cursor.fetchone()

    if not row:
        return None

    result = {
        "ward_id": row[0],
        "ward_name": row[1],
        "municipal_corp_id": row[2],
        "municipal_corp_name": row[3],
    }

    # 3️⃣ Cache result (24 hours)
    cache.set(cache_key, result, timeout=60 * 60 * 24)

    return result




# from django.db import connection

# def resolve_ward_from_location(lat: float, lng: float):
#     """
#     Returns ward + municipal corporation for given GPS location
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT
#                 w.id   AS ward_id,
#                 w.name AS ward_name,
#                 mc.id  AS corp_id,
#                 mc.name AS corp_name
#             FROM ward w
#             JOIN municipal_corporation mc
#               ON mc.id = w.municipal_corp_id
#             WHERE ST_Contains(
#                 w.geometry,
#                 ST_SetSRID(ST_MakePoint(%s, %s), 4326)
#             )
#             LIMIT 1;
#             """,
#             [lng, lat]
#         )

#         row = cursor.fetchone()

#     if not row:
#         return None

#     return {
#         "ward_id": row[0],
#         "ward_name": row[1],
#         "municipal_corp_id": row[2],
#         "municipal_corp_name": row[3],
#     }

