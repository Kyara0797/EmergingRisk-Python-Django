from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import date, datetime, time
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from urllib.parse import urlparse
from django.contrib.auth import get_user_model, authenticate
from .models import Source
from urllib.parse import urlparse

ALLOWED_FILE_EXTS = {'.pdf', '.doc', '.docx'}


from .models import (
    Category,
    Theme, 
    Event, 
    Source,
    LINE_OF_BUSINESS_CHOICES,
    RISK_TAXONOMY_LV1,
    RISK_TAXONOMY_LV2,
    RISK_TAXONOMY_LV3,
    STATUS_CHOICES,
    POTENTIAL_IMPACT_CHOICES
)
from config import settings
import os.path
from tracker.models import RISK_CHOICES
from django.forms.widgets import ClearableFileInput

ALLOWED_EXTS = {
    'PDF': {'.pdf'},
    'DOC': {'.doc', '.docx'},
    'EMAIL': {'.eml', '.msg'},
}



RISK_RATING_CHOICES = [
    ('LOW', 'Low'),
    ('MEDIUM', 'Medium'),
    ('HIGH', 'High'),
    ('CRITICAL', 'Critical'),
]

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'})
        }

class ThemeForm(forms.ModelForm):
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_category'
        })
    )
    
    risk_rating = forms.ChoiceField(
        choices=[('', '---------')] + list(RISK_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select risk-rating-select'}),
        required=True
    )
    class Meta:
        model = Theme
        fields = ['category', 'name', 'risk_rating', 'onset_timeline']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'risk_rating': forms.Select(attrs={'class': 'form-control'}),
            'onset_timeline': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    
    
class EventForm(forms.ModelForm):
    name = forms.CharField(
        min_length=3,
    max_length=30,
    widget=forms.TextInput(attrs={
        'placeholder': 'Enter event name (3–30 characters)',
        'class': 'form-control title-input'
    }),
    required=True,
    error_messages={
        'required': 'The name is required.',
        'min_length': 'Minimum 3 characters.',
        'max_length': 'Maximum 30 characters.'  
    }
    )
    
    theme = forms.ModelChoiceField(
        queryset=Theme.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    date_identified = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            },
            format='%Y-%m-%d',
        ),
        input_formats=['%Y-%m-%d'],
        label="Date Identified",
        help_text="Pick a date (today or past).",
        error_messages={
            "required": "Please select a date.",
            "invalid": "Enter a valid date.",
        },
    )
    
    risk_rating = forms.ChoiceField(
        choices=[('', '---------')] + Event.RISK_RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select risk-rating-select'}),
        required=True
    )
    
    status = forms.ChoiceField(
    choices=[('', '---------')] + list(Event.STATUS_CHOICES),
    widget=forms.Select(attrs={'class': 'form-control status-select'}),
    required=True
    )
    
    control_in_place = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input switch'})
    )
    
    impacted_lines = forms.MultipleChoiceField(
        choices=LINE_OF_BUSINESS_CHOICES,   # ⬅️ respetar el orden definido
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'business-lines'}),
        label="Impacted Business Lines",
        required=True
    )
    
    risk_taxonomy_lv1 = forms.MultipleChoiceField(
        choices=RISK_TAXONOMY_LV1,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'taxonomy-lv1'}),
        label="Risk Taxonomy Level 1",
        required=True
    )
    
    risk_taxonomy_lv2 = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'taxonomy-lv2'}),
        label="Risk Taxonomy Level 2",
        required=True
    )
    
    risk_taxonomy_lv3 = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'taxonomy-lv3'}),
        label="Risk Taxonomy Level 3",
        required=True
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Add a description to the event',
            'class': 'form-control full-width'
        }),
        required=True
    )

    class Meta:
        model = Event
        fields = [
            'theme', 'name', 'date_identified', 'description',
            'impacted_lines', 'risk_taxonomy_lv1', 'risk_taxonomy_lv2',
            'risk_taxonomy_lv3', 'status', 'control_in_place', 'risk_rating',
        ]

    def _valid_lv2_from(self, lv1_list):
        choices = []
        for lv1 in (lv1_list or []):
            choices.extend(RISK_TAXONOMY_LV2.get(lv1, []))
        seen, result = set(), []
        for val, label in choices:
            if val not in seen:
                seen.add(val)
                result.append((val, label))
        return result

    def _valid_lv3_from(self, lv2_list):
        choices = []
        for lv2 in (lv2_list or []):
            choices.extend(RISK_TAXONOMY_LV3.get(lv2, []))
        seen, result = set(), []
        for val, label in choices:
            if val not in seen:
                seen.add(val)
                result.append((val, label))
        return result
    # -----------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        initial_theme = kwargs.pop('initial_theme', None)
        super().__init__(*args, **kwargs)
        
        if initial_theme:
            self.initial['theme'] = initial_theme
            self.fields['theme'].widget = forms.HiddenInput()
        
        if initial_theme and not self.instance.pk:
            self.initial['risk_rating'] = initial_theme.risk_rating

        if self.is_bound:
            lv1_selected = self.data.getlist('risk_taxonomy_lv1')
            self.fields['risk_taxonomy_lv2'].choices = self._valid_lv2_from(lv1_selected)

            lv2_selected = self.data.getlist('risk_taxonomy_lv2')
            self.fields['risk_taxonomy_lv3'].choices = self._valid_lv3_from(lv2_selected)
        else:
            lv1_initial = self.initial.get('risk_taxonomy_lv1', [])
            self.fields['risk_taxonomy_lv2'].choices = self._valid_lv2_from(lv1_initial)

            lv2_initial = self.initial.get('risk_taxonomy_lv2', [])
            self.fields['risk_taxonomy_lv3'].choices = self._valid_lv3_from(lv2_initial)

    def clean(self):
        cleaned_data = super().clean()
        lv1 = cleaned_data.get('risk_taxonomy_lv1', [])
        lv2 = cleaned_data.get('risk_taxonomy_lv2', [])
        lv3 = cleaned_data.get('risk_taxonomy_lv3', [])
        
        # Enhanced hierarchical validation
        self.validate_taxonomy_hierarchy(lv1, lv2, lv3)
        
        # Handle "All" selection for impacted lines
        impacted_lines = list(dict.fromkeys(cleaned_data.get('impacted_lines', [])))
    
        if 'All' in impacted_lines:
            selected = [value for value, _ in LINE_OF_BUSINESS_CHOICES
                if value not in {'All', 'Evaluation in progress'}]
        else:
            # quitar "All" si vino mezclado
            selected = [v for v in impacted_lines if v != 'All']

        # mantener el orden declarativo de LINE_OF_BUSINESS_CHOICES
        ordered_selected = [value for value, _ in LINE_OF_BUSINESS_CHOICES if value in selected]
        cleaned_data['impacted_lines'] = ordered_selected
        # --------------------------------------------------------------------

        return cleaned_data
    
    def validate_taxonomy_hierarchy(self, lv1, lv2, lv3):
        """Validate the taxonomy hierarchy with proper error messages"""
        if not lv1:
            self.add_error('risk_taxonomy_lv1', "Select at least one Level 1 option")
            return
        
        # Validate Level 2
        valid_lv2 = []
        invalid_lv2 = []
        
        for lv1_item in lv1:
            if lv1_item in RISK_TAXONOMY_LV2:
                valid_lv2.extend([choice[0] for choice in RISK_TAXONOMY_LV2[lv1_item]])
        
        for item in lv2:
            if item not in valid_lv2:
                invalid_lv2.append(item)
        
        if invalid_lv2:
            self.add_error('risk_taxonomy_lv2', 
                           f"Invalid Level 2 options: {', '.join(invalid_lv2)}. "
                           f"Valid options for selected Level 1: {', '.join(valid_lv2)}")
        
        # Validate Level 3 if Level 2 is valid
        if not invalid_lv2 and lv2:
            valid_lv3 = []
            invalid_lv3 = []
            
            for lv2_item in lv2:
                if lv2_item in RISK_TAXONOMY_LV3:
                    valid_lv3.extend([choice[0] for choice in RISK_TAXONOMY_LV3[lv2_item]])
            
            for item in lv3:
                if item not in valid_lv3:
                    invalid_lv3.append(item)
            
            if invalid_lv3:
                self.add_error('risk_taxonomy_lv3', 
                               f"Invalid Level 3 options: {', '.join(invalid_lv3)}. "
                               f"Valid options for selected Level 2: {', '.join(valid_lv3)}")

    def get_valid_lv2_choices(self):
        lv1_selections = self.initial.get('risk_taxonomy_lv1', [])
        return self._valid_lv2_from(lv1_selections)

    def get_valid_lv3_choices(self):
        lv2_selections = self.initial.get('risk_taxonomy_lv2', [])
        return self._valid_lv3_from(lv2_selections)

    def clean_date_identified(self):
        d = self.cleaned_data.get("date_identified")
        if not d:
            return d
        from datetime import datetime, time
        naive_dt = datetime.combine(d, time.min)
        aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        if aware_dt.date() > timezone.localdate():
            raise forms.ValidationError("Date must be today or in the past.")
        return aware_dt

