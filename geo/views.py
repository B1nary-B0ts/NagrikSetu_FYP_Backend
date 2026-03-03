from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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
                },
                "municipal_corporation": {
                    "id": result["municipal_corp_id"],
                    "name": result["municipal_corp_name"]
                }
            },
            status = status.HTTP_200_OK
        )