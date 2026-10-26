from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
import os
from modules.admin_panel.models import Document, Company, AuditTrail


@login_required
def document_list_view(request):
    doc_type = request.GET.get('type', '').strip()
    status = request.GET.get('status', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Document.objects.select_related('company', 'uploaded_by').all().order_by('-uploaded_at')
    if doc_type and doc_type != 'all':
        qs = qs.filter(document_type=doc_type)
    if status and status != 'all':
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/documents/list.html', {
        'page_obj': page_obj,
        'doc_types': Document.DOC_TYPES,
        'status_choices': Document.STATUS_CHOICES,
        'selected_type': doc_type,
        'selected_status': status,
        'total_count': paginator.count
    })


@login_required
def document_upload_view(request):
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
            uploaded_by=request.user,
            file_size=file_obj.size,
            file_format=ext,
            notes=notes,
            status='PENDING'
        )

        AuditTrail.objects.create(
            record_type='DOCUMENT',
            record_id=str(doc.document_id),
            action='UPLOAD',
            new_value=doc.title,
            user_role=request.user.role,
            notes=f"Uploaded {doc.get_document_type_display()} ({doc.file_size} bytes)",
            timestamp=timezone.now().isoformat()
        )

        messages.success(request, f"Document '{doc.title}' uploaded successfully.")
        return redirect('admin_documents:list')

    companies = Company.objects.order_by('company_name')[:100]
    return render(request, 'admin/documents/upload.html', {
        'doc_types': Document.DOC_TYPES,
        'companies': companies
    })


@login_required
def document_action_view(request, document_id):
    doc = get_object_or_404(Document, document_id=document_id)
    action = request.POST.get('action') # 'VERIFY' or 'REJECT'
    notes = request.POST.get('notes', '')

    if action == 'VERIFY':
        doc.status = 'VERIFIED'
        doc.verified_at = timezone.now()
        doc.notes = f"{doc.notes or ''} [Verified: {notes}]".strip()
        doc.save()
        messages.success(request, f"Document '{doc.title}' verified.")
    elif action == 'REJECT':
        doc.status = 'REJECTED'
        doc.notes = f"{doc.notes or ''} [Rejected: {notes}]".strip()
        doc.save()
        messages.warning(request, f"Document '{doc.title}' marked as rejected.")

    AuditTrail.objects.create(
        record_type='DOCUMENT',
        record_id=str(doc.document_id),
        action=f"STATUS_{action}",
        previous_value='PENDING',
        new_value=doc.status,
        user_role=request.user.role,
        notes=notes,
        timestamp=timezone.now().isoformat()
    )

    return redirect('admin_documents:list')
