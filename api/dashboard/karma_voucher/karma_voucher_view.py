from rest_framework.views import APIView

from db.task import VoucherLog, TaskList
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import ImportCSV
from utils.karma_voucher import generate_karma_voucher
from .karma_voucher_serializer import VoucherLogCSVSerializer, VoucherLogSerializer
from utils.types import RoleType

import decouple
from django.core.mail import EmailMessage
from email.mime.image import MIMEImage


class ImportVoucherLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        try:
            file_obj = request.FILES['voucher_log']
        except KeyError:
            return CustomResponse(general_message={'File not found.'}).get_failure_response()
        
        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(general_message={'Empty csv file.'}).get_failure_response()

        temp_headers = ['user_id', 'karma', 'mail', 'task', 'Month/Week']
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(general_message={f'{key} does not exist in the file.'}).get_failure_response()
            
        current_user = JWTUtils.fetch_user_id(request)
        
        valid_rows = []
        error_rows = []

        for row in excel_data[1:]:
            mu_id = row.get('user_id')
            task_hashtag = row.get('task')
            karma = row.get('karma')
            mail = row.get('mail')
            month_week = row.pop('Month/Week')

            user = User.objects.filter(mu_id=mu_id).first()
            task = TaskList.objects.filter(hashtag=task_hashtag).first()
            
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
                row['user_id'] = user.id
                del row['task']
                row['task_id'] = task.id
                serializer = VoucherLogCSVSerializer(data=row, context={"current_user": current_user})
                if serializer.is_valid():
                    
                    email_host_user = decouple.config("EMAIL_HOST_USER")
                    from_mail = decouple.config('FROM_MAIL')
                    to = [mail]
                    subject = "Congratulations on earning Karma points!"
                    domain = decouple.config("FR_DOMAIN_NAME")
                    message = """ Greetings from GTech µLearn!

    Great news! You are just one step away from claiming your Karma points. Simply post the Karma card attached to this email in the #task-dropbox channel and include the specified hashtag to redeem your points
    Name: {}
    Email: {}""".format(user.fullname, mail)
                    
                    msg = EmailMessage(
                        subject,
                        message,
                        from_mail,
                        to
                    )
                    karma_voucher_image = generate_karma_voucher(name=str(user.fullname), karma=str(int(karma)), muid=mu_id, hashtag=task_hashtag, month=month_week)
                    karma_voucher_image.seek(0)
                    attachment = MIMEImage(karma_voucher_image.read())
                    attachment.add_header('Content-Disposition', 'attachment', filename=str(user.fullname) + '.jpg')
                    msg.attach(attachment)
                    
                    msg.send(fail_silently=False)

                    serializer.save()
                    valid_rows.append(serializer.data)

                else:
                    row['error'] = serializer.errors
                    error_rows.append(row)

        return CustomResponse(response={"Success": valid_rows, "Failed": error_rows}).get_success_response()


class VoucherLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request): 
        voucher_queryset = VoucherLog.objects.all()
        voucher_serializer = VoucherLogSerializer(voucher_queryset, many=True)
        return CustomResponse(response=voucher_serializer.data).get_success_response()
