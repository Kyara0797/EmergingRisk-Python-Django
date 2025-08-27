from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import forms
from django.views.generic import DetailView
from django.db import transaction

from .models import Category, Theme, Event, Source, UserAccessLog
from .forms import ThemeForm, EventForm, SourceForm, RegisterForm

import json

from .models import (
    LINE_OF_BUSINESS_CHOICES,
    RISK_TAXONOMY_LV1,
    RISK_TAXONOMY_LV2,
    RISK_TAXONOMY_LV3,
    STATUS_CHOICES,
)

# =========================
# Helpers generales
# =========================

def _taxonomy_label_lists(event):
    # LV1: lista de tuplas -> dict
    lv1_map = dict(RISK_TAXONOMY_LV1)

    # LV2/LV3: dicts aplanados
    lv2_map = {val: label for items in RISK_TAXONOMY_LV2.values() for val, label in items}
    lv3_map = {val: label for items in RISK_TAXONOMY_LV3.values() for val, label in items}

    lv1_labels = [lv1_map.get(v, v) for v in (event.risk_taxonomy_lv1 or [])]
    lv2_labels = [lv2_map.get(v, v) for v in (event.risk_taxonomy_lv2 or [])]
    lv3_labels = [lv3_map.get(v, v) for v in (event.risk_taxonomy_lv3 or [])]
    return lv1_labels, lv2_labels, lv3_labels


def _resolve_theme_from_request(request, theme_id=None, theme_pk=None):
    
    candidates = [
        theme_id,
        theme_pk,
        request.GET.get("theme_id"),
        request.GET.get("theme_pk"),
        request.GET.get("theme"),
    ]
    for val in candidates:
        if val:
            try:
                return get_object_or_404(Theme, pk=int(val))
            except (ValueError, TypeError):
                continue
    return None


def _prefill_event_initial(request, theme):
   
    initial = {
        "theme": theme.pk if theme else None,
        "risk_rating": request.GET.get("risk_rating") or request.GET.get("risk") or "LOW",
    }
    if request.GET.get("name"):
        initial["name"] = request.GET.get("name")
    if request.GET.get("date_identified") or request.GET.get("date"):
        initial["date_identified"] = request.GET.get("date_identified") or request.GET.get("date")
    return initial


def build_taxonomy_json(selected_lv1=None, selected_lv2=None, selected_lv3=None):
    """
    Construye JSON jerárquico a partir de las constantes y marca 'selected' donde corresponda.

    Retorna:
    {
      "flat": {"lv1":..., "lv2":..., "lv3":...},
      "hierarchical": [
        {key,label,selected?, children:[
          {key,label,selected?, children:[
            {key,label,selected?}
          ]}
        ]}
      ]
    }
    """
    sel_lv1 = set(selected_lv1 or [])
    sel_lv2 = set(selected_lv2 or [])
    sel_lv3 = set(selected_lv3 or [])

    hierarchical = []
    for lv1_key, lv1_label in RISK_TAXONOMY_LV1:
        lv1_node = {
            "key": lv1_key,
            "label": lv1_label,
            "selected": lv1_key in sel_lv1,
            "children": [],
        }
        for lv2_key, lv2_label in RISK_TAXONOMY_LV2.get(lv1_key, []):
            lv2_node = {
                "key": lv2_key,
                "label": lv2_label,
                "selected": lv2_key in sel_lv2,
                "children": [],
            }
            for lv3_key, lv3_label in RISK_TAXONOMY_LV3.get(lv2_key, []):
                lv3_node = {
                    "key": lv3_key,
                    "label": lv3_label,
                    "selected": lv3_key in sel_lv3,
                }
                lv2_node["children"].append(lv3_node)
            lv1_node["children"].append(lv2_node)
        hierarchical.append(lv1_node)

    return {
        "flat": {"lv1": RISK_TAXONOMY_LV1, "lv2": RISK_TAXONOMY_LV2, "lv3": RISK_TAXONOMY_LV3},
        "hierarchical": hierarchical,
    }


