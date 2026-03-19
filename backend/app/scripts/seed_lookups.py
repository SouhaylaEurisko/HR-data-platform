"""
Seed script — populates lookup_category, lookup_option, and a default organization.

Usage:
    cd backend
    python -m app.scripts.seed_lookups
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import func, text

from app.config.database import SessionLocal, init_db
from app.models.organization import Organization
from app.models.lookup import LookupCategory, LookupOption


def _sync_organization_id_sequence(db) -> None:
    """
    After DELETEs, PostgreSQL still advances the id sequence, so the next INSERT
    can get id=2 even with an empty table. Align sequence with MAX(id).
    """
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    m = db.query(func.max(Organization.id)).scalar()
    if m is None:
        return
    db.execute(
        text(
            "SELECT setval("
            "pg_get_serial_sequence('organization', 'id'), "
            "CAST(:m AS bigint), true)"
        ),
        {"m": m},
    )


def _next_organization_id(db) -> int | None:
    """
    If there are no organizations yet, return 1 so the default org is always id=1
    after a cleared DB. Otherwise None (let the DB assign).
    """
    m = db.query(func.max(Organization.id)).scalar()
    if m is None:
        return 1
    return None


SEED_DATA = {
    "workplace_type": {
        "label": "Workplace Type",
        "description": "Where the employee will work",
        "options": [
            ("hybrid", "Hybrid", 1),
            ("remote", "Remote", 2),
            ("onsite", "On-Site", 3),
        ],
    },
    "employment_type": {
        "label": "Employment Type",
        "description": "Type of employment contract",
        "options": [
            ("full_time", "Full-Time", 1),
            ("part_time", "Part-Time", 2),
            ("contractual", "Contractual model only", 3),
            ("Long term contract only", "Long term", 4),
            ("Open for both options", "Open for both options", 5),
        ],
    },
    "employment_status": {
        "label": "Employment Status",
        "description": "Current employment status of the candidate",
        "options": [
            ("employed", "Employed", 1),
            ("unemployed", "Unemployed", 2),
        ],
    },
    "residency_type": {
        "label": "Residency Type",
        "description": "Legal residency status",
        "options": [
            ("citizen", "Citizen", 1),
            ("permanent_resident", "Permanent Resident", 2),
            ("work_visa", "Work Visa", 3),
            ("tourist_visa", "Tourist Visa", 4),
            ("student_visa", "Student Visa", 5),
        ],
    },
    "marital_status": {
        "label": "Marital Status",
        "description": "Marital status of the candidate",
        "options": [
            ("single", "Single", 1),
            ("married", "Married", 2),
            ("divorced", "Divorced", 3),
            ("widowed", "Widowed", 4),
            ("engaged", "Engaged", 5),
        ],
    },
    "education_level": {
        "label": "Education Level",
        "description": "Highest education level attained",
        "options": [
            ("high_school", "High School", 1),
            ("associate", "Associate", 2),
            ("bachelor", "Bachelor", 3),
            ("master", "Master", 4),
            ("doctorate", "Doctorate", 5),
        ],
    },
    "education_completion": {
        "label": "Education Completion Status",
        "description": "Whether the education was completed",
        "options": [
            ("completed", "Completed", 1),
            ("in_progress", "In Progress", 2),
            ("incomplete", "Incomplete", 3),
            ("dropped_out", "Dropped Out", 4),
        ],
    },
    "passport_validity": {
        "label": "Passport Validity Status",
        "description": "Current passport status",
        "options": [
            ("valid", "Valid", 1),
            ("expired", "Expired", 2),
            ("no_passport", "No Passport", 3),
            ("renewal_in_progress", "Renewal in Progress", 4),
        ],
    },
}


def seed(db):
    # -- Default organization --
    existing_org = db.query(Organization).filter_by(slug="default").first()
    if not existing_org:
        org_kwargs: dict = {"name": "Default Organization", "slug": "default"}
        forced_id = _next_organization_id(db)
        if forced_id is not None:
            org_kwargs["id"] = forced_id
        org = Organization(**org_kwargs)
        db.add(org)
        db.flush()
        _sync_organization_id_sequence(db)
        print("Created default organization.")
    else:
        print("Default organization already exists.")

    # -- Lookup categories & options --
    for code, data in SEED_DATA.items():
        cat = db.query(LookupCategory).filter_by(code=code).first()
        if not cat:
            cat = LookupCategory(
                code=code,
                label=data["label"],
                description=data["description"],
                is_system=True,
            )
            db.add(cat)
            db.flush()
            print(f"  Created category: {code}")
        else:
            print(f"  Category already exists: {code}")

        for opt_code, opt_label, order in data["options"]:
            existing = (
                db.query(LookupOption)
                .filter_by(category_id=cat.id, code=opt_code, organization_id=None)
                .first()
            )
            if not existing:
                db.add(LookupOption(
                    category_id=cat.id,
                    organization_id=None,
                    code=opt_code,
                    label=opt_label,
                    display_order=order,
                    is_active=True,
                ))
                print(f"    + {opt_code}")
            else:
                print(f"    (exists) {opt_code}")

    db.commit()
    print("\nSeed complete.")


def main():
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
