# import os
# import django

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()

# from users.models import User
# from departments.models import Department, DepartmentHead, DepartmentWorker
# from geo.models import Ward, MunicipalCorporation

# # ============================================================
# # CONFIG
# # ============================================================
# MUNICIPAL_CORP_ID = 1
# WARD_IDS = [4, 20]  # K/E Ward, F/N Ward
# PASSWORD = "Admin@1234"

# municipal_corp = MunicipalCorporation.objects.get(id=MUNICIPAL_CORP_ID)
# wards = Ward.objects.filter(id__in=WARD_IDS)

# print(f"Municipal Corp: {municipal_corp.name}")
# for w in wards:
#     print(f"Ward: {w.name} (id={w.id})")

# # ============================================================
# # DATA TEMPLATE — will be created for EACH ward
# # ============================================================
# # {ward_short} will be replaced with 'ke' or 'fn'
# dept_head_templates = [
#     {"name": "Rajesh Kumar",  "email": "head.publicworks.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Public Works"},
#     {"name": "Priya Sharma",  "email": "head.health.{ward_short}@mmc.gov.in",       "phone": "900000{n}", "dept_keyword": "Health"},
#     {"name": "Amit Patil",    "email": "head.solidwaste.{ward_short}@mmc.gov.in",   "phone": "900000{n}", "dept_keyword": "Solid Waste"},
#     {"name": "Sunita Desai",  "email": "head.water.{ward_short}@mmc.gov.in",        "phone": "900000{n}", "dept_keyword": "Water Supply"},
# ]

# dept_worker_templates = [
#     # Public Works
#     {"name": "Suresh Jadhav",   "email": "worker.pw1.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Public Works"},
#     {"name": "Mahesh Rane",     "email": "worker.pw2.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Public Works"},
#     {"name": "Ganesh More",     "email": "worker.pw3.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Public Works"},
#     # Health
#     {"name": "Kavita Nair",     "email": "worker.h1.{ward_short}@mmc.gov.in",   "phone": "900000{n}", "dept_keyword": "Health"},
#     {"name": "Ramesh Joshi",    "email": "worker.h2.{ward_short}@mmc.gov.in",   "phone": "900000{n}", "dept_keyword": "Health"},
#     {"name": "Seema Kulkarni",  "email": "worker.h3.{ward_short}@mmc.gov.in",   "phone": "900000{n}", "dept_keyword": "Health"},
#     # Solid Waste
#     {"name": "Vijay Shinde",    "email": "worker.sw1.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Solid Waste"},
#     {"name": "Ajay Pawar",      "email": "worker.sw2.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Solid Waste"},
#     {"name": "Nitin Sawant",    "email": "worker.sw3.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Solid Waste"},
#     # Water Supply
#     {"name": "Deepak Mane",     "email": "worker.ws1.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Water Supply"},
#     {"name": "Sachin Bhosale",  "email": "worker.ws2.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Water Supply"},
#     {"name": "Rahul Gaikwad",   "email": "worker.ws3.{ward_short}@mmc.gov.in",  "phone": "900000{n}", "dept_keyword": "Water Supply"},
# ]

# # ============================================================
# # PHONE NUMBER COUNTER — unique across all entries
# # ============================================================
# phone_counter = [9000100001]  # using list so it can be mutated in helper

# def next_phone():
#     phone = str(phone_counter[0])
#     phone_counter[0] += 1
#     return phone

# # ward id → short name for email/username
# ward_short_map = {
#     4:  "ke",
#     20: "fn",
# }

# # ============================================================
# # CREATE FOR EACH WARD
# # ============================================================
# for ward in wards:
#     ward_short = ward_short_map[ward.id]
#     print(f"\n{'='*50}")
#     print(f"Processing Ward: {ward.name} ({ward_short})")
#     print(f"{'='*50}")

#     created_heads = {}  # dept.name → DepartmentHead

#     # --- Department Heads ---
#     print("\n--- Creating Department Heads ---")
#     for template in dept_head_templates:
#         email = template["email"].replace("{ward_short}", ward_short)
#         phone = next_phone()

#         dept = Department.objects.filter(
#             name__icontains=template["dept_keyword"]
#         ).first()

#         if not dept:
#             print(f"  ❌ Department not found for keyword: {template['dept_keyword']}")
#             continue

#         user, created = User.objects.get_or_create(
#             email=email,
#             defaults={
#                 "name": f"{template['name']} ({ward.name})",
#                 "phone": phone,
#                 "role": "dept_head",
#                 "username": email,
#             }
#         )
#         if created:
#             user.set_password(PASSWORD)
#             user.save()
#             print(f"  ✅ Created user: {user.name}")
#         else:
#             print(f"  ⚠️  Already exists: {user.name}")

