from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe


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
        max_length=30,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter event name (max 30 characters)',
            'class': 'form-control title-input'
        }),
        required=True
    )
    
    theme = forms.ModelChoiceField(
        queryset=Theme.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    date_identified = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
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
        choices=sorted(LINE_OF_BUSINESS_CHOICES, key=lambda x: x[1]),
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

    # ----------------- Helpers internos para armar choices válidos -----------------
    def _valid_lv2_from(self, lv1_list):
        """Returna choices válidos de LV2 según LV1 seleccionado, sin duplicados."""
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
        """Returna choices válidos de LV3 según LV2 seleccionado, sin duplicados."""
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
        
        # Set initial risk rating from theme if creating new event
        if initial_theme and not self.instance.pk:
            self.initial['risk_rating'] = initial_theme.risk_rating

        # --- POBLADO DINÁMICO DE CHOICES (clave para que Django valide correctamente) ---
        if self.is_bound:
            # En POST: usar las selecciones enviadas por el usuario
            lv1_selected = self.data.getlist('risk_taxonomy_lv1')
            self.fields['risk_taxonomy_lv2'].choices = self._valid_lv2_from(lv1_selected)

            lv2_selected = self.data.getlist('risk_taxonomy_lv2')
            self.fields['risk_taxonomy_lv3'].choices = self._valid_lv3_from(lv2_selected)
        else:
            # En GET/edición inicial: usar initial o instance
            lv1_initial = self.initial.get('risk_taxonomy_lv1', [])
            self.fields['risk_taxonomy_lv2'].choices = self._valid_lv2_from(lv1_initial)

            lv2_initial = self.initial.get('risk_taxonomy_lv2', [])
            self.fields['risk_taxonomy_lv3'].choices = self._valid_lv3_from(lv2_initial)
        # ----------------------------------------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()
        lv1 = cleaned_data.get('risk_taxonomy_lv1', [])
        lv2 = cleaned_data.get('risk_taxonomy_lv2', [])
        lv3 = cleaned_data.get('risk_taxonomy_lv3', [])
        
        # Enhanced hierarchical validation
        self.validate_taxonomy_hierarchy(lv1, lv2, lv3)
        
        # Handle "All" selection for impacted lines
        impacted_lines = cleaned_data.get('impacted_lines', [])
        if 'All' in impacted_lines:
            cleaned_data['impacted_lines'] = [choice[0] for choice in LINE_OF_BUSINESS_CHOICES if choice[0] != 'All']
        
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

    # Mantengo estos métodos por compatibilidad (si los llamas en otros lados):
    def get_valid_lv2_choices(self):
        lv1_selections = self.initial.get('risk_taxonomy_lv1', [])
        return self._valid_lv2_from(lv1_selections)

    def get_valid_lv3_choices(self):
        lv2_selections = self.initial.get('risk_taxonomy_lv2', [])
        return self._valid_lv3_from(lv2_selections)

    
class SourceForm(forms.ModelForm):
    # Limitar el dropdown a PDF / DOC / EMAIL, con opción vacía al inicio
    SOURCE_TYPES = [
        ("", "---------"),
        ("PDF", "PDF"),
        ("DOC", "DOC / DOCX"),
        ("EMAIL", "Email (link o .eml/.msg)"),
    ]

    # Radios con iconos para Potential Impact
    POTENTIAL_IMPACT_CHOICES = [
        ("ESCALATING", mark_safe('<i class="fas fa-arrow-up text-danger"></i> Escalating')),
        ("MAINTAINING", mark_safe('<i class="fas fa-arrow-right text-warning"></i> Maintaining')),
        ("DECREASING", mark_safe('<i class="fas fa-arrow-down text-success"></i> Decreasing')),
    ]

    source_type = forms.ChoiceField(
        choices=SOURCE_TYPES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_source_type"})
    )

    potential_impact = forms.ChoiceField(
        choices=POTENTIAL_IMPACT_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={"class": "list-unstyled"})
    )

    class Meta:
        model = Source
        fields = [
            "name",
            "source_type",
            "source_date",
            "summary",
            "potential_impact",
            "potential_impact_notes",
            "link_or_file",
            "file_upload",
            "event",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "source_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "summary": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "potential_impact_notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "link_or_file": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://... o mailto:..."}),
            "file_upload": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.doc,.docx,.eml,.msg"}),
            "event": forms.HiddenInput(),
        }
        labels = {
            "link_or_file": "URL",
            "file_upload": "File Upload",
        }

    # ---------- helpers ----------
    @staticmethod
    def _ext(filename: str) -> str:
        return os.path.splitext(filename or "")[1].lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nunca requerimos 'event' en el form visible
        self.fields["event"].required = False

        # Prefijar source_type cuando editas un Source existente
        if self.instance and self.instance.pk:
            if self.instance.file_upload:
                ext = self._ext(self.instance.file_upload.name)
                if ext == ".pdf":
                    self.initial.setdefault("source_type", "PDF")
                elif ext in (".doc", ".docx"):
                    self.initial.setdefault("source_type", "DOC")
                elif ext in (".eml", ".msg"):
                    self.initial.setdefault("source_type", "EMAIL")
            elif self.instance.link_or_file:
                # Si el link es mailto: lo tratamos como EMAIL
                if str(self.instance.link_or_file).startswith("mailto:"):
                    self.initial.setdefault("source_type", "EMAIL")

    # ---------- validaciones ----------
    def clean(self):
        cleaned = super().clean()
        stype = cleaned.get("source_type")
        url = cleaned.get("link_or_file")
        f = cleaned.get("file_upload")

        # Reglas por tipo
        if not stype:
            raise forms.ValidationError("Please select a Source Type.")

        if stype == "PDF":
            if not f:
                raise forms.ValidationError("For PDF please upload a .pdf file.")
            ext = self._ext(f.name)
            if ext != ".pdf":
                raise forms.ValidationError("Invalid file: only .pdf is allowed for PDF type.")
            cleaned["link_or_file"] = ""  # aseguramos exclusividad

        elif stype == "DOC":
            if not f:
                raise forms.ValidationError("For DOC please upload a .doc or .docx file.")
            ext = self._ext(f.name)
            if ext not in (".doc", ".docx"):
                raise forms.ValidationError("Invalid file: only .doc or .docx is allowed for DOC type.")
            cleaned["link_or_file"] = ""

        elif stype == "EMAIL":
            # Email permite URL (http/https o mailto) y/o archivo .eml/.msg
            if not url and not f:
                raise forms.ValidationError("For Email provide a URL (http/https or mailto) or upload an .eml/.msg file.")
            if url and not (url.startswith("http://") or url.startswith("https://") or url.startswith("mailto:")):
                raise forms.ValidationError("URL must start with http://, https:// or mailto:.")
            if f:
                ext = self._ext(f.name)
                if ext not in (".eml", ".msg"):
                    raise forms.ValidationError("Email attachments must be .eml or .msg.")

        # Límite de tamaño / extensiones permitidas (si tienes settings configurados)
        if f:
            ext = self._ext(f.name)
            valid_exts = getattr(settings, "VALID_FILE_EXTENSIONS", {".pdf", ".doc", ".docx", ".eml", ".msg"})
            max_size = getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)  # 5MB por defecto
            if ext not in valid_exts:
                raise forms.ValidationError(f"Unsupported file extension. Allowed: {', '.join(sorted([x[1:] for x in valid_exts]))}")
            if f.size > max_size:
                raise forms.ValidationError(f"File too large. Max size is {round(max_size/1024/1024)} MB.")

        return cleaned
    
class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }