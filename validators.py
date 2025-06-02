from fastapi import HTTPException
import re

def validate_fullname(fullname: str):
    if not fullname.strip():
        raise HTTPException(status_code=400, detail="Full name cannot be empty.")
    parts = fullname.strip().split()
    if len(parts) < 2:
        raise HTTPException(
            status_code=400,
            detail="Full name must include at least first name and last name.",
        )


def validate_phone(phone: str):
    if not phone.strip():
        raise HTTPException(status_code=400, detail="Phone number cannot be empty.")
    if not re.match(r"^\d{10,15}$", phone):
        raise HTTPException(
            status_code=400, detail="Phone number must be 10 to 15 digits."
        )


def validate_inn(inn: str):
    if not inn.strip():
        raise HTTPException(status_code=400, detail="INN cannot be empty.")
    if not re.match(r"^(\d{10}|\d{12})$", inn):
        raise HTTPException(
            status_code=400, detail="INN must be either 10 or 12 digits."
        )


def validate_password(password: str):
    if not password:
        raise HTTPException(status_code=400, detail="Password cannot be empty.")
    if len(password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters long."
        )
