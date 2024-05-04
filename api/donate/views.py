import razorpay
from io import BytesIO
from reportlab.pdfgen import canvas

from django.http import HttpResponse
from rest_framework.views import APIView

from utils.response import CustomResponse
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
            data = {
                "amount": int(float(request.data.get("amount")) * 100),
                "currency": request.data.get("currency", "INR"),
                "payment_capture": 1,
                "notes": {
                    "email": request.data.get("email"),
                    "name": request.data.get("name"),
                    "company": request.data.get("company", None),
                },
            }
            order = razorpay_client.order.create(data)
            return CustomResponse(response=order).get_success_response()
        except razorpay.errors.BadRequestError as e:
            return CustomResponse(message=str(e)).get_error_response()


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
                "Payment ID": data['id'],
                "Payment Method": data['method'],
                "Amount": float(data['amount']) / 100,
                "Currency": data['currency'],
                "Name": data['notes']['name'],
                "Email": data['notes']['email'],
                "Company": data['notes']['company']
            }
            return create_receipt(transaction_details)
        except razorpay.errors.SignatureVerificationError as e:
            return CustomResponse(message=str(e)).get_error_response()
