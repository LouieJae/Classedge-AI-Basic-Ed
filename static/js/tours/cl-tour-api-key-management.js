/* cl-tour-api-key-management.js — walkthrough for API Key Management
 * (accounts/templates/accounts/api_page/api_key_list.html).
 *
 * Generate and manage API keys for integrations and third-party access.
 * The keys table (#api-keys-table) is a DataTable filled after load; the
 * stats cards stay hidden until there's data, so they're left out of the tour.
 *
 * Stable anchors:
 *   .api-key-header   — title + Generate New Key button (always)
 *   #create-key-btn   — Generate New Key button (always)
 *   #api-keys-table   — the API keys table (always)
 */
(function () {
  'use strict';

  function add(id, config) {
    if (window.ClTour && typeof window.ClTour.register === 'function') {
      window.ClTour.register(id, config);
    } else {
      (window.__clTourPending = window.__clTourPending || []).push([id, config]);
    }
  }

  function present(sel) { return !!document.querySelector(sel); }

  add('api-key-management', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'API key management',
        text:
          'Generate and manage <strong>API keys</strong> for integrations ' +
          'and third-party access. Treat each key like a password — anyone ' +
          'with it can act on your behalf.',
        attachTo: { element: '.api-key-header', on: 'bottom' },
      },
      {
        id: 'create',
        title: 'Generate a key',
        text:
          '<strong>Generate New Key</strong> creates one and shows it ' +
          '<strong>once</strong> — copy it right away, because it can\'t be ' +
          'retrieved again after you close the dialog.',
        attachTo: { element: '#create-key-btn', on: 'bottom' },
        showOn: function () { return present('#create-key-btn'); },
      },
      {
        id: 'table',
        title: 'Your keys',
        text:
          'Every key with its label, status, and usage. From here you can ' +
          '<strong>rename</strong>, <strong>revoke</strong>, or delete a ' +
          'key — revoking immediately cuts off whatever was using it.',
        attachTo: { element: '#api-keys-table', on: 'top' },
        showOn: function () { return present('#api-keys-table'); },
      },
    ],
  });
})();
