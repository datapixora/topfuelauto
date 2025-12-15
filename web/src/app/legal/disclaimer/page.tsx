export default function DisclaimerPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Data Sources & Disclaimer</h1>
      <p className="text-gray-600 mb-8">Last Updated: December 15, 2025 | Version 1.0</p>

      <div className="prose prose-gray max-w-none">
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">1. What TopFuelAuto Is</h2>
          <p>
            TopFuelAuto is a vehicle meta-search and alert platform. We help you find vehicles across the web by
            aggregating publicly available listings from multiple third-party sources. Think of us as a search
            engine for vehicles—we don't own, sell, or broker any vehicles ourselves.
          </p>
          <p className="mt-4 font-medium">
            We are NOT:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>A vehicle dealer or broker</li>
            <li>An auction house or bidding platform</li>
            <li>A seller of vehicles</li>
            <li>An agent for buyers or sellers</li>
            <li>Affiliated with or endorsed by any data provider</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">2. Data Sources and Third-Party Providers</h2>
          <p>
            TopFuelAuto aggregates vehicle listing data from various third-party sources and public APIs. These
            sources may include (but are not limited to):
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li><strong>MarketCheck:</strong> Vehicle listings from dealerships and online marketplaces</li>
            <li><strong>Copart Public Pages:</strong> Publicly available auction listings</li>
            <li><strong>Other Third-Party Services:</strong> Additional data providers and public sources</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-2">Important Notes About Data Sources:</h3>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>No Ownership:</strong> We do not own, create, or control the listing data, vehicle images,
              descriptions, or pricing information. All such content belongs to the respective sources and their
              owners.
            </li>
            <li>
              <strong>No Affiliation:</strong> We are not affiliated with, endorsed by, or sponsored by any of the
              data providers mentioned above. Their names and trademarks are the property of their respective owners.
            </li>
            <li>
              <strong>Third-Party Terms:</strong> When you click on a listing to view details, you will be redirected
              to the source website. Your use of those websites is governed by their own terms of service and privacy
              policies.
            </li>
            <li>
              <strong>Provider Changes:</strong> Third-party data providers may change their availability, terms,
              pricing, or API access at any time. We may enable, disable, or throttle data sources at our discretion.
            </li>
            <li>
              <strong>No Guarantee of Availability:</strong> We do not guarantee continuous access to any specific
              data source or provider.
            </li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">3. Trademark and Copyright Notice</h2>
          <p>
            All trademarks, service marks, trade names, and logos displayed on TopFuelAuto are the property of their
            respective owners. The display of such marks does not imply any endorsement, affiliation, or sponsorship
            by or with TopFuelAuto.
          </p>
          <p className="mt-4">
            Examples of third-party trademarks that may appear in search results include but are not limited to:
            MarketCheck, Copart, and various vehicle manufacturer names and logos. These are used solely for
            identification purposes.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">4. Data Accuracy and Freshness</h2>
          <p>
            We make reasonable efforts to display accurate and up-to-date information, but we cannot guarantee:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>
              <strong>Accuracy:</strong> Listing prices, vehicle conditions, mileage, specifications, and descriptions
              may be incorrect, incomplete, or outdated.
            </li>
            <li>
              <strong>Availability:</strong> Vehicles may have been sold, removed, or marked unavailable on the source
              site without being updated in our system.
            </li>
            <li>
              <strong>Freshness:</strong> We may cache search results for performance optimization. Cached data may
              be up to 15 minutes old or more. Real-time availability is NOT guaranteed.
            </li>
            <li>
              <strong>Completeness:</strong> Some listings may be missing information, images, or details due to
              limitations in the source data.
            </li>
          </ul>
          <p className="mt-4 font-medium text-lg">
            YOU MUST VERIFY ALL INFORMATION ON THE ORIGINAL SOURCE WEBSITE BEFORE MAKING ANY DECISIONS OR TAKING
            ANY ACTIONS.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">5. No Warranty or Guarantee</h2>
          <p>
            THE SERVICE AND ALL LISTING DATA ARE PROVIDED "AS IS" WITHOUT ANY WARRANTIES OF ANY KIND.
          </p>
          <p className="mt-4">
            We explicitly disclaim all warranties, express or implied, including but not limited to:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Warranties of accuracy, completeness, or reliability</li>
            <li>Warranties of merchantability or fitness for a particular purpose</li>
            <li>Warranties that the Service will be uninterrupted or error-free</li>
            <li>Warranties that defects will be corrected</li>
            <li>Warranties regarding the quality, condition, or legality of vehicles listed</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">6. No Responsibility for Third-Party Transactions</h2>
          <p>
            TopFuelAuto is NOT involved in any transactions between you and vehicle sellers, dealerships, or auction
            houses. We do not:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Process payments for vehicles</li>
            <li>Facilitate bidding or auctions</li>
            <li>Verify seller credentials or legitimacy</li>
            <li>Inspect vehicles or verify their condition</li>
            <li>Provide escrow or dispute resolution services</li>
            <li>Guarantee the performance or honesty of sellers</li>
          </ul>
          <p className="mt-4 font-medium">
            Any disputes, issues, or claims related to vehicle purchases must be resolved directly with the seller
            or source website. We are not liable for any losses, damages, or disputes arising from third-party
            transactions.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">7. No Automated Scraping Guarantee</h2>
          <p>
            While we make reasonable efforts to maintain data feeds from our sources, we do NOT guarantee:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Continuous availability of any data source</li>
            <li>That all listings from a source will appear in search results</li>
            <li>That scraping or API access will remain functional</li>
            <li>That we will restore broken data feeds within any specific timeframe</li>
          </ul>
          <p className="mt-4">
            Data sources may be temporarily or permanently disabled due to technical issues, rate limiting, provider
            changes, or business decisions.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">8. Rate Limits and Service Restrictions</h2>
          <p>
            We implement rate limits to protect our infrastructure and ensure fair usage. These limits may change
            without notice. Excessive use may result in:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Temporary throttling of search requests</li>
            <li>Suspension of account features</li>
            <li>Account termination</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">9. Limitation of Liability</h2>
          <p>
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, TOPFUELAUTO SHALL NOT BE LIABLE FOR ANY DAMAGES ARISING FROM:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Inaccurate, incomplete, or outdated listing data</li>
            <li>Unavailable or sold vehicles</li>
            <li>Fraudulent listings or sellers</li>
            <li>Service interruptions or data source outages</li>
            <li>Reliance on information displayed in search results</li>
            <li>Third-party website actions or policies</li>
            <li>Any vehicle purchase or transaction</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">10. User Responsibility</h2>
          <p className="font-medium text-lg">
            YOU ARE SOLELY RESPONSIBLE FOR:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-2">
            <li>Verifying all vehicle information on the original source website</li>
            <li>Conducting due diligence before making any purchase decisions</li>
            <li>Inspecting vehicles in person or through a trusted third party</li>
            <li>Reviewing seller terms, return policies, and warranties</li>
            <li>Understanding auction rules, fees, and buyer premiums</li>
            <li>Complying with all applicable laws and regulations</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">11. Changes to Data Sources</h2>
          <p>
            We reserve the right to add, remove, or modify data sources at any time without notice. We are not
            obligated to provide access to any specific data source or provider.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">12. Contact for Rights Holders</h2>
          <p>
            If you believe your content, trademark, or copyrighted material is being displayed inappropriately on
            TopFuelAuto, please see our{' '}
            <a href="/legal/takedown" className="text-blue-600 hover:underline">
              Takedown Request page
            </a>
            {' '}for information on how to submit a request.
          </p>
        </section>

        <section className="mb-8 border-t pt-8">
          <h2 className="text-2xl font-semibold mb-4">خلاصه فارسی (Persian Summary)</h2>
          <div className="text-right" dir="rtl">
            <p className="mb-4">
              تاپ‌فیول‌اتو یک موتور جستجوی خودرو است که اطلاعات عمومی را از منابع مختلف جمع‌آوری می‌کند.
              ما خودرو نمی‌فروشیم و کارگزار یا حراج نیستیم.
            </p>
            <p className="mb-4">
              <strong>منابع داده:</strong> ما از منابع عمومی مانند MarketCheck و Copart استفاده می‌کنیم.
              ما مالک این اطلاعات نیستیم و وابسته به این شرکت‌ها نیستیم. نام‌های تجاری متعلق به صاحبان آنها است.
            </p>
            <p className="mb-4">
              <strong>دقت اطلاعات:</strong> ما نمی‌توانیم دقت، کامل بودن یا به‌روز بودن اطلاعات را تضمین کنیم.
              اطلاعات ممکن است قدیمی یا نادرست باشد. خودروها ممکن است فروخته شده باشند. شما باید همه اطلاعات
              را در وب‌سایت اصلی بررسی کنید.
            </p>
            <p className="mb-4">
              <strong>بدون ضمانت:</strong> سرویس "همان‌طور که هست" ارائه می‌شود بدون هیچ تضمینی. ما مسئولیتی
              در قبال معاملات شما نداریم. هرگونه مشکل باید مستقیماً با فروشنده حل شود.
            </p>
            <p>
              <strong>مسئولیت شما:</strong> شما باید اطلاعات را بررسی کنید، خودرو را معاینه کنید، و قوانین
              را رعایت کنید.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
