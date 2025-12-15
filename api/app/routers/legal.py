"""
Legal documents API endpoints.
Provides versioned access to Terms of Service, Privacy Policy, Disclaimer, and Takedown pages.
"""
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


class LegalDocument(BaseModel):
    """Legal document response model"""
    title: str
    version: str
    last_updated: str
    content: str


LEGAL_DOCUMENTS = {
    "terms": {
        "title": "Terms of Service",
        "version": "1.0",
        "last_updated": "2025-12-15",
        "content": """
# Terms of Service

**Last Updated:** December 15, 2025 | **Version:** 1.0

## 1. Overview

Welcome to TopFuelAuto. We provide a vehicle search and alert platform that helps you find vehicles across the web by aggregating publicly available listings from third-party sources. We are NOT a broker, auction house, or vehicle seller. We simply help you discover listings and redirect you to the original sources where the vehicles are actually listed.

By accessing or using TopFuelAuto (the "Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree with these Terms, please do not use our Service.

## 2. What We Do (and Don't Do)

### We Do:
- Aggregate publicly available vehicle listings from third-party sources
- Provide search and filtering tools to help you find vehicles
- Send you alerts when new listings match your saved searches
- Redirect you to the original source where the listing is published
- Cache search results temporarily for performance

### We Don't:
- Own, sell, or broker vehicles
- Provide bidding or transaction services
- Claim ownership of listing data, images, or vehicle information
- Guarantee the accuracy, availability, or freshness of listings
- Have control over third-party websites or their listings
- Act as an agent for buyers or sellers

## 3. User Accounts and Subscriptions

To access certain features (such as saved searches and alerts), you must create an account. You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.

We offer both free and paid subscription plans. Paid plans grant access to additional features as described on our pricing page. Subscription fees are charged in advance on a recurring basis (monthly or annually). You may cancel your subscription at any time through your account settings.

Refunds are provided at our sole discretion. If you cancel a paid subscription, you will retain access to premium features until the end of your current billing period.

## 4. No Warranties; Service "As Is"

THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND. We do not warrant that the Service will be uninterrupted, secure, or error-free, or that listing data will be accurate, complete, or up-to-date.

You are solely responsible for verifying all information on the original source website before making any decisions or taking any actions based on listings found through our Service.

For the complete Terms of Service, please visit: https://topfuelauto.com/legal/terms
        """.strip()
    },
    "privacy": {
        "title": "Privacy Policy",
        "version": "1.0",
        "last_updated": "2025-12-15",
        "content": """
# Privacy Policy

**Last Updated:** December 15, 2025 | **Version:** 1.0

## 1. Introduction

TopFuelAuto ("we", "us", or "our") respects your privacy and is committed to protecting your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our vehicle search and alert platform.

## 2. Information We Collect

### 2.1 Information You Provide
- **Account Information:** Email address, password, and optional profile information
- **Saved Searches:** Search queries, filters, and alert preferences you save
- **Payment Information:** Processed by our payment provider (Stripe); we do not store full credit card numbers

### 2.2 Information Collected Automatically
- **Usage Data:** Pages visited, features used, search queries, time spent on the Service
- **Device Information:** Browser type, operating system, device identifiers
- **IP Address:** Your IP address for rate limiting and security purposes
- **Cookies and Similar Technologies:** Session cookies, authentication tokens, preference cookies

## 3. How We Use Your Information

We use the information we collect to:
- Provide, operate, and maintain the Service
- Process your searches and display relevant vehicle listings
- Send you alerts when new listings match your saved searches
- Process your subscription payments
- Authenticate your account and prevent fraud
- Enforce rate limits and prevent abuse

## 4. How We Share Your Information

We do NOT sell your personal information. We may share your information with:
- **Service Providers:** Payment processors (Stripe), hosting providers, email services
- **Legal Requirements:** If required by law, court order, or government request

## 5. Your Rights and Choices

- **Access and Correction:** You may access and update your account information
- **Data Deletion:** You may delete your account at any time
- **Email Preferences:** You may opt out of marketing emails

For the complete Privacy Policy, please visit: https://topfuelauto.com/legal/privacy
        """.strip()
    },
    "disclaimer": {
        "title": "Data Sources & Disclaimer",
        "version": "1.0",
        "last_updated": "2025-12-15",
        "content": """
# Data Sources & Disclaimer

**Last Updated:** December 15, 2025 | **Version:** 1.0

## 1. What TopFuelAuto Is

TopFuelAuto is a vehicle meta-search and alert platform. We help you find vehicles across the web by aggregating publicly available listings from multiple third-party sources. Think of us as a search engine for vehicles—we don't own, sell, or broker any vehicles ourselves.

**We are NOT:**
- A vehicle dealer or broker
- An auction house or bidding platform
- A seller of vehicles
- An agent for buyers or sellers
- Affiliated with or endorsed by any data provider

## 2. Data Sources and Third-Party Providers

TopFuelAuto aggregates vehicle listing data from various third-party sources and public APIs. These sources may include (but are not limited to):
- **MarketCheck:** Vehicle listings from dealerships and online marketplaces
- **Copart Public Pages:** Publicly available auction listings
- **Other Third-Party Services:** Additional data providers and public sources

### Important Notes About Data Sources:
- **No Ownership:** We do not own, create, or control the listing data, vehicle images, descriptions, or pricing information
- **No Affiliation:** We are not affiliated with, endorsed by, or sponsored by any of the data providers
- **Third-Party Terms:** When you click on a listing, you will be redirected to the source website
- **Provider Changes:** Third-party data providers may change their availability at any time

## 3. Data Accuracy and Freshness

We cannot guarantee:
- **Accuracy:** Listing prices, vehicle conditions, specifications may be incorrect or outdated
- **Availability:** Vehicles may have been sold or removed
- **Freshness:** We may cache search results for performance; data may not be real-time
- **Completeness:** Some listings may be missing information or details

**YOU MUST VERIFY ALL INFORMATION ON THE ORIGINAL SOURCE WEBSITE BEFORE MAKING ANY DECISIONS.**

## 4. No Warranty or Guarantee

THE SERVICE AND ALL LISTING DATA ARE PROVIDED "AS IS" WITHOUT ANY WARRANTIES OF ANY KIND.

For the complete Disclaimer, please visit: https://topfuelauto.com/legal/disclaimer
        """.strip()
    },
    "takedown": {
        "title": "Takedown Requests & Contact",
        "version": "1.0",
        "last_updated": "2025-12-15",
        "content": """
# Takedown Requests & Contact

**Last Updated:** December 15, 2025 | **Version:** 1.0

## 1. Overview

TopFuelAuto aggregates publicly available vehicle listings from third-party sources. We do not own, create, or control the content displayed in search results. All listing data, images, and descriptions belong to their respective owners and sources.

If you believe that content displayed on TopFuelAuto infringes your intellectual property rights or violates your rights in any way, you may submit a takedown request.

## 2. Copyright Infringement (DMCA)

TopFuelAuto respects intellectual property rights and complies with the Digital Millennium Copyright Act (DMCA). To submit a DMCA takedown request, please provide:

### Required Information:
- **Identification of the copyrighted work:** Describe the work you claim has been infringed
- **Location of infringing material:** Provide specific URL(s) on TopFuelAuto
- **Your contact information:** Name, address, email, and phone number
- **Good faith statement:** Statement that you believe the use is not authorized
- **Accuracy statement:** Statement under penalty of perjury
- **Signature:** Your physical or electronic signature

## 3. How to Submit a Takedown Request

To submit a takedown request, please send an email to:

**legal@topfuelauto.com**
*(Placeholder - Replace with actual email)*

Please include "DMCA Takedown Request" or "Takedown Request" in the subject line.

## 4. Response Time

We will review all takedown requests in good faith and respond within a reasonable timeframe, typically within 5-7 business days.

If we determine that the request is valid, we will:
- Remove the content from our search results and cached data
- Notify you of the action taken

**Note:** Removing content from TopFuelAuto does NOT remove it from the original source website. You may need to contact the source directly.

## 5. General Contact

For general inquiries, support, or non-legal matters:

**support@topfuelauto.com**
*(Placeholder - Replace with actual email)*

For the complete Takedown & Contact information, please visit: https://topfuelauto.com/legal/takedown
        """.strip()
    }
}


@router.get("/terms", response_model=LegalDocument)
def get_terms_of_service():
    """Get Terms of Service document"""
    return LEGAL_DOCUMENTS["terms"]


@router.get("/privacy", response_model=LegalDocument)
def get_privacy_policy():
    """Get Privacy Policy document"""
    return LEGAL_DOCUMENTS["privacy"]


@router.get("/disclaimer", response_model=LegalDocument)
def get_disclaimer():
    """Get Data Sources & Disclaimer document"""
    return LEGAL_DOCUMENTS["disclaimer"]


@router.get("/takedown", response_model=LegalDocument)
def get_takedown_info():
    """Get Takedown Request & Contact information"""
    return LEGAL_DOCUMENTS["takedown"]
