export default function TermsOfServicePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Terms of Service</h1>
      <p className="text-gray-600 mb-8">Last Updated: December 15, 2025 | Version 1.0</p>

      <div className="prose prose-gray max-w-none">
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">1. Overview</h2>
          <p>
            Welcome to TopFuelAuto. We provide a vehicle search and alert platform that helps you find vehicles
            across the web by aggregating publicly available listings from third-party sources. We are NOT a
            broker, auction house, or vehicle seller. We simply help you discover listings and redirect you to
            the original sources where the vehicles are actually listed.
          </p>
          <p className="mt-4">
            By accessing or using TopFuelAuto (the "Service"), you agree to be bound by these Terms of Service
            ("Terms"). If you do not agree with these Terms, please do not use our Service.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">2. What We Do (and Don't Do)</h2>
          <h3 className="text-xl font-medium mt-4 mb-2">We Do:</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li>Aggregate publicly available vehicle listings from third-party sources</li>
            <li>Provide search and filtering tools to help you find vehicles</li>
            <li>Send you alerts when new listings match your saved searches</li>
            <li>Redirect you to the original source where the listing is published</li>
            <li>Cache search results temporarily for performance</li>
          </ul>

          <h3 className="text-xl font-medium mt-4 mb-2">We Don't:</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li>Own, sell, or broker vehicles</li>
            <li>Provide bidding or transaction services</li>
            <li>Claim ownership of listing data, images, or vehicle information</li>
            <li>Guarantee the accuracy, availability, or freshness of listings</li>
            <li>Have control over third-party websites or their listings</li>
            <li>Act as an agent for buyers or sellers</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">3. User Accounts and Subscriptions</h2>
          <p>
            To access certain features (such as saved searches and alerts), you must create an account. You are
            responsible for maintaining the confidentiality of your account credentials and for all activities
            that occur under your account.
          </p>
          <p className="mt-4">
            We offer both free and paid subscription plans. Paid plans grant access to additional features as
            described on our pricing page. Subscription fees are charged in advance on a recurring basis (monthly
            or annually). You may cancel your subscription at any time through your account settings.
          </p>
          <p className="mt-4">
            Refunds are provided at our sole discretion. If you cancel a paid subscription, you will retain
            access to premium features until the end of your current billing period.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">4. Acceptable Use</h2>
          <p>You agree NOT to:</p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Use automated tools (bots, scrapers, etc.) to access our Service</li>
            <li>Attempt to bypass rate limits or abuse our API</li>
            <li>Interfere with or disrupt the Service or servers</li>
            <li>Use the Service for any illegal or unauthorized purpose</li>
            <li>Impersonate others or provide false information</li>
            <li>Scrape, copy, or redistribute listing data from our Service</li>
            <li>Violate any applicable laws or regulations</li>
          </ul>
          <p className="mt-4">
            We reserve the right to suspend or terminate accounts that violate these Terms or engage in abusive
            behavior.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">5. Rate Limits and Service Availability</h2>
          <p>
            We implement rate limits to ensure fair usage and protect our infrastructure. Excessive requests may
            result in temporary or permanent restrictions. We reserve the right to modify, suspend, or discontinue
            any part of the Service at any time without notice.
          </p>
          <p className="mt-4">
            Third-party data providers may change their availability, terms, or pricing. We may enable, disable,
            or throttle data sources at our discretion. We do not guarantee uninterrupted access to any specific
            data source.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">6. No Warranties; Service "As Is"</h2>
          <p>
            THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
            IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
            OR NON-INFRINGEMENT.
          </p>
          <p className="mt-4">
            We do not warrant that:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>The Service will be uninterrupted, secure, or error-free</li>
            <li>Listing data will be accurate, complete, or up-to-date</li>
            <li>Search results will meet your requirements</li>
            <li>Any errors will be corrected</li>
          </ul>
          <p className="mt-4">
            You are solely responsible for verifying all information on the original source website before making
            any decisions or taking any actions based on listings found through our Service.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">7. Limitation of Liability</h2>
          <p>
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, TOPFUELAUTO, ITS OFFICERS, DIRECTORS, EMPLOYEES, AND AGENTS
            SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY
            LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE,
            GOODWILL, OR OTHER INTANGIBLE LOSSES, RESULTING FROM:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Your use or inability to use the Service</li>
            <li>Any unauthorized access to or use of our servers and/or any personal information stored therein</li>
            <li>Any interruption or cessation of transmission to or from the Service</li>
            <li>Any bugs, viruses, or other harmful code that may be transmitted through the Service</li>
            <li>Any errors or omissions in any content or listing data</li>
            <li>Any loss or damage of any kind incurred as a result of your use of the Service</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">8. Indemnification</h2>
          <p>
            You agree to indemnify, defend, and hold harmless TopFuelAuto and its officers, directors, employees,
            and agents from and against any claims, liabilities, damages, losses, and expenses, including reasonable
            attorney's fees, arising out of or in any way connected with your access to or use of the Service or
            your violation of these Terms.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">9. Third-Party Links and Content</h2>
          <p>
            Our Service may contain links to third-party websites, services, and content that are not owned or
            controlled by TopFuelAuto. We have no control over, and assume no responsibility for, the content,
            privacy policies, or practices of any third-party websites or services.
          </p>
          <p className="mt-4">
            You acknowledge and agree that TopFuelAuto shall not be responsible or liable, directly or indirectly,
            for any damage or loss caused or alleged to be caused by or in connection with the use of or reliance
            on any such content, goods, or services available on or through any such websites or services.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">10. Intellectual Property</h2>
          <p>
            The Service and its original content (excluding third-party listing data), features, and functionality
            are and will remain the exclusive property of TopFuelAuto and its licensors. The Service is protected
            by copyright, trademark, and other laws.
          </p>
          <p className="mt-4">
            Vehicle listings, images, descriptions, and pricing information displayed on our Service are the
            property of their respective owners and sources. We do not claim ownership of this third-party content.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">11. Privacy</h2>
          <p>
            Your use of the Service is also governed by our{' '}
            <a href="/legal/privacy" className="text-blue-600 hover:underline">
              Privacy Policy
            </a>
            . Please review it to understand how we collect, use, and protect your information.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">12. Changes to Terms</h2>
          <p>
            We reserve the right to modify or replace these Terms at any time. If we make material changes, we
            will notify you by email (if you have provided one) or by posting a notice on the Service prior to
            the effective date of the changes.
          </p>
          <p className="mt-4">
            Your continued use of the Service after any changes constitutes your acceptance of the new Terms. If
            you do not agree to the new Terms, you must stop using the Service.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">13. Termination</h2>
          <p>
            We may terminate or suspend your account and access to the Service immediately, without prior notice
            or liability, for any reason, including if you breach these Terms. Upon termination, your right to
            use the Service will immediately cease.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">14. Governing Law and Jurisdiction</h2>
          <p>
            These Terms shall be governed by and construed in accordance with the laws of the State of Delaware,
            United States, without regard to its conflict of law provisions.
          </p>
          <p className="mt-4">
            Any disputes arising out of or relating to these Terms or the Service shall be resolved exclusively
            in the state or federal courts located in Delaware, and you consent to the personal jurisdiction of
            such courts.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">15. Contact Us</h2>
          <p>
            If you have any questions about these Terms, please contact us through our{' '}
            <a href="/legal/takedown" className="text-blue-600 hover:underline">
              contact page
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
