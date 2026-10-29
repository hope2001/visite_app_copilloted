"""Idempotent demo data seeding. Run with: python -m app.seed

Requires VMP_SEED_PASSWORD (min 12 chars). Intended for local/demo environments only.
"""

import logging
import os
import sys
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.domain.enums import Role
from app.models import User, Visit
from app.schemas.visit import VisitCreate, VisitorInput
from app.services.visit_service import VisitService

logger = logging.getLogger("app.seed")

MIN_SEED_PASSWORD_LENGTH = 12


@dataclass(frozen=True)
class DemoUser:
    email: str
    full_name: str
    role: Role


DEMO_USERS = (
    DemoUser("alice.employee@acme-corp.com", "Alice Martin", Role.EMPLOYEE),
    DemoUser("bob.employee@acme-corp.com", "Bob Dupont", Role.EMPLOYEE),
    DemoUser("sam.security@acme-corp.com", "Sam Keller", Role.SECURITY),
    DemoUser("ada.admin@acme-corp.com", "Ada Admin", Role.ADMIN),
)


def seed_users(db: Session, password: str) -> None:
    password_hash = hash_password(password)
    for demo in DEMO_USERS:
        if db.scalar(select(User.id).where(User.email == demo.email)) is None:
            db.add(
                User(
                    email=demo.email,
                    full_name=demo.full_name,
                    role=demo.role,
                    password_hash=password_hash,
                )
            )
            logger.info("Created demo user", extra={"role": demo.role.value})
    db.commit()


def seed_visits(db: Session, visits: VisitService) -> None:
    if db.scalar(select(Visit.id).limit(1)) is not None:
        return
    alice = db.scalars(select(User).where(User.email == DEMO_USERS[0].email)).one()
    today = visits.today()
    samples = (
        ("Jane Doe", "jane.doe@contoso.com", "Contoso", "Quarterly business review", today),
        ("John Smith", "john.smith@fabrikam.com", "Fabrikam", "Network maintenance", today),
        (
            "Lena Weber",
            "lena.weber@northwind.com",
            "Northwind",
            "Job interview",
            today + timedelta(days=1),
        ),
    )
    for full_name, email, company, purpose, expected_date in samples:
        visits.register_visit(
            alice,
            VisitCreate(
                visitor=VisitorInput(full_name=full_name, email=email, company=company),
                purpose=purpose,
                expected_date=expected_date,
            ),
        )
    logger.info("Created demo visits", extra={"count": len(samples)})


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    password = os.environ.get("VMP_SEED_PASSWORD", "")
    if len(password) < MIN_SEED_PASSWORD_LENGTH:
        logger.error("VMP_SEED_PASSWORD must be set (at least 12 characters).")
        return 1

    engine = create_db_engine(settings.database_url)
    try:
        with create_session_factory(engine)() as db:
            seed_users(db, password)
            seed_visits(db, VisitService(db, SystemClock(), settings.timezone))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