def _selected_lists_from_event_or_initial(event, form_initial):
    """
    Devuelve (lv1, lv2, lv3) para pintar selección en el árbol
    usando el evento (si existe) o el initial del form.
    """
    lv1 = (form_initial.get("risk_taxonomy_lv1") or (getattr(event, "risk_taxonomy_lv1", None) or []))
    lv2 = (form_initial.get("risk_taxonomy_lv2") or (getattr(event, "risk_taxonomy_lv2", None) or []))
    lv3 = (form_initial.get("risk_taxonomy_lv3") or (getattr(event, "risk_taxonomy_lv3", None) or []))
    return lv1, lv2, lv3


# =========================
# Dashboard / Threads
# =========================

@login_required
def dashboard(request):
    categories = Category.objects.all()
    themes = Theme.objects.all().order_by('-created_at')[:5]
    events = Event.objects.all().order_by('-date_identified')[:5]
    return render(request, 'tracker/dashboard.html', {
        'categories': categories,
        'themes': themes,
        'events': events
    })


@login_required
def theme_list_all(request):
    themes = Theme.objects.all().order_by('name')

    search_query = request.GET.get('q')
    if search_query:
        themes = themes.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    paginator = Paginator(themes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tracker/theme_list.html', {
        'themes': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'search_query': search_query or ''
    })


