from rest_framework.views import APIView

from db.task import VoucherLog, TaskList
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import ImportCSV, send_template_mail
from utils.karma_voucher import generate_karma_voucher
from .karma_voucher_serializer import VoucherLogCSVSerializer, VoucherLogSerializer
from utils.types import RoleType

from email.mime.image import MIMEImage

import uuid
from utils.utils import DateTimeUtils


class ImportVoucherLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        try:
            file_obj = request.FILES['voucher_log']
        except KeyError:
            return CustomResponse(general_message={'File not found.'}).get_failure_response()
        
        # Read Excel data from the uploaded file
        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(general_message={'Empty csv file.'}).get_failure_response()

        # Define headers and validate them in the first row
        temp_headers = ['user_id', 'karma', 'mail', 'task', 'month', 'week']
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(general_message={f'{key} does not exist in the file.'}).get_failure_response()
            
        current_user = JWTUtils.fetch_user_id(request)
        
        valid_rows = []
        error_rows = []

        # Process each row of data in the Excel file
        for row in excel_data[1:]:
            mu_id = row.get('user_id')
            task_hashtag = row.get('task')
            karma = row.get('karma')
            mail = row.get('mail')
            month = row.get('month')
            week = row.get('week')
            
            # Query for user and task
            user = User.objects.filter(mu_id=mu_id).first()
            task = TaskList.objects.filter(hashtag=task_hashtag).first()
            
            # Validate data and build valid rows
            if not user:
                row['error'] = f"Invalid user id: {mu_id}"
                error_rows.append(row)
            elif not task:
                row['error'] = f"Invalid task hashtag: {task_hashtag}"
                error_rows.append(row)
            elif task.voucher == 0:
                row['error'] = f"Task {task_hashtag} is not a voucher task"
                error_rows.append(row)  
            elif mail != user.email:
                row['error'] = f"Invalid email: {mail}"
                error_rows.append(row)
            elif karma == 0:
                row['error'] = f"Karma cannot be 0"
                error_rows.append(row)
            else :
                # Prepare valid row data
                row['user_id'] = user.id
                del row['task']
                row['task_id'] = task.id
                row['id'] = str(uuid.uuid4())
                row['code'] = str(uuid.uuid4())
                row['created_by_id'] = current_user
                row['updated_by_id'] = current_user
                row['created_at'] = DateTimeUtils.get_current_utc_time()
                row['updated_at'] = DateTimeUtils.get_current_utc_time()
                valid_rows.append(row)

                # Prepare email context and attachment
                subject = "Congratulations on earning Karma points!"
                month_week = month + '/' + week
                karma_voucher_image = generate_karma_voucher(name=str(user.fullname), karma=str(int(karma)), muid=mu_id, hashtag=task_hashtag, month=month_week)
                karma_voucher_image.seek(0)
                attachment = MIMEImage(karma_voucher_image.read())
                attachment.add_header('Content-Disposition', 'attachment', filename=str(user.fullname) + '.jpg')

                email_context = {
                    "user": user.fullname,
                    "email": mail
                } 

                send_template_mail(
                    context=email_context,
                    subject=subject,
                    address=['base_mail.html'],
                    attachment=attachment,
                )

        # Serialize and save valid voucher rows
        voucher_serializer = VoucherLogCSVSerializer(data=valid_rows, many=True)
        if voucher_serializer.is_valid():
            voucher_serializer.save()
        else:
            error_rows.append(voucher_serializer.errors)
                
        return CustomResponse(response={"Success": voucher_serializer.data, "Failed": error_rows}).get_success_response()


class VoucherLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request): 
        voucher_queryset = VoucherLog.objects.all()
        voucher_serializer = VoucherLogSerializer(voucher_queryset, many=True)
        return CustomResponse(response=voucher_serializer.data).get_success_response()