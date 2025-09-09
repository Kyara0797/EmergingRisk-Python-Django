from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone 
import uuid

STATUS_CHOICES = [
    ('HORIZON SCANNING', 'Horizon Scanning'),
    ('UNDER MONITORING', 'Under Monitoring'),
    ('TRANSITION TO KNOWN RISK', 'Transition to known risk'),
]

RISK_TAXONOMY_LV1 = [
    ('Cybersecurity & Technology Risk', 'Cybersecurity & Technology Risk'),
    ('Financial Risk', 'Financial Risk'),
    ('Operational Risk', 'Operational Risk'),
    ('Regulatory Compliance Risk', 'Regulatory Compliance Risk'),
    ('Reputational Risk', 'Reputational Risk'),
    ('Strategic Risk', 'Strategic Risk')
]

RISK_TAXONOMY_LV2 = {
    'Financial Risk': [
        ('Counterparty Risk', 'Counterparty Risk'),
        ('Liquidity Risk (Incl. Capital Risk)', 'Liquidity Risk (Incl. Capital Risk)'),
        ('Market Risk (Incl. Interest Rate Risk & Exchange Rate Risk)', 'Market Risk (Incl. Interest Rate Risk & Exchange Rate Risk)'),
        ('Insurance Risk', 'Insurance Risk'),
    ],
    'Operational Risk': [
        ('Third Party Risk Management', 'Third Party Risk Management'),
        ('Model Risk (Fraud, Decisioning, etc.)', 'Model Risk (Fraud, Decisioning, etc.)'),
        ('Recovery Risk', 'Recovery Risk'),
        ('Location Risk', 'Location Risk'),
        ('Execution, Delivery and Process Risk', 'Execution, Delivery and Process Risk'),
        ('Payment Processing Risk', 'Payment Processing Risk'),
        ('Human Resource Risk', 'Human Resource Risk'),
        ('Client & Product Risk', 'Client & Product Risk'),
        ('Fraud Risk (Internal & External)', 'Fraud Risk (Internal & External)'),
        ('Financial Planning & Accounting Risk', 'Financial Planning & Accounting Risk'),
        ('Legal Risk', 'Legal Risk'),
        ('Compliance Nonregulatory', 'Compliance Nonregulatory'),
    ],
    'Cybersecurity & Technology Risk': [
        ('Cyber Risk', 'Cyber Risk'),
        ('Tech Risk', 'Tech Risk'),
    ],
    'Regulatory Compliance Risk': [
        ('ACH Non-Compliance', 'ACH Non-Compliance'),
        ('Conduct Risk (Ethic)', 'Conduct Risk (Ethic)'),
        ('Consumer Protection', 'Consumer Protection'),
        ('Financial Crimes', 'Financial Crimes'),
        ('Money Transmission Compliance', 'Money Transmission Compliance'),
        ('Other Regulatory Risk', 'Other Regulatory Risk'),
        ('Data & Privacy Compliance', 'Data & Privacy Compliance'),
    ],
    'Strategic Risk': [
        ('External Change (Incl. Geopolitical, Country Risk, Competition Risk, Partnership Risk, Emerging Risk)', 'External Change (Incl. Geopolitical, Country Risk, Competition Risk, Partnership Risk, Emerging Risk)'),
        ('Business Strategy', 'Business Strategy'),
        ('Corporate Governance', 'Corporate Governance'),
    ],
    'Reputational Risk': [
        ('Reputation Risk (Inc. Brand)', 'Reputation Risk (Inc. Brand)'),
    ]
}

RISK_TAXONOMY_LV3 = {
    'Counterparty Risk': [
        ('Indirect Channel/Aggregator Risk', 'Indirect Channel/Aggregator Risk'),
        ('Ineffective Credit Risk Governance', 'Ineffective Credit Risk Governance'),
        ('Insolvency Risk', 'Insolvency Risk'),
        ('Dispute/Chargeback/Claims of Error Risk', 'Dispute/Chargeback/Claims of Error Risk'),
        ('Client or Third-party Receivables', 'Client or Third-party Receivables'),
    ],
    'Liquidity Risk (Incl. Capital Risk)': [
        ('Liquidity Risk', 'Liquidity Risk'),
        ('Capital Risk', 'Capital Risk'),
    ],
    'Market Risk (Incl. Interest Rate Risk & Exchange Rate Risk)': [
        ('Interest Rate Risk', 'Interest Rate Risk'),
        ('Exchange Rate Risk', 'Exchange Rate Risk'),
        ('Tax Risk', 'Tax Risk'),
    ],
    'Insurance Risk': [
        ('Coverage Risk', 'Coverage Risk'),
        ('Limits Risk', 'Limits Risk'),
    ],
    'Third Party Risk Management': [
        ('Unsuitable Third-Party Selection (New vendor due diligence)', 'Unsuitable Third-Party Selection (New vendor due diligence)'),
        ('Third Party Delivery Failure (Existing vendor monitoring)', 'Third Party Delivery Failure (Existing vendor monitoring)'),
        ('Other Connected Risks (Cyber, Tech, Data, BCM, Compliance)', 'Other Connected Risks (Cyber, Tech, Data, BCM, Compliance)'),
        ('Inadequate Termination Execution', 'Inadequate Termination Execution'),
    ],
    'Model Risk (Fraud, Decisioning, etc.)': [
        ('Conceptual Flaws', 'Conceptual Flaws'),
        ('Performance Issues', 'Performance Issues'),
        ('Instability', 'Instability'),
        ('Opaqueness', 'Opaqueness'),
        ('Unfair Outputs', 'Unfair Outputs'),
        ('Implementation Errors', 'Implementation Errors'),
        ('Use Risks', 'Use Risks'),
    ],
    'Recovery Risk': [
        ('Business Recovery Risk (BR)', 'Business Recovery Risk (BR)'),
        ('Technology Recovery Risk (TR)', 'Technology Recovery Risk (TR)'),
    ],
    'Location Risk': [
        ('Physical Risk', 'Physical Risk'),
        ('Environmental Risk', 'Environmental Risk'),
    ],
    'Execution, Delivery and Process Risk': [
        ('Enterprise Risk and Controls', 'Enterprise Risk and Controls'),
        ('Transaction Capture, Execution and Maintenance', 'Transaction Capture, Execution and Maintenance'),
        ('Monitoring and Reporting', 'Monitoring and Reporting'),
        ('Change Management (Non-Technology)', 'Change Management (Non-Technology)'),
    ],
    'Payment Processing Risk': [
        ('Authorization Risk', 'Authorization Risk'),
        ('Settlement Risk', 'Settlement Risk'),
        ('Funding Transaction Risk', 'Funding Transaction Risk'),
    ],
    'Human Resource Risk': [
        ('Workers Compensation Risk', 'Workers Compensation Risk'),
        ('Talent Development and Management Risk', 'Talent Development and Management Risk'),
        ('Illegal Diversity and Inclusion Risk', 'Illegal Diversity and Inclusion Risk'),
        ('Other – Human Resource Risk', 'Other – Human Resource Risk'),
        ('Disability/Discrimination/Retaliation Risk', 'Disability/Discrimination/Retaliation Risk'),
        ('Wage/Hour Class Action Risk', 'Wage/Hour Class Action Risk'),
        ('Benefit Plan Risk', 'Benefit Plan Risk'),
    ],
    'Client & Product Risk': [
        ('Client or Account Mismanagement', 'Client or Account Mismanagement'),
        ('Improper Product/Service Design (incl product defect)', 'Improper Product/Service Design (incl product defect)'),
        ('Improper Distribution / Implementation / Delivery', 'Improper Distribution / Implementation / Delivery'),
        ('Inadequate Customer Service', 'Inadequate Customer Service'),
    ],
    'Fraud Risk (Internal & External)': [
        ('Internal Fraud Risk (Theft, Unauthorized Activities)', 'Internal Fraud Risk (Theft, Unauthorized Activities)'),
        ('Merchant Fraud', 'Merchant Fraud'),
        ('External Fraud Risk (Theft, Fraud)', 'External Fraud Risk (Theft, Fraud)'),
    ],
    'Financial Planning & Accounting Risk': [
        ('Ineffective Financial Planning and Analysis', 'Ineffective Financial Planning and Analysis'),
        ('Ineffective Accounting and Reporting (Including Billing)', 'Ineffective Accounting and Reporting (Including Billing)'),
    ],
    'Legal Risk': [
        ('Contractual rights/obligation failures', 'Contractual rights/obligation failures'),
        ('IP Infringement Risk', 'IP Infringement Risk'),
        ('Litigation Risk', 'Litigation Risk'),
    ],
    'Compliance Nonregulatory': [
        ('Cards Network Non-Compliance (incl. PCI)', 'Cards Network Non-Compliance (incl. PCI)'),
    ],
    'Cyber Risk': [
        ('Ineffective Cybersecurity Risk Management', 'Ineffective Cybersecurity Risk Management'),
        ('Cybersecurity Strategy and Program / Project Failure', 'Cybersecurity Strategy and Program / Project Failure'),
        ('Secure Design Deficiencies and Coding Errors', 'Secure Design Deficiencies and Coding Errors'),
        ('Unauthorized or Misused Access', 'Unauthorized or Misused Access'),
        ('Ineffective Data Protection', 'Ineffective Data Protection'),
        ('Vulnerability Exploit', 'Vulnerability Exploit'),
        ('Security Operational Failure', 'Security Operational Failure'),
        ('Ineffective Cybersecurity Incident Management', 'Ineffective Cybersecurity Incident Management'),
    ],
    'Tech Risk': [
        ('Ineffective Technology Risk Management', 'Ineffective Technology Risk Management'),
        ('Technology Strategy and Program / Project Failure', 'Technology Strategy and Program / Project Failure'),
        ('Ineffective Technology Asset Management', 'Ineffective Technology Asset Management'),
        ('Design Deficiencies and Coding Errors', 'Design Deficiencies and Coding Errors'),
        ('Change Implementation Failure', 'Change Implementation Failure'),
        ('Technology Operations Failure', 'Technology Operations Failure'),
        ('Insufficient Capacity', 'Insufficient Capacity'),
        ('Ineffective Technology Incident Management', 'Ineffective Technology Incident Management'),
    ],
    'ACH Non-Compliance': [
        ('ACH Non-Compliance', 'ACH Non-Compliance'),  # Text input
    ],
    'Conduct Risk (Ethic)': [
        ('Conflict of Interest', 'Conflict of Interest'),
        ('Ethics', 'Ethics'),
    ],
    'Consumer Protection': [
        ('Inadequate or Insufficient Debt Collection, or Debtor Protection', 'Inadequate or Insufficient Debt Collection, or Debtor Protection'),
        ('Inadequate or Insufficient Consumer Communication (incl Disclosures, Alerts, Marketing Materials)', 'Inadequate or Insufficient Consumer Communication (incl Disclosures, Alerts, Marketing Materials)'),
        ('Other Consumer Protection Regulatory Compliance', 'Other Consumer Protection Regulatory Compliance'),
        ('Inadequate or Insufficient Credit Reporting', 'Inadequate or Insufficient Credit Reporting'),
    ],
    'Financial Crimes': [
        ('Anti Money Laundering Compliance', 'Anti Money Laundering Compliance'),
        ('Anti Bribery and Corruption Compliance', 'Anti Bribery and Corruption Compliance'),
        ('Antitrust Compliance', 'Antitrust Compliance'),
        ('Sanction Compliance', 'Sanction Compliance'),
    ],
    'Money Transmission Compliance': [
        ('License Obligations', 'License Obligations'),
        ('Flow of Funds', 'Flow of Funds'),
    ],
    'Other Regulatory Risk': [
        ('Other Regulatory Risk', 'Other Regulatory Risk'),  # Text input
    ],
    'Data & Privacy Compliance': [
        ('Data Privacy Risk', 'Data Privacy Risk'),
        ('Records Management Risk', 'Records Management Risk'),
        ('Data Governance Risk', 'Data Governance Risk'),
        ('Artificial Intelligence Risk', 'Artificial Intelligence Risk'),
    ],
    'External Change (Incl. Geopolitical, Country Risk, Competition Risk, Partnership Risk, Emerging Risk)': [
        ('Country Risk', 'Country Risk'),
        ('Competition Risk', 'Competition Risk'),
        ('Consumer Behavior Change', 'Consumer Behavior Change'),
        ('Client Regulatory Risk', 'Client Regulatory Risk'),
        ('Partnership/Network/Sponsorship Risk', 'Partnership/Network/Sponsorship Risk'),
    ],
    'Business Strategy': [
        ('Ineffective Business Strategic Plan', 'Ineffective Business Strategic Plan'),
        ('M&A and Divestiture Management Failure', 'M&A and Divestiture Management Failure'),
    ],
    'Corporate Governance': [
        ('Corporate Structure - Board and Shareholder Relations', 'Corporate Structure - Board and Shareholder Relations'),
        ('Corporate Structure - Legal Entity', 'Corporate Structure - Legal Entity'),
        ('ESG Risk', 'ESG Risk'),
    ],
    'Reputation Risk (Inc. Brand)': [
        ('Reactive Brand and Reputation Management', 'Reactive Brand and Reputation Management'),
        ('Ineffective Marketing and Communication', 'Ineffective Marketing and Communication'),
        ('Ineffective social media and Public Relations', 'Ineffective social media and Public Relations'),
    ]
}


