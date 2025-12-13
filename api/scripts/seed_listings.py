import random
from decimal import Decimal
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.listing import Listing

LOCATIONS = ["Los Angeles, CA", "New York, NY", "Miami, FL", "Houston, TX", "Seattle, WA", "Chicago, IL"]
CONDITIONS = ["USED", "NEW"]
TRANSMISSIONS = ["Automatic", "Manual"]


def get_or_create_vehicle(db, make, model, trim, year):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.make == make, Vehicle.model == model, Vehicle.trim == trim, Vehicle.year == year)
        .first()
    )
    if vehicle:
        return vehicle
    vehicle = Vehicle(make=make, model=model, trim=trim, year=year)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def create_listing(db, vehicle, title, price, currency="USD"):
    listing = Listing(
        vehicle_id=vehicle.id,
        title=title,
        price=Decimal(price),
        currency=currency,
        location=random.choice(LOCATIONS),
        condition=random.choice(CONDITIONS),
        transmission=random.choice(TRANSMISSIONS),
        risk_flags=[],
    )
    listing.search_text = f"{vehicle.year} {vehicle.make} {vehicle.model} {vehicle.trim or ''} {title}"
    db.add(listing)
    db.commit()
    db.refresh(listing)
    db.execute(
        text("UPDATE listings SET search_tsv = to_tsvector('simple', unaccent(search_text)) WHERE id=:id"),
        {"id": listing.id},
    )
    db.commit()


def seed():
    db = SessionLocal()
    try:
        listings_created = 0

        gtr_vehicle = get_or_create_vehicle(db, "Nissan", "GT-R", "Skyline", 2005)
        gtr_titles = [
            "Nissan GT-R 2005",
            "Nissan GTR 2005 Skyline GT-R",
            "2005 Skyline GT-R R34",
            "2005 Nissan GT-R Premium",
            "Skyline GTR 2005 JDM",
        ]
        for title in gtr_titles:
            create_listing(db, gtr_vehicle, title, price=55000 + listings_created * 500)
            listings_created += 1

        sample_cars = [
            ("Toyota", "Supra", "RZ", 1998, 72000),
            ("BMW", "M3", "Competition", 2018, 65000),
            ("Tesla", "Model 3", "Performance", 2022, 52000),
            ("Ford", "Mustang", "GT", 2016, 34000),
            ("Porsche", "911", "Carrera", 2015, 98000),
            ("Audi", "RS7", "", 2019, 89000),
            ("Subaru", "WRX", "STI", 2020, 41000),
            ("Honda", "Civic", "Type R", 2021, 45000),
            ("Chevrolet", "Corvette", "Z06", 2017, 76000),
            ("Lexus", "IS 350", "F Sport", 2020, 38000),
        ]

        for make, model, trim, year, base_price in sample_cars:
            vehicle = get_or_create_vehicle(db, make, model, trim or None, year)
            for i in range(4):
                title = f"{year} {make} {model} {trim} #{i+1}"
                create_listing(db, vehicle, title, price=base_price + i * 1000)
                listings_created += 1
                if listings_created >= 50:
                    break
            if listings_created >= 50:
                break

        print(f"Seeded {listings_created} listings")
    finally:
        db.close()


if __name__ == "__main__":
    seed()