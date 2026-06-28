"""Joining letter PDF generation for onboarding."""

from documents.pdf_utils import build_simple_pdf


def build_joining_letter_pdf(onboarding):
    """Return PDF bytes for an onboarding record."""

    employee = onboarding.employee
    name = f"{employee.first_name} {employee.last_name}".strip()
    joining = onboarding.joining_date or employee.joining_date
    department = (
        employee.department.name if employee.department else "To be assigned"
    )
    designation = (
        employee.designation.title if employee.designation else "To be assigned"
    )

    lines = [
        "JOINING LETTER",
        "",
        f"Date: {joining}",
        "",
        f"Dear {name},",
        "",
        "We are pleased to confirm your appointment with our organization.",
        f"Employee Code: {employee.employee_code}",
        f"Department: {department}",
        f"Designation: {designation}",
        f"Joining Date: {joining}",
        "",
        "Please report on your joining date with the required documents.",
        "We look forward to a successful association.",
        "",
        "Human Resources Department",
    ]

    if onboarding.notes:
        lines.extend(["", f"Notes: {onboarding.notes}"])

    return build_simple_pdf(lines)
