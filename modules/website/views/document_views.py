from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import os
from modules.admin_panel.models import Document, Company, AuditTrail


def public_document_upload_view(request):
    """Allows public NGOs or partners to submit grant proposals or verification documents."""
    if request.method == 'POST' and request.FILES.get('file'):
        file_obj = request.FILES['file']
        title = request.POST.get('title', '').strip() or file_obj.name
        doc_type = request.POST.get('document_type', 'CSR_PROPOSAL')
        company_id = request.POST.get('company_id', '').strip()
        notes = request.POST.get('notes', '').strip()

        company = Company.objects.filter(company_id=company_id).first() if company_id else None
        ext = os.path.splitext(file_obj.name)[1].lower().replace('.', '')

        doc = Document.objects.create(
            title=title,
            document_type=doc_type,
            file=file_obj,
            company=company,
            uploaded_by=request.user if request.user.is_authenticated else None,
            file_size=file_obj.size,
            file_format=ext,
            notes=notes,
            status='PENDING'
        )

        AuditTrail.objects.create(
            record_type='DOCUMENT',
            record_id=str(doc.document_id),
            action='PUBLIC_UPLOAD',
            new_value=doc.title,
            user_role='Public / NGO',
            notes=f"Public proposal/document upload: {doc.title}",
            timestamp=timezone.now().isoformat()
        )

        messages.success(request, f"Document '{doc.title}' uploaded successfully! It is queued for audit review.")
        return redirect('website:home')

    companies = Company.objects.order_by('company_name')[:100]
    return render(request, 'website/document_upload.html', {
        'doc_types': Document.DOC_TYPES,
        'companies': companies
    })
