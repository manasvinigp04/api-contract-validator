# API Specification Analysis

**API:** E-Commerce Platform API

**Version:** 2.1.0

**Description:** Comprehensive e-commerce API supporting product catalog, shopping cart,
order management, payment processing, and user authentication.

This API demonstrates complex scenarios including:
- Schema composition (oneOf, anyOf, allOf)
- Discriminators for polymorphic responses
- Complex validation rules and constraints
- Multi-step workflows (cart → checkout → payment → fulfillment)
- Nested objects and arrays
- Security with OAuth2 and API keys


**Analysis Date:** 2026-04-25 02:14:38

---

## Overview

- **Total Endpoints:** 18
- **Schemas Defined:** 21
- **Spec File:** `e-commerce-api.yaml`

### Endpoints by HTTP Method

| Method | Count |
|--------|-------|
| DELETE | 2 |
| GET | 7 |
| PATCH | 4 |
| POST | 5 |

## API Endpoints

### `/cart`

#### GET

**Summary:** Get current user's cart

**Responses:**
- `200`: Current cart
- `401`: N/A

---

#### POST

**Summary:** Add item to cart

**Request Body:** Required

**Responses:**
- `200`: Item added to cart
- `400`: N/A
- `401`: N/A
- `404`: N/A

---

### `/cart/items/{itemId}`

#### PATCH

**Summary:** Update cart item quantity

**Request Body:** Required

**Responses:**
- `200`: Cart item updated
- `400`: N/A
- `401`: N/A
- `404`: N/A

---

#### DELETE

**Summary:** Remove item from cart

**Responses:**
- `200`: Item removed
- `401`: N/A
- `404`: N/A

---

### `/orders`

#### GET

**Summary:** List user's orders

**Parameters:**
- `status` (query) - string
- `fromDate` (query) - string
- `toDate` (query) - string

**Responses:**
- `200`: List of orders
- `401`: N/A

---

#### POST

**Summary:** Create order from cart

**Request Body:** Required

**Responses:**
- `201`: Order created
- `400`: N/A
- `401`: N/A
- `422`: Unprocessable entity (e.g., cart empty, items out of stock)

---

### `/orders/{orderId}`

#### GET

**Summary:** Get order details

**Responses:**
- `200`: Order details
- `401`: N/A
- `404`: N/A

---

#### PATCH

**Summary:** Update order (cancel only)

**Request Body:** Required

**Responses:**
- `200`: Order updated
- `400`: N/A
- `401`: N/A
- `404`: N/A
- `409`: Conflict (e.g., order already shipped)

---

### `/payments`

#### POST

**Summary:** Process payment for order

**Request Body:** Required

**Responses:**
- `200`: Payment processed
- `400`: N/A
- `401`: N/A
- `402`: Payment required (payment failed)

---

### `/products`

#### GET

**Summary:** Search and list products

**Parameters:**
- `category` (query) - string
- `minPrice` (query) - number
- `maxPrice` (query) - number
- `inStock` (query) - boolean
- `page` (query) - integer
- `limit` (query) - integer
- `sortBy` (query) - string

**Responses:**
- `200`: List of products
- `400`: N/A

---

#### POST

**Summary:** Create a new product

**Request Body:** Required

**Responses:**
- `201`: Product created successfully
- `400`: N/A
- `401`: N/A
- `403`: N/A

---

### `/products/{productId}`

#### GET

**Summary:** Get product details

**Responses:**
- `200`: Product details
- `404`: N/A

---

#### PATCH

**Summary:** Update product

**Request Body:** Required

**Responses:**
- `200`: Product updated
- `400`: N/A
- `401`: N/A
- `404`: N/A

---

#### DELETE

**Summary:** Delete product

**Responses:**
- `204`: Product deleted successfully
- `401`: N/A
- `404`: N/A

---

### `/users/addresses`

#### GET

**Summary:** List user addresses

