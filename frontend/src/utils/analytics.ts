import { trackAnalyticsEvent } from "../api/client";

// ── Types ───────────────────────────────────────────────────────────────────

export interface UTMParams {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  ref?: string;
  referrer?: string;
  [key: string]: string | undefined;
}

// ── Identification & Storage Keys ──────────────────────────────────────────

const FIRST_UTM_KEY = "syntropy_first_utm";
const LAST_UTM_KEY = "syntropy_last_utm";
const ANON_ID_KEY = "syntropy_anon_id";
const SESSION_ID_KEY = "syntropy_session_id";

function getOrCreateAnonId(): string {
  try {
    let anonId = localStorage.getItem(ANON_ID_KEY);
    if (!anonId) {
      anonId = "anon_" + Math.random().toString(36).substring(2, 12) + Date.now().toString(36);
      localStorage.setItem(ANON_ID_KEY, anonId);
    }
    return anonId;
  } catch {
    return "anon_fallback";
  }
}

function getOrCreateSessionId(): string {
  try {
    let sid = sessionStorage.getItem(SESSION_ID_KEY);
    if (!sid) {
      sid = "sess_" + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
      sessionStorage.setItem(SESSION_ID_KEY, sid);
    }
    return sid;
  } catch {
    return "sess_fallback";
  }
}

// ── UTM Capture Engine ──────────────────────────────────────────────────────

export function captureUTMs(): UTMParams {
  if (typeof window === "undefined") return {};

  const params = new URLSearchParams(window.location.search);
  const utmKeys = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref"];
  const currentUTMs: UTMParams = {};
  let found = false;

  for (const key of utmKeys) {
    const val = params.get(key);
    if (val) {
      currentUTMs[key] = val;
      found = true;
    }
  }

  if (document.referrer && !document.referrer.includes(window.location.hostname)) {
    currentUTMs.referrer = document.referrer;
    found = true;
  }

  try {
    if (found) {
      // First-touch attribution (preserve earliest acquisition channel)
      if (!localStorage.getItem(FIRST_UTM_KEY)) {
        localStorage.setItem(FIRST_UTM_KEY, JSON.stringify(currentUTMs));
      }
      // Last-touch attribution (update current session journey)
      sessionStorage.setItem(LAST_UTM_KEY, JSON.stringify(currentUTMs));
    }
  } catch {
    // Storage access error
  }

  return currentUTMs;
}

export function getStoredUTMs(): UTMParams {
  try {
    const last = sessionStorage.getItem(LAST_UTM_KEY);
    if (last) return JSON.parse(last);
    const first = localStorage.getItem(FIRST_UTM_KEY);
    if (first) return JSON.parse(first);
  } catch {
    // parse error
  }
  return {};
}

// ── Core Event Tracker ──────────────────────────────────────────────────────

declare global {
  interface Window {
    dataLayer?: any[];
    posthog?: { capture: (event: string, properties?: any) => void };
    mixpanel?: { track: (event: string, properties?: any) => void };
  }
}

export function track(eventName: string, properties: Record<string, any> = {}): void {
  if (typeof window === "undefined") return;

  const utms = getStoredUTMs();
  const anonId = getOrCreateAnonId();
  const sessionId = getOrCreateSessionId();

  const payload = {
    ...properties,
    anon_id: anonId,
    session_id: sessionId,
    screen_width: window.innerWidth,
    path: window.location.pathname,
    referrer: document.referrer || undefined,
    ...utms,
  };

  // 1. Dispatch to Syntropy API
  trackAnalyticsEvent(eventName, payload);

  // 2. Google Tag Manager / GA4 integration
  if (Array.isArray(window.dataLayer)) {
    window.dataLayer.push({
      event: eventName,
      ...payload,
    });
  }

  // 3. PostHog integration (if script loaded)
  if (window.posthog && typeof window.posthog.capture === "function") {
    window.posthog.capture(eventName, payload);
  }

  // 4. Mixpanel integration (if script loaded)
  if (window.mixpanel && typeof window.mixpanel.track === "function") {
    window.mixpanel.track(eventName, payload);
  }
}

// ── High-Intent Conversion Events ───────────────────────────────────────────

export const Analytics = {
  pageView: (pageName: string) => track("page_view", { page: pageName }),
  demoInteracted: (action: string, details?: Record<string, any>) =>
    track("demo_interacted", { action, ...details }),
  bankSwitched: (bankName: string) => track("bank_switched", { bank: bankName }),
  searchQueried: (query: string) => track("search_queried", { query }),
  tagClicked: (tag: string) => track("tag_clicked", { tag }),
  statementCleanedTested: (bank: string, format: string) =>
    track("statement_cleaner_tested", { bank, format }),
  waitlistJoined: (email: string, position?: number) =>
    track("waitlist_joined", { email, position }),
  consentStarted: (bank?: string) => track("consent_started", { bank }),
  ctaClicked: (ctaName: string, location: string) =>
    track("cta_clicked", { cta: ctaName, location }),
};

// Initialize UTM capture on module load
if (typeof window !== "undefined") {
  captureUTMs();
}
