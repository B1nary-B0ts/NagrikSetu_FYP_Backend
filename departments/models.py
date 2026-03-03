from django.db import models
from users.models import User
from geo.models import Ward
from geo.models import MunicipalCorporation
# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class DepartmentHead(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="dept_head_profile"
    )
    dept = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="heads"
    )
    ward = models.ForeignKey(
        Ward, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name="dept_heads"
    )
    municipal_corp = models.ForeignKey(
        MunicipalCorporation, on_delete=models.CASCADE,
        related_name="dept_heads"
    )

    def __str__(self):
        location = self.ward.name if self.ward else self.municipal_corp.name
        return f"{self.user.name} - {self.dept.name} ({location})"
    
class DepartmentWorker(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="dept_worker_profile"
    )
    dept_head = models.ForeignKey(
        DepartmentHead, on_delete=models.CASCADE, related_name="workers"
    )
    available = models.BooleanField(default=True)