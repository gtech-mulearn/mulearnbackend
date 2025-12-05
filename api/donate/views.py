import razorpay
import uuid
import base64
from io import BytesIO
from datetime import datetime

from django.http import HttpResponse
from rest_framework.views import APIView

from utils.response import CustomResponse
from utils.utils import send_template_mail
from .donate_serializer import DonorSerializer, DonationSerializer, SubscriptionSerializer, OrderSerializer
from db.donor import Donor
from db.donation import Donation
from mulearnbackend.settings import RAZORPAY_ID, RAZORPAY_SECRET

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.units import mm

razorpay_client = razorpay.Client(auth=(RAZORPAY_ID, RAZORPAY_SECRET))


def number_to_words(num):
    """Convert a number to words (Indian numbering system)"""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    if num == 0:
        return 'Zero'
    
    def convert_less_than_thousand(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
        else:
            return ones[n // 100] + ' Hundred' + (' ' + convert_less_than_thousand(n % 100) if n % 100 else '')
    
    def convert_indian(n):
        if n < 1000:
            return convert_less_than_thousand(n)
        elif n < 100000:
            return convert_indian(n // 1000) + ' Thousand' + (' ' + convert_less_than_thousand(n % 1000) if n % 1000 else '')
        elif n < 10000000:
            return convert_indian(n // 100000) + ' Lakh' + (' ' + convert_indian(n % 100000) if n % 100000 else '')
        else:
            return convert_indian(n // 10000000) + ' Crore' + (' ' + convert_indian(n % 10000000) if n % 10000000 else '')
    
    # Handle decimal part
    num = float(num)
    integer_part = int(num)
    decimal_part = int(round((num - integer_part) * 100))
    
    result = convert_indian(integer_part)
    if decimal_part:
        result += ' and ' + convert_indian(decimal_part) + ' Paise'
    
    return result + ' Only'


def generate_donation_invoice(invoice_data):
    """
    Generate a professional donation invoice PDF.
    
    Args:
        invoice_data: dict with keys:
            - invoice_number: str
            - date: str
            - donor_name: str
            - donor_email: str
            - donor_address: str (optional)
            - donor_pan: str (optional)
            - donor_phone: str (optional)
            - company: str (optional)
            - amount: float
            - currency: str
            - payment_id: str
            - donation_type: str
            - remarks: str (optional)
    
    Returns:
        bytes: PDF content
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Margins
    left_margin = 30
    right_margin = width - 30
    top_margin = height - 30
    
    # Colors
    header_color = colors.HexColor('#1a1a1a')
    border_color = colors.HexColor('#000000')
    
    # ========== TITLE ==========
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, top_margin, "INVOICE")
    
    y = top_margin - 30
    
    # ========== HEADER SECTION ==========
    # Left box - Organization details
    c.setStrokeColor(border_color)
    c.setLineWidth(1)
    c.rect(left_margin, y - 80, 270, 80)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin + 5, y - 15, "MULEARN FOUNDATION")
    c.setFont("Helvetica", 8)
    c.drawString(left_margin + 5, y - 28, "NILA BUILDING, PHASE-1, TECHNOPARK")
    c.drawString(left_margin + 5, y - 40, "KARYAVATTOM, THIRUVANANTHAPURAM")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.blue)
    c.drawString(left_margin + 5, y - 52, "E-Mail: mulearnadmin@gtechindia.org")
    c.setFillColor(colors.black)
    
    # Right boxes - Invoice details
    box_start_x = 300
    box_width = (right_margin - box_start_x) / 2
    
    # Invoice No and Date row
    c.rect(box_start_x, y - 35, box_width, 35)
    c.rect(box_start_x + box_width, y - 35, box_width, 35)
    
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + 5, y - 12, "Invoice No.")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(box_start_x + 5, y - 28, str(invoice_data.get('invoice_number', 'N/A')))
    
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + box_width + 5, y - 12, "Dated")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(box_start_x + box_width + 5, y - 28, invoice_data.get('date', datetime.now().strftime('%d-%b-%y')))
    
    # Delivery Note and Mode of Payment row
    c.rect(box_start_x, y - 60, box_width, 25)
    c.rect(box_start_x + box_width, y - 60, box_width, 25)
    
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + 5, y - 47, "Delivery Note")
    c.drawString(box_start_x + box_width + 5, y - 47, "Mode/Terms of Payment")
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + box_width + 5, y - 57, "Online Payment")
    
    # Reference row
    c.rect(box_start_x, y - 80, box_width, 20)
    c.rect(box_start_x + box_width, y - 80, box_width, 20)
    
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + 5, y - 72, "Reference No. & Date.")
    c.drawString(box_start_x + box_width + 5, y - 72, "Other References")
    
    y = y - 80
    
    # ========== CONSIGNEE / BUYER SECTION ==========
    consignee_height = 70
    
    # Consignee box
    c.rect(left_margin, y - consignee_height, 270, consignee_height)
    c.setFont("Helvetica", 8)
    c.drawString(left_margin + 5, y - 12, "Consignee (Ship to)")
    c.setFont("Helvetica-Bold", 9)
    
    donor_name = invoice_data.get('donor_name', 'N/A')
    company = invoice_data.get('company', '')
    if company:
        c.drawString(left_margin + 5, y - 25, company)
        c.setFont("Helvetica", 8)
        c.drawString(left_margin + 5, y - 37, f"Contact: {donor_name}")
    else:
        c.drawString(left_margin + 5, y - 25, donor_name)
    
    donor_address = invoice_data.get('donor_address', '')
    if donor_address:
        # Word wrap address
        address_lines = [donor_address[i:i+40] for i in range(0, len(donor_address), 40)]
        y_offset = 37 if company else 37
        for i, line in enumerate(address_lines[:2]):
            c.setFont("Helvetica", 8)
            c.drawString(left_margin + 5, y - y_offset - (i * 12), line)
    
    # Right side order details
    c.rect(box_start_x, y - 25, box_width, 25)
    c.rect(box_start_x + box_width, y - 25, box_width, 25)
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + 5, y - 12, "Buyer's Order No.")
    c.drawString(box_start_x + box_width + 5, y - 12, "Dated")
    
    c.rect(box_start_x, y - 50, box_width, 25)
    c.rect(box_start_x + box_width, y - 50, box_width, 25)
    c.drawString(box_start_x + 5, y - 37, "Dispatch Doc No.")
    c.drawString(box_start_x + box_width + 5, y - 37, "Delivery Note Date")
    
    c.rect(box_start_x, y - consignee_height, box_width, 20)
    c.rect(box_start_x + box_width, y - consignee_height, box_width, 20)
    c.drawString(box_start_x + 5, y - 62, "Dispatched through")
    c.drawString(box_start_x + box_width + 5, y - 62, "Destination")
    
    y = y - consignee_height
    
    # ========== BUYER (Bill to) SECTION ==========
    buyer_height = 60
    c.rect(left_margin, y - buyer_height, 270, buyer_height)
    c.rect(box_start_x, y - buyer_height, right_margin - box_start_x, buyer_height)
    
    c.setFont("Helvetica", 8)
    c.drawString(left_margin + 5, y - 12, "Buyer (Bill to)")
    c.setFont("Helvetica-Bold", 9)
    
    if company:
        c.drawString(left_margin + 5, y - 25, company)
        c.setFont("Helvetica", 8)
        c.drawString(left_margin + 5, y - 37, f"Contact: {donor_name}")
    else:
        c.drawString(left_margin + 5, y - 25, donor_name)
    
    if donor_address:
        y_offset = 49 if company else 37
        for i, line in enumerate(address_lines[:2]):
            c.setFont("Helvetica", 8)
            c.drawString(left_margin + 5, y - y_offset - (i * 12), line)
    
    c.setFont("Helvetica", 8)
    c.drawString(box_start_x + 5, y - 12, "Terms of Delivery")
    
    y = y - buyer_height
    
    # ========== ITEMS TABLE ==========
    table_header_height = 25
    item_row_height = 120
    
    # Calculate column widths to span full width (right_margin - left_margin = 535)
    total_width = right_margin - left_margin
    col_widths = [35, 245, 65, 65, 45, 80]  # Total = 535
    headers = ['Sl\nNo.', 'Particulars', 'Quantity', 'Rate', 'per', 'Amount']
    
    c.setLineWidth(1)
    x = left_margin
    for i, (header, col_width) in enumerate(zip(headers, col_widths)):
        c.rect(x, y - table_header_height, col_width, table_header_height)
        c.setFont("Helvetica-Bold", 9)
        lines = header.split('\n')
        for j, line in enumerate(lines):
            c.drawCentredString(x + col_width / 2, y - 10 - (j * 10), line)
        x += col_width
    
    y = y - table_header_height
    
    # Item row
    x = left_margin
    for col_width in col_widths:
        c.rect(x, y - item_row_height, col_width, item_row_height)
        x += col_width
    
    # Item content
    c.setFont("Helvetica", 10)
    c.drawCentredString(left_margin + col_widths[0] / 2, y - 20, "1")
    
    donation_type = invoice_data.get('donation_type', 'Donation')
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin + col_widths[0] + 10, y - 20, f"Sponsorship-Mulearn")
    c.setFont("Helvetica", 9)
    c.drawString(left_margin + col_widths[0] + 10, y - 35, f"({donation_type})")
    
    amount = float(invoice_data.get('amount', 0))
    c.setFont("Helvetica", 10)
    c.drawRightString(right_margin - 10, y - 20, f"{amount:,.2f}")
    
    y = y - item_row_height
    
    # Total row
    total_row_height = 25
    x = left_margin
    for i, col_width in enumerate(col_widths):
        c.rect(x, y - total_row_height, col_width, total_row_height)
        x += col_width
    
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_margin - col_widths[5] - 10, y - 17, "Total")
    c.setFillColor(colors.HexColor('#0000FF'))
    c.drawRightString(right_margin - 10, y - 17, f"₹ {amount:,.2f}")
    c.setFillColor(colors.black)
    
    # E. & O.E.
    c.setFont("Helvetica-Oblique", 8)
    c.drawRightString(right_margin - 5, y - total_row_height - 10, "E. & O.E")
    
    y = y - total_row_height
    
    # ========== AMOUNT IN WORDS ==========
    amount_words_height = 30
    c.rect(left_margin, y - amount_words_height, right_margin - left_margin, amount_words_height)
    
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor('#0000FF'))
    c.drawString(left_margin + 5, y - 12, "Amount Chargeable (in words)")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    currency = invoice_data.get('currency', 'INR')
    amount_in_words = number_to_words(amount)
    c.drawString(left_margin + 5, y - 25, f"{currency} {amount_in_words}")
    
    y = y - amount_words_height
    
    # ========== REMARKS AND BANK DETAILS ==========
    remarks_height = 100
    c.rect(left_margin, y - remarks_height, 200, remarks_height)
    c.rect(left_margin + 200, y - remarks_height, right_margin - left_margin - 200, remarks_height)
    
    # Remarks
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(left_margin + 5, y - 12, "Remarks:")
    c.setFont("Helvetica", 9)
    remarks = invoice_data.get('remarks', 'Sponsorship for Mulearn')
    c.drawString(left_margin + 5, y - 25, remarks)
    
    # Bank Details
    bank_x = left_margin + 210
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bank_x + 80, y - 15, "Company's Bank Details")
    
    c.setFont("Helvetica", 8)
    details = [
        ("A/c Holder's Name :", "MULEARN FOUNDATION"),
        ("Bank Name        :", "ICICI Bank"),
        ("A/c No.          :", "263405011014"),
        ("Branch & IFS Code:", "Technopark, Trivandrum & ICIC0002534"),
    ]
    
    for i, (label, value) in enumerate(details):
        c.setFont("Helvetica", 8)
        c.drawString(bank_x + 5, y - 30 - (i * 12), label)
        c.setFont("Helvetica-Bold", 8)
        if "ICIC" in value or "MULEARN" in value:
            c.setFillColor(colors.HexColor('#8B0000'))
        c.drawString(bank_x + 90, y - 30 - (i * 12), value)
        c.setFillColor(colors.black)
    
    # for MULEARN FOUNDATION
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor('#8B0000'))
    c.drawRightString(right_margin - 10, y - 75, "for MULEARN FOUNDATION")
    c.setFillColor(colors.black)
    
    y = y - remarks_height
    
    # ========== SIGNATURE ==========
    signature_height = 30
    c.rect(left_margin, y - signature_height, right_margin - left_margin, signature_height)
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin - 10, y - 20, "Authorised Signatory")
    
    y = y - signature_height
    
    # ========== FOOTER ==========
    c.setFillColor(colors.HexColor('#8B0000'))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y - 20, "This is a Computer Generated Invoice")
    c.setFillColor(colors.black)
    
    c.save()
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


def generate_invoice_number():
    """Generate a unique invoice number based on timestamp"""
    now = datetime.now()
    return f"MUL{now.strftime('%Y%m%d%H%M%S')}"


def create_receipt(transaction_details):
    """Legacy function - redirects to new invoice generator"""
    invoice_data = {
        'invoice_number': generate_invoice_number(),
        'date': datetime.now().strftime('%d-%b-%y'),
        'donor_name': transaction_details.get('Name', 'N/A'),
        'donor_email': transaction_details.get('Email', ''),
        'amount': transaction_details.get('Amount', 0),
        'currency': transaction_details.get('Currency', 'INR'),
        'payment_id': transaction_details.get('payment_id', ''),
        'donation_type': 'One-time Donation',
    }
    
    pdf_content = generate_donation_invoice(invoice_data)
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="mulearn_donation_receipt.pdf"'
    response.write(pdf_content)
    return response



def get_or_create_donor(email, donor_data):
    """
    Get existing donor by email or create a new one.
    Returns the Donor instance.
    """
    try:
        donor = Donor.objects.get(email=email)
        # Update donor info if changed
        for field in ['name', 'phone_number', 'pan_number', 'address', 'company', 'is_organisation']:
            if field in donor_data and donor_data[field]:
                setattr(donor, field, donor_data[field])
        donor.save()
        return donor
    except Donor.DoesNotExist:
        serializer = DonorSerializer(data=donor_data)
        if serializer.is_valid():
            return serializer.save()
        raise ValueError(f"Invalid donor data: {serializer.errors}")


class RazorPayOrderAPI(APIView):
    def post(self, request):
        try:
            serializer = OrderSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse(general_message=serializer.errors).get_failure_response()
            validated_data = serializer.validated_data

            data = {
                "amount": int(float(validated_data.get("amount")) * 100),
                "currency": validated_data.get("currency", "INR"),
                "payment_capture": 1,
                "notes": {
                    "email": validated_data.get("email"),
                    "name": validated_data.get("name"),
                    "phone_number": validated_data.get("phone_number", ""),
                    "company": validated_data.get("company", ""),
                    "pan_number": validated_data.get("pan_number", ""),
                    "address": validated_data.get("address", ""),
                    "donation_type": validated_data.get("donation_type", "one-time"),
                    "is_organisation": str(validated_data.get("is_organisation", False)),
                    "amount": str(float(validated_data.get("amount"))),
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
            
            # Fetch payment details from Razorpay
            payment_data = razorpay_client.payment.fetch(
                request.data.get("razorpay_payment_id")
            )
            
            notes = payment_data.get('notes', {})
            order_id = request.data.get("razorpay_order_id")
            payment_id = request.data.get("razorpay_payment_id")
            
            # Prepare donor data
            donor_data = {
                'name': notes.get('name', ''),
                'email': notes.get('email', ''),
                'phone_number': notes.get('phone_number', ''),
                'pan_number': notes.get('pan_number', ''),
                'address': notes.get('address', ''),
                'company': notes.get('company', ''),
                'is_organisation': notes.get('is_organisation', 'False') == 'True',
            }
            
            # Get or create donor
            donor = get_or_create_donor(donor_data['email'], donor_data)
            
            # Create donation record
            donation_data = {
                'donor': donor.id,
                'order_id': order_id,
                'payment_id': payment_id,
                'payment_method': payment_data.get('method', ''),
                'amount': float(payment_data['amount']) / 100,
                'currency': payment_data.get('currency', 'INR'),
                'donation_type': notes.get('donation_type', 'one-time'),
                'is_paid': True,
            }
            
            donation_serializer = DonationSerializer(data=donation_data)
            if donation_serializer.is_valid():
                donation_serializer.save()
            
            # Build transaction details for response
            transaction_details = {
                "Amount": float(payment_data['amount']) / 100,
                "Currency": payment_data.get('currency', 'INR'),
                "payment_id": payment_id,
                "Payment_method": payment_data.get('method', ''),
                "Name": notes.get('name', ''),
                "Email": notes.get('email', ''),
            }
            if company := notes.get('company'):
                transaction_details["Company"] = company
            if phone_number := notes.get('phone_number'):
                transaction_details["Phone Number"] = phone_number
            if pan_number := notes.get('pan_number'):
                transaction_details["PAN number"] = pan_number
            if address := notes.get('address'):
                transaction_details["Address"] = address

            # Generate invoice PDF
            donation_type = notes.get('donation_type', 'one-time')
            invoice_number = generate_invoice_number()
            invoice_data = {
                'invoice_number': invoice_number,
                'date': datetime.now().strftime('%d-%b-%y'),
                'donor_name': notes.get('name', ''),
                'donor_email': notes.get('email', ''),
                'donor_address': notes.get('address', ''),
                'donor_pan': notes.get('pan_number', ''),
                'donor_phone': notes.get('phone_number', ''),
                'company': notes.get('company', ''),
                'amount': float(payment_data['amount']) / 100,
                'currency': payment_data.get('currency', 'INR'),
                'payment_id': payment_id,
                'donation_type': donation_type.replace('-', ' ').title() + ' Donation',
                'remarks': 'Sponsorship for Mulearn',
            }
            
            pdf_content = generate_donation_invoice(invoice_data)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Add PDF to response for frontend download
            transaction_details["invoice_pdf"] = pdf_base64
            transaction_details["invoice_number"] = invoice_number

            # Send donation confirmation email with PDF attachment
            email_context = {
                "email": notes.get('email', ''),
                "name": notes.get('name', ''),
                "amount": float(payment_data['amount']) / 100,
                "currency": payment_data.get('currency', 'INR'),
                "pan_number": notes.get('pan_number', ''),
                "address": notes.get('address', ''),
                "company": notes.get('company', ''),
                "donation_type": donation_type.replace('-', ' ').title(),
            }
            try:
                send_template_mail(
                    context=email_context,
                    subject="Thank You for Your Donation to µLearn!",
                    address=["donation_confirmation.html"],
                    attachment=("Mulearn_Donation_Receipt.pdf", pdf_content, "application/pdf"),
                )
            except Exception as e:
                # Log the error but don't fail the payment verification
                print(f"Failed to send donation confirmation email: {str(e)}")

            return CustomResponse(response=transaction_details).get_success_response()
        except razorpay.errors.SignatureVerificationError as e:
            return CustomResponse(general_message="Payment Verification Failed").get_failure_response()


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
                    "donor_address": validated_data.get("address", ""),
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
                "address": validated_data.get("address", ""),
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
                    "donor_address": validated_data.get("address", ""),
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
            
            notes = subscription.get('notes', {})
            donation_type = notes.get('donation_type', 'monthly')
            
            # Prepare donor data
            donor_data = {
                'name': notes.get('donor_name', ''),
                'email': notes.get('donor_email', ''),
                'phone_number': notes.get('donor_phone_number', ''),
                'pan_number': notes.get('donor_pan_number', ''),
                'address': notes.get('donor_address', ''),
                'company': notes.get('company', ''),
                'is_organisation': notes.get('is_organisation', 'False') == 'True',
            }
            
            # Get or create donor
            donor = get_or_create_donor(donor_data['email'], donor_data)
            
            # Create donation record
            donation_data = {
                'donor': donor.id,
                'order_id': subscription_id,  # Store subscription_id as order_id
                'payment_id': payment_id,
                'payment_method': payment.get('method', ''),
                'amount': float(notes.get('amount', payment['amount'] / 100)),
                'currency': payment.get('currency', 'INR'),
                'donation_type': donation_type,
                'is_paid': True,
            }
            
            donation_serializer = DonationSerializer(data=donation_data)
            if donation_serializer.is_valid():
                donation_serializer.save()
            
            # Build transaction details for response
            transaction_details = {
                "Amount": float(payment['amount']) / 100,
                "Currency": payment.get('currency', 'INR'),
                "payment_id": payment_id,
                "subscription_id": subscription_id,
                "Payment_method": payment.get('method', 'N/A'),
                "Name": notes.get('donor_name', ''),
                "Email": notes.get('donor_email', ''),
                "Donation_Type": donation_type,
                "Status": subscription.get('status', ''),
            }
            
            if company := notes.get('company'):
                transaction_details["Company"] = company
            if phone_number := notes.get('donor_phone_number'):
                transaction_details["Phone Number"] = phone_number
            if pan_number := notes.get('donor_pan_number'):
                transaction_details["PAN number"] = pan_number
            if address := notes.get('donor_address'):
                transaction_details["Address"] = address
            
            # Generate invoice PDF
            invoice_number = generate_invoice_number()
            invoice_data = {
                'invoice_number': invoice_number,
                'date': datetime.now().strftime('%d-%b-%y'),
                'donor_name': notes.get('donor_name', ''),
                'donor_email': notes.get('donor_email', ''),
                'donor_address': notes.get('donor_address', ''),
                'donor_pan': notes.get('donor_pan_number', ''),
                'donor_phone': notes.get('donor_phone_number', ''),
                'company': notes.get('company', ''),
                'amount': float(payment['amount']) / 100,
                'currency': payment.get('currency', 'INR'),
                'payment_id': payment_id,
                'donation_type': f'{donation_type.capitalize()} Recurring Donation',
                'remarks': 'Recurring Sponsorship for Mulearn',
            }
            
            pdf_content = generate_donation_invoice(invoice_data)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Add PDF to response for frontend download
            transaction_details["invoice_pdf"] = pdf_base64
            transaction_details["invoice_number"] = invoice_number
            
            # Send donation confirmation email with PDF attachment
            email_context = {
                "email": notes.get('donor_email', ''),
                "name": notes.get('donor_name', ''),
                "amount": float(payment['amount']) / 100,
                "currency": payment.get('currency', 'INR'),
                "pan_number": notes.get('donor_pan_number', ''),
                "address": notes.get('donor_address', ''),
                "company": notes.get('company', ''),
                "donation_type": f"{donation_type.capitalize()} Recurring",
            }
            try:
                send_template_mail(
                    context=email_context,
                    subject="Thank You for Your Recurring Donation to µLearn!",
                    address=["donation_confirmation.html"],
                    attachment=("Mulearn_Donation_Receipt.pdf", pdf_content, "application/pdf"),
                )
            except Exception as e:
                # Log the error but don't fail the payment verification
                print(f"Failed to send donation confirmation email: {str(e)}")
            
            return CustomResponse(response=transaction_details).get_success_response()
            
        except razorpay.errors.SignatureVerificationError as e:
            return CustomResponse(general_message="Subscription Payment Verification Failed").get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=f"Error verifying subscription: {str(e)}").get_failure_response()

