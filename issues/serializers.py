from rest_framework import serializers
from .models import Issue, IssueReport
from users.serializers import UserSerializer
from departments.serializers import (
    DepartmentSerializer,
    DepartmentHeadSerializer,
    DepartmentWorkerSerializer
)
from geo.serializers import WardLiteSerializer, MunicipalCorpLiteSerializer


class IssueReportCreateSerializer(serializers.Serializer):
    image = serializers.ImageField()
    description = serializers.CharField(required=False, allow_blank=True)

    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)

    ward_id = serializers.IntegerField()
    municipal_corp_id = serializers.IntegerField()

class IssueReportSerializer(serializers.ModelSerializer):
    citizen = UserSerializer(read_only=True)

    class Meta:
        model = IssueReport
        fields = [
            "id",
            "citizen",
            "description",
            "image_url",

            # AI results (filled asynchronously)
            "match_score",
            "is_mismatch",
            "is_duplicate",

            "created_at",
        ]

class IssueSerializer(serializers.ModelSerializer):
    ward = WardLiteSerializer(read_only=True)
    municipal_corp = MunicipalCorpLiteSerializer(read_only=True)

    dept = DepartmentSerializer(read_only=True)
    dept_head = DepartmentHeadSerializer(read_only=True)

    workers = DepartmentWorkerSerializer(many=True, read_only=True)
    reports = IssueReportSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id",

            "ward",
            "municipal_corp",

            "dept",
            "dept_head",
            "workers",

            "latitude",
            "longitude",

            "severity",
            "status",

            "after_image_url",
            "resolved_at",

            "reports",

            "created_at",
            "updated_at",
        ]

class MyIssueReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueReport
        fields = [
            "id",
            "description",
            "image_url",
            "match_score",
            "is_mismatch",
            "is_duplicate",
            "created_at",
        ]
        # no citizen field — it's always the logged in user

class MyIssueSerializer(serializers.ModelSerializer):
    ward = WardLiteSerializer(read_only=True)
    municipal_corp = MunicipalCorpLiteSerializer(read_only=True)
    dept = DepartmentSerializer(read_only=True)
    # dept_head = DepartmentHeadSerializer(read_only=True)        
    # workers = DepartmentWorkerSerializer(many=True, read_only=True)
    my_report = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id",
            "ward",
            "municipal_corp",
            "dept",
            # "dept_head",
            # "workers",
            # "latitude",
            # "longitude",
            "severity",
            "status",
            "after_image_url",
            "resolved_at",
            "my_report",
            # "created_at",
            # "updated_at",
        ]

    def get_my_report(self, obj):
        user = self.context["request"].user
        report = obj.reports.filter(citizen=user).first()
        return MyIssueReportSerializer(report).data if report else None
    
class NearbyIssueSerializer(serializers.ModelSerializer):
    dept = DepartmentSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    report_count = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id",
            "latitude",
            "longitude",
            "severity",
            "status",
            "dept",
            "primary_image",   # image to show in map popup
            "report_count",    # how many citizens reported this
            "created_at",
        ]

    def get_primary_image(self, obj):
        report = obj.reports.filter(is_duplicate=False).first()
        return report.image_url if report else None

    def get_report_count(self, obj):
        return obj.reports.count()