from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geo.models import WardHead, MunicipalCorpHead
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import json

from users.permissions import RolePermission


from .serializers import LocationResolveSerializer
from .services.location_resolver import resolve_ward_from_location

# Create your views here.

class ResolveLocationView(APIView):

    permission_classes = []

    def post(self, request):
        serializer = LocationResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data["latitude"]
        lng = serializer.validated_data["longitude"]

        result = resolve_ward_from_location(lat, lng)

        if not result:
            return Response(
                {
                    "error": "Location not inside supported wards"
                },
                status = status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            {
                "ward": {
                    "id": result["ward_id"],
                    "name": result["ward_name"]
                } if result["ward_id"] else None,
                "municipal_corporation": {
                    "id": result["municipal_corp_id"],
                    "name": result["municipal_corp_name"]
                },
                "resolved_by": result["resolved_by"]
            },
            status=status.HTTP_200_OK
        )
    
class WardBoundaryView(APIView):
    """
    Returns GeoJSON boundary for the logged-in ward head's ward.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        try:
            ward_head = WardHead.objects.select_related("ward").get(
                user=request.user
            )
        except WardHead.DoesNotExist:
            return Response(
                {"error": "Ward head profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        ward = ward_head.ward

        # ST_AsGeoJSON converts PostGIS geometry to GeoJSON string
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ST_AsGeoJSON(geometry)
                FROM ward
                WHERE id = %s
                """,
                [ward.id]
            )
            row = cursor.fetchone()

        if not row or not row[0]:
            return Response(
                {"error": "No boundary data available for this ward"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "ward_id": ward.id,
            "ward_name": ward.name,
            "type": "Feature",
            "geometry": json.loads(row[0]),
            "properties": {
                "id": ward.id,
                "name": ward.name,
            }
        })


class CorpBoundaryView(APIView):
    """
    Returns GeoJSON boundary for the logged-in corp head's
    municipal corporation — and optionally all ward boundaries within it.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        try:
            corp_head = MunicipalCorpHead.objects.select_related(
                "municipal_corp"
            ).get(user=request.user)
        except MunicipalCorpHead.DoesNotExist:
            return Response(
                {"error": "Municipal corp head profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        corp = corp_head.municipal_corp

        # include_wards=true returns all ward boundaries too
        # useful for rendering a ward-level map inside the corp boundary
        include_wards = request.query_params.get("include_wards", "false").lower() == "true"

        with connection.cursor() as cursor:
            # Corp boundary
            cursor.execute(
                """
                SELECT ST_AsGeoJSON(geometry)
                FROM municipal_corporation
                WHERE id = %s
                """,
                [corp.id]
            )
            corp_row = cursor.fetchone()

            ward_features = []
            if include_wards:
                cursor.execute(
                    """
                    SELECT id, name, ST_AsGeoJSON(geometry)
                    FROM ward
                    WHERE municipal_corp_id = %s
                      AND geometry IS NOT NULL
                    ORDER BY name
                    """,
                    [corp.id]
                )
                ward_rows = cursor.fetchall()
                ward_features = [
                    {
                        "type": "Feature",
                        "geometry": json.loads(row[2]),
                        "properties": {
                            "id": row[0],
                            "name": row[1],
                        }
                    }
                    for row in ward_rows
                    if row[2]  # skip wards with no geometry
                ]

        if not corp_row or not corp_row[0]:
            return Response(
                {"error": "No boundary data available for this corporation"},
                status=status.HTTP_404_NOT_FOUND
            )

        response = {
            "municipal_corp_id": corp.id,
            "municipal_corp_name": corp.name,
            "type": "Feature",
            "geometry": json.loads(corp_row[0]),
            "properties": {
                "id": corp.id,
                "name": corp.name,
            }
        }

        if include_wards:
            response["wards"] = {
                "type": "FeatureCollection",
                "features": ward_features,
                "total": len(ward_features)
            }

        return Response(response)