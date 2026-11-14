import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

from db.user import User
from db.task import TaskList, VoucherLog
from api.dashboard.karma_voucher.karma_voucher_serializer import (
    VoucherLogCreateSerializer, VoucherLogUpdateSerializer, ALLOWED_MONTHS, ALLOWED_WEEKS
)
from utils.utils import DateTimeUtils

def test_validations():
    print("Setting up test data...")
    user = User.objects.first()
    task = TaskList.objects.first()

    if not user or not task:
        print("Error: Need at least one User and one Task in the database to run tests.")
        return

    print(f"Using User: {user.muid}")
    print(f"Using Task: {task.hashtag}")

    # --- Test 1: Invalid Month ---
    print("\n--- Test 1: Invalid Month ---")
    data = {
        'user': user.muid,
        'task': task.id,
        'karma': 100,
        'month': 'InvalidMonth',
        'week': 'W1'
    }
    serializer = VoucherLogCreateSerializer(data=data)
    if not serializer.is_valid():
        print(f"✅ Correctly rejected invalid month: {serializer.errors}")
    else:
        print("❌ FAILED: Accepted invalid month")

    # --- Test 2: Invalid Week ---
    print("\n--- Test 2: Invalid Week ---")
    data['month'] = 'January'
    data['week'] = 'InvalidWeek'
    serializer = VoucherLogCreateSerializer(data=data)
    if not serializer.is_valid():
        print(f"✅ Correctly rejected invalid week: {serializer.errors}")
    else:
        print("❌ FAILED: Accepted invalid week")

    # --- Test 3: Uniqueness Check ---
    print("\n--- Test 3: Uniqueness Check ---")
    current_year = DateTimeUtils.get_current_utc_time().year
    
    # Ensure no existing voucher conflicts for this specific test case first
    VoucherLog.objects.filter(
        user=user, 
        task=task, 
        month='January', 
        week='W1', 
        created_at__year=current_year
    ).delete()

    # Create one
    VoucherLog.objects.create(
        code="TEMP_TEST_CODE_RETRY",
        user=user,
        task=task,
        karma=100,
        month='January',
        week='W1',
        claimed=False,
        created_by=user,
        updated_by=user,
        created_at=DateTimeUtils.get_current_utc_time(),
        updated_at=DateTimeUtils.get_current_utc_time()
    )

    # Try to create duplicate via serializer
    data['week'] = 'W1'
    serializer = VoucherLogCreateSerializer(data=data)
    if not serializer.is_valid():
        if "Voucher already exists" in str(serializer.errors):
             print(f"✅ Correctly detected duplicate: {serializer.errors}")
        else:
             print(f"⚠️ Rejected but maybe for wrong reason? {serializer.errors}")
    else:
        print("❌ FAILED: Accepted duplicate voucher")

    # Cleanup
    VoucherLog.objects.filter(code="TEMP_TEST_CODE_RETRY").delete()
    print("Cleaned up temporary voucher.")

if __name__ == "__main__":
    test_validations()
