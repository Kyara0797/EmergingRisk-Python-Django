from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import forms
from django.views.generic import DetailView


from .models import Category, Theme, Event, Source, UserAccessLog
from .forms import ThemeForm, EventForm, SourceForm, RegisterForm

import json

from .models import (
    LINE_OF_BUSINESS_CHOICES,
    RISK_TAXONOMY_LV1,
    RISK_TAXONOMY_LV2,
    RISK_TAXONOMY_LV3,
    STATUS_CHOICES
)
from django.http.response import HttpResponse, HttpResponseForbidden,\
    HttpResponseRedirect
from django.views.decorators.http import require_GET
import os

def _taxonomy_label_lists(event):
    # map de LV1: lista de tuplas -> dict
    lv1_map = dict(RISK_TAXONOMY_LV1)

    # map de LV2/LV3: dicts aplanados
    lv2_map = {}
    for items in RISK_TAXONOMY_LV2.values():
        for val, label in items:
            lv2_map[val] = label

    lv3_map = {}
    for items in RISK_TAXONOMY_LV3.values():
        for val, label in items:
            lv3_map[val] = label

    lv1_labels = [lv1_map.get(v, v) for v in (event.risk_taxonomy_lv1 or [])]
    lv2_labels = [lv2_map.get(v, v) for v in (event.risk_taxonomy_lv2 or [])]
    lv3_labels = [lv3_map.get(v, v) for v in (event.risk_taxonomy_lv3 or [])]
    return lv1_labels, lv2_labels, lv3_labels

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
    events = theme.events.all()
    return render(request, 'tracker/theme_detail.html', {
        'theme': theme,
        'events': events
    })

@login_required
def add_theme(request):
    if request.method == 'POST':
        form = ThemeForm(request.POST)
        if form.is_valid():
            theme = form.save(commit=False)
            theme.created_by = request.user
            theme.save()
            messages.success(request, "Theme created successfully")
            return redirect('view_theme', pk=theme.pk)
    else:
        form = ThemeForm()
    return render(request, 'tracker/add_theme.html', {'form': form})

@login_required
def add_event(request, theme_id=None):
    
    theme = get_object_or_404(Theme, pk=theme_id) if theme_id else None
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            
            
            if theme:
                event.theme = theme
            
           
            event.save()
            
            
            form.save_m2m()
            
           
            messages.success(request, "Event created successfully!")
            
            
            return redirect('event_detail', pk=event.pk)
        
        
    else:
        
        initial = {'theme': theme} if theme else {}
        form = EventForm(initial=initial)
    
    return render(request, 'tracker/event_edit.html', {
        'form': form,
        'theme': theme,
        'creating': True
    })
    
@login_required
def add_event_redirect(request):
    # Intenta obtener el último theme visto
    last_theme_id = request.session.get('last_viewed_theme')
    if last_theme_id:
        try:
            theme = Theme.objects.get(pk=last_theme_id)
            return redirect('add_event', theme_pk=theme.pk)
        except Theme.DoesNotExist:
            pass
    
    # Si no hay último theme, usa el primero disponible
    first_theme = Theme.objects.first()
    if first_theme:
        return redirect('add_event', theme_pk=first_theme.pk)
    
    # Si no hay themes, redirige a crear uno nuevo
    messages.warning(request, "Please create a Theme first")
    return redirect('add_theme')