#         dept_head, _ = DepartmentHead.objects.get_or_create(
#             user=user,
#             defaults={
#                 "dept": dept,
#                 "ward": ward,
#                 "municipal_corp": municipal_corp,
#             }
#         )
#         created_heads[dept.name] = dept_head
#         print(f"  ✅ DeptHead: {user.name} → {dept.name} → {ward.name}")

#     # --- Department Workers ---
#     print("\n--- Creating Department Workers ---")
#     for template in dept_worker_templates:
#         email = template["email"].replace("{ward_short}", ward_short)
#         phone = next_phone()

#         dept = Department.objects.filter(
#             name__icontains=template["dept_keyword"]
#         ).first()

#         if not dept:
#             print(f"  ❌ Department not found for keyword: {template['dept_keyword']}")
#             continue

#         dept_head = created_heads.get(dept.name)
#         if not dept_head:
#             print(f"  ❌ No dept head found for: {dept.name}")
#             continue

#         user, created = User.objects.get_or_create(
#             email=email,
#             defaults={
#                 "name": f"{template['name']} ({ward.name})",
#                 "phone": phone,
#                 "role": "dept_worker",
#                 "username": email,
#             }
#         )
#         if created:
#             user.set_password(PASSWORD)
#             user.save()
#             print(f"  ✅ Created user: {user.name}")
#         else:
#             print(f"  ⚠️  Already exists: {user.name}")

#         DepartmentWorker.objects.get_or_create(
#             user=user,
#             defaults={
#                 "dept_head": dept_head,
#                 "available": True,
#             }
#         )
#         print(f"  ✅ DeptWorker: {user.name} → {dept.name} → {ward.name}")

# print("\n✅ All done!")
# print(f"Total dept heads created: 8 (4 depts × 2 wards)")
# print(f"Total workers created: 24 (3 workers × 4 depts × 2 wards)")
# print(f"Password for all: {PASSWORD}")


import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# ── Debug — confirm which DB you're actually connecting to ──
from django.db import connection, transaction
print("\n── DB Connection Details ──")
print(f"Host     : {connection.settings_dict['HOST']}")
print(f"Database : {connection.settings_dict['NAME']}")
print(f"User     : {connection.settings_dict['USER']}")
print(f"Port     : {connection.settings_dict['PORT']}")
print("───────────────────────────\n")

from users.models import User
from departments.models import Department, DepartmentHead, DepartmentWorker
from geo.models import Ward, MunicipalCorporation

print(f"Users in DB before seeding: {User.objects.count()}")

# ============================================================
# CONFIG
# ============================================================
MUNICIPAL_CORP_ID = 7
WARD_IDS = [457]
PASSWORD = "Admin@1234"

municipal_corp = MunicipalCorporation.objects.get(id=MUNICIPAL_CORP_ID)
wards = Ward.objects.filter(id__in=WARD_IDS)

print(f"Municipal Corp: {municipal_corp.name}")
for w in wards:
    print(f"Ward: {w.name} (id={w.id})")

if not wards.exists():
    print("❌ No wards found for given WARD_IDS. Exiting.")
    sys.exit(1)

# ============================================================
# DATA TEMPLATE
# ============================================================
dept_head_templates = [
    {"name": "Rajesh Kumar",  "email": "head.publicworks.{ward_short}@nmmc.gov.in",  "dept_keyword": "Public Works"},
    {"name": "Priya Sharma",  "email": "head.health.{ward_short}@nmmc.gov.in",       "dept_keyword": "Health"},
    {"name": "Amit Patil",    "email": "head.solidwaste.{ward_short}@nmmc.gov.in",   "dept_keyword": "Solid Waste"},
    {"name": "Sunita Desai",  "email": "head.water.{ward_short}@nmmc.gov.in",        "dept_keyword": "Water Supply"},
]

