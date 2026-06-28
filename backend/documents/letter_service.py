"""Generate HR letters as PDFs and persist them as EmployeeDocument records."""

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from employees.models import Employee

from .models import DocumentCategory, EmployeeDocument
from .pdf_utils import build_simple_pdf


LETTER_OFFER = "offer"
LETTER_APPOINTMENT = "appointment"
LETTER_EXPERIENCE = "experience"
LETTER_RELIEVING = "relieving"
LETTER_WARNING = "warning"
LETTER_PROMOTION = "promotion"

LETTER_TYPES = {
    LETTER_OFFER: "Offer Letter",
    LETTER_APPOINTMENT: "Appointment Letter",
    LETTER_EXPERIENCE: "Experience Letter",
    LETTER_RELIEVING: "Relieving Letter",
    LETTER_WARNING: "Warning Letter",
    LETTER_PROMOTION: "Promotion Letter",
}

CATEGORY_NAMES = {
    LETTER_OFFER: "Offer Letters",
    LETTER_APPOINTMENT: "Appointment Letters",
    LETTER_EXPERIENCE: "HR Documents",
    LETTER_RELIEVING: "HR Documents",
    LETTER_WARNING: "HR Documents",
    LETTER_PROMOTION: "HR Documents",
}


def _employee_name(employee):
    return f"{employee.first_name} {employee.last_name}".strip()


def _department_name(employee):
    if employee.department:
        return employee.department.name
    return "To be assigned"


def _designation_name(employee):
    if employee.designation:
        return employee.designation.title
    return "To be assigned"


def _today_str():
    return timezone.localdate().isoformat()


def build_offer_letter_pdf(employee):
    lines = [
        "OFFER LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        f"Dear {_employee_name(employee)},",
        "",
        "We are pleased to offer you employment with our organization.",
        f"Employee Code: {employee.employee_code}",
        f"Designation: {_designation_name(employee)}",
        f"Department: {_department_name(employee)}",
        f"Proposed Joining Date: {employee.joining_date}",
        "",
        "This offer is subject to verification of documents and",
        "completion of onboarding formalities.",
        "",
        "We look forward to welcoming you to the team.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


def build_appointment_letter_pdf(employee):
    lines = [
        "APPOINTMENT LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        f"Dear {_employee_name(employee)},",
        "",
        "With reference to your application and interviews, we are pleased",
        "to appoint you to the following position:",
        "",
        f"Employee Code: {employee.employee_code}",
        f"Designation: {_designation_name(employee)}",
        f"Department: {_department_name(employee)}",
        f"Date of Joining: {employee.joining_date}",
        "",
        "Your appointment is on the terms and conditions communicated",
        "during the selection process and company policies in force.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


def build_experience_letter_pdf(employee):
    lines = [
        "EXPERIENCE LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        "To Whom It May Concern,",
        "",
        f"This is to certify that {_employee_name(employee)}",
        f"(Employee Code: {employee.employee_code}) was employed with",
        "our organization.",
        f"Designation: {_designation_name(employee)}",
        f"Department: {_department_name(employee)}",
        f"Period of Service: {employee.joining_date} to {_today_str()}",
        "",
        "During the tenure, the employee demonstrated professionalism",
        "and commitment to assigned responsibilities.",
        "",
        "We wish continued success in future endeavors.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


def build_relieving_letter_pdf(employee):
    last_day = _today_str()
    try:
        resignation = employee.resignation
    except ObjectDoesNotExist:
        resignation = None

    if resignation and resignation.last_working_day:
        last_day = resignation.last_working_day.isoformat()
    elif resignation and resignation.resignation_date:
        last_day = resignation.resignation_date.isoformat()

    lines = [
        "RELIEVING LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        f"Dear {_employee_name(employee)},",
        "",
        "This is to confirm that you have been relieved from your duties",
        "with our organization as per the details below:",
        "",
        f"Employee Code: {employee.employee_code}",
        f"Designation: {_designation_name(employee)}",
        f"Department: {_department_name(employee)}",
        f"Date of Joining: {employee.joining_date}",
        f"Last Working Day: {last_day}",
        "",
        "We thank you for your contributions and wish you all the best.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


def build_warning_letter_pdf(employee, notes=""):
    reason = notes.strip() or "Violation of company policy / conduct standards."
    lines = [
        "WARNING LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        f"Dear {_employee_name(employee)},",
        "",
        "This letter serves as a formal warning regarding the matter below:",
        "",
        reason,
        "",
        f"Employee Code: {employee.employee_code}",
        f"Designation: {_designation_name(employee)}",
        f"Department: {_department_name(employee)}",
        "",
        "You are advised to take corrective action immediately. Further",
        "instances may lead to disciplinary action as per company policy.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


def build_promotion_letter_pdf(employee, new_designation=""):
    promoted_to = new_designation.strip() or _designation_name(employee)
    lines = [
        "PROMOTION LETTER",
        "",
        f"Date: {_today_str()}",
        "",
        f"Dear {_employee_name(employee)},",
        "",
        "We are pleased to inform you of your promotion, effective immediately.",
        "",
        f"Employee Code: {employee.employee_code}",
        f"Department: {_department_name(employee)}",
        f"New Designation: {promoted_to}",
        "",
        "Congratulations on this achievement. We are confident you will",
        "continue to excel in your expanded role.",
        "",
        "Human Resources Department",
    ]
    return build_simple_pdf(lines)


BUILDERS = {
    LETTER_OFFER: lambda employee, **kw: build_offer_letter_pdf(employee),
    LETTER_APPOINTMENT: lambda employee, **kw: build_appointment_letter_pdf(employee),
    LETTER_EXPERIENCE: lambda employee, **kw: build_experience_letter_pdf(employee),
    LETTER_RELIEVING: lambda employee, **kw: build_relieving_letter_pdf(employee),
    LETTER_WARNING: lambda employee, **kw: build_warning_letter_pdf(
        employee, notes=kw.get("notes", "")
    ),
    LETTER_PROMOTION: lambda employee, **kw: build_promotion_letter_pdf(
        employee, new_designation=kw.get("new_designation", "")
    ),
}


def get_category(letter_type):
    name = CATEGORY_NAMES.get(letter_type)
    if not name:
        return None
    return DocumentCategory.objects.filter(name=name).first()


def generate_letter_document(employee, letter_type, notes="", new_designation=""):
    """Build a PDF letter and save it as an EmployeeDocument."""

    if letter_type not in LETTER_TYPES:
        raise ValueError(f"Unsupported letter type: {letter_type}")

    category = get_category(letter_type)
    if category is None:
        raise ValueError(
            f"Document category '{CATEGORY_NAMES[letter_type]}' is not configured."
        )

    with transaction.atomic():
        employee = (
            Employee.objects
            .select_related("department", "designation", "resignation")
            .get(pk=employee.pk)
        )

        pdf_bytes = BUILDERS[letter_type](
            employee,
            notes=notes,
            new_designation=new_designation,
        )

        label = LETTER_TYPES[letter_type]
        today = _today_str()
        title = f"{label} - {employee.employee_code} ({today})"
        filename = f"{letter_type}_letter_{employee.employee_code}_{today}.pdf"

        document = EmployeeDocument(
            employee=employee,
            category=category,
            title=title,
        )
        document.file.save(filename, ContentFile(pdf_bytes), save=True)

        try:
            from lifecycle.models import Onboarding
            from lifecycle.onboarding_checklist import sync_onboarding_document_status

            onboarding = Onboarding.objects.filter(employee=employee).first()
            if onboarding:
                sync_onboarding_document_status(onboarding)
        except Exception:
            pass

        return document
