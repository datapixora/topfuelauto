export default function PrivacyPolicyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-gray-600 mb-8">Last Updated: December 15, 2025 | Version 1.0</p>

      <div className="prose prose-gray max-w-none">
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
          <p>
            TopFuelAuto ("we", "us", or "our") respects your privacy and is committed to protecting your personal
            information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information
            when you use our vehicle search and alert platform.
          </p>
          <p className="mt-4">
            Please read this Privacy Policy carefully. By using our Service, you consent to the practices described
            in this policy.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>

          <h3 className="text-xl font-medium mt-4 mb-2">2.1 Information You Provide</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Account Information:</strong> Email address, password, and optional profile information</li>
            <li><strong>Saved Searches:</strong> Search queries, filters, and alert preferences you save</li>
            <li><strong>Payment Information:</strong> Processed by our payment provider (Stripe); we do not store full credit card numbers</li>
            <li><strong>Communications:</strong> Messages you send us through contact forms or email</li>
          </ul>

          <h3 className="text-xl font-medium mt-4 mb-2">2.2 Information Collected Automatically</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Usage Data:</strong> Pages visited, features used, search queries, time spent on the Service</li>
            <li><strong>Device Information:</strong> Browser type, operating system, device identifiers</li>
            <li><strong>IP Address:</strong> Your IP address for rate limiting and security purposes</li>
            <li><strong>Cookies and Similar Technologies:</strong> Session cookies, authentication tokens, preference cookies</li>
          </ul>

          <h3 className="text-xl font-medium mt-4 mb-2">2.3 Information from Third Parties</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Data Providers:</strong> We receive publicly available vehicle listing data from third-party sources (e.g., MarketCheck, Copart public APIs)</li>
            <li><strong>Payment Processors:</strong> Transaction confirmations and payment status from Stripe</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
          <p>We use the information we collect to:</p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Provide, operate, and maintain the Service</li>
            <li>Process your searches and display relevant vehicle listings</li>
            <li>Send you alerts when new listings match your saved searches</li>
            <li>Process your subscription payments</li>
            <li>Authenticate your account and prevent fraud</li>
            <li>Enforce rate limits and prevent abuse</li>
            <li>Respond to your inquiries and support requests</li>
            <li>Improve and optimize the Service</li>
            <li>Analyze usage patterns and trends</li>
            <li>Send you administrative notifications (e.g., service updates, security alerts)</li>
            <li>Comply with legal obligations</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">4. How We Share Your Information</h2>
          <p>We do NOT sell your personal information. We may share your information with:</p>

          <h3 className="text-xl font-medium mt-4 mb-2">4.1 Service Providers</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Payment Processors:</strong> Stripe for subscription billing</li>
            <li><strong>Hosting Providers:</strong> Cloud infrastructure providers (e.g., Render, Vercel)</li>
            <li><strong>Email Services:</strong> To send alerts and notifications</li>
          </ul>

          <h3 className="text-xl font-medium mt-4 mb-2">4.2 Data Providers</h3>
          <p className="mt-2">
            When you click on a listing to view details on the source website, you will be redirected to that
            third-party site. We do not control how those sites use your information. Please review their privacy
            policies.
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">4.3 Legal Requirements</h3>
          <p className="mt-2">
            We may disclose your information if required by law, court order, or government request, or if we
            believe disclosure is necessary to protect our rights, your safety, or the safety of others.
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">4.4 Business Transfers</h3>
          <p className="mt-2">
            In the event of a merger, acquisition, or sale of assets, your information may be transferred to the
            acquiring entity.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">5. Data Retention</h2>
          <p>
            We retain your personal information for as long as your account is active or as needed to provide you
            the Service. You may delete your account at any time, and we will delete your personal information
            within 30 days, except where retention is required by law or for legitimate business purposes (e.g.,
            fraud prevention, financial records).
          </p>
          <p className="mt-4">
            Search history and cached listing data may be retained for up to 90 days for performance optimization.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">6. Data Security</h2>
          <p>
            We implement reasonable technical and organizational measures to protect your information from
            unauthorized access, disclosure, alteration, or destruction. These measures include:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Encrypted connections (HTTPS/TLS)</li>
            <li>Password hashing and secure authentication</li>
            <li>Access controls and monitoring</li>
            <li>Regular security assessments</li>
          </ul>
          <p className="mt-4">
            However, no method of transmission over the internet or electronic storage is 100% secure. We cannot
            guarantee absolute security of your information.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">7. Your Rights and Choices</h2>

          <h3 className="text-xl font-medium mt-4 mb-2">7.1 Access and Correction</h3>
          <p className="mt-2">
            You may access and update your account information through your account settings.
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">7.2 Data Deletion</h3>
          <p className="mt-2">
            You may delete your account at any time. Upon deletion, we will remove your personal information within
            30 days, subject to legal retention requirements.
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">7.3 Email Preferences</h3>
          <p className="mt-2">
            You may opt out of marketing emails by clicking the unsubscribe link in any email. You cannot opt out
            of essential service notifications (e.g., account security alerts).
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">7.4 Cookies</h3>
          <p className="mt-2">
            You can control cookies through your browser settings. Disabling cookies may limit functionality of
            the Service.
          </p>

          <h3 className="text-xl font-medium mt-4 mb-2">7.5 Do Not Track</h3>
          <p className="mt-2">
            We do not currently respond to Do Not Track (DNT) signals.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">8. Children's Privacy</h2>
          <p>
            Our Service is not intended for children under 13 years of age. We do not knowingly collect personal
            information from children under 13. If you are a parent or guardian and believe your child has provided
            us with personal information, please contact us, and we will delete it.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">9. International Users</h2>
          <p>
            Our Service is operated in the United States. If you are located outside the United States, your
            information will be transferred to and processed in the United States. By using the Service, you consent
            to this transfer.
          </p>
          <p className="mt-4">
            Users in the European Economic Area (EEA), UK, or other jurisdictions with data protection laws may
            have additional rights under applicable regulations (e.g., GDPR). Please contact us to exercise these
            rights.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">10. Third-Party Services and Links</h2>
          <p>
            Our Service contains links to third-party websites (vehicle listing sources, payment processors, etc.).
            We are not responsible for the privacy practices of these third parties. We encourage you to review
            their privacy policies.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">11. Changes to This Privacy Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. We will notify you of material changes by email
            (if you have provided one) or by posting a notice on the Service. The "Last Updated" date at the top
            will reflect when changes were made.
          </p>
          <p className="mt-4">
            Your continued use of the Service after any changes constitutes your acceptance of the new Privacy
            Policy.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">12. Contact Us</h2>
          <p>
            If you have any questions about this Privacy Policy or how we handle your information, please contact
            us through our{' '}
            <a href="/legal/takedown" className="text-blue-600 hover:underline">
              contact page
            </a>
            .
          </p>
        </section>

        <section className="mb-8 border-t pt-8">
          <h2 className="text-2xl font-semibold mb-4">خلاصه فارسی (Persian Summary)</h2>
          <div className="text-right" dir="rtl">
            <p className="mb-4">
              ما به حریم خصوصی شما احترام می‌گذاریم. این سیاست توضیح می‌دهد که چگونه اطلاعات شما را جمع‌آوری،
              استفاده و محافظت می‌کنیم.
            </p>
            <p className="mb-4">
              <strong>اطلاعاتی که جمع‌آوری می‌کنیم:</strong> ایمیل، رمز عبور، جستجوهای ذخیره شده، اطلاعات دستگاه،
              آدرس IP، و کوکی‌ها. اطلاعات پرداخت توسط Stripe پردازش می‌شود و ما شماره کارت کامل را ذخیره نمی‌کنیم.
            </p>
            <p className="mb-4">
              <strong>استفاده از اطلاعات:</strong> برای ارائه سرویس، ارسال هشدارها، پردازش پرداخت، جلوگیری از
              سوءاستفاده، و بهبود سرویس. ما اطلاعات شخصی شما را نمی‌فروشیم.
            </p>
            <p className="mb-4">
              <strong>حقوق شما:</strong> می‌توانید اطلاعات خود را مشاهده، به‌روزرسانی یا حذف کنید. می‌توانید
              حساب خود را حذف کنید و ما اطلاعات را ظرف ۳۰ روز حذف خواهیم کرد.
            </p>
            <p>
              برای سوالات، با ما تماس بگیرید.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
