#!/usr/bin/env python3
"""
Mock data generator — DelightOn Garments Ltd. (BIBA Sem 3, NCI)
================================================================
Fresh, 100% original synthetic dataset (new seed, new values) for a
school-uniform garment manufacturer in severe operational and financial
distress. Produces 24 CSV tables covering Sales/CRM, Orders & Billing,
Supply Chain & Inventory, Production, and HR & Operations.

KEY DATA-QUALITY RULES (per project requirements)
  * CURRENCY  - every monetary value is EUR, rounded to 2 dp; financial
                tables carry an explicit `currency` = 'EUR' column.
  * TAX       - NO GST columns anywhere. Irish VAT is used and CALCULATED:
                  - children's clothing (Primary / Gaelscoil orders): 0%
                  - adult-size clothing (Secondary / College orders): 23%
                  - fabric & trims (B2B supply): 23%
                Invoices carry net_total, vat_rate, vat_amount, grand_total
                with the identity  grand_total = net_total + vat_amount.
  * INTEGRITY - all FKs resolve; grand_total = advance + payments + balance;
                lot remaining <= initial; no effect precedes its cause.

EMBEDDED BUSINESS-DISTRESS SIGNALS (for dashboards)
  * Lead conversion DROPS year-on-year   (~28% AY2025 -> ~16% AY2026)
  * Late deliveries WORSEN year-on-year  (~40% AY2025 -> ~60% AY2026)
  * Supply-chain bottleneck: ~40% of fabric POs arrive late (two vendors
    are chronic offenders); late fabric correlates with late orders
  * Cutting wastage 9-15% vs a 5% plan; ~17% of purchased fabric idle
  * ~5% of delivered garments returned; receivables ageing

Usage:  python3 generate_mock_data.py [output_dir]
Seed fixed (4321) => fully reproducible.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 4321
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IE")
Faker.seed(SEED)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("delighton_data")
OUT.mkdir(parents=True, exist_ok=True)
NOW = datetime(2026, 7, 22, 9, 0, 0)

VAT_STANDARD = 23.0          # adult clothing, fabric, trims
VAT_CHILD = 0.0              # children's clothing (Irish zero rate)
CHILD_INSTITUTIONS = {"Primary School", "Gaelscoil"}


# ---------------------------------------------------------------- helpers
def ts(d):
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else ""


def rand_dt(start, end):
    return start + timedelta(seconds=random.uniform(0, max((end - start).total_seconds(), 1)))


def eur(x):
    return round(float(x), 2)


def eircode():
    r = random.choice(["D03", "D05", "D07", "D10", "D13", "D16", "D18", "D20", "D22",
                       "A63", "A86", "K32", "K78", "W12", "W91", "R95", "C15", "N91", "Y14", "P31"])
    return f"{r} " + "".join(random.choices("ACDEFHKNPRTVWXY0123456789", k=4))


def mobile():
    return f"+353 8{random.choice('35679')} {random.randint(100, 999)} {random.randint(1000, 9999)}"


def landline():
    return f"+353 {random.choice(['1', '45', '46', '59'])} {random.randint(200, 899)} {random.randint(1000, 9999)}"


def ie_vat_number():
    return f"IE{random.randint(1000000, 9999999)}{random.choice('ABCDEFGHIJ')}"


def save(name, rows):
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"  {name:<24s} {len(df):>6,d} rows")
    return df


def academic_year(d):
    return d.year + 1 if d.month >= 9 else d.year


print(f"Generating DelightOn Garments Ltd. dataset -> {OUT.resolve()}\n")

# ---------------------------------------------------------------- 1. users
USER_DEFS = [
    ("Fiona Keane", "admin"), ("Ronan Hayes", "sales"), ("Grainne Dolan", "sales"),
    ("Tomas Whelan", "sales"), ("Maeve Costello", "operations"), ("Barry Lynam", "production"),
    ("Aisling Corr", "production"), ("Dermot Scully", "accounts"), ("Una Prendergast", "accounts"),
    ("Killian Roche", "warehouse"), ("Sorcha Tierney", "customer_service"), ("Vincent Dowd", "management"),
]
users = [{
    "id": i, "name": nm,
    "email": nm.lower().replace(" ", ".") + "@delighton.ie",
    "role": role, "is_active": True,
    "created_at": ts(datetime(2024, 8, 1) + timedelta(days=i)),
} for i, (nm, role) in enumerate(USER_DEFS, 1)]
save("users", users)
UIDS = list(range(1, 13))
SALES = [2, 3, 4]


def audit(created, uid=None):
    return {"created_by": uid or random.choice(UIDS), "created_at": ts(created),
            "updated_by": random.choice(UIDS),
            "updated_at": ts(created + timedelta(days=random.randint(0, 25)))}


# ---------------------------------------------------------------- 2. lookups
save("lead_sources", [{
    "id": i, "name": n, "description": d, "is_active": True, **audit(datetime(2024, 8, 12))}
    for i, n, d in [
        (1, "School Referral", "Recommended by an existing customer school"),
        (2, "Website Enquiry", "Enquiry form on delighton.ie"),
        (3, "Education Trade Fair", "Leads captured at education expos"),
        (4, "Direct Outreach", "Cold calls / emails by sales team"),
        (5, "Search Ads", "Paid Google search campaigns"),
        (6, "Repeat Customer", "Expansion business from current schools"),
        (7, "Retail Partner", "Partner uniform shops"),
        (8, "Social Media", "Facebook / Instagram / LinkedIn"),
    ]])

save("lead_statuses", [{
    "id": i, "name": n, "description": d, "sort_order": so, "is_active": True,
    "process_stage": st, **audit(datetime(2024, 8, 12))}
    for i, n, d, so, st in [
        (1, "New", "Untouched lead", 1, "lead"),
        (2, "Contacted", "First contact made", 2, "lead"),
        (3, "Follow-up Scheduled", "Awaiting scheduled follow-up", 3, "lead"),
        (4, "Quotation Sent", "Formal quote issued", 4, "lead"),
        (5, "Negotiation", "Terms under discussion", 5, "lead"),
        (6, "Converted", "Won - order created", 6, "both"),
        (7, "Lost", "Lost to competitor / no budget", 7, "lead"),
        (8, "Dormant", "No response after 3 attempts", 8, "lead"),
    ]])

# garment_types: (id, name, gender, category, net EUR price range, metres/pc)
GARMENTS = [
    (1,  "Boys Trousers",         "male",   "bottomwear", (23, 35), 1.30),
    (2,  "Girls Skirt",           "female", "bottomwear", (21, 31), 1.10),
    (3,  "Pinafore",              "female", "dress",      (27, 39), 1.60),
    (4,  "Crested School Jumper", "unisex", "knitwear",   (25, 37), 0.00),
    (5,  "Crested Polo Shirt",    "unisex", "topwear",    (12, 19), 0.90),
    (6,  "School Shirt",          "male",   "topwear",    (11, 17), 1.20),
    (7,  "School Blouse",         "female", "topwear",    (11, 17), 1.15),
    (8,  "School Tie",            "unisex", "accessory",  (6, 11),  0.20),
    (9,  "Crested Blazer",        "unisex", "outerwear",  (58, 88), 1.90),
    (10, "Tracksuit Bottoms",     "unisex", "sportswear", (18, 27), 1.25),
    (11, "Half-Zip PE Top",       "unisex", "sportswear", (23, 33), 1.40),
    (12, "PE Shorts",             "unisex", "sportswear", (10, 16), 0.70),
]
save("garment_types", [{
    "id": i, "name": n, "description": f"{n} - DelightOn standard school specification",
    "is_active": True, "gender": g, "clothing_category": c, **audit(datetime(2024, 8, 18))}
    for i, n, g, c, _, _ in GARMENTS])
G_PRICE = {g[0]: g[4] for g in GARMENTS}
G_FABRIC = {g[0]: g[5] for g in GARMENTS}

VENDOR_NAMES = ["Kildare Weaving Mills Ltd", "Boyne Valley Textiles", "Emerald Cloth Supplies",
                "Lir Knitwear & Cresting", "Quayside Fabric Traders", "Slaney Sports Textiles",
                "Harland Shirting Co. (UK)", "Meath Trimmings & Threads"]
CHRONIC_LATE_VENDORS = {2, 5}   # supply-chain bottleneck offenders

FABRICS = [
    (1, "Poly-Viscose Suiting Charcoal", "65% polyester 35% viscose", 240, 150.0, 6.95, "Charcoal"),
    (2, "Poly-Viscose Suiting Navy", "65% polyester 35% viscose", 240, 150.0, 6.90, "Navy"),
    (3, "Wool-Blend Knit Navy", "50% wool 50% acrylic", 320, 160.0, 11.80, "Navy"),
    (4, "Wool-Blend Knit Wine", "50% wool 50% acrylic", 320, 160.0, 11.80, "Wine"),
    (5, "Pique Cotton White", "100% combed cotton pique", 210, 180.0, 5.55, "White"),
    (6, "Poplin Shirting White", "60% cotton 40% polyester", 115, 150.0, 4.05, "White"),
    (7, "Poplin Shirting Sky", "60% cotton 40% polyester", 115, 150.0, 4.10, "Sky Blue"),
    (8, "Gaberdine Forest Green", "100% polyester gaberdine", 260, 150.0, 5.75, "Forest Green"),
    (9, "Melton Blazer Cloth Navy", "70% wool 30% polyester", 420, 150.0, 17.20, "Navy"),
    (10, "Tricot Sports Knit Navy", "100% polyester tricot", 200, 165.0, 4.45, "Navy"),
    (11, "Tricot Sports Knit Green", "100% polyester tricot", 200, 165.0, 4.50, "Forest Green"),
    (12, "Tartan Kilting Cloth", "63% polyester 34% viscose 3% elastane", 300, 145.0, 9.45, "Green Tartan"),
]
save("fabric_types", [{
    "id": i, "name": n, "composition": comp, "gsm": gsm, "width": w,
    "price_per_meter": p, "currency": "EUR",
    "supplier": random.choice(VENDOR_NAMES), "color": c, "is_active": True}
    for i, n, comp, gsm, w, p, c in FABRICS])
F_PRICE = {f[0]: f[5] for f in FABRICS}

save("production_phases", [{
    "id": i, "name": n, "sequence_order": i, "is_active": True,
    "created_at": ts(datetime(2024, 8, 18))}
    for i, n in enumerate(["Cutting", "Stitching", "Embroidery & Cresting",
                           "Finishing & Pressing", "Quality Check", "Packing"], 1)])
PHASES = list(range(1, 7))

EMP_ROLES = (["Cutter"] * 5 + ["Stitching Operator"] * 14 + ["Embroidery Operator"] * 3 +
             ["Presser / Finisher"] * 4 + ["QC Inspector"] * 3 + ["Packer"] * 3)
employees = []
for i, role in enumerate(EMP_ROLES, 1):
    hired = rand_dt(datetime(2023, 2, 1), datetime(2025, 11, 1))
    active = random.random() > 0.09
    employees.append({"id": i, "name": fake.name(), "role": role, "phone_number": mobile(),
                      "is_active": active, **audit(hired),
                      "deactivated_at": "" if active else ts(rand_dt(datetime(2026, 1, 1), NOW))})
save("employees", employees)
CUTTERS = [e["id"] for e in employees if e["role"] == "Cutter"]
STITCHERS = [e["id"] for e in employees if e["role"] == "Stitching Operator"]
ALL_EMP = [e["id"] for e in employees]

vendors = [{
    "id": i, "name": vn, "contact_person": fake.name(),
    "email": "orders@" + "".join(c for c in vn.lower() if c.isalnum())[:16] + ".ie",
    "phone": landline(),
    "address": f"{fake.street_address()}, {fake.city()}, {eircode()}",
    "vat_number": ie_vat_number(),                       # GST removed -> Irish VAT number
    "payment_terms": random.choice(["30 days net", "45 days net",
                                    "50% advance, balance on delivery", "60 days net"]),
    "is_active": True, "created_at": ts(datetime(2024, 8, 8)),
} for i, vn in enumerate(VENDOR_NAMES, 1)]
save("vendors", vendors)

# ---------------------------------------------------------------- 3. customers
PATTERNS = ["St. {s}'s National School", "St. {s}'s NS", "Scoil {g}", "Gaelscoil {g}",
            "Colaiste {g}", "St. {s}'s Secondary School", "{t} Community College",
            "{t} Educate Together NS", "{t} Community School", "Holy Family Secondary School {t}",
            "De La Salle College {t}", "Ursuline Secondary School {t}", "CBS {t}",
            "St. {s}'s College", "{t} Vocational School"]
SAINTS = ["Senan", "Gobnait", "Malachy", "Laurence", "Dympna", "Fintan", "Ronan",
          "Colman", "Assumpta", "Eunan", "Munchin", "Fergal", "Jarlath", "Bronagh"]
GAELIC = ["Naomh Iosaf", "Realt na Mara", "an Droichid", "Chroi Ro Naofa", "Naithi",
          "na Tra", "Cholmain", "Bhreandain"]
TOWNS = ["Dundalk", "Portmarnock", "Kilcullen", "Enfield", "Sallins", "Edenderry", "Longford",
         "Roscrea", "Carlow", "Baltinglass", "Blessington", "Clane", "Duleek", "Laytown",
         "Stamullen", "Rathangan", "Monasterevin", "Kinnegad", "Moate", "Ferbane", "Birr",
         "Bagenalstown", "Tullow", "Rathdrum", "Kilcoole", "Donabate", "Lusk", "Ratoath",
         "Dunshaughlin", "Oldcastle"]

def pick_institution(nm):
    if any(k in nm for k in ["National", "NS", "Educate Together"]) or nm.startswith("Scoil"):
        return "Primary School"
    if nm.startswith("Gaelscoil"):
        return "Gaelscoil"
    if "College" in nm and random.random() < 0.25:
        return "College / Institute"
    if any(k in nm for k in ["De La Salle", "Ursuline", "Holy Family"]) and random.random() < 0.5:
        return "Fee-paying Secondary"
    return "Secondary School"

names, seen = [], set()
while len(names) < 40:
    nm = random.choice(PATTERNS).format(s=random.choice(SAINTS), g=random.choice(GAELIC),
                                        t=random.choice(TOWNS))
    if nm not in seen:
        seen.add(nm); names.append(nm)

customers = []
for i, nm in enumerate(names, 1):
    customers.append({
        "id": i, "name": nm,
        "short_code": "".join(w[0] for w in nm.replace("'", "").replace(".", "").split()[:3]).upper() + f"{i:02d}",
        "institution_type": pick_institution(nm),
        "address": f"{fake.street_address()}, {random.choice(TOWNS)}, "
                   f"Co. {random.choice(['Dublin', 'Kildare', 'Meath', 'Wicklow', 'Louth', 'Carlow', 'Offaly', 'Westmeath'])}, {eircode()}",
        "contact_person": fake.name(), "contact_number": landline(),
        "email": "office@" + "".join(c for c in nm.lower() if c.isalnum())[:20] + ".ie",
        "is_active": True, "password": "<hashed>", **audit(rand_dt(datetime(2024, 9, 1), datetime(2026, 4, 30))),
    })
customers_df = save("customer_master", customers)
CUST_BY_ID = {c["id"]: c for c in customers}

# ---------------------------------------------------------------- 4. leads (declining conversion)
CONV_RATE = {2025: 0.28, 2026: 0.16}       # <-- dropping lead conversion signal
REQ_SETS = [([1, 4, 5, 8], [2, 4, 5, 8]), ([1, 6, 4, 8], [3, 7, 4, 8]),
            ([1, 6, 9, 8], [2, 7, 9, 8]), ([10, 11, 12], [10, 11, 12]),
            ([1, 5, 10, 11], [2, 5, 10, 11]), ([1, 4], [3, 4])]
MONTH_W = {1: 4, 2: 5, 3: 5, 4: 5, 5: 4, 6: 2, 7: 1, 8: 1, 9: 2, 10: 2, 11: 2, 12: 1}

def lead_date():
    span = random.choices([(datetime(2024, 9, 1), datetime(2025, 8, 31)),
                           (datetime(2025, 9, 1), datetime(2026, 6, 30))], weights=[44, 56])[0]
    for _ in range(60):
        d = rand_dt(span[0], min(span[1], NOW - timedelta(days=25)))
        if random.random() < MONTH_W[d.month] / 5.0:
            return d
    return d

N_LEADS = 180
leads, converted = [], []
for i in range(1, N_LEADS + 1):
    created = lead_date()
    ay = academic_year(created)
    is_repeat = random.random() < 0.30
    cust = random.choice(customers) if is_repeat else None
    if cust:
        school, itype = cust["name"], cust["institution_type"]
        contact, phone, email = cust["contact_person"], cust["contact_number"], cust["email"]
        loc = cust["address"].split(", ")[1]
    else:
        school = random.choice(PATTERNS).format(s=random.choice(SAINTS), g=random.choice(GAELIC),
                                                t=random.choice(TOWNS))
        itype = pick_institution(school)
        contact, phone = fake.name(), landline()
        email = "office@" + "".join(c for c in school.lower() if c.isalnum())[:20] + ".ie"
        loc = random.choice(TOWNS)

    won = random.random() < CONV_RATE[ay]
    if won:
        status = 6; converted.append(i)
    else:
        status = random.choices([2, 3, 4, 5, 7, 8], weights=[10, 16, 16, 10, 30, 18])[0]
    m_req, f_req = random.choice(REQ_SETS)
    male_amt = eur(sum(random.uniform(*G_PRICE[g]) for g in m_req))
    female_amt = eur(sum(random.uniform(*G_PRICE[g]) for g in f_req))
    follow = created + timedelta(days=random.randint(5, 40))
    stale = status in (3, 4, 5) and random.random() < 0.55
    leads.append({
        "id": i, "school_name": school, "institution_type": itype,
        "requirement": f"Uniform programme for ~{random.randint(70, 850)} students, "
                       f"{'September reopening' if random.random() < 0.8 else 'January intake'}",
        "contact_person": contact, "phone_number": phone, "email": email, "location": loc,
        "follow_up_date": ts(follow - timedelta(days=random.randint(20, 90)) if stale else follow),
        "next_action_plan": random.choice(["Send revised quotation", "Arrange sample fitting day",
                                           "Call principal re: budget", "Await board decision",
                                           "Schedule measurement visit", ""]),
        "remarks_notes": random.choice(["Comparing two other suppliers on price",
                                        "Wants crest embroidery in unit price",
                                        "Previous supplier missed deadline", "", "", ""]),
        "assigned_to": random.choice(SALES), "created_by": random.choice(SALES),
        "created_at": ts(created), "updated_at": ts(created + timedelta(days=random.randint(1, 55))),
        "is_active": status not in (7, 8),
        "lead_source_id": random.choices(range(1, 9),
                                         weights=[16, 20, 12, 15, 8, 30 if is_repeat else 5, 7, 7])[0],
        "lead_status_id": status,
        "required_clothing_types": json.dumps(sorted(set(m_req + f_req))),
        "required_male_clothing_types": json.dumps(m_req),
        "required_female_clothing_types": json.dumps(f_req),
        "year": str(ay), "updated_by": random.choice(SALES),
        "customer_id": cust["id"] if cust else "",
        "payment_collection_type": random.choice(["school_billed", "per_student", "per_student"]),
        "male_payment_amount": male_amt, "female_payment_amount": female_amt,
        "currency": "EUR",
        "is_potential_customer": status in (4, 5),
        "referrer_name": fake.name() if random.random() < 0.15 else "",
        "batch_label": f"AY{ay}",
    })
save("leads_master", leads)

# ---------------------------------------------------------------- 5. orders (worsening lateness)
LATE_RATE = {2025: 0.40, 2026: 0.60}       # <-- delivery-delay trend signal
orders = []
for oid, lid in enumerate(sorted(converted), 1):
    L = leads[lid - 1]
    created = datetime.strptime(L["created_at"], "%Y-%m-%d %H:%M:%S") + timedelta(days=random.randint(10, 45))
    cust_id = L["customer_id"] or random.choice(customers)["id"]
    ay = int(L["year"])
    sep = datetime(ay, 8, 25)
    expected = min(sep - timedelta(days=random.randint(5, 20)),
                   created + timedelta(days=random.randint(45, 90)))
    po_late = random.random() < 0.40                       # supply bottleneck
    if expected < NOW - timedelta(days=15):
        is_late = random.random() < LATE_RATE[ay] or (po_late and random.random() < 0.75)
        delay = random.randint(4, 24) if is_late else -random.randint(0, 4)
        actual, status = expected + timedelta(days=delay), "delivered"
    else:
        actual, status = None, random.choice(["measurement", "production", "production", "packing"])
    orders.append({
        "id": oid, "order_id": f"DLO-{expected.year}-{oid:03d}", "lead_id": lid,
        "customer_id": cust_id, "school_name": L["school_name"], "year": L["year"],
        "institution_type": CUST_BY_ID[cust_id]["institution_type"], "status": status,
        "requirements": L["required_clothing_types"],
        "contact_person": L["contact_person"], "phone_number": L["phone_number"],
        "email": L["email"], "location": L["location"],
        "expected_delivery_date": ts(expected), "actual_delivery_date": ts(actual),
        "created_by": random.choice(SALES), "created_at": ts(created),
        "updated_by": random.choice(UIDS), "updated_at": ts(created + timedelta(days=18)),
        "is_active": True, "payment_contact_name": fake.name(), "payment_contact_mobile": mobile(),
        "batch_label": L["batch_label"], "assigned_to": random.choice(SALES),
        "_po_late": po_late,   # internal flag, dropped before save
    })
orders_df_rows = [{k: v for k, v in o.items() if k != "_po_late"} for o in orders]
save("order_master", orders_df_rows)
ORDER_BY_ID = {o["id"]: o for o in orders}

# ---------------------------------------------------------------- 6. measurements
PRIM_CLASSES = ["Junior Infants", "Senior Infants", "1st Class", "2nd Class",
                "3rd Class", "4th Class", "5th Class", "6th Class"]
SEC_CLASSES = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year"]

def mjson(cls):
    base = 58 if cls in PRIM_CLASSES else 78
    chest = base + random.randint(0, 26)
    return json.dumps({"chest_cm": chest, "waist_cm": chest - random.randint(4, 10),
                       "hip_cm": chest + random.randint(0, 8), "shoulder_cm": round(chest * 0.42),
                       "sleeve_cm": round(chest * 0.55), "length_cm": round(chest * 0.78)})

measurements, order_net = [], {}
mid = 0
for o in orders:
    L = leads[o["lead_id"] - 1]
    m_req, f_req = json.loads(L["required_male_clothing_types"]), json.loads(L["required_female_clothing_types"])
    per_student = L["payment_collection_type"] == "per_student"
    child = o["institution_type"] in CHILD_INSTITUTIONS
    ocreated = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
    net_total = 0.0
    for _ in range(random.randint(45, 230)):
        mid += 1
        gender = random.choice(["male", "female"])
        req = m_req if gender == "male" else f_req
        cls = random.choice(PRIM_CLASSES if child else SEC_CLASSES)
        qty = {str(g): (2 if G_PRICE[g][1] < 20 else 1) for g in req}
        payable = eur(sum(random.uniform(*G_PRICE[int(g)]) * q for g, q in qty.items()))
        received = eur(payable if random.random() > 0.32 else payable * random.uniform(0.2, 0.7)) if per_student else 0.0
        net_total += payable
        name = (fake.first_name_male() if gender == "male" else fake.first_name_female()) + " " + fake.last_name()
        mdate = ocreated + timedelta(days=random.randint(3, 25))
        measurements.append({
            "id": mid, "lead_id": o["lead_id"], "order_id": o["id"], "school_id": o["customer_id"],
            "person_name": name, "student_name": name, "student_class": cls,
            "student_section": random.choice(["A", "B", "C"]), "roll_number": str(random.randint(1, 40)),
            "gender": gender, "mobile_number": mobile() if per_student else "",
            "clothing_types": json.dumps(req), "measurements": mjson(cls),
            "quantities": json.dumps(qty),
            "total_payable": payable, "payment_received": received,
            "balance_amount": eur(payable - received), "currency": "EUR",
            "measurement_date": ts(mdate),
            "measurement_status": "completed" if o["status"] != "measurement" else random.choice(["completed", "pending"]),
            "taken_by": random.choice(SALES + [5]), "notes": "",
            "created_by": random.choice(SALES), "created_at": ts(mdate),
            "updated_by": random.choice(UIDS), "updated_at": ts(mdate), "is_active": True,
        })
    order_net[o["id"]] = eur(net_total)
save("measurements", measurements)

# ---------------------------------------------------------------- 7. invoices + payments (VAT calculated)
invoices, payments = [], []
inv_id = pay_id = 0
MODES = ["Bank Transfer", "Card", "Cheque", "Cash"]
for o in orders:
    inv_id += 1
    net = order_net[o["id"]]
    vat_rate = VAT_CHILD if o["institution_type"] in CHILD_INSTITUTIONS else VAT_STANDARD
    vat_amount = eur(net * vat_rate / 100)
    gross = eur(net + vat_amount)
    ocreated = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
    inv_date = ocreated + timedelta(days=random.randint(5, 15))
    advance = eur(gross * random.uniform(0.20, 0.40))
    if o["status"] == "delivered":
        paid_frac = 1.0 if random.random() < 0.62 else random.uniform(0.55, 0.92)
    else:
        paid_frac = random.uniform(0.0, 0.45)
    outstanding = eur(max(gross - advance, 0))
    to_collect = min(eur(outstanding * paid_frac), outstanding)
    n_inst = random.randint(1, 3) if to_collect > 0 else 0
    collected = 0.0
    for k in range(n_inst):
        pay_id += 1
        # last installment absorbs any cent-rounding remainder
        amt = eur(to_collect - collected) if k == n_inst - 1 else eur(to_collect / n_inst)
        collected += amt
        pdt = min(inv_date + timedelta(days=random.randint(10, 120) * (k + 1)), NOW)
        payments.append({"id": pay_id, "order_id": o["id"], "amount": amt, "currency": "EUR",
                         "payment_date": ts(pdt), "payment_mode": random.choice(MODES),
                         "transaction_type": "Payment",
                         "receipt_number": f"RCPT-{pdt.year}-{pay_id:04d}", "notes": "",
                         "recorded_by": random.choice([8, 9]), "created_at": ts(pdt)})
    items = [{"garment_type_id": g, "description": next(n for i, n, *_ in GARMENTS if i == g),
              "qty": random.randint(40, 380), "currency": "EUR"}
             for g in json.loads(o["requirements"])]
    invoices.append({
        "id": inv_id, "invoice_number": f"DINV-{inv_date.year}-{inv_id:04d}", "order_id": o["id"],
        "invoice_date": ts(inv_date), "line_items_json": json.dumps(items),
        "net_total": net, "vat_rate": vat_rate, "vat_amount": vat_amount, "grand_total": gross,
        "currency": "EUR", "advance_paid": advance,
        "balance": (lambda b: 0.0 if b <= 0 else b)(eur(gross - advance - collected)),
        "is_active": True, "created_by": random.choice([8, 9]), "created_at": ts(inv_date),
        "bill_to_name": o["school_name"], "bill_to_address": CUST_BY_ID[o["customer_id"]]["address"],
        "bank_details": "DelightOn Garments Ltd - IBAN IE64 BOFI 9000 1712 3456 78 - BIC BOFIIE2D",
        "comments": f"All amounts in EUR. VAT @ {vat_rate:.0f}% "
                    f"({'children''s clothing zero-rated' if vat_rate == 0 else 'standard rate'}).",
        "signatory_name": "Dermot Scully", "updated_at": ts(inv_date), "updated_by": 8,
        "is_draft": False,
    })
save("order_invoices", invoices)
save("order_payments", payments)

# ---------------------------------------------------------------- 8. procurement (bottlenecks)
purchase_orders, po_items, fabric_purchases, fabric_lots = [], [], [], []
po_id = poi_id = fp_id = lot_id = 0
for o in orders:
    ocreated = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
    pieces = {}
    for m in measurements:
        if m["order_id"] != o["id"]:
            continue
        for g, q in json.loads(m["quantities"]).items():
            pieces[int(g)] = pieces.get(int(g), 0) + q
    po_id += 1
    po_date = ocreated + timedelta(days=random.randint(2, 10))
    vendor = random.choice(list(CHRONIC_LATE_VENDORS)) if o["_po_late"] and random.random() < 0.7 \
        else random.randint(1, 8)
    expected_del = po_date + timedelta(days=random.randint(7, 21))
    actual_del = expected_del + timedelta(days=random.randint(5, 20)) if o["_po_late"] \
        else expected_del - timedelta(days=random.randint(0, 3))
    net_po = 0.0
    for g in json.loads(o["requirements"]):
        need = pieces.get(g, 0) * G_FABRIC[g]
        if need <= 0:
            continue
        ftype = random.choice(list(F_PRICE))
        qty = round(need * random.uniform(1.08, 1.28), 2)      # habitual over-ordering
        unit = F_PRICE[ftype]
        line_net = eur(qty * unit)
        line_vat = eur(line_net * VAT_STANDARD / 100)
        poi_id += 1
        po_items.append({
            "id": poi_id, "purchase_order_id": po_id, "fabric_type_id": ftype,
            "quantity": qty, "unit_of_measure": "meters",
            "unit_price": unit, "net_price": line_net,
            "vat_rate": VAT_STANDARD, "vat_amount": line_vat,
            "total_price": eur(line_net + line_vat), "currency": "EUR",
            "specifications": f"For {next(n for i, n, *_ in GARMENTS if i == g)} - shrinkage-tested",
            "order_id": o["id"], "clothing_type_id": g, "material_type": "fabric",
            "manufacturer": VENDOR_NAMES[vendor - 1],
            "color": next(f[6] for f in FABRICS if f[0] == ftype),
            "created_by": 5, "created_at": ts(po_date),
            "buffer_stock": round(qty - need, 2), "per_piece_requirement": G_FABRIC[g],
            "piece_count": pieces.get(g, 0),
        })
        net_po += line_net + line_vat
        fp_id += 1
        fabric_purchases.append({
            "id": fp_id, "invoice_number": f"VINV-{po_date.year}-{fp_id:04d}",
            "invoice_date": ts(actual_del), "vendor_id": vendor,
            "vendor_name": VENDOR_NAMES[vendor - 1], "fabric_type_id": ftype,
            "manufacturer": VENDOR_NAMES[vendor - 1],
            "color": next(f[6] for f in FABRICS if f[0] == ftype),
            "quantity": qty, "unit": "meters",
            "cost_per_unit": unit, "net_cost": line_net,
            "vat_rate": VAT_STANDARD, "vat_amount": line_vat,
            "total_cost": eur(line_net + line_vat), "currency": "EUR",
            "notes": "", "created_by": 5, "created_at": ts(actual_del),
        })
        lot_id += 1
        fabric_lots.append({
            "id": lot_id, "lot_number": f"LOT-{po_date.year}-{lot_id:04d}",
            "purchase_id": fp_id, "fabric_type_id": ftype,
            "color": next(f[6] for f in FABRICS if f[0] == ftype),
            "initial_quantity": qty,
            "remaining_quantity": round(qty * (1 - random.uniform(0.70, 0.96)), 2),
            "unit": "meters", "price_per_unit": unit, "currency": "EUR",
            "created_at": ts(actual_del + timedelta(days=1)),
            "updated_at": ts(NOW - timedelta(days=random.randint(0, 60))),
        })
    purchase_orders.append({
        "id": po_id, "po_number": f"DPO-{po_date.year}-{po_id:04d}", "vendor_id": vendor,
        "total_amount": eur(net_po), "currency": "EUR", "po_date": ts(po_date),
        "expected_delivery": ts(expected_del), "actual_delivery": ts(actual_del),
        "status": "received" if o["status"] != "measurement" else random.choice(["approved", "sent"]),
        "notes": "Fabric delayed - production start pushed" if o["_po_late"] else "",
        "created_by": 5, "created_at": ts(po_date), "order_id": o["id"],
        "remarks": "All prices in EUR incl. VAT @ 23%",
    })
save("purchase_orders", purchase_orders)
save("purchase_order_items", po_items)
save("fabric_purchases", fabric_purchases)
save("fabric_lots", fabric_lots)
LOTS_BY_TYPE = {}
for l in fabric_lots:
    LOTS_BY_TYPE.setdefault(l["fabric_type_id"], []).append(l["id"])

# ---------------------------------------------------------------- 9. production
cutting_log, cutting_groups, daily_log = [], [], []
cl_id = cg_id = dl_id = 0
WASTE_REASONS = ["Pattern misalignment on tartan repeat", "Fabric flaw discovered mid-lay",
                 "Manual marker inefficiency", "Operator error - re-cut required",
                 "Shade variation between lots", ""]
for o in orders:
    if o["status"] == "measurement":
        continue
    ocreated = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
    start_delay = 14 + (random.randint(5, 18) if o["_po_late"] else 0)   # bottleneck propagates
    pieces = {}
    for m in measurements:
        if m["order_id"] != o["id"]:
            continue
        for g, q in json.loads(m["quantities"]).items():
            pieces[int(g)] = pieces.get(int(g), 0) + q
    for g in json.loads(o["requirements"]):
        total = pieces.get(g, 0)
        if total == 0 or G_FABRIC[g] == 0:
            continue
        cg_id += 1
        cutting_groups.append({"id": cg_id, "order_id": o["order_id"], "garment_type_id": g,
                               "group_number": cg_id, "adjusted_measurements": "{}",
                               "notes": "Held awaiting fabric delivery" if o["_po_late"] else "",
                               "created_by": 6, "created_at": ts(ocreated + timedelta(days=start_delay)),
                               "updated_at": ts(ocreated + timedelta(days=start_delay))})
        remaining, n_b = total, max(1, total // random.randint(60, 120))
        for b in range(n_b):
            cl_id += 1
            pcs = remaining if b == n_b - 1 else min(remaining, random.randint(40, 120))
            remaining -= pcs
            fm = round(pcs * G_FABRIC[g], 2)
            exp_w, act_w = round(fm * 0.05, 2), round(fm * random.uniform(0.09, 0.15), 2)
            ftype = random.choice(list(LOTS_BY_TYPE))
            cutting_log.append({
                "id": cl_id, "order_id": o["id"], "clothing_type_id": g,
                "fabric_lot_id": random.choice(LOTS_BY_TYPE[ftype]),
                "fabric_consumed_meters": round(fm + act_w, 2), "pieces_produced": pcs,
                "expected_wastage": exp_w, "actual_wastage": act_w,
                "wastage_reason": random.choice(WASTE_REASONS) if act_w > exp_w * 1.8 else "",
                "cut_by": random.choice(CUTTERS),
                "cut_date": ts(ocreated + timedelta(days=start_delay + b * 2)),
                "notes": "", "created_by": 6,
                "created_at": ts(ocreated + timedelta(days=start_delay + b * 2)),
            })
        start = ocreated + timedelta(days=start_delay + 2)
        for phase in PHASES:
            done, day = 0, start + timedelta(days=(phase - 1) * 3)
            while done < total:
                dl_id += 1
                todays = min(total - done, random.randint(25, 90))
                done += todays
                daily_log.append({"id": dl_id, "order_id": o["id"], "phase_id": phase,
                                  "clothing_type_id": g, "production_date": ts(min(day, NOW)),
                                  "employee_id": random.choice(STITCHERS if phase == 2 else ALL_EMP),
                                  "pieces_completed": todays,
                                  "pieces_in_progress": max(0, min(total - done, 30)),
                                  "pieces_pending": max(0, total - done), "notes": "",
                                  "created_by": 6, "created_at": ts(min(day, NOW))})
                day += timedelta(days=1)
save("cutting_log", cutting_log)
save("cutting_groups", cutting_groups)
save("daily_production_log", daily_log)
CG = {(c["order_id"], c["garment_type_id"]): c["id"] for c in cutting_groups}

# ---------------------------------------------------------------- 10. delivery_records
delivery = []
dr_id = 0
RETURN_REASONS = ["Size too small - remake requested", "Loose stitching at seam",
                  "Crest embroidery misplaced", "Fabric shade mismatch", "Hem fault"]
for m in measurements:
    o = ORDER_BY_ID[m["order_id"]]
    if o["status"] not in ("delivered", "packing") or random.random() > 0.32:
        continue
    for g, q in json.loads(m["quantities"]).items():
        g = int(g)
        cgid = CG.get((o["order_id"], g))
        if not cgid:
            continue
        for piece in range(1, q + 1):
            dr_id += 1
            delivered = o["status"] == "delivered"
            returned = delivered and random.random() < 0.05
            ddate = (datetime.strptime(o["actual_delivery_date"], "%Y-%m-%d %H:%M:%S")
                     if o["actual_delivery_date"] else None)
            delivery.append({
                "id": dr_id, "unique_code": f"{o['order_id']}-M{m['id']}-G{g}-P{piece}",
                "order_id": o["order_id"], "measurement_id": m["id"], "garment_type_id": g,
                "cutting_group_id": cgid, "student_name": m["student_name"],
                "student_class": m["student_class"], "student_section": m["student_section"],
                "adjusted_measurements": m["measurements"], "original_measurements": m["measurements"],
                "status": "returned" if returned else ("delivered" if delivered else "ready_for_packing"),
                "dc_number": f"DC-{o['order_id'][-3:]}-{random.randint(1, 4)}" if delivered else "",
                "piece_index": piece, "created_by": 6,
                "created_at": ts(datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S") + timedelta(days=32)),
                "updated_at": ts(ddate or NOW), "delivered_at": ts(ddate),
                "delivered_by": 10 if delivered else "",
                "returned_at": ts(ddate + timedelta(days=random.randint(2, 14))) if returned else "",
                "returned_by": 11 if returned else "",
                "return_reason": random.choice(RETURN_REASONS) if returned else "",
            })
save("delivery_records", delivery)

# ---------------------------------------------------------------- 11. stock_master (VAT, no GST)
stock = []
for i in range(1, 25):
    g = random.choice([x[0] for x in GARMENTS])
    f = random.choice(FABRICS)
    stock.append({"id": i, "clothing_type_id": g, "item_code": f"DSK-{i:04d}",
                  "lot_batch": f"LOT-{random.randint(2025, 2026)}-{random.randint(1, 90):04d}",
                  "material_type": f[1], "manufacturer": random.choice(VENDOR_NAMES),
                  "material_color": f[6], "available_qty": round(random.uniform(15, 220), 2),
                  "unit_of_measure": "meters", "purchase_price": f[5],
                  "vat_rate": VAT_STANDARD, "currency": "EUR",
                  "created_at": ts(rand_dt(datetime(2025, 1, 1), NOW)), "updated_at": ts(NOW),
                  "remarks": "Purchase price ex-VAT, EUR"})
save("stock_master", stock)

# ---------------------------------------------------------------- 12. validation
print("\n=== VALIDATION ===")
errs = 0
def check(label, ok):
    global errs
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}")
    if not ok:
        errs += 1

lm = pd.read_csv(OUT / "leads_master.csv"); om = pd.read_csv(OUT / "order_master.csv")
ms = pd.read_csv(OUT / "measurements.csv"); inv = pd.read_csv(OUT / "order_invoices.csv")
pay = pd.read_csv(OUT / "order_payments.csv"); dr = pd.read_csv(OUT / "delivery_records.csv")
cl = pd.read_csv(OUT / "cutting_log.csv"); fl = pd.read_csv(OUT / "fabric_lots.csv")
po = pd.read_csv(OUT / "purchase_orders.csv")

check("every order references a valid lead", om.lead_id.isin(lm.id).all())
check("every order references a valid customer", om.customer_id.isin(customers_df.id).all())
check("every measurement references a valid order", ms.order_id.isin(om.id).all())
check("every invoice references a valid order", inv.order_id.isin(om.id).all())
check("every payment references a valid order", pay.order_id.isin(om.id).all())
check("every delivery record references a valid measurement", dr.measurement_id.isin(ms.id).all())
check("every cutting log references a valid fabric lot", cl.fabric_lot_id.isin(fl.id).all())
check("VAT identity: grand_total = net_total + vat_amount",
      ((inv.net_total + inv.vat_amount - inv.grand_total).abs() < 0.05).all())
check("VAT correctly calculated: vat_amount = net_total * vat_rate",
      ((inv.net_total * inv.vat_rate / 100 - inv.vat_amount).abs() < 0.05).all())
merged = inv.merge(pay.groupby("order_id")["amount"].sum().rename("paid"),
                   left_on="order_id", right_index=True, how="left").fillna({"paid": 0})
check("accounting identity: grand_total = advance + payments + balance",
      ((merged.grand_total - merged.advance_paid - merged.paid - merged.balance).abs() < 0.05).all())
check("no negative balances", (inv.balance >= -0.01).all())
check("fabric lots: remaining <= initial", (fl.remaining_quantity <= fl.initial_quantity).all())
check("no GST column anywhere",
      not any("gst" in c.lower() for f in OUT.glob("*.csv") for c in pd.read_csv(f, nrows=0).columns))
check("all financial tables carry currency = EUR",
      all((pd.read_csv(OUT / f)["currency"] == "EUR").all()
          for f in ["order_invoices.csv", "order_payments.csv", "purchase_orders.csv",
                    "fabric_purchases.csv", "stock_master.csv"]))

lm["_conv"] = lm.lead_status_id == 6
conv_by_year = lm.groupby("year")["_conv"].mean()
dv = om[om.actual_delivery_date.notna()].copy()
dv["late"] = pd.to_datetime(dv.actual_delivery_date) > pd.to_datetime(dv.expected_delivery_date)
late_by_year = dv.groupby("year")["late"].mean()
po["po_late"] = pd.to_datetime(po.actual_delivery) > pd.to_datetime(po.expected_delivery)
worst = po.groupby("vendor_id")["po_late"].mean().sort_values(ascending=False).head(2)
ret = (dr.status == "returned").sum() / max((dr.status.isin(["delivered", "returned"])).sum(), 1)
waste = cl.actual_wastage.sum() / cl.fabric_consumed_meters.sum() * 100
idle = fl.remaining_quantity.sum() / fl.initial_quantity.sum() * 100

print("\n=== DISTRESS-TREND KPIs (baseline for dashboards) ===")
for y in sorted(conv_by_year.index):
    print(f"  AY{y}: lead conversion {conv_by_year[y]:5.1%}   "
          f"late deliveries {late_by_year.get(y, float('nan')):5.1%}")
print(f"  Late fabric POs overall  : {po.po_late.mean():5.1%}  "
      f"(worst vendors: {', '.join(VENDOR_NAMES[v-1] for v in worst.index)})")
print(f"  Garment return rate      : {ret:5.1%}")
print(f"  Avg cutting wastage      : {waste:4.1f}% (plan 5%)")
print(f"  Idle fabric stock        : {idle:4.1f}% of purchased metres")
print(f"  Open receivables (gross) : EUR {inv.balance.sum():,.2f}")
print(f"  Total VAT invoiced       : EUR {inv.vat_amount.sum():,.2f}")
print(f"\n{'ALL CHECKS PASSED' if errs == 0 else f'{errs} CHECK(S) FAILED'}")