dept_worker_templates = [
    # Public Works
    {"name": "Suresh Jadhav",   "email": "worker.pw1.{ward_short}@nmmc.gov.in",  "dept_keyword": "Public Works"},
    {"name": "Mahesh Rane",     "email": "worker.pw2.{ward_short}@nmmc.gov.in",  "dept_keyword": "Public Works"},
    {"name": "Ganesh More",     "email": "worker.pw3.{ward_short}@nmmc.gov.in",  "dept_keyword": "Public Works"},
    # Health
    {"name": "Kavita Nair",     "email": "worker.h1.{ward_short}@nmmc.gov.in",   "dept_keyword": "Health"},
    {"name": "Ramesh Joshi",    "email": "worker.h2.{ward_short}@nmmc.gov.in",   "dept_keyword": "Health"},
    {"name": "Seema Kulkarni",  "email": "worker.h3.{ward_short}@nmmc.gov.in",   "dept_keyword": "Health"},
    # Solid Waste
    {"name": "Vijay Shinde",    "email": "worker.sw1.{ward_short}@nmmc.gov.in",  "dept_keyword": "Solid Waste"},
    {"name": "Ajay Pawar",      "email": "worker.sw2.{ward_short}@nmmc.gov.in",  "dept_keyword": "Solid Waste"},
    {"name": "Nitin Sawant",    "email": "worker.sw3.{ward_short}@nmmc.gov.in",  "dept_keyword": "Solid Waste"},
    # Water Supply
    {"name": "Deepak Mane",     "email": "worker.ws1.{ward_short}@nmmc.gov.in",  "dept_keyword": "Water Supply"},
    {"name": "Sachin Bhosale",  "email": "worker.ws2.{ward_short}@nmmc.gov.in",  "dept_keyword": "Water Supply"},
    {"name": "Rahul Gaikwad",   "email": "worker.ws3.{ward_short}@nmmc.gov.in",  "dept_keyword": "Water Supply"},
]

# ============================================================
# PHONE NUMBER COUNTER
# ============================================================
phone_counter = [9100100001]

def next_phone():
    phone = str(phone_counter[0])
    phone_counter[0] += 1
    return phone

ward_short_map = {
    457: "w76",
}

# ============================================================
# CREATE FOR EACH WARD — wrapped in atomic transaction
# ============================================================
try:
    with transaction.atomic():
        for ward in wards:
            ward_short = ward_short_map[ward.id]
            print(f"\n{'='*50}")
            print(f"Processing Ward: {ward.name} ({ward_short})")
            print(f"{'='*50}")

            created_heads = {}

            # --- Department Heads ---
            print("\n--- Creating Department Heads ---")
            for template in dept_head_templates:
                email = template["email"].replace("{ward_short}", ward_short)
                phone = next_phone()

                dept = Department.objects.filter(
                    name__icontains=template["dept_keyword"]
                ).first()

                if not dept:
                    print(f"  ❌ Department not found for keyword: {template['dept_keyword']}")
                    continue

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "name": f"{template['name']} ({ward.name})",
                        "phone": phone,
                        "role": "dept_head",
                        "username": email,
                    }
                )
                if created:
                    user.set_password(PASSWORD)
                    user.save()
                    print(f"  ✅ Created user: {user.name} | email: {user.email} | phone: {user.phone}")
                else:
                    print(f"  ⚠️  Already exists: {user.name}")

                dept_head, _ = DepartmentHead.objects.get_or_create(
                    user=user,
                    defaults={
                        "dept": dept,
                        "ward": ward,
                        "municipal_corp": municipal_corp,
                    }
                )
                created_heads[dept.name] = dept_head
                print(f"  ✅ DeptHead: {user.name} → {dept.name} → {ward.name}")

            # --- Department Workers ---
            print("\n--- Creating Department Workers ---")
            for template in dept_worker_templates:
                email = template["email"].replace("{ward_short}", ward_short)
                phone = next_phone()

                dept = Department.objects.filter(
                    name__icontains=template["dept_keyword"]
                ).first()

                if not dept:
                    print(f"  ❌ Department not found for keyword: {template['dept_keyword']}")
                    continue

                dept_head = created_heads.get(dept.name)
                if not dept_head:
                    print(f"  ❌ No dept head found for: {dept.name}")
                    continue

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "name": f"{template['name']} ({ward.name})",
                        "phone": phone,
                        "role": "dept_worker",
                        "username": email,
                    }
                )
                if created:
                    user.set_password(PASSWORD)
                    user.save()
                    print(f"  ✅ Created user: {user.name} | email: {user.email} | phone: {user.phone}")
                else:
                    print(f"  ⚠️  Already exists: {user.name}")

                DepartmentWorker.objects.get_or_create(
                    user=user,
                    defaults={
                        "dept_head": dept_head,
                        "available": True,
                    }
                )
                print(f"  ✅ DeptWorker: {user.name} → {dept.name} → {ward.name}")

        print(f"\nUsers in DB after seeding: {User.objects.count()}")
        print("\n✅ All done!")
        print(f"Total dept heads: 4 (4 depts × 1 ward)")
        print(f"Total workers: 12 (3 workers × 4 depts × 1 ward)")
        print(f"Password for all: {PASSWORD}")

except Exception as e:
    print(f"\n❌ ERROR — transaction rolled back")
    print(f"Exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()