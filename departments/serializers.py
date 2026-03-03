from rest_framework import serializers
from .models import Department, DepartmentHead, DepartmentWorker
from users.serializers import UserSerializer
from geo.serializers import WardSerializer, MunicipalCorporationSerializer

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]
    
class DepartmentHeadSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    dept = DepartmentSerializer()
    ward = WardSerializer()
    municipal_corp = MunicipalCorporationSerializer()

    class Meta:
        model = DepartmentHead
        fields = [
            "id", "user", "dept", "ward", "municipal_corp"
        ]

class DepartmentWorkerSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    dept_head = DepartmentHeadSerializer()

    class Meta:
        model = DepartmentWorker
        fields = ["id", "user", "dept_head", "available"]