_URL_VALIDATOR = URLValidator(schemes=["http", "https"])

def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def clean_name(self):
    v = (self.cleaned_data.get('name') or '').strip()
    if len(v) < 3:
        raise forms.ValidationError('The name is required (3–30 characters, not just spaces).')
    return v

class MultiFileInput(forms.ClearableFileInput):
    """File input con multiple=True (para extra_files, no para file_upload del modelo)."""
    allow_multiple_selected = True


class SourceForm(forms.ModelForm):
    # Campo visible como fecha (tu lógica actual se conserva)
    source_date = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Select a date",
                "id": "id_source_date",
            },
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
        label="Source date",
        help_text="Pick a date (today or past).",
        error_messages={
            "required": "Please select a date.",
            "invalid": "Enter a valid date.",
        },
    )

    # Mantenemos source_type en el form pero oculto; lo calculamos en clean()
    source_type = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Source
        fields = [
            "event",
            "name",
            "source_date",
            "link_or_file",
            "file_upload",
            "summary",
            "source_type",              # <- permanece en fields
            "potential_impact",
            "potential_impact_notes",
        ]
        widgets = {
            "event": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 30}),
            "link_or_file": forms.URLInput(attrs={"class": "form-control", "id": "id_link_or_file"}),
            "summary": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "potential_impact_notes": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = getattr(self, "instance", None)
        if inst and getattr(inst, "pk", None) and getattr(inst, "source_date", None):
            sd = inst.source_date
           
            if isinstance(sd, datetime):
                try:
                    sd = timezone.localtime(sd).date()
                except Exception:
                    sd = sd.date()
            
            self.initial["source_date"] = sd.strftime("%Y-%m-%d")

    def clean_link_or_file(self):
        val = (self.cleaned_data.get("link_or_file") or "").strip()
        if not val:
            return val  # vacío permitido

        if val.lower().startswith("mailto:"):
            if "@" not in val[7:]:
                raise forms.ValidationError("Enter a valid mailto: address.")
            return val

        u = urlparse(val)
        if u.scheme not in ("http", "https") or not u.netloc:
            raise forms.ValidationError("Enter a valid URL (http/https) or a mailto: address.")
        return val

    def clean_source_date(self):
        d = self.cleaned_data.get("source_date")
        if not d:
            return d
        
        if isinstance(d, datetime):
            d = d.date()
        if d > timezone.localdate():
            raise forms.ValidationError("Date must be today or in the past.")
        return d  

    def clean(self):
        cleaned = super().clean()

        # Señales de lo que el usuario adjuntó
        has_main_link = bool((cleaned.get("link_or_file") or "").strip())
        has_main_file = bool(cleaned.get("file_upload"))

        # Archivos adicionales que vienen por request.FILES (name="extra_files")
        extra_files = []
        if hasattr(self.files, "getlist"):
            try:
                extra_files = self.files.getlist("extra_files")
            except Exception:
                extra_files = []

        has_any_file = has_main_file or bool(extra_files)

        # Inferencia de tipo sin forzar validaciones adicionales
        if has_main_link and has_any_file:
            st = "MIXED"
        elif has_main_link:
            st = "LINK"
        elif has_any_file:
            st = "FILE"
        else:
            st = ""  
        cleaned["source_type"] = st
        return cleaned
    
User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Choose a username",
                "autocomplete": "username",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # password1/password2 NO son campos de modelo, por eso se estilan aquí
        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Repeat your password",
            "autocomplete": "new-password",
        })

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Permite loguear con email o username usando solo ModelBackend."""
    def clean(self):
        cd = super().clean()
        username = cd.get("username")
        if username and "@" in username:
            U = get_user_model()
            try:
                user = U.objects.get(email__iexact=username)
                # traducir email -> username real (lo que espera el backend por defecto)
                self.cleaned_data["username"] = user.username
            except U.DoesNotExist:
                # dejar el valor; fallará como credenciales inválidas normales
                pass
        return cd