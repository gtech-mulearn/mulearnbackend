import razorpay
import uuid
from io import BytesIO

from django.http import HttpResponse
from rest_framework.views import APIView

from utils.response import CustomResponse
from .donate_serializer import DonorSerializer, SubscriptionSerializer
from mulearnbackend.settings import RAZORPAY_ID, RAZORPAY_SECRET

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

razorpay_client = razorpay.Client(auth=(RAZORPAY_ID, RAZORPAY_SECRET))

def create_receipt(transaction_details):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    title_style = ParagraphStyle(
        name="TitleStyle",
        fontName="Helvetica-Bold",
        fontSize=20,
        alignment=1,
        spaceAfter=20
    )
    title_text = "Payment Receipt"
    title = Paragraph(title_text, title_style)
    title_width, title_height = title.wrap(width, height)
    title.drawOn(c, (width - title_width) / 2, height - title_height - 30)

    data = [(key, value) for key, value in transaction_details.items()]
    table = Table(data, colWidths=(200, 300))
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 220)

    footer_text = "Thank you for Donation!"
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, 50, footer_text)

    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="razorpay_receipt.pdf"'
    response.write(pdf)
    return response




class RazorPayOrderAPI(APIView):
    def post(self, request):
        try:
            serializer = DonorSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse(general_message=serializer.errors).get_failure_response()
            validated_data = serializer.validated_data

            data = {
                "amount": int(float(validated_data.get("amount")) * 100),
                "currency": validated_data.get("currency"),
                "payment_capture": 1,
                "notes": {
                    "email": validated_data.get("email"),
                    "name": validated_data.get("name"),
                    "phone_number": validated_data.get("phone_number", None),
                    "company": validated_data.get("company", None),
                    "pan_number": validated_data.get("pan_number", None),
                    "validated_data": validated_data
                },
            }
            order = razorpay_client.order.create(data)
            return CustomResponse(response=order).get_success_response()
        except razorpay.errors.BadRequestError as e:
            return CustomResponse(message=str(e)).get_failure_response()


class RazorPayVerification(APIView):
    def post(self, request):
        try:
            razorpay_client.utility.verify_payment_signature(
                {
                    "razorpay_payment_id": request.data.get("razorpay_payment_id"),
                    "razorpay_order_id": request.data.get("razorpay_order_id"),
                    "razorpay_signature": request.data.get("razorpay_signature"),
                }
            )
            data = razorpay_client.payment.fetch(
                request.data.get("razorpay_payment_id")
            )
            transaction_details = {
                "Amount": float(data['amount']) / 100,
                "Currency": data.get('currency', None),
                "payment_id":data['id'],
                "Payment_method":data['method'],
                "Name": data['notes']['name'],
                "Email": data['notes']['email'],
            }
            if extra_data := data['notes'].get('company', None):
                transaction_details["Company"] = extra_data
            if extra_data := data['notes'].get('phone_number', None):
                transaction_details["Phone Number"] = extra_data
            if extra_data := data['notes'].get('pan_number', None):
                transaction_details["PAN number"] = extra_data

            serializer = DonorSerializer(data=data['notes']['validated_data'])
            if serializer.is_valid():
                 serializer.save()

            return CustomResponse(response = transaction_details).get_success_response()
        except razorpay.errors.SignatureVerificationError as e:
            return CustomResponse(general_message = "Payment Verification Failed").get_failure_response()


# ============================================
# RECURRING PAYMENT APIs (Subscriptions)
# ============================================

