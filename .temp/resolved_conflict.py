class EnablerCampusNote(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    enabler = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enabler_notes')
    campus = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='enabler_campus_notes')
    note = models.TextField()
    status = models.CharField(max_length=20, default='open')
    priority = models.CharField(max_length=20, default='medium')
    follow_up_date = models.DateField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='enabler_note_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='enabler_note_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'enabler_campus_note'


class CollegeShowcase(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='showcase')
    about = models.TextField(null=True, blank=True)
    hero_image = models.CharField(max_length=255, null=True, blank=True)
    highlights = models.JSONField(default=list)
    gallery = models.JSONField(default=list)
    testimonials = models.JSONField(default=list)
    contact_email = models.CharField(max_length=255, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='college_showcase_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='college_showcase_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'college_showcase'