**Responses:**
- `200`: List of addresses
- `401`: N/A

---

#### POST

**Summary:** Add new address

**Request Body:** Required

**Responses:**
- `201`: Address added
- `400`: N/A
- `401`: N/A

---

### `/users/profile`

#### GET

**Summary:** Get current user profile

**Responses:**
- `200`: User profile
- `401`: N/A

---

#### PATCH

**Summary:** Update user profile

**Request Body:** Required

**Responses:**
- `200`: Profile updated
- `400`: N/A
- `401`: N/A

---

## Data Schemas

### Address

**Properties:**

- `city`: string (min: 2, max: 100) ✓
- `country`: string (pattern: `^[A-Z]{2}$`) ✓
- `id`: string ✓
- `isDefault`: boolean
- `label`: string (enum: home, work, other)
- `postalCode`: string (pattern: `^[0-9]{5}(-[0-9]{4})?$`) ✓
- `state`: string (min: 2, max: 50) ✓
- `street`: string (min: 5, max: 200) ✓
- `street2`: string (max: 200)

### AddressInput

**Properties:**

- `city`: string (min: 2, max: 100) ✓
- `country`: string (pattern: `^[A-Z]{2}$`) ✓
- `isDefault`: boolean
- `label`: string (enum: home, work, other)
- `postalCode`: string (pattern: `^[0-9]{5}(-[0-9]{4})?$`) ✓
- `state`: string (min: 2, max: 50) ✓
- `street`: string (min: 5, max: 200) ✓
- `street2`: string (max: 200)

### BankTransferPayment

**Properties:**

- `accountNumber`: string (pattern: `^[0-9]{10,12}$`) ✓
- `routingNumber`: string (pattern: `^[0-9]{9}$`) ✓
- `type`: string (enum: bank_transfer) ✓

### Cart

**Properties:**

- `createdAt`: string ✓
- `id`: string ✓
- `items`: array ✓
- `totals`: object ✓
- `updatedAt`: string ✓
- `userId`: string ✓

### CartItem

**Properties:**

- `customization`: object
- `id`: string ✓
- `productId`: string ✓
- `productImage`: string
- `productName`: string ✓
- `quantity`: integer (min: 1, max: 99) ✓
- `totalPrice`: number (min: 0) ✓
- `unitPrice`: number (min: 0) ✓

### CartTotals

**Properties:**

- `discount`: number (min: 0)
- `shipping`: number (min: 0) ✓
- `subtotal`: number (min: 0) ✓
- `tax`: number (min: 0) ✓
- `total`: number (min: 0) ✓

### CreditCardPayment

**Properties:**

- `cardNumber`: string (pattern: `^[0-9]{16}$`) ✓
- `cardholderName`: string (min: 2) ✓
- `cvv`: string (pattern: `^[0-9]{3,4}$`) ✓
- `expiryMonth`: integer (min: 1, max: 12) ✓
- `expiryYear`: integer (min: 2024, max: 2040) ✓
- `type`: string (enum: credit_card) ✓

### Error

**Properties:**

- `details`: array
- `error`: string ✓
- `message`: string ✓
- `requestId`: string

### Order

**Properties:**

- `billingAddress`: object
- `createdAt`: string ✓
- `estimatedDelivery`: string
- `id`: string ✓
- `items`: array ✓
- `orderNumber`: string (pattern: `^ORD-[0-9]{8}$`)
- `paymentStatus`: string (enum: pending, authorized, captured, failed, refunded)
- `shippingAddress`: object ✓
- `status`: string (enum: pending, processing, shipped, delivered, cancelled) ✓
- `totals`: object ✓
- `trackingNumber`: string
- `updatedAt`: string
- `userId`: string ✓

### OrderInput

**Properties:**

- `billingAddressId`: string
- `paymentMethodId`: string ✓
- `promoCode`: string (pattern: `^[A-Z0-9]{6,12}$`)
- `shippingAddressId`: string ✓
- `specialInstructions`: string (max: 500)

