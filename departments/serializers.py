from rest_framework import serializers
from .models import Department, DepartmentHead, DepartmentWorker
from issues.models import Issue
from users.serializers import UserSerializer
from geo.serializers import MunicipalCorpLiteSerializer, WardLiteSerializer, WardSerializer, MunicipalCorporationSerializer

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

class DeptHeadIssueSerializer(serializers.ModelSerializer):
    ward = WardLiteSerializer(read_only=True)
    municipal_corp = MunicipalCorpLiteSerializer(read_only=True)
    dept = DepartmentSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    report_count = serializers.IntegerField(read_only=True)  # from annotate

    class Meta:
        model = Issue
        fields = [
            "id",
            "ward",
            "municipal_corp",
            "dept",
            "latitude",
            "longitude",
            "severity",
            "status",
            "primary_image",
            "report_count",
            "after_image_url",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def get_primary_image(self, obj):
        report = obj.reports.filter(is_duplicate=False).first()
        return report.image_url if report else None
    
class DepartmentWorkerAssignSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = DepartmentWorker
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "available",
        ]

class WorkerIssueSerializer(serializers.ModelSerializer):
    ward = WardLiteSerializer(read_only=True)
    municipal_corp = MunicipalCorpLiteSerializer(read_only=True)
    dept = DepartmentSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    report_count = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id",
            "ward",
            "municipal_corp",
            "dept",
            "latitude",
            "longitude",
            "severity",
            "status",
            "primary_image",
            "report_count",
            "after_image_url",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def get_primary_image(self, obj):
        report = obj.reports.filter(is_duplicate=False).first()
        return report.image_url if report else None

    def get_report_count(self, obj):
        return obj.reports.count()