RISK_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

RISK_COLORS = {
    'low': 'success',
    'medium': 'warning',
    'high': 'orange',
    'critical': 'danger'
}

CATEGORY_CHOICES = [
    ('Political', 'Political'),
    ('Economic', 'Economic'),
    ('Social', 'Social'),
    ('Technological', 'Technological'),
    ('Legal', 'Legal'),
    ('Environmental', 'Environmental'),
]

ONSET_TIMELINE_CHOICES = [
    ('<1 year', '<1 year'),
    ('1-2 years', '1-2 years'),
    ('2+ years', '2+ years'),
]

LINE_OF_BUSINESS_CHOICES = [
    ('All', 'All'),
    ('APAC', 'APAC'),
    ('EMEA', 'EMEA'),
    ('FIG', 'FIG'),
    ('Issuer', 'Issuer'),
    ('LATAM', 'LATAM'),
    ('Merchant', 'Merchant'),
    ('Evaluation in progress', 'Evaluation in progress'),
    
]


SOURCE_TYPE_CHOICES = [
    ('Article', 'Article'),
    ('Internal', 'Internal'),
    ('News', 'News'),
    ('Regulation', 'Regulation'),
    ('Report', 'Report'),
]

POTENTIAL_IMPACT_CHOICES = [
    ('ESCALATING', '<i class="fas fa-arrow-up text-danger"></i> Risk is Escalating'),
    ('MAINTAINING', '<i class="fas fa-arrow-right text-warning"></i> Risk is Maintaining'),
    ('DECREASING', '<i class="fas fa-arrow-down text-success"></i> Risk is Decreasing'),
]

