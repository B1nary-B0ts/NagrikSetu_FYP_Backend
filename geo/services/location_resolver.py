# geo/services/location_resolver.py
import json
from django.db import connection
from django.core.cache import cache


def normalize_coordinates(lat: float, lng: float, precision: int = 4):
    return round(lat, precision), round(lng, precision)

def resolve_ward_from_location(lat: float, lng: float):
    """
    Returns ward + municipal corporation for given GPS location.
    Falls back to municipal corporation only if ward data is unavailable.
    """

    lat_n, lng_n = normalize_coordinates(lat, lng)
    cache_key = f"geo:ward:{lat_n}:{lng_n}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    with connection.cursor() as cursor:

        # 1️⃣ Try ward first (works for BMC etc. where ward data exists)
        cursor.execute(
            """
            SELECT
                w.id    AS ward_id,
                w.name  AS ward_name,
                mc.id   AS corp_id,
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

        if row:
            result = {
                "ward_id": row[0],
                "ward_name": row[1],
                "municipal_corp_id": row[2],
                "municipal_corp_name": row[3],
                "resolved_by": "ward",       # helpful for debugging
            }
        else:
            # 2️⃣ Fallback — try matching just the municipal corporation boundary
            # (handles NMMC, and any corp without ward-level data)
            cursor.execute(
                """
                SELECT
                    mc.id   AS corp_id,
                    mc.name AS corp_name
                FROM municipal_corporation mc
                WHERE ST_Contains(
                    mc.geometry,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                LIMIT 1;
                """,
                [lng, lat]
            )
            corp_row = cursor.fetchone()

            if not corp_row:
                return None  # point is outside all known boundaries

            result = {
                "ward_id": None,             # explicitly None, not missing
                "ward_name": None,
                "municipal_corp_id": corp_row[0],
                "municipal_corp_name": corp_row[1],
                "resolved_by": "municipal_corp",
            }

    cache.set(cache_key, result, timeout=60 * 60 * 24)
    return result

# def resolve_ward_from_location(lat: float, lng: float):
#     """
#     Returns ward + municipal corporation for given GPS location
#     """

#     lat_n, lng_n = normalize_coordinates(lat, lng)
#     cache_key = f"geo:ward:{lat_n}:{lng_n}"

#     # 1️⃣ Try Redis first
#     cached = cache.get(cache_key)
#     if cached:
#         return cached

#     # 2️⃣ Fallback to PostGIS
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

#     result = {
#         "ward_id": row[0],
#         "ward_name": row[1],
#         "municipal_corp_id": row[2],
#         "municipal_corp_name": row[3],
#     }

#     # 3️⃣ Cache result (24 hours)
#     cache.set(cache_key, result, timeout=60 * 60 * 24)

#     return result





