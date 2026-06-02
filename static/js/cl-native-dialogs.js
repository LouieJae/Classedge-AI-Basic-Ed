/* ============================================================================
 * [Classedge LMS] cl-native-dialogs.js — replace browser-native alert() with
 * SweetAlert2 globally.
 *
 * Background. ~93 alert() call sites across ~51 files in the codebase still
 * pop the ugly browser-native dialog box. Rather than touch every site, we
 * monkey-patch window.alert to route through SweetAlert2 (already loaded by
 * both base templates). Every existing alert() call site is auto-converted
 * on the next page load.
 *
 * Why this is safe to do globally:
 *   • An audit confirmed zero call sites use the "alert(msg); window.location
 *     = url" pattern, so the async nature of Swal.fire (vs blocking alert)
 *     doesn't break sequencing anywhere.
 *   • alert() returns undefined and callers never branch on the return value.
 *   • If SweetAlert2 isn't loaded on a particular page (rare), we fall back
 *     to the captured native alert so nothing silently breaks.
 *
 * Heuristic icon detection. Most legacy alert() calls are error messages
 * ("Failed to load …", "Please correct …", "Invalid …"). We sniff the
 * message text to pick a sensible Swal icon — warning for errors, success
 * for affirmations, info as the catch-all. Call sites that want a specific
 * icon can call Swal.fire() directly.
 *
 * NOT shimmed: window.confirm() and window.prompt(). Both are synchronous
 * and callers do branch on the return value (`if (confirm(...))`); replacing
 * them with async Swal.fire would silently break that pattern.
 * ============================================================================ */
(function () {
  'use strict';

  if (typeof window === 'undefined') return;
  if (window.__clNativeDialogsShimmed) return;
  window.__clNativeDialogsShimmed = true;

  const nativeAlert = window.alert ? window.alert.bind(window) : function () {};

  // Light keyword sniffing — distinguishes the three common alert categories
  // in this codebase. Kept case-insensitive and tolerant of phrasing.
  const ERR_RX = /\b(error|fail(ed|ure)?|invalid|cannot|unable|denied|forbidden|missing|required|please\s+correct|not\s+found|wrong|please\s+(enter|select|provide|choose)|incorrect)\b/i;
  const OK_RX  = /\b(success(ful)?|saved|created|updated|deleted|sent|copied|imported|added|done)\b/i;

  function pickIcon(msg) {
    if (msg == null) return 'info';
    const s = String(msg);
    if (ERR_RX.test(s)) return 'warning';
    if (OK_RX.test(s))  return 'success';
    return 'info';
  }

  function brandColor() {
    try {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-primary').trim() || '#1b4332';
    } catch (_) {
      return '#1b4332';
    }
  }

  window.alert = function (msg) {
    if (!window.Swal || typeof window.Swal.fire !== 'function') {
      // SweetAlert2 not on this page — preserve the legacy UX rather than
      // silently dropping the message.
      return nativeAlert(msg);
    }
    const text = msg == null ? '' : String(msg);
    const icon = pickIcon(text);
    window.Swal.fire({
      text: text,
      icon: icon,
      // Title is implied by the icon — leaving title undefined keeps the
      // modal compact and the message itself centered, which matches the
      // existing one-line `alert(...)` UX better than a heading + body.
      confirmButtonText: 'OK',
      confirmButtonColor: brandColor(),
      // Match the rest of the LMS confirm dialogs: locked focus inside the
      // dialog so keyboard users can dismiss with Enter / Escape.
      heightAuto: false,  // avoid Bootstrap-modal scroll-lock conflict
    });
    // alert() returns undefined; match that contract so any `void alert(...)`
    // or assignment-style callers behave identically.
    return undefined;
  };
})();
