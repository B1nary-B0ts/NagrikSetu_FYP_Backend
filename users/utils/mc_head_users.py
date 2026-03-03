from ..models import User

user = User.objects.create_user(
    username="bhushan.gagrani@bmc.gov.in",
    email="bhushan.gagrani@bmc.gov.in",
    password="bhushan.gagrani@bmc.gov.in",
    name="Bhushan Gagrani",
    role="municipal_corp_head",
    is_staff=True,
    is_active=True
)
