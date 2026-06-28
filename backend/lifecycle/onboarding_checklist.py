"""Onboarding required document checklist integrated with EmployeeDocument uploads."""

from documents.models import EmployeeDocument

# Required items for onboarding completion (matched against uploaded documents).
ONBOARDING_CHECKLIST = [
    {
        'key': 'offer_letter',
        'label': 'Offer Letter',
        'category': 'Offer Letters',
    },
    {
        'key': 'appointment_letter',
        'label': 'Appointment Letter',
        'category': 'Appointment Letters',
    },
    {
        'key': 'id_proof',
        'label': 'ID Proof',
        'category': 'HR Documents',
        'keywords': ('id', 'aadhaar', 'pan', 'passport'),
    },
    {
        'key': 'bank_proof',
        'label': 'Bank Proof',
        'category': 'HR Documents',
        'keywords': ('bank', 'account', 'ifsc'),
    },
]


def _document_matches(item, document):
    if document.category is None:
        return False
    if document.category.name != item['category']:
        return False
    keywords = item.get('keywords')
    if not keywords:
        return True
    haystack = f"{document.title} {document.file.name}".lower()
    return any(word in haystack for word in keywords)


def compute_document_checklist(employee):
    """Return checklist rows with upload status and aggregate completion."""

    documents = list(
        EmployeeDocument.objects
        .select_related('category')
        .filter(employee=employee)
        .order_by('-uploaded_at')
    )

    items = []
    completed = 0

    for spec in ONBOARDING_CHECKLIST:
        matched = None
        for doc in documents:
            if _document_matches(spec, doc):
                matched = doc
                break

        uploaded = matched is not None
        if uploaded:
            completed += 1

        items.append({
            'key': spec['key'],
            'label': spec['label'],
            'category': spec['category'],
            'uploaded': uploaded,
            'document_id': matched.id if matched else None,
            'document_title': matched.title if matched else None,
            'uploaded_at': (
                matched.uploaded_at.isoformat() if matched else None
            ),
        })

    total = len(ONBOARDING_CHECKLIST)
    percent = round((completed / total) * 100, 1) if total else 0.0
    missing = [row['label'] for row in items if not row['uploaded']]

    return {
        'items': items,
        'completed_count': completed,
        'total_count': total,
        'completion_percent': percent,
        'missing_documents': missing,
        'is_complete': completed == total and total > 0,
    }


def sync_onboarding_document_status(onboarding):
    """Update onboarding.documents_submitted from checklist completion."""

    if onboarding is None:
        return None

    checklist = compute_document_checklist(onboarding.employee)
    is_complete = checklist['is_complete']

    if onboarding.documents_submitted != is_complete:
        onboarding.documents_submitted = is_complete
        if is_complete and onboarding.status == 'PENDING':
            onboarding.status = 'IN_PROGRESS'
        onboarding.save(update_fields=['documents_submitted', 'status', 'updated_at'])

    return checklist