@login_required
def add_source(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)
    
    if request.method == 'POST':
        form = SourceForm(request.POST, request.FILES)
        if form.is_valid():
            source = form.save(commit=False)
            source.event = event  
            source.created_by = request.user
            source.save()
            
            messages.success(request, f"Source '{source.name}' added successfully!")
            return redirect('view_event', event_id=event.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        
        form = SourceForm(initial={'event': event})
    
    return render(request, 'tracker/add_source.html', {
        'form': form,
        'event': event
    })

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
def view_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    show_archived = request.GET.get('show_archived') == '1'
    sources = event.sources.all()
    if not show_archived:
        sources = sources.filter(is_active=True)

    source_type = request.GET.get('source_type')
    if source_type:
        sources = sources.filter(source_type=source_type)

    lv1_labels, lv2_labels, lv3_labels = _taxonomy_label_lists(event)

    return render(request, 'tracker/event_detail.html', {
        'event': event,
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
        'risk_lv1_labels': lv1_labels,
        'risk_lv2_labels': lv2_labels,
        'risk_lv3_labels': lv3_labels,
    })
    
class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = 'tracker/event_confirm_delete.html'
    success_url = reverse_lazy('dashboard')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Event deleted successfully")
        return super().delete(request, *args, **kwargs)
    
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

@login_required
@user_passes_test(lambda u: u.is_superuser)
def access_logs(request):
    logs = UserAccessLog.objects.all().order_by('-login_time')[:100]
    return render(request, 'tracker/access_logs.html', {'logs': logs})

def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out")
    return redirect('login')

class ThemeUpdateView(LoginRequiredMixin, UpdateView):
    model = Theme
    form_class = ThemeForm
    template_name = 'tracker/theme_edit.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Theme updated successfully")
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
            messages.error(request, "Cannot delete: Theme has associated events")
            return redirect('view_theme', pk=self.object.pk)
        
        messages.success(request, "Theme deleted successfully")
        return super().delete(request, *args, **kwargs)

class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'tracker/event_edit.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Event updated successfully")
        return response
    
    def get_success_url(self):
        return reverse_lazy('view_event', kwargs={'event_id': self.object.id})



class SourceUpdateView(LoginRequiredMixin, UpdateView):
    model = Source
    form_class = SourceForm
    template_name = 'tracker/source_edit.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
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

        # Etiquetas LV1–LV3
        lv1_labels, lv2_labels, lv3_labels = _taxonomy_label_lists(event)

        # Parámetros de filtro
        source_type = self.request.GET.get('source_type')
        show_archived = self.request.GET.get('show_archived') == '1'

        # Sources: por defecto solo activos
        sources = event.sources.all()
        if not show_archived:
            sources = sources.filter(is_active=True)
        if source_type:
            sources = sources.filter(source_type=source_type)

        ctx.update({
            'risk_lv1_labels': lv1_labels,
            'risk_lv2_labels': lv2_labels,
            'risk_lv3_labels': lv3_labels,

            'sources': sources,
            'source_types': Source.SOURCE_TYPE_CHOICES,
            'selected_source_type': source_type,
            'show_archived': show_archived,  # para checkbox "Show archived"

            # opcional si usas badge de color
            'risk_colors': {
                'LOW': 'success',
                'MEDIUM': 'warning',
                'HIGH': 'danger',
                'CRITICAL': 'dark',
            },
        })
        return ctx


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
def add_source_redirect(request):
    
    last_event_id = request.session.get('last_viewed_event')
    if last_event_id:
        event = Event.objects.filter(pk=last_event_id).first()
        if event:
            return redirect('add_source', event_pk=event.pk)
    
    first_event = Event.objects.first()
    if first_event:
        return redirect('add_source', event_pk=first_event.pk)
    
    messages.warning(request, "Please create an Event first")
    return redirect('dashboard')

@login_required
def theme_list_by_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    themes = Theme.objects.filter(category=category).order_by('name')
    return render(request, 'tracker/theme_list.html', {
        'category': category,
        'themes': themes
    })
    
@login_required
def theme_detail(request, pk):
    theme = get_object_or_404(Theme, pk=pk)
    return render(request, 'tracker/theme_detail.html', {'theme': theme})


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    sources = event.sources.all()

    lv1_labels, lv2_labels, lv3_labels = _taxonomy_label_lists(event)

    return render(request, 'tracker/event_detail.html', {
        'event': event,
        'sources': sources,
        'risk_lv1_labels': lv1_labels,
        'risk_lv2_labels': lv2_labels,
        'risk_lv3_labels': lv3_labels,
    })
    

@login_required
def source_detail(request, pk):
    source = get_object_or_404(Source, pk=pk)
    is_pdf = False
    if source.file_upload:
        ext = source.file_upload.name.lower().rsplit('.', 1)[-1]
        is_pdf = (ext == 'pdf') 
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
    
@login_required
def edit_event(request, pk=None, theme_pk=None):
    if pk:  
        event = get_object_or_404(Event, pk=pk)
        theme = event.theme
    else:  
        theme = get_object_or_404(Theme, pk=theme_pk)
        event = Event(theme=theme, created_by=request.user)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            
            # Save JSON fields manually
            event.impacted_lines = request.POST.getlist('impacted_lines')
            event.risk_taxonomy_lv1 = request.POST.getlist('risk_taxonomy_lv1')
            event.risk_taxonomy_lv2 = request.POST.getlist('risk_taxonomy_lv2')
            event.risk_taxonomy_lv3 = request.POST.getlist('risk_taxonomy_lv3')
            
            event.save()
            messages.success(request, "Event saved successfully!")
            return redirect('view_event', event_id=event.id)
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = EventForm(instance=event, initial_theme=theme)
    
    # Prepare hierarchical taxonomy data
    hierarchical_taxonomy = []
    for lv1 in RISK_TAXONOMY_LV1:
        lv1_key, lv1_label = lv1[0], lv1[1]
        lv1_entry = {
            'key': lv1_key,
            'label': lv1_label,
            'selected': lv1_key in (form.initial.get('risk_taxonomy_lv1') or []),
            'children': []
        }
        
        # Add LV2 children
        for lv2 in RISK_TAXONOMY_LV2.get(lv1_key, []):
            lv2_key, lv2_label = lv2[0], lv2[1]
            lv2_entry = {
                'key': lv2_key,
                'label': lv2_label,
                'selected': lv2_key in (form.initial.get('risk_taxonomy_lv2') or []),
                'children': []
            }
            
            # Add LV3 children
            for lv3 in RISK_TAXONOMY_LV3.get(lv2_key, []):
                lv3_key, lv3_label = lv3[0], lv3[1]
                lv2_entry['children'].append({
                    'key': lv3_key,
                    'label': lv3_label,
                    'selected': lv3_key in (form.initial.get('risk_taxonomy_lv3') or [])
                })
            
            lv1_entry['children'].append(lv2_entry)
        
        hierarchical_taxonomy.append(lv1_entry)
    
    return render(request, 'tracker/event_edit.html', {
        'form': form,
        'event': event,
        'theme': theme,
        'creating': pk is None,
        'RISK_TAXONOMY_LV1': RISK_TAXONOMY_LV1,
        'RISK_TAXONOMY_LV2': RISK_TAXONOMY_LV2,
        'RISK_TAXONOMY_LV3': RISK_TAXONOMY_LV3,
        'HIERARCHICAL_TAXONOMY': hierarchical_taxonomy,
        'taxonomy_json': json.dumps({
            'flat': {
                'lv1': RISK_TAXONOMY_LV1,
                'lv2': RISK_TAXONOMY_LV2,
                'lv3': RISK_TAXONOMY_LV3
            },
            'hierarchical': hierarchical_taxonomy
        })
    })
    
def _check_token(request):
    token = request.GET.get("token")
    expected = os.getenv("ONEOFF_TOKEN")
    return expected and token == expected

@require_GET
def oneoff_reset_superuser(request):
    if not _check_token(request):
        return HttpResponseForbidden("forbidden")

    User = get_user_model()
    username = os.getenv("RESET_USER", "admin")
    email    = os.getenv("RESET_EMAIL", "admin@example.com")
    password = os.getenv("RESET_PASS", "root1234")

    if not password:
        return HttpResponse("missing RESET_PASS", status=400)

    u, created = User.objects.get_or_create(
        username=username, defaults={"email": email}
    )
    u.is_staff = True
    u.is_superuser = True
    u.email = email
    u.set_password(password)
    u.save()

    total = User.objects.count()
    users = list(User.objects.values_list("username", flat=True))
    msg = ("created" if created else "updated") + f" superuser {u.username}"
    return HttpResponse(f"{msg}\nusers={total}\n{users}", content_type="text/plain")

@require_GET
def oneoff_autologin_admin(request):
    """
    Inicia sesión como el superuser y redirige al /admin sin pasar por el formulario.
    Solo si el token es válido.
    """
    if not _check_token(request):
        return HttpResponseForbidden("forbidden")

    User = get_user_model()
    username = os.getenv("RESET_USER", "admin")
    try:
        u = User.objects.get(username=username)
    except User.DoesNotExist:
        return HttpResponse("superuser not found; call /oneoff-reset/ first", status=404)

    # Fuerza backend por defecto y crea sesión
    u.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, u)
    return HttpResponseRedirect("/admin/")