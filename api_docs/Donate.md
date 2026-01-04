# Donate API Reference

## One-Time Payment (Razorpay)

### Create Order
**Endpoint:** `/api/v1/donate/order/create/`
**Method:** `POST`
**Brief:** Create a Razorpay order for donation.

**Request Body:**
```json
{
  "amount": "decimal",
  "currency": "INR",
  "name": "string",
  "email": "string",
  "phone_number": "string (optional)",
  "company": "string (optional)",
  "pan_number": "string (optional)",
  "address": "string (optional)",
  "donation_type": "one-time/monthly/yearly",
  "is_organisation": boolean
}
```

### Verify Payment
**Endpoint:** `/api/v1/donate/payment/verify/`
**Method:** `POST`
**Brief:** Verify Razorpay payment and generate receipt.

**Request Body:**
```json
{
  "razorpay_payment_id": "string",
  "razorpay_order_id": "string",
  "razorpay_signature": "string"
}
```

## Subscription Payment (Recurring)

### Create Subscription
**Endpoint:** `/api/v1/donate/subscription/create/`
**Method:** `POST`
**Brief:** Create a Razorpay subscription for recurring donation.
**Request Body:** Same as Create Order.

### Verify Subscription
**Endpoint:** `/api/v1/donate/subscription/verify/`
**Method:** `POST`
**Brief:** Verify Razorpay subscription payment.

**Request Body:**
```json
{
  "razorpay_subscription_id": "string",
  "razorpay_payment_id": "string",
  "razorpay_signature": "string"
}
```