@login_required
def theme_list(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    themes = Theme.objects.filter(category=category).order_by('name')
    return render(request, 'tracker/theme_list.html', {
        'category': category,
        'themes': themes
    })


@login_required
def view_theme(request, pk):
    theme = get_object_or_404(Theme, pk=pk)
   
    request.session['last_viewed_theme'] = theme.pk
    events = theme.events.all()
    return render(request, 'tracker/theme_detail.html', {
        'theme': theme,
        'events': events
    })


@login_required
def add_theme(request):
   
    preselect_category_id = request.GET.get('category')
    initial = {}
    if preselect_category_id:
        try:
            initial['category'] = Category.objects.get(pk=preselect_category_id)
        except Category.DoesNotExist:
            pass

    if request.method == 'POST':
        form = ThemeForm(request.POST)
        if form.is_valid():
            theme = form.save(commit=False)
            theme.created_by = request.user
            theme.save()
            messages.success(request, "Theme created successfully")
            return redirect('view_theme', pk=theme.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ThemeForm(initial=initial)

    return render(request, 'tracker/add_theme.html', {'form': form})


# =========================
# Events: Add / Edit / View / Delete
# =========================

@login_required
def add_event(request, theme_id=None, theme_pk=None):
    
    theme = _resolve_theme_from_request(request, theme_id=theme_id, theme_pk=theme_pk)

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            if theme:
                event.theme = theme

            # Guardar JSON/list fields desde POST (coherente con edit)
            event.impacted_lines = form.cleaned_data["impacted_lines"]
            event.risk_taxonomy_lv1 = request.POST.getlist("risk_taxonomy_lv1")
            event.risk_taxonomy_lv2 = request.POST.getlist("risk_taxonomy_lv2")
            event.risk_taxonomy_lv3 = request.POST.getlist("risk_taxonomy_lv3")

            event.save()
            messages.success(request, "Event created successfully")
            return redirect("view_event", event_id=event.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EventForm(initial=_prefill_event_initial(request, theme))

    # Selección para pintar árbol
    sel_lv1, sel_lv2, sel_lv3 = _selected_lists_from_event_or_initial(None, form.initial)
    taxonomy_json = json.dumps(build_taxonomy_json(sel_lv1, sel_lv2, sel_lv3), ensure_ascii=False)

    return render(
        request,
        "tracker/event_edit.html",
        {
            "creating": True,
            "theme": theme,
            "form": form,
            "RISK_TAXONOMY_LV1": RISK_TAXONOMY_LV1,  # LV1 directo en template
            "taxonomy_json": taxonomy_json,          # LV2/LV3 desde JSON
        },
    )


@login_required
def edit_event(request, pk=None, theme_pk=None):
   
    if pk:
        event = get_object_or_404(Event, pk=pk)
        theme = event.theme
    else:
        theme = get_object_or_404(Theme, pk=theme_pk)
        event = Event(theme=theme, created_by=request.user)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)

            
            event.impacted_lines = form.cleaned_data["impacted_lines"]
            event.risk_taxonomy_lv1 = request.POST.getlist("risk_taxonomy_lv1")
            event.risk_taxonomy_lv2 = request.POST.getlist("risk_taxonomy_lv2")
            event.risk_taxonomy_lv3 = request.POST.getlist("risk_taxonomy_lv3")

            event.save()
            messages.success(request, "Event saved successfully!")
            return redirect("view_event", event_id=event.id)
        else:
            messages.error(request, "Please correct the errors below")
    else:
        
        form = EventForm(instance=event, initial_theme=theme) if pk is None else EventForm(instance=event)

    
    sel_lv1, sel_lv2, sel_lv3 = _selected_lists_from_event_or_initial(event, form.initial)
    taxonomy_json = json.dumps(build_taxonomy_json(sel_lv1, sel_lv2, sel_lv3), ensure_ascii=False)

    return render(
        request,
        "tracker/event_edit.html",
        {
            "form": form,
            "event": event if pk else None,
            "theme": theme,
            "creating": pk is None,
            "RISK_TAXONOMY_LV1": RISK_TAXONOMY_LV1,
            "taxonomy_json": taxonomy_json,
        },
    )


@login_required
def view_event(request, event_id):
    """
    Detalle del evento (con filtros de sources) + etiquetas LV1/LV2/LV3.
    """
    event = get_object_or_404(Event, pk=event_id)
    request.session["last_viewed_event"] = event.pk  # para add_source_redirect

    # Filtros
    show_archived = request.GET.get("show_archived") == "1"
    source_type = request.GET.get("source_type")

    sources = event.sources.all()
    if not show_archived:
        sources = sources.filter(is_active=True)
    if source_type:
        sources = sources.filter(source_type=source_type)

    lv1_labels, lv2_labels, lv3_labels = _taxonomy_label_lists(event)

    # ... después de obtener event
    impact_lobs_display = list(event.impacted_lines or [])
    if "All" in impact_lobs_display:
        impact_lobs_display = [k for k, _ in LINE_OF_BUSINESS_CHOICES if k != "All"]

    
    return render(
        request,
        "tracker/event_detail.html",
        {
            "event": event,
            "sources": sources,
            "source_types": Source.SOURCE_TYPE_CHOICES,
            "selected_source_type": source_type,
            "show_archived": show_archived,
            "risk_colors": {
                "LOW": "success",
                "MEDIUM": "warning",
                "HIGH": "danger",
                "CRITICAL": "dark",
            },
            "impact_lobs_display": impact_lobs_display,
            "risk_lv1_labels": lv1_labels,
            "risk_lv2_labels": lv2_labels,
            "risk_lv3_labels": lv3_labels,
        },
    )


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = 'tracker/event_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Event deleted successfully")
        return super().delete(request, *args, **kwargs)

@login_required
def add_source_redirect(request):
    """
    Redirección inteligente para crear Source:
    - si hay último event visto en sesión, redirige a add_source con ese event
    - si no, usa el primer event disponible
    - si no hay events, manda al dashboard con aviso
    """
    last_event_id = request.session.get('last_viewed_event')
    if last_event_id:
        from .models import Event  # evitar import circular si mueves cosas
        event = Event.objects.filter(pk=last_event_id).first()
        if event:
            return redirect('add_source', event_pk=event.pk)

    from .models import Event
    first_event = Event.objects.first()
    if first_event:
        return redirect('add_source', event_pk=first_event.pk)

    messages.warning(request, "Please create an Event first")
    return redirect('dashboard')



@login_required
def add_event_redirect(request):
    
    last_theme_id = request.session.get('last_viewed_theme')
    if last_theme_id:
        try:
            theme = Theme.objects.get(pk=last_theme_id)
            return redirect('add_event', theme_id=theme.pk) 
        except Theme.DoesNotExist:
            pass

    first_theme = Theme.objects.first()
    if first_theme:
        return redirect('add_event', theme_id=first_theme.pk)

    messages.warning(request, "Please create a Theme first")
    return redirect('add_theme')


# =========================
# Sources (Add/Update/Delete)
# =========================

@login_required
def add_source(request, event_pk):
    """
    Crea 1..N Source(s):
      - 0 o 1 por link (si se ingresa)
      - 0..N por archivos (si se suben varios)
    Reglas:
      * Summary debe ser único por Event (case-insensitive)
      * Si no hay link NI archivos -> error
    """
    event = get_object_or_404(Event, pk=event_pk)

    if request.method == 'POST':
        form = SourceForm(request.POST, request.FILES, initial={'event': event})
        if form.is_valid():
            # Summary único (servidor)
            summary = (form.cleaned_data.get('summary') or '').strip()
            if summary and Source.objects.filter(event=event, summary__iexact=summary).exists():
                form.add_error('summary', 'Summary must be different from existing ones for this event.')

            if not form.errors:
                link = (form.cleaned_data.get('link_or_file') or '').strip()
                files = request.FILES.getlist('file_upload')
                created = 0

                with transaction.atomic():
                    # 1) Link (opcional)
                    if link:
                        s = Source(
                            event=event,
                            name=form.cleaned_data['name'],
                            source_date=form.cleaned_data['source_date'],
                            summary=summary,
                            potential_impact=form.cleaned_data.get('potential_impact'),
                            potential_impact_notes=form.cleaned_data.get('potential_impact_notes'),
                            link_or_file=link,
                            created_by=request.user,
                            source_type='LINK',
                        )
                        s.save()
                        created += 1

                    # 2) Archivos (0..N)
                    if files:
                        for f in files:
                            s = Source(
                                event=event,
                                name=form.cleaned_data['name'],
                                source_date=form.cleaned_data['source_date'],
                                summary=summary,
                                potential_impact=form.cleaned_data.get('potential_impact'),
                                potential_impact_notes=form.cleaned_data.get('potential_impact_notes'),
                                file_upload=f,
                                created_by=request.user,
                                source_type='FILE',
                            )
                            s.save()
                            created += 1

                if created == 0:
                    form.add_error(None, 'Please add a link and/or at least one file.')
                else:
                    messages.success(request, f"{created} source(s) added successfully!")
                    return redirect('view_event', event_id=event.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SourceForm(initial={'event': event})

    existing_summaries = list(Source.objects.filter(event=event).values_list('summary', flat=True))
    return render(request, 'tracker/add_source.html', {
        'form': form,
        'event': event,
        'existing_summaries_json': json.dumps(existing_summaries),
    })


class SourceUpdateView(LoginRequiredMixin, UpdateView):
    model = Source
    form_class = SourceForm
    template_name = 'tracker/source_edit.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object.event
        # Summary únicos: excluir el actual
        existing = list(
            Source.objects.filter(event=event)
            .exclude(pk=self.object.pk)
            .values_list('summary', flat=True)
        )
        ctx['existing_summaries_json'] = json.dumps(existing)
        return ctx

    def form_valid(self, form):
        # Summary único (servidor)
        summary = (form.cleaned_data.get('summary') or '').strip()
        if summary and Source.objects.filter(
            event=self.object.event,
            summary__iexact=summary
        ).exclude(pk=self.object.pk).exists():
            form.add_error('summary', 'Summary must be different from existing ones for this event.')
            return self.form_invalid(form)

        # Guarda el registro principal
        response = super().form_valid(form)

        # Archivos extra (además del primero que ya tomó el form)
        files = self.request.FILES.getlist('file_upload')
        if files and len(files) > 1:
            base = self.object
            # Crear clones para los archivos extra
            with transaction.atomic():
                for f in files[1:]:
                    Source.objects.create(
                        event=base.event,
                        name=base.name,
                        source_date=base.source_date,
                        summary=base.summary,
                        potential_impact=base.potential_impact,
                        potential_impact_notes=base.potential_impact_notes,
                        file_upload=f,
                        created_by=self.request.user,
                        source_type='FILE',
                    )

        messages.success(self.request, "Source updated successfully")
        return response

    def get_success_url(self):
        return reverse_lazy('view_event', kwargs={'event_id': self.object.event.id})


class SourceDeleteView(LoginRequiredMixin, DeleteView):
    model = Source
    template_name = 'tracker/source_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, "Source deleted successfully")
        return reverse_lazy('view_event', kwargs={'event_id': self.object.event.id})


# =========================
# Auth & misceláneos
# =========================

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def access_logs(request):
    logs = UserAccessLog.objects.all().order_by('-login_time')[:100]
    return render(request, 'tracker/access_logs.html', {'logs': logs})


def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out")
    return redirect('login')


# =========================
# Theme update/delete
# =========================

class ThemeUpdateView(LoginRequiredMixin, UpdateView):
    model = Theme
    form_class = ThemeForm
    template_name = 'tracker/theme_edit.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Thread updated successfully")
        return response

    def get_success_url(self):
        return reverse_lazy('view_theme', kwargs={'pk': self.object.pk})


class ThemeDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Theme
    template_name = 'tracker/theme_confirm_delete.html'
    success_url = reverse_lazy('theme_list')

    def test_func(self):
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.events.exists():
            messages.error(request, "Cannot delete: Thread has associated events")
            return redirect('view_theme', pk=self.object.pk)

        messages.success(request, "Thread deleted successfully")
        return super().delete(request, *args, **kwargs)


# =========================
# Listados y utilidades varias
# =========================

@login_required
def event_list(request):
    events = Event.objects.select_related('theme').order_by('-date_identified')

    # búsqueda opcional (?q=...)
    q = request.GET.get('q')
    if q:
        events = events.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(theme__name__icontains=q)
        )

    # paginación
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tracker/event_list.html', {
        'events': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'search_query': q or ''
    })


