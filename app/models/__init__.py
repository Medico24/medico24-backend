"""Database models."""

from app.models.admins import admins
from app.models.appointments import appointments
from app.models.clinics import clinics
from app.models.doctor_clinics import doctor_clinics
from app.models.doctors import doctors
from app.models.notifications import notification_deliveries, notifications
from app.models.patients import patients
from app.models.pharmacies import (
    pharmacies,
    pharmacy_hours,
    pharmacy_locations,
)
from app.models.pharmacy_staff import pharmacy_staff
from app.models.push_tokens import push_tokens
from app.models.users import users

__all__ = [
    "admins",
    "appointments",
    "clinics",
    "doctor_clinics",
    "doctors",
    "notification_deliveries",
    "notifications",
    "patients",
    "pharmacies",
    "pharmacy_hours",
    "pharmacy_locations",
    "pharmacy_staff",
    "push_tokens",
    "users",
]
