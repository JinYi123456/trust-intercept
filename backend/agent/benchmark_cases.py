"""Benchmark case set for the Evaluation Lab.

Case provenance (no fabricated sourcing):
- source="sms_spam_collection": verbatim messages from the SMS Spam Collection
  v.1 (Almeida et al., ACM DOCENG'11; UCI ML Repository, id 228). Labels are
  the dataset's own ground truth (spam -> scam, ham -> legit). Copyright
  remains with the dataset authors; used here in unmodified excerpt form for
  research/evaluation.
- source="synthetic": written by the TRUST//INTERCEPT team for this benchmark,
  reflecting publicly reported scam patterns (parcel fees, Macau scam,
  e-wallet freeze, LHDN/PDRM impersonation). NOT real victim messages.
- CIC-Trap4Phish: NOT integrated. The dataset page returned HTTP 404 at the
  time of benchmark construction and access normally requires a request to
  the CIC team. Recorded here as a documented gap, not as a data source.

Channel tags record how the artefact would arrive (sms/email/url/qr). URL and
QR payloads are benchmarked as their decoded text representation; the URL-input
API path is exercised separately by the backend test-suite.

Language tags: en | ms (Bahasa Malaysia) | manglish (colloquial Malaysian
English). The rule engine is English-keyword based, so Malay cases measure the
known multilingual gap honestly.
"""
from __future__ import annotations

