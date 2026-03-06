from django.db import models
from users.models import User
from geo.models import Ward
from geo.models import MunicipalCorporation
from departments.models import Department,DepartmentHead,DepartmentWorker
# Create your models here.
class Issue(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True)
    municipal_corp = models.ForeignKey(MunicipalCorporation, on_delete=models.CASCADE)

    dept = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    dept_head = models.ForeignKey(
        DepartmentHead, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    workers = models.ManyToManyField(
        DepartmentWorker, blank=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    severity = models.CharField(
        max_length=20,
        choices=[
            ("LOW", "LOW"),
            ("MEDIUM", "MEDIUM"),
            ("HIGH", "HIGH"),
            ("CRITICAL", "CRITICAL"),
        ],
        null=True, blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=[
            ("PROCESSING", "PROCESSING"),
            ("NEEDS_CONFIRMATION", "NEEDS_CONFIRMATION"),
            ("ASSIGNED", "ASSIGNED"),
            ("IN_PROGRESS", "IN_PROGRESS"),
            ("RESOLVED", "RESOLVED"),
            ("CLOSED", "CLOSED"),
        ],
        default="PROCESSING"
    )
    after_image_url = models.TextField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Issue #{self.id} - {self.status}"
    

class IssueReport(models.Model):
    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE,
        related_name="reports",
        null=True, blank=True
    )

    citizen = models.ForeignKey(
        User, on_delete=models.CASCADE
    )

    description = models.TextField(null=True, blank=True)

    image_url = models.TextField()
    local_image_path = models.TextField(null=True, blank=True)

    match_score = models.FloatField(null=True, blank=True)
    is_mismatch = models.BooleanField(default=False)

    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        Issue, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="duplicates"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IssueReport #{self.id} for Issue #{self.issue.id}"

# class Issue(models.Model):
#     citizen = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="issues"
#     )
#     dept = models.ForeignKey(
#         Department, on_delete=models.CASCADE, related_name="issues"
#     )
#     dept_head = models.ForeignKey(
#         DepartmentHead, on_delete=models.SET_NULL,
#         null=True, blank=True, related_name="issues"
#     )
#     ward = models.ForeignKey(
#         Ward, on_delete=models.SET_NULL,
#         null=True, blank=True, related_name="issues"
#     )
#     municipal_corp = models.ForeignKey(
#         MunicipalCorporation, on_delete=models.CASCADE,
#         related_name="issues"
#     )
#     workers = models.ManyToManyField(
#         DepartmentWorker,
#         related_name="assigned_issues",
#         blank=True
#     )

#     # title = models.CharField(max_length=255, blank=True, null=True)
#     description = models.TextField(max_length=255, blank=True, null=True)
#     image_url = models.TextField(blank=True, null=True)
#     after_image_url = models.TextField(blank=True, null=True)

#     latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
#     longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

#     severity = models.CharField(max_length=20, blank=True, null=True)
#     status = models.CharField(max_length=20, default='issued')

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Issue #{self.id} - {self.status}"
