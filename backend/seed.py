"""
Creates the database tables (if they don't exist yet) and exactly ONE
admin login account -- nothing else. There's no other way to get your
first admin account, since creating one normally requires already being
logged in as an admin.

Everything else -- events, tracks, teams, judge accounts -- is meant to
be created by that admin through the Admin dashboard once they're
signed in. This script doesn't add any of that for you.

    python seed.py

By default it creates username "admin" / password "adminpass1". Override
either with environment variables so you're not stuck on the default in
a real deployment:

    ADMIN_NAME="Event Organizer" ADMIN_USERNAME="admin" ADMIN_PASSWORD="something-only-you-know" python seed.py

Safe to re-run: if an admin with that username already exists, this
just confirms it's there and exits -- it never overwrites a password.
"""
import os

from app.database import SessionLocal, Base, engine
from app.auth import hash_password
from app import models

Base.metadata.create_all(bind=engine)

ADMIN_NAME = os.getenv("ADMIN_NAME", "Event Organizer")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminpass1")


def main():
    db = SessionLocal()

    existing = db.query(models.Admin).filter(models.Admin.username == ADMIN_USERNAME.lower()).first()
    if existing:
        print(f'An admin with username "{ADMIN_USERNAME}" already exists (id={existing.id}). Nothing to do.')
        db.close()
        return

    admin = models.Admin(
        name=ADMIN_NAME,
        username=ADMIN_USERNAME.lower(),
        hashed_password=hash_password(ADMIN_PASSWORD),
    )
    db.add(admin)
    db.commit()

    print("Admin account created:")
    print(f"  name:     {ADMIN_NAME}")
    print(f"  username: {ADMIN_USERNAME}")
    print(f"  password: {ADMIN_PASSWORD}")
    print("\nLog in on the Admin tab with this, then create your event, "
          "tracks, teams, and judge accounts from the Admin dashboard.")
    if ADMIN_PASSWORD == "adminpass1":
        print("\n⚠️  You're using the default password -- change it (or re-run "
              "with ADMIN_PASSWORD set) before sharing this with anyone.")

    db.close()


if __name__ == "__main__":
    main()