CASES: list[dict[str, str]] = [
    # ------------------------------------------------------------------
    # Verbatim SMS Spam Collection — spam (ground truth: spam -> scam)
    # ------------------------------------------------------------------
    {"id": "uci_sp_01", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "URGENT! We are trying to contact U. Todays draw shows that you have won a £2000 prize GUARANTEED. Call 09058094507 from land line. Claim 3030. Valid 12hrs only"},
    {"id": "uci_sp_02", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Congratulations ur awarded 500 of CD vouchers or 125gift guaranteed & Free entry 2 100 wkly draw txt MUSIC to 87066 TnCs www.Ldew.com1win150ppmx3age16"},
    {"id": "uci_sp_03", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Thanks for your subscription to Ringtone UK your mobile will be charged £5/month Please confirm by replying YES or NO. If you reply NO you will not be charged"},
    {"id": "uci_sp_04", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Hi. Customer Loyalty Offer:The NEW Nokia6650 Mobile from ONLY £10 at TXTAUCTION! Txt word: START to No: 81151 & get yours Now! 4T&Ctxt TC 150p/MTmsg"},
    {"id": "uci_sp_05", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "URGENT! We are trying to contact you. Last weekends draw shows that you have won a £900 prize GUARANTEED. Call 09061701939. Claim code S89. Valid 12hrs only"},
    {"id": "uci_sp_06", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Thanks for your ringtone order, ref number K718. Your mobile will be charged £4.50. Should your tone not arrive please call customer services on 09065069120"},
    {"id": "uci_sp_07", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "PRIVATE! Your 2004 Account Statement for 07742676969 shows 786 unredeemed Bonus Points. To claim call 08719180248 Identifier Code: 45239 Expires"},
    {"id": "uci_sp_08", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Gr8 Poly tones 4 ALL mobs direct 2u rply with POLY TITLE to 8007 eg POLY BREATHE1 Titles: CRAZYIN, SLEEPINGWITH, FINEST, YMCA :getzed.co.uk POBox365O4W45WQ 300p"},
    {"id": "uci_sp_09", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "URGENT! Your Mobile number has been awarded with a £2000 Bonus Caller Prize. Call 09058095201 from land line. Valid 12hrs only"},
    {"id": "uci_sp_10", "label": "scam", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "December only! Had your mobile 11mths+? You are entitled to update to the latest colour camera mobile for Free! Call The Mobile Update Co FREE on 08002986906"},
    # ------------------------------------------------------------------
    # Verbatim SMS Spam Collection — ham (ground truth: ham -> legit)
    # ------------------------------------------------------------------
    {"id": "uci_hm_01", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Sorry, I'll call later in meeting."},
    {"id": "uci_hm_02", "label": "legit", "channel": "sms", "language": "manglish", "source": "sms_spam_collection",
     "text": "K. Did you call me just now ah?"},
    {"id": "uci_hm_03", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "I call you later, don't have network. If urgnt, sms me."},
    {"id": "uci_hm_04", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Sir, I need AXIS BANK account no and bank address."},
    {"id": "uci_hm_05", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Mark works tomorrow. He gets out at 5. His work is by your house so he can meet u afterwards."},
    {"id": "uci_hm_06", "label": "legit", "channel": "sms", "language": "manglish", "source": "sms_spam_collection",
     "text": "U can call me now..."},
    {"id": "uci_hm_07", "label": "legit", "channel": "sms", "language": "manglish", "source": "sms_spam_collection",
     "text": "I am waiting machan. Call me once you free."},
    {"id": "uci_hm_08", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "Hello. Damn this christmas thing. I think i have decided to keep this mp3 that doesnt work."},
    {"id": "uci_hm_09", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "No calls..messages..missed calls"},
    {"id": "uci_hm_10", "label": "legit", "channel": "sms", "language": "en", "source": "sms_spam_collection",
     "text": "As per your request 'Melle Melle (Oru Minnaminunginte Nurungu Vettam)' has been set as your callertune for all Callers. Press *9 to copy your friends Callertune"},
    # ------------------------------------------------------------------
    # Synthetic — English SMS scams (Malaysia patterns)
    # ------------------------------------------------------------------
    {"id": "syn_scam_poslaju", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "PosLaju: Your parcel is HELD at our depot due to an unpaid delivery fee of RM3.90. Settle within 24 hours at https://bit.ly/plj-8812 or it will be returned. Enter your IC and card number to release."},
    {"id": "syn_scam_maybank", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "MAYBANK SECURITY: Your account will be suspended today. Verify immediately at https://maybank-secure.info and provide your password and OTP."},
    {"id": "syn_scam_macau", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "PDRM HQ NOTICE: There is a criminal case and arrest warrant against your name for money laundering. Cooperate or be arrested today. Transfer the clearance sum to the officer's account. Do not tell anyone."},
    {"id": "syn_scam_tng", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Touch 'n Go eWallet: Your account will be FROZEN in 12 hours due to unusual activity. Verify your identity now at https://tng-verify.top and enter your PIN to unfreeze."},
    {"id": "syn_scam_lhdn", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "LHDN: You are eligible for a tax refund of RM1,240.00. Submit your bank account details at https://lhdn-refund.info within 48 hours or the refund is forfeited."},
    {"id": "syn_scam_task", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "JOB OFFER: Earn RM300/day doing simple product reviews from home. Pay RM50 registration to start today. Transfer to the HR account and send your IC copy."},
    {"id": "syn_scam_insurance", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Your insurance policy lapses tonight! Pay RM99.90 now at https://pay-policy.click to keep coverage. Urgent - final notice. Call +6012-9988776 to confirm your card details."},
    {"id": "syn_scam_shopee", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Shopee: Congratulations! You won the monthly lucky draw - iPhone 15. Claim within 12 hours at https://shopee-winner.click, pay RM18 courier fee first."},
    # ------------------------------------------------------------------
    # Synthetic — Bahasa Malaysia scams
    # ------------------------------------------------------------------
    {"id": "syn_ms_parcel", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "PosLaju: Bungkusan anda ditahan di depot kerana yuran penghantaran tidak dibayar RM2.50. Bayar dalam 24 jam di https://bit.ly/plj-991 untuk pengeluaran. Sila lengkapkan maklumat kad kredit anda."},
    {"id": "syn_ms_bank", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Maybank: Akaun anda akan diblokir hari ini kerana aktiviti mencurigakan. Sahkan segera di https://maybank-malaysia.info dan masukkan kata laluan serta OTP anda."},
    {"id": "syn_ms_tng", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Touch 'n Go eWallet: Akaun anda akan dibekukan dalam 12 jam. Sahkan segera di pautan ini dan berikan nombor PIN anda untuk pengesahan identiti."},
    {"id": "syn_ms_lhdn", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "LHDN: Tahniah, anda layak menerima bayaran balik cukai RM1,240.00. Sila isi maklumat akaun bank anda di pautan berikut dalam 48 jam. https://bayaran-balik-lhdn.info"},
    {"id": "syn_ms_macau", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Ini Jabatan Imigresen Malaysia. Terdapat kes jenayah dan waran tangkap atas nama anda berhubung pengubahan wang haram. Bayar melalui akaun yang diberikan hari ini untuk menyelesaikan kes. Jangan beritahu keluarga anda."},
    {"id": "syn_ms_prize", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Tahniah! Anda telah memenangi hadiah utama iPhone 15 dalam cabutan bertuah. Bayar yuran pos RM18 untuk menuntut hadiah. Klik https://bit.ly/hadiah-12 hari ini juga."},
    # ------------------------------------------------------------------
    # Synthetic — Manglish scams
    # ------------------------------------------------------------------
    {"id": "syn_ml_parcel", "label": "scam", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "J&T Express: your parcel got stuck at customs lah, pay RM4 handling fee first then we can deliver. Click https://bit.ly/jt-fee4 to settle, today last day."},
    {"id": "syn_ml_bank", "label": "scam", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "Eh your Maybank account kena blocked already la. Quick quick verify here https://mbb-verify.top else cannot use. Need your OTP also."},
    {"id": "syn_ml_police", "label": "scam", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "This is PDRM officer speaking. Got one criminal case under your name, money laundering. If you don't settle the summon today they will come and arrest you. Pay via the account we give you now."},
    {"id": "syn_ml_tng", "label": "scam", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "TNG eWallet kena frozen liau. Verify your identity within 2 hours at this link and put your PIN to unfreeze, later cannot pay liao. https://tng-unfreeze.click"},
    # ------------------------------------------------------------------
    # Synthetic — email channel scams
    # ------------------------------------------------------------------
    {"id": "syn_em_lhdn", "label": "scam", "channel": "email", "language": "en", "source": "synthetic",
     "text": "From: e-Filing LHDN <no-reply@lhdn-refund.tax-gov-my.com> Subject: Tax Refund Pending Action. Dear taxpayer, your refund of RM2,314.50 is on hold. Confirm your banking details at https://lhdn-refund.tax-gov-my.com within 48 hours or the refund will be forfeited."},
    {"id": "syn_em_dhl", "label": "scam", "channel": "email", "language": "en", "source": "synthetic",
     "text": "From: DHL Express <tracking@dhl-parcel-notify.com> Subject: Shipment on hold - customs charges. Your shipment DHL7781293 is held at KLIA customs. Pay the RM12.90 clearance fee at https://dhl-pay-fee.com to release it. Failure to pay within 24 hours returns the package."},
    {"id": "syn_em_job", "label": "scam", "channel": "email", "language": "en", "source": "synthetic",
     "text": "Congratulations! You are selected for the Data Entry position (RM3,800/month, work from home). To activate your employment, pay the RM180 processing fee via bank transfer to the HR account today."},
    # ------------------------------------------------------------------
    # Synthetic — URL / QR channel scams (decoded payload representation)
    # ------------------------------------------------------------------
    {"id": "syn_url_bitly", "label": "scam", "channel": "url", "language": "en", "source": "synthetic",
     "text": "https://bit.ly/pos-3x9f?claim=parcel — link received alone in SMS, shortened destination unknown."},
    {"id": "syn_qr_payment", "label": "scam", "channel": "qr", "language": "en", "source": "synthetic",
     "text": "QR decoded payload: https://pay.now-claim.info/parcel?fee=4.90&id=QX-2213"},
    {"id": "syn_url_prize", "label": "scam", "channel": "url", "language": "en", "source": "synthetic",
     "text": "https://t.co/xYz991?claim=prize — you have won! Open to claim your reward."},
    # ------------------------------------------------------------------
    # Synthetic — legitimate (English / Malay / Manglish)
    # ------------------------------------------------------------------
    {"id": "syn_lg_poslaju", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "PosLaju Malaysia: Your item EM993214521MY is out for delivery today. Track at poslaju.com.my/track. No payment is required."},
    {"id": "syn_lg_jt", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "J&T Express: Your parcel JT2299 is scheduled for redelivery tomorrow 10am-1pm because nobody was home. Reschedule in the J&T app if needed."},
    {"id": "syn_lg_maybank", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Maybank: Your October e-statement is ready in the MAE app. Open the app to view it. We will never ask for your password or OTP via SMS."},
    {"id": "syn_lg_tng", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Touch 'n Go eWallet: You paid RM18.50 to KFC Malaysia on 12 Oct at 1:32pm. This is an official receipt. No action needed."},
    {"id": "syn_lg_lhdn", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "LHDNM: e-Filing acknowledgment. Your BE form was submitted successfully on 10 Oct. Receipt available in the MyTax portal. Do not reply to this SMS."},
    {"id": "syn_lg_school", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "SMK Taman Ilmu: Parent-teacher meeting this Saturday 9am at Dewan Besar. Please confirm attendance with your child's class teacher."},
    {"id": "syn_lg_clinic", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Klinik Sehat: Reminder - your appointment with Dr. Lim is this Thursday 3:30pm. Reply CANCEL to change. No fees involved."},
    {"id": "syn_lg_delivered", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Ninja Van: Your parcel NV88123 was delivered and signed at 2:15pm today. Thank you for shopping with us."},
    {"id": "syn_lg_card", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "CIMB: Your new debit card has been mailed and will arrive in 3-5 working days. Activate it in the CIMB Clicks app when it arrives."},
    {"id": "syn_lg_telco", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Celcom: Your monthly bill of RM68 is due on the 25th. View it in the Celcom Life app. Auto-billing is active."},
    {"id": "syn_lg_qr_wifi", "label": "legit", "channel": "qr", "language": "en", "source": "synthetic",
     "text": "QR decoded payload: WIFI:T:WPA;S=CafeAzlan;P:kopiluv4321;;"},
    {"id": "syn_lg_url_dhl", "label": "legit", "channel": "url", "language": "en", "source": "synthetic",
     "text": "Track your DHL shipment at https://www.dhl.com/track/D-9823 — no action needed."},
    {"id": "syn_lg_ms_jim", "label": "legit", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Jabatan Imigresen: Tempahan temujanji anda untuk pengurusan pasport telah disahkan pada 20 Okt, jam 10 pagi. Bawa dokumen asal ke kaunter. Tiada bayaran diperlukan."},
    {"id": "syn_lg_ms_receipt", "label": "legit", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Maybank: Resit rasmi. Pembayaran bil Astro RM85.60 berjaya pada 12 Okt, jam 8:15 malam. Tiada tindakan diperlukan."},
    {"id": "syn_lg_ml_pacakge", "label": "legit", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "Boss, parcel from Lazada already put at guardhouse ya. Collect before 10pm. Thanks!"},
    # ------------------------------------------------------------------
    # Synthetic — borderline (legit-ish or ambiguous; predicted positive
    # on these counts as false-positive pressure)
    # ------------------------------------------------------------------
    {"id": "bln_stop", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "You have 1 new voicemail. Reply STOP to opt out of these notifications."},
    {"id": "bln_appt_map", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Appointment reminder: dental check-up tomorrow 11am. Map: https://maps.google.com/xyz. Reply to reschedule."},
    {"id": "bln_refund", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Your refund of RM89.90 has been processed and will appear in your account in 3-5 working days. No action needed."},
    {"id": "bln_bank_confirm", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Maybank: Did you authorise a RM450 transfer to ALI BIN ABU? If you did not make this transaction, call the number on the back of your card immediately."},
    {"id": "bln_einvoice", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Your e-invoice for order 88213 is ready. View it in the Shopee app under Purchases: https://shopee.com.my/einv/88213"},
    {"id": "bln_rate", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Thanks for contacting our support team today. Rate your chat from 1-5 by replying to this SMS. Standard message rates apply."},
    {"id": "bln_pickup", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Parcel pickup reminder: collect your parcel at Pickup Point Kulai by Friday 9pm or it will be returned to sender."},
    {"id": "bln_charity", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "FLOOD RELIEF APPEAL: Donate to feed 100 displaced families this month. Registered NGO since 2009. Donate at our official website or mosque counters only."},
    {"id": "bln_roadtax", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "JPJ: Your road tax expires in 14 days. Renew online at the myJPJ app or any post office branch."},
    {"id": "bln_roaming", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Yes 4G: Roaming is now active on your line. Data roaming rates apply according to your plan. Manage settings in the Yes app."},
    {"id": "bln_sale", "label": "borderline", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "MEGA SALE: Up to 70% off sneakers this weekend only at our Sunway store! Show this SMS for extra 5% off. While stocks last."},
    {"id": "bln_address", "label": "borderline", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Your shipment requires address confirmation before customs clearance. Please verify the delivery address in the seller's app. No payment is requested."},
    # ------------------------------------------------------------------
    # Synthetic — adversarial wording
    # ------------------------------------------------------------------
    {"id": "adv_safe_reminder", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Security reminder: criminals may use URGENT language, OTP requests and payment links. This notice asks you to do nothing and verify through the official app."},
    {"id": "adv_otp_negative", "label": "legit", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Banks will NEVER call you to ask for your OTP or PIN. If anyone does, hang up and call the number on your card. This public-awareness message contains no links."},
    {"id": "adv_neighbour", "label": "legit", "channel": "sms", "language": "manglish", "source": "synthetic",
     "text": "Hi neighbour! I found a parcel with your name at my gate. Can you collect it from No. 12 after 6pm? I'm out till 5. Thanks!"},
    {"id": "adv_polite_scam", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "Hello Auntie, this is Jason from Maybank card centre. No rush at all, but our records show an unusual RM2,300 charge. When you are free, just confirm the last 4 digits of your card and the OTP so I can reverse it today. Take your time."},
    {"id": "adv_ms_meta", "label": "scam", "channel": "sms", "language": "ms", "source": "synthetic",
     "text": "Selamat pagi. Ini dari Bahagian Kes PDRM. Ini bukan scam dan tiada kaitan dengan penipuan. Kami hanya perlukan kerjasama anda untuk sahkan maklumat akaun berhubung kes jenayah siber. Jangan risau, segalanya selamat."},
    {"id": "adv_en_meta", "label": "scam", "channel": "sms", "language": "en", "source": "synthetic",
     "text": "WARNING: This is NOT a scam. Government officers never ask for OTP - so we are asking you to confirm yours now to prove this message is genuine. Verify at the link within 24 hours."},
]


def benchmark_cases() -> list[dict[str, str]]:
    """Public accessor so the evaluation harness owns ordering/metadata."""
    return CASES
