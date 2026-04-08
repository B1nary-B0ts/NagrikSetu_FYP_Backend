# from ..models import User

# user = User.objects.create_user(
#     username="bhushan.gagrani@bmc.gov.in",
#     email="bhushan.gagrani@bmc.gov.in",
#     password="bhushan.gagrani@bmc.gov.in",
#     name="Bhushan Gagrani",
#     role="municipal_corp_head",
#     is_staff=True,
#     is_active=True
# )




import os
import sys
import django

# Add project root (Backend) to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from users.models import User
from geo.models import Ward, WardHead

ward_ids = [20, 457]

users_data = [
    #{"email": "ke.ward@bmc.gov.in", "name": "K/E Ward Head"},
    {"email": "fn.ward@bmc.gov.in", "name": "F/N Ward Head", "phone": "9000000022"},
    {"email": "ward76@bmc.gov.in", "name": "Ward 76 Head", "phone": "9000000032"},
]

for i in range(2):
    ward = Ward.objects.get(id=ward_ids[i])

    user = User.objects.create_user(
        username=users_data[i]["email"],
        email=users_data[i]["email"],
        password="password123",
        name=users_data[i]["name"],
        phone=users_data[i]["phone"],
        role="ward_head",
        is_staff=True,
        is_active=True
    )

    WardHead.objects.create(ward=ward, user=user)

    print(f"✅ Created {users_data[i]['name']}")