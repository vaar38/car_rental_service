from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class CarCategory(Base):
    __tablename__ = "car_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("car_categories.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    price_per_day = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="available")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    
    __table_args__ = (
        CheckConstraint("price_per_day > 0"),
        CheckConstraint("year >= 1990"),
        CheckConstraint("status IN ('available', 'rented', 'maintenance')"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False, index=True)
    pickup_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    return_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("end_date >= start_date"),
        CheckConstraint("total_price >= 0"),
        CheckConstraint("status IN ('pending', 'confirmed', 'active', 'completed', 'cancelled')"),
    )

    