class Category(models.Model):
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name

class Theme(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='themes',
        db_index=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    risk_rating = models.CharField(max_length=20, choices=RISK_CHOICES)
    onset_timeline = models.CharField(max_length=20, choices=ONSET_TIMELINE_CHOICES)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_themes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['risk_rating']),
        ]
    
    def get_risk_color(self):
        key = (self.risk_rating or '').strip().upper()
        return RISK_COLORS.get(self.risk_rating, 'secondary')

    def clean(self):
        if not self.name.strip():
            raise ValidationError("The name cannot be empty.")
        
        if self.pk:
            original = Theme.objects.get(pk=self.pk)
            for field in self._meta.fields:
                if getattr(self, field.name) == "":
                    setattr(self, field.name, getattr(original, field.name))

    def get_absolute_url(self):
        return reverse('view_theme', kwargs={'pk': self.pk})
    
    def __str__(self):
        return f"{self.name} ({self.category})"

class Event(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Definición de constantes para choices
    ESCALATING = 'ESCALATING'
    MAINTAINING = 'MAINTAINING'
    DECREASING = 'DECREASING'
    
    # Choices para risk_rating
    RISK_RATING_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Choices para status (asumiendo que necesitas esta definición)
    STATUS_CHOICES = sorted([
        ('HORIZON SCANNING', 'Horizon Scanning'),
        ('UNDER MONITORING', 'Under monitoring'),
        ('TRANSITION TO KNOWN RISK', 'Transition to known risk'),
    ], key=lambda x: x[1])
    
    # Diccionario de colores para risk_rating
    RISK_COLORS = {
        'LOW': 'success',
        'MEDIUM': 'warning',
        'HIGH': 'orange',
        'CRITICAL': 'danger',
    }
    
    # Campos del modelo
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='events',
        db_index=True
    )
    name = models.CharField(max_length=200)
    date_identified = models.DateField()
    description = models.TextField()
    
  
    impacted_lines = models.JSONField(default=list)
    risk_taxonomy_lv1 = models.JSONField(default=list)
    risk_taxonomy_lv2 = models.JSONField(default=list)
    risk_taxonomy_lv3 = models.JSONField(default=list)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    risk_rating = models.CharField(
        max_length=20, 
        choices=RISK_RATING_CHOICES,
        default='MEDIUM' 
    )
    control_in_place = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_identified']
        indexes = [
            models.Index(fields=['-date_identified']),
            models.Index(fields=['status']),
            models.Index(fields=['risk_rating']),
        ]
    
    def get_risk_color(self):
        return self.RISK_COLORS.get(self.risk_rating, 'secondary')
    
    def get_risk_display(self):
        return self.get_risk_rating_display()
    
    def get_absolute_url(self):
        return reverse('view_event', kwargs={'pk': self.pk})
    
    def clean(self):
        super().clean()
        # Validación adicional para asegurar que los campos requeridos están presentes
        required_fields = ['name', 'date_identified', 'description']
        for field in required_fields:
            if not getattr(self, field):
                raise ValidationError({field: f"{field.replace('_', ' ').title()} is required"})
    def __str__(self):
        return f"{self.name} ({self.theme})"
    
    
class RiskTaxonomyLv2(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class RiskTaxonomyLv3(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

def generate_download_token():
    return uuid.uuid4().hex

class Source(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    SOURCE_TYPE_CHOICES = [
        ('LINK', 'Link'),
        ('FILE', 'File'),
        ('MIXED', 'Mixed'),
    ]

    event = models.ForeignKey('tracker.Event', on_delete=models.CASCADE, related_name='sources', db_index=True)
    name = models.CharField(max_length=200)

    
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default='FILE')

    source_date = models.DateField()
    summary = models.TextField()

    POTENTIAL_IMPACT_CHOICES = [
        ('ESCALATING', 'Escalating'),
        ('DECREASING', 'Decreasing'),
        ('MAINTAINING', 'Maintaining'),
        
    ]
    potential_impact = models.CharField(max_length=20, choices=POTENTIAL_IMPACT_CHOICES, blank=True, null=True)
    potential_impact_notes = models.TextField(blank=True, null=True)

    link_or_file = models.URLField(max_length=500, blank=True)
    file_upload = models.FileField(upload_to='sources/%Y/%m/%d/', blank=True, null=True)

    download_token = models.UUIDField(
        default=uuid.uuid4,   
        unique=True,
        null=False,
        editable=False,
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sources')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-source_date']
        indexes = [
            models.Index(fields=['-source_date']),
            models.Index(fields=['source_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

    def has_file(self) -> bool:
        return bool(self.file_upload)

    def get_download_url(self):
        
        return reverse("secure_file_download", args=[str(self.download_token)])

class SourceFileVersion(models.Model):
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name="file_history",
        db_index=True,
    )
    # Apuntamos al mismo archivo antiguo; no lo copiamos ni movemos
    file = models.FileField(upload_to='sources/%Y/%m/%d/')
    replaced_at = models.DateTimeField(auto_now_add=True)
    replaced_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True)

    download_token = models.UUIDField(
        default=uuid.uuid4,   
        unique=True,
        null=False,
        editable=False,
    )
    class Meta:
        ordering = ["-replaced_at"]

    def __str__(self):
        base = (self.file.name or "").split("/")[-1]
        return f"{base} ({self.replaced_at:%Y-%m-%d})"

    def get_download_url(self):
        return reverse("secure_file_download", args=[str(self.download_token)])
    

class DownloadLog(models.Model):
    when       = models.DateTimeField(auto_now_add=True)
    user       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip         = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    object_key = models.TextField()   
    token      = models.UUIDField()   

    class Meta:
        ordering = ['-when']
        indexes  = [
            models.Index(fields=['-when']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        who = self.user.username if self.user else "anonymous"
        return f"{self.when:%Y-%m-%d %H:%M:%S} - {who} -> {self.object_key}"


class UserAccessLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    login_time = models.DateTimeField(default=timezone.now)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    session_duration = models.DurationField(blank=True, null=True)

    class Meta:
        verbose_name = "User Access Log"
        verbose_name_plural = "User Access Logs"
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['-login_time']),
            models.Index(fields=['user']),
        ]

    def save(self, *args, **kwargs):
        if self.logout_time and self.login_time:
            self.session_duration = self.logout_time - self.login_time
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
    

class TempUpload(models.Model):
    KIND_CHOICES = (("MAIN", "Main"), ("EXTRA", "Extra"))

    batch_id = models.CharField(max_length=40, db_index=True)  # UUID por formulario
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to="temp_sources/%Y/%m/%d/")
    original_name = models.CharField(max_length=255)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_name} ({self.kind})"