class RazorPaySubscriptionAPI(APIView):
    
    def post(self, request):
        try:
            serializer = SubscriptionSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse(general_message=serializer.errors).get_failure_response()
            
            validated_data = serializer.validated_data
            amount = int(float(validated_data.get("amount")) * 100)  # Convert to paise
            currency = validated_data.get("currency", "INR")
            donation_type = validated_data.get("donation_type")
            
            # Determine interval based on donation type
            if donation_type == "monthly":
                period = "monthly"
                interval = 1
            else:  # yearly
                period = "yearly"
                interval = 1
            

            plan_name = f"Donation_{donation_type}_{amount}_{uuid.uuid4().hex[:8]}"
            
            plan_data = {
                "period": period,
                "interval": interval,
                "item": {
                    "name": f"µLearn {donation_type.capitalize()} Donation - ₹{amount // 100}",
                    "amount": amount,
                    "currency": currency,
                    "description": f"{donation_type.capitalize()} recurring donation to µLearn Foundation"
                },
                "notes": {
                    "donor_name": validated_data.get("name"),
                    "donor_email": validated_data.get("email"),
                    "donor_phone_number": validated_data.get("phone_number", ""),
                    "donor_pan_number": validated_data.get("pan_number", ""),
                    "company": validated_data.get("company", ""),
                    "is_organisation": str(validated_data.get("is_organisation", False)),
                }
            }
            
            plan = razorpay_client.plan.create(plan_data)
            plan_id = plan['id']
            
            # Create serializable version of validated_data for notes
            serializable_data = {
                "name": validated_data.get("name"),
                "email": validated_data.get("email"),
                "phone_number": validated_data.get("phone_number", ""),
                "pan_number": validated_data.get("pan_number", ""),
                "company": validated_data.get("company", ""),
                "amount": float(validated_data.get("amount")),
                "currency": currency,
            }
            
            # Step 2: Create a Subscription
            subscription_data = {
                "plan_id": plan_id,
                "total_count": 12 if donation_type == "monthly" else 5,  # 12 months or 5 years
                "quantity": 1,
                "customer_notify": 1,
                "notes": {
                    "donor_name": validated_data.get("name"),
                    "donor_email": validated_data.get("email"),
                    "donor_phone_number": validated_data.get("phone_number", ""),
                    "donor_pan_number": validated_data.get("pan_number", ""),
                    "company": validated_data.get("company", ""),
                    "is_organisation": str(validated_data.get("is_organisation", False)),
                    "donation_type": donation_type,
                    "amount": str(float(validated_data.get("amount"))),
                }
            }
            
            subscription = razorpay_client.subscription.create(subscription_data)
            
            return CustomResponse(response={
                "subscription_id": subscription['id'],
                "plan_id": plan_id,
                "status": subscription['status'],
                "short_url": subscription.get('short_url', ''),
                "amount": amount,
                "currency": currency,
                "donation_type": donation_type,
            }).get_success_response()
            
        except razorpay.errors.BadRequestError as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=f"Error creating subscription: {str(e)}").get_failure_response()


class RazorPaySubscriptionVerification(APIView):
    
    def post(self, request):
        try:
            subscription_id = request.data.get("razorpay_subscription_id")
            payment_id = request.data.get("razorpay_payment_id")
            signature = request.data.get("razorpay_signature")
            
            # Verify subscription payment signature
            razorpay_client.utility.verify_subscription_payment_signature({
                "razorpay_subscription_id": subscription_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            
            # Fetch subscription details
            subscription = razorpay_client.subscription.fetch(subscription_id)
            
            # Fetch payment details
            payment = razorpay_client.payment.fetch(payment_id)
            
            transaction_details = {
                "Amount": float(payment['amount']) / 100,
                "Currency": payment.get('currency', 'INR'),
                "payment_id": payment_id,
                "subscription_id": subscription_id,
                "Payment_method": payment.get('method', 'N/A'),
                "Name": subscription['notes'].get('donor_name', ''),
                "Email": subscription['notes'].get('donor_email', ''),
                "Donation_Type": subscription['notes'].get('donation_type', 'recurring'),
                "Status": subscription.get('status', ''),
            }
            
            if company := subscription['notes'].get('company'):
                transaction_details["Company"] = company
            if phone_number := subscription['notes'].get('donor_phone_number'):
                transaction_details["Phone Number"] = phone_number
            if pan_number := subscription['notes'].get('donor_pan_number'):
                transaction_details["PAN number"] = pan_number
            
            # Save donor data
            if validated_data := subscription['notes'].get('validated_data'):
                donor_serializer = DonorSerializer(data=validated_data)
                if donor_serializer.is_valid():
                    donor_serializer.save()
            
            return CustomResponse(response=transaction_details).get_success_response()
            
        except razorpay.errors.SignatureVerificationError as e:
            return CustomResponse(general_message="Subscription Payment Verification Failed").get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=f"Error verifying subscription: {str(e)}").get_failure_response()
