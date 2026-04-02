class Company(models.Model):
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='company_user_id', related_name='company_user')
    name = models.CharField(max_length=75, unique=True)
    logo = models.TextField(blank=True, null=True)
    description = models.TextField()
    industry_sector = models.CharField(max_length=75, blank=True, null=True)
    website_link = models.TextField(blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    slug = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    legal_name = models.CharField(max_length=150, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    company_size = models.CharField(max_length=50, blank=True, null=True)
    linkedin_url = models.TextField(blank=True, null=True)
    verification_document_url = models.TextField(blank=True, null=True)
    verification_requested_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.CharField(max_length=36, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=36, blank=True, null=True)
    deleted_by = models.CharField(max_length=36, blank=True, null=True)
