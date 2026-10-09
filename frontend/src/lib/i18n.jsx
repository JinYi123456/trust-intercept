import { createContext, useContext, useEffect, useMemo, useState } from "react";

/**
 * Minimal BM/EN toggle for key labels — aimed at non-technical users
 * (Malaysian parents and seniors). Deep technical copy stays English;
 * only the decision-critical labels are translated.
 */

const DICTIONARY = {
  en: {
    // Header / global
    appName: "TRUST//INTERCEPT",
    langButton: "Bahasa Melayu",
    skipToContent: "Skip to main content",
    offlineBanner:
      "You are offline — results cannot load or refresh. Reconnect and try again.",
    retry: "Try again",
    loadingGeneric: "Loading…",

    // Verdict
    verdictTitle: "The result",
    verdictQuestion: "Is this message safe?",
    riskLow: "Likely safe",
    riskMedium: "Be careful",
    riskHigh: "Danger — likely a scam",
    confidence: "How sure we are",
    summaryTitle: "In plain words",
    uncertaintyTitle: "What we are not sure about",

    // Cues
    cuesTitle: "Suspicious parts we found",
    cuesEmpty:
      "No usual scam tricks were found in this message — no fake urgency, no requests for bank codes or passwords, no payment demands.",
    cueSeverityHigh: "Serious",
    cueSeverityMedium: "Worrying",
    cueSeverityLow: "Minor",

    // What could make us wrong
    wrongTitle: "What could make us wrong",
    wrongIntro:
      "Before you decide, here is what could flip this result — check these if you still feel unsure.",

    // Safest next step
    nextStepTitle: "The safest next step",
    nextStepFallback:
      "Do not click any link or call any number in the message. Contact the company using the number on their official website or your bank card.",
    independentSources: "Verify ONLY through:",
    reportMyTitle: "Report it (Malaysia)",
    reportMyBody:
      "Call NSRC 997 (24/7) · Check mule accounts: semakmule.rmp.gov.my · Bank Negara: bnm.gov.my · Never use links from the suspicious message.",

    // Decision gate
    decideTitle: "Your decision",
    decideHint:
      "Nothing happens until you choose. TRUST//INTERCEPT only advises — you decide.",
    approve: "Looks safe — approve",
    reject: "Report / warn — reject",
    moreActions: "Other options",
    looksSafe: "Looks Safe",
    report: "Report This",
    blockWarn: "Block / Warn",
    disagree: "I disagree, re-check",

    // Details sections
    details: "Details",
    detailsShow: "Show details",
    detailsHide: "Hide details",
    detailsHow: "How we investigated",
    detailsTech: "Technical panels",

    // Review sub-labels
    didNotCheck: "What TRUST//INTERCEPT did NOT check",
    case: "Case",
    auditLog: "Audit log",

    // Other pages
    submitHeading: "Check a suspicious message",
    submitIntro:
      "Paste a message, drop a link, scan a QR code, upload a screenshot, or upload a suspicious voice call. TRUST//INTERCEPT checks the evidence and explains what it found in plain language — you decide what to do next.",
    tabText: "Message text",
    tabUrl: "URL",
    tabImage: "Screenshot / QR",
    tabCamera: "Live camera scan",
    tabAudio: "Audio / voice call",
    hintText: "Paste a suspicious SMS or email body.",
    hintUrl: "Paste a link you were asked to open.",
    hintImage: "Upload a screenshot or a QR-code image.",
    hintCamera: "Point your camera at a physical QR code — decoded on-device.",
    hintAudio:
      "Upload or record a suspicious voicemail or voice call for deepfake and coercion analysis.",
    loadScamSample: "⚠ LOAD SAMPLE: PARCEL-FEE SCAM SMS",
    loadLegitSample: "✓ LOAD SAMPLE: LEGITIMATE COURIER SMS",
    urlHelper:
      "TRUST//INTERCEPT traces the redirect chain (≤5 hops), checks domain age and reputation — before you ever open it.",
    imageKindScreenshot: "MESSAGE SCREENSHOT",
    imageKindQr: "QR CODE IMAGE",
    chooseImage: "Click to choose an image",
    imageNote: "Screenshots are OCR'd locally; QR codes are decoded offline.",
    recordMic: "🎙 RECORD FROM MICROPHONE",
    stopRecording: "⏹ STOP RECORDING",
    clearClip: "✕ CLEAR CLIP",
    uploadAudio: "Click to upload a voicemail / call recording",
    replaceAudio: "Replace audio file",
    audioNote:
      ".mp3 / .wav / .m4a / .ogg · max 20 MB · analysed locally first, audio never persisted",
    audioContextPlaceholder:
      "Optional context: what did the caller claim? e.g. 'Caller said my son was kidnapped and demanded a wire transfer' — helps the coercion scan.",
    investigate: "⚡ INVESTIGATE WITH TRUST//INTERCEPT",
    submissionFailed: "SUBMISSION FAILED:",
    selectedFile: "Selected:",
    micBlocked: "Microphone access was blocked — upload an audio file instead.",
    imageTypeLabel: "Image type",
    audioContextLabel: "Context for the analysts (optional)",
    safetyLine:
      "NOTHING IS SENT, BLOCKED, OR FILED AUTOMATICALLY. EVERY ACTION REQUIRES YOUR EXPLICIT APPROVAL.",
    reportHeading: "Your scam report",
    reportDownload: "Download report",
    reportCopy: "Copy report",
    coachHeading: "Quick practice quiz",
    evalHeading: "How accurate is the checker?",

    // Buttons / states
    cancel: "Cancel",
    back: "Back",
    goBackHome: "Back to start",
    refresh: "Refresh",
  },
  bm: {
    appName: "TRUST//INTERCEPT",
    langButton: "English",
    skipToContent: "Terus ke kandungan utama",
    offlineBanner:
      "Anda sedang luar talian — keputusan tidak dapat dimuatkan. Sambung semula dan cuba lagi.",
    retry: "Cuba lagi",
    loadingGeneric: "Sedang dimuatkan…",

    verdictTitle: "Keputusan kami",
    verdictQuestion: "Adakah mesej ini selamat?",
    riskLow: "Kemungkinan selamat",
    riskMedium: "Berhati-hati",
    riskHigh: "Bahaya — kemungkinan penipuan",
    confidence: "Tahap keyakinan kami",
    summaryTitle: "Dalam bahasa mudah",
    uncertaintyTitle: "Apa yang kami tidak pasti",

    cuesTitle: "Bahagian mencurigakan yang kami jumpa",
    cuesEmpty:
      "Tiada tipu muslihat biasa dijumpai — tiada desakan tergesa-gesa, tiada permintaan kod bank atau kata laluan, tiada tuntutan bayaran.",
    cueSeverityHigh: "Serius",
    cueSeverityMedium: "Membimbangkan",
    cueSeverityLow: "Kecil",

    wrongTitle: "Apa yang mungkin buatkan kami silap",
    wrongIntro:
      "Sebelum anda memutuskan, semak senarai ini jika anda masih ragu-ragu.",

    nextStepTitle: "Langkah paling selamat seterusnya",
    nextStepFallback:
      "Jangan tekan mana-mana pautan atau hubungi nombor dalam mesej itu. Hubungi syarikat melalui nombor di laman web rasmi mereka atau di kad bank anda.",
    independentSources: "Sahkan HANYA melalui:",
    reportMyTitle: "Laporkan (Malaysia)",
    reportMyBody:
      "Hubungi NSRC 997 (24/7) · Semak akaun jerat: semakmule.rmp.gov.my · Bank Negara: bnm.gov.my · Jangan guna pautan dari mesej mencurigakan.",

    decideTitle: "Keputusan anda",
    decideHint:
      "Tiada apa-apa berlaku sehingga anda memilih. TRUST//INTERCEPT hanya menasihati — anda yang memutuskan.",
    approve: "Nampak selamat — luluskan",
    reject: "Lapor / beri amaran — tolak",
    moreActions: "Pilihan lain",
    looksSafe: "Nampak Selamat",
    report: "Lapor Ini",
    blockWarn: "Beri Amaran",
    disagree: "Saya tidak setuju, semak semula",

    details: "Butiran",
    detailsShow: "Tunjuk butiran",
    detailsHide: "Sembunyikan butiran",
    detailsHow: "Bagaimana kami siasat",
    detailsTech: "Panel teknikal",

    didNotCheck: "Apa yang TRUST//INTERCEPT TIDAK semak",
    case: "Kes",
    auditLog: "Log audit",

    submitHeading: "Semak mesej yang mencurigakan",
    submitIntro:
      "Tampal mesej, tampal pautan, imbas kod QR, muat naik tangkapan skrin, atau muat naik rakaman suara yang mencurigakan. TRUST//INTERCEPT menyemak bukti dan menerangkan apa yang dijumpai dalam bahasa mudah — anda yang memutuskan langkah seterusnya.",
    tabText: "Teks mesej",
    tabUrl: "URL",
    tabImage: "Tangkapan skrin / QR",
    tabCamera: "Imbas kamera langsung",
    tabAudio: "Audio / panggilan suara",
    hintText: "Tampal SMS atau e-mel yang mencurigakan.",
    hintUrl: "Tampal pautan yang anda diminta buka.",
    hintImage: "Muat naik tangkapan skrin atau imej kod QR.",
    hintCamera: "Halakan kamera pada kod QR fizikal — dinyahkod pada peranti anda.",
    hintAudio:
      "Muat naik atau rakam voicemail / panggilan mencurigakan untuk analisis deepfake dan paksaan.",
    loadScamSample: "⚠ MUAT CONTOH: SMS PENIPUAN YURAN PARSEL",
    loadLegitSample: "✓ MUAT CONTOH: SMS KURIER SAH",
    urlHelper:
      "TRUST//INTERCEPT menjejak rantaian pautan (≤5 lompatan), menyemak umur domain dan reputasi — sebelum anda membukanya.",
    imageKindScreenshot: "TANGKAPAN SKRIN",
    imageKindQr: "IMEJ KOD QR",
    chooseImage: "Klik untuk pilih imej",
    imageNote: "Tangkapan skrin dibaca (OCR) secara tempatan; kod QR dinyahkod luar talian.",
    recordMic: "🎙 RAKAM DARI MIKROFON",
    stopRecording: "⏹ HENTIKAN RAKAMAN",
    clearClip: "✕ PADAM KLIP",
    uploadAudio: "Klik untuk muat naik voicemail / rakaman panggilan",
    replaceAudio: "Tukar fail audio",
    audioNote:
      ".mp3 / .wav / .m4a / .ogg · maksimum 20 MB · dianalisis secara tempatan dahulu, audio tidak disimpan",
    audioContextPlaceholder:
      "Konteks (pilihan): apa yang didakwa oleh pemanggil? cth. 'Pemanggil kata anak saya diculik dan minta pindahkan wang' — membantu imbasan paksaan.",
    investigate: "⚡ SIASAT DENGAN TRUST//INTERCEPT",
    submissionFailed: "HANTARAN GAGAL:",
    selectedFile: "Dipilih:",
    micBlocked: "Akses mikrofon disekat — muat naik fail audio sebagai gantinya.",
    imageTypeLabel: "Jenis imej",
    audioContextLabel: "Konteks untuk juruanalisis (pilihan)",
    safetyLine:
      "TIADA APA-APA DIHANTAR, DISEKAT, ATAU DILAPORKAN SECARA AUTOMATIK. SETIAP TINDAKAN MEMERLUKAN KELULUSAN ANDA.",
    reportHeading: "Laporan penipuan anda",
    reportDownload: "Muat turun laporan",
    reportCopy: "Salin laporan",
    coachHeading: "Kuiz latihan ringkas",
    evalHeading: "Sejauh mana ketepatan pemeriksa ini?",

    cancel: "Batal",
    back: "Kembali",
    goBackHome: "Kembali ke mula",
    refresh: "Muat semula",
  },
};

const LANG_KEY = "ti-lang";
const LangContext = createContext({ lang: "en", t: (key) => key, setLang: () => {} });

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem(LANG_KEY) === "bm" ? "bm" : "en";
    } catch {
      return "en";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(LANG_KEY, lang);
    } catch {
      /* private mode — non-fatal */
    }
    document.documentElement.lang = lang === "bm" ? "ms" : "en";
  }, [lang]);

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: (key) => DICTIONARY[lang][key] ?? DICTIONARY.en[key] ?? key,
    }),
    [lang]
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  return useContext(LangContext);
}

/** Map a backend severity to its plain-language label key. */
export function severityLabelKey(severity) {
  switch (String(severity || "").toLowerCase()) {
    case "high":
      return "cueSeverityHigh";
    case "medium":
      return "cueSeverityMedium";
    default:
      return "cueSeverityLow";
  }
}

/** Map a backend verdict score to its plain-language label key. */
export function scoreLabelKey(score) {
  switch (String(score || "").toLowerCase()) {
    case "high":
      return "riskHigh";
    case "medium":
      return "riskMedium";
    default:
      return "riskLow";
  }
}
