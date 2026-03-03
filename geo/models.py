from django.db import models
from users.models import User

class MunicipalCorporation(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    geometry = None #models.TextField(null=True, blank=True)  # only WKT

    class Meta:
        managed = False
        db_table = "municipal_corporation"

    def __str__(self):
        return self.name


class Ward(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    municipal_corp = models.ForeignKey(
        MunicipalCorporation,
        on_delete=models.CASCADE,
        related_name="wards",
        db_column="municipal_corp_id",
    )
    geometry = None #models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "ward"

    def __str__(self):
        return f"{self.name} ({self.municipal_corp.name})"


class MunicipalCorpHead(models.Model):
    id = models.AutoField(primary_key=True)
    municipal_corp = models.OneToOneField(
        MunicipalCorporation,
        on_delete=models.CASCADE,
        db_column="municipal_corp_id",
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    class Meta:
        managed = False #set true
        db_table = "municipal_corp_head"


class WardHead(models.Model):
    id = models.AutoField(primary_key=True)
    ward = models.OneToOneField(
        Ward,
        on_delete=models.CASCADE,
        db_column="ward_id",
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    class Meta:
        managed = False #set true
        db_table = "ward_head"



# from django.db import models
# from django.contrib.gis.db import models as gis_models
# from users.models import User
# # Create your models here.

# class MunicipalCorporation(models.Model):
#     name = models.CharField(max_length=100)
#     geometry = gis_models.GeometryField(null=True, blank=True, srid=4326)
#     head = models.OneToOneField(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name="municipal_corp_head"
#     )

#     def __str__(self):
#         return self.name
    
# class Ward(models.Model):
#     name = models.CharField(max_length=100)
#     municipal_corp = models.ForeignKey(
#         MunicipalCorporation, on_delete=models.CASCADE,
#         related_name="wards"
#     )
#     geometry = gis_models.GeometryField(null=True, blank=True, srid=4326) 

#     def __str__(self):
#         return f"{self.name} ({self.municipal_corp.name})"