### OrderItem

**Properties:**

- `productId`: string ✓
- `productName`: string ✓
- `quantity`: integer (min: 1) ✓
- `totalPrice`: number (min: 0) ✓
- `unitPrice`: number (min: 0) ✓

### Pagination

**Properties:**

- `limit`: integer (min: 1) ✓
- `page`: integer (min: 1) ✓
- `total`: integer (min: 0) ✓
- `totalPages`: integer (min: 0) ✓

### PayPalPayment

**Properties:**

- `email`: string ✓
- `type`: string (enum: paypal) ✓

### PaymentInput

**Properties:**

- `orderId`: string ✓
- `paymentMethod`: object ✓

### PaymentResult

**Properties:**

- `amount`: number (min: 0) ✓
- `currency`: string (enum: USD, EUR, GBP)
- `failureReason`: string
- `status`: string (enum: success, failed, pending) ✓
- `timestamp`: string ✓
- `transactionId`: string ✓

### Product

**Properties:**

- `category`: string (enum: electronics, clothing, books, home, sports) ✓
- `compareAtPrice`: number (min: 0.01)
- `createdAt`: string ✓
- `description`: string (max: 2000)
- `id`: string (pattern: `^[A-Z0-9]{8}$`) ✓
- `images`: array
- `inStock`: boolean ✓
- `inventory`: object
- `name`: string (min: 3, max: 200) ✓
- `price`: number (min: 0.01, max: 999999.99) ✓
- `rating`: object
- `sku`: string (pattern: `^SKU-[A-Z0-9]{6}$`) ✓
- `tags`: array
- `updatedAt`: string
- `variants`: array

### ProductInput

**Properties:**

- `category`: string (enum: electronics, clothing, books, home, sports) ✓
- `description`: string (max: 2000)
- `initialQuantity`: integer (min: 0)
- `name`: string (min: 3, max: 200) ✓
- `price`: number (min: 0.01, max: 999999.99) ✓
- `sku`: string (pattern: `^SKU-[A-Z0-9]{6}$`) ✓
- `tags`: array

### ProductUpdate

**Properties:**

- `description`: string (max: 2000)
- `inStock`: boolean
- `name`: string (min: 3, max: 200)
- `price`: number (min: 0.01)

### ProductVariant

**Properties:**

- `attributes`: object
- `id`: string ✓
- `name`: string ✓
- `priceModifier`: number ✓
- `sku`: string ✓

### UserProfile

**Properties:**

- `createdAt`: string ✓
- `dateOfBirth`: string
- `email`: string ✓
- `firstName`: string (min: 1, max: 50) ✓
- `id`: string ✓
- `lastName`: string (min: 1, max: 50) ✓
- `phone`: string (pattern: `^\+?[1-9]\d{1,14}$`)
- `preferences`: object

### UserProfileUpdate

**Properties:**

- `firstName`: string (min: 1, max: 50)
- `lastName`: string (min: 1, max: 50)
- `phone`: string (pattern: `^\+?[1-9]\d{1,14}$`)
- `preferences`: object

## Test Scenarios (Manual)

Based on this specification, you should test:

### Contract Validation
- ✅ All endpoints return correct status codes
- ✅ Response schemas match specification
- ✅ Required fields are present
- ✅ Field types match (string, integer, boolean)

### Input Validation
- ✅ Invalid input rejected with 400/422
- ✅ Missing required fields rejected
- ✅ Type validation enforced
- ✅ Constraint validation (min/max, pattern, enum)

### Edge Cases
- ✅ Boundary values (min/max lengths, ranges)
- ✅ Empty arrays and null values
- ✅ Very long strings
- ✅ Special characters

---

*To run automated validation with ACV:*

```bash
acv validate /Users/I764709/api-contract-validator/demo/specs/e-commerce-api.yaml --api-url http://localhost:PORT
```