@login_required
def get_themes(request):
    category_id = request.GET.get('category_id')
    themes = Theme.objects.filter(category_id=category_id).order_by('name')
    return render(request, 'tracker/theme_dropdown_options.html', {'themes': themes})


@login_required
def get_events(request):
    theme_id = request.GET.get('theme_id')
    events = Event.objects.filter(theme_id=theme_id).order_by('name')
    return render(request, 'tracker/event_dropdown_options.html', {'events': events})


# =========================
# Detail Views (CBVs) - opcionalmente usados por tus URLs
# =========================

class ThemeDetailView(LoginRequiredMixin, DetailView):
    model = Theme
    template_name = 'tracker/theme_detail.html'
    context_object_name = 'theme'


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'tracker/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object

        # Parámetros de filtro
        source_type = self.request.GET.get('source_type')
        show_archived = self.request.GET.get('show_archived') == '1'

        # Sources: por defecto solo activos
        sources = event.sources.all()
        if not show_archived:
            sources = sources.filter(is_active=True)
        if source_type:
            sources = sources.filter(source_type=source_type)

        lv1_labels, lv2_labels, lv3_labels = _taxonomy_label_lists(event)

        ctx.update({
            'risk_lv1_labels': lv1_labels,
            'risk_lv2_labels': lv2_labels,
            'risk_lv3_labels': lv3_labels,
            'sources': sources,
            'source_types': Source.SOURCE_TYPE_CHOICES,
            'selected_source_type': source_type,
            'show_archived': show_archived,
            'risk_colors': {
                'LOW': 'success',
                'MEDIUM': 'warning',
                'HIGH': 'danger',
                'CRITICAL': 'dark',
            },
        })
        return ctx


# (Opcional) Mantener compatibilidad con URLs antiguas que apunten a event_detail (función)
@login_required
def event_detail(request, pk):
    # Reusa la misma lógica del detalle unificado
    return view_event(request, event_id=pk)

@login_required
def theme_list_by_category(request, category_id):
    # Alias para mantener compatibilidad con la URL vieja
    return theme_list(request, category_id)


@login_required
def source_detail(request, pk):
    source = get_object_or_404(Source, pk=pk)
    is_pdf = False
    if source.file_upload:
        try:
            ext = source.file_upload.name.lower().rsplit('.', 1)[-1]
            is_pdf = (ext == 'pdf')
        except Exception:
            is_pdf = False

    return render(request, 'tracker/source_detail.html', {
        'source': source,
        'is_pdf': is_pdf,
    })
    

@login_required
def toggle_source_active(request, pk):
    source = get_object_or_404(Source, pk=pk)
    source.is_active = not source.is_active
    source.save(update_fields=['is_active'])
    if source.is_active:
        messages.success(request, "Source restored.")
    else:
        messages.info(request, "Source archived.")
    return redirect('source_detail', pk=source.pk)