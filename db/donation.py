from django.db import models
from db.donor import Donor


class Donation(models.Model):
    """
    Donation model - tracks individual donations/payments.
    Links to Donor for personal info, stores payment details separately.
    """
    id = models.CharField(primary_key=True, max_length=36)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, db_column='donor_id', related_name='donations')
    order_id = models.CharField(max_length=100, null=True, blank=True)  # Razorpay order_id or subscription_id
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    donation_name = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    donation_type = models.CharField(max_length=20)  # 'one-time', 'monthly', 'yearly'
    is_paid = models.BooleanField(default=False)
    # Bank transfer fields
    payment_status = models.CharField(max_length=30, default='COMPLETED')  # 'COMPLETED', 'PENDING_VERIFICATION', 'REJECTED'
    reference_code = models.CharField(max_length=50, null=True, blank=True)
    proof_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'donation'
