/**
 * h5p-lesson.js
 *
 * Handles lazy initialisation of H5P activities embedded in a LessonPage
 * and wires up xAPI event tracking for each one.
 *
 * Dependencies (loaded before this script):
 *   - wagtail_lms/vendor/h5p-standalone/main.bundle.js  (H5PStandalone)
 *
 * The <script> tag that loads main.bundle.js carries data attributes:
 *   data-frame-js   path to frame.bundle.js
 *   data-frame-css  path to h5p.css (used by the H5P frame)
 *   data-h5p-css    path to h5p.css (injected into <head> once)
 */
(function () {
  'use strict';

  /* -----------------------------------------------------------------------
     Read paths from the loader script's data attributes so templates only
     need one place to set static asset URLs.
     ----------------------------------------------------------------------- */
  var loaderScript = document.getElementById('h5p-standalone-script');
  if (!loaderScript) {
    console.warn('h5p-lesson.js: could not find #h5p-standalone-script element.');
    return;
  }
  var FRAME_JS  = loaderScript.dataset.frameJs;
  var FRAME_CSS = loaderScript.dataset.frameCss;
  var H5P_CSS   = loaderScript.dataset.h5pCss;

  /* -----------------------------------------------------------------------
     CSRF token — read from the hidden input Django injects via {% csrf_token %}.
     ----------------------------------------------------------------------- */
  function getCsrfToken() {
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  /* -----------------------------------------------------------------------
     Minimal EventDispatcher shim.

     When H5P content uses an "iframe" embed type, the frame code forwards
     events to window.parent.H5P.externalDispatcher. We pre-create this
     object so the forwarding doesn't throw, and so our .on('xAPI', ...)
     listener registered after .then() continues to work.
     ----------------------------------------------------------------------- */
  function createEventDispatcher() {
    var listeners = {};
    return {
      on: function (name, fn) {
        if (!listeners[name]) { listeners[name] = []; }
        listeners[name].push(fn);
      },
      trigger: function (event) {
        var name = (typeof event === 'string') ? event : event.type;
        var fns = (listeners[name] || []).concat(listeners['*'] || []);
        for (var i = 0; i < fns.length; i++) {
          fns[i].call(this, event);
        }
      }
    };
  }

  /* Ensure window.H5P.externalDispatcher exists before any player loads. */
  window.H5P = window.H5P || {};
  if (!window.H5P.externalDispatcher) {
    window.H5P.externalDispatcher = createEventDispatcher();
  }

  /* -----------------------------------------------------------------------
     Inject h5p.css once into <head> when the first player initialises.
     ----------------------------------------------------------------------- */
  var h5pCssInjected = false;
  function ensureH5PCss() {
    if (h5pCssInjected) { return; }
    h5pCssInjected = true;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = H5P_CSS;
    document.head.appendChild(link);
  }

  /* -----------------------------------------------------------------------
     Initialise a single H5P activity container.

     Each container carries:
       data-activity-id  Django H5PActivity PK
       data-content-url  base URL for h5p-standalone (h5pJsonPath)
       data-xapi-url     POST endpoint for xAPI statements
       data-xapi-iri     unique IRI used to filter shared dispatcher events
     ----------------------------------------------------------------------- */
  function initActivity(container) {
    if (container.dataset.initialized) { return; }
    container.dataset.initialized = 'true';

    var activityId  = container.dataset.activityId;
    var contentUrl  = container.dataset.contentUrl;
    var xapiUrl     = container.dataset.xapiUrl;
    var xapiIri     = container.dataset.xapiIri;
    var playerEl    = container.querySelector('.lms-h5p-activity__player');
    var placeholder = container.querySelector('.lms-h5p-activity__placeholder');

    if (!playerEl) {
      console.warn('h5p-lesson.js: player element not found for activity', activityId);
      return;
    }

    ensureH5PCss();

    var options = {
      h5pJsonPath:  contentUrl,
      frameJs:      FRAME_JS,
      frameCss:     FRAME_CSS,
      xAPIObjectIRI: xapiIri,   /* unique per activity — used to filter events */
    };

    new H5PStandalone.H5P(playerEl, options)
      .then(function () {
        /* Hide placeholder once player has rendered */
        if (placeholder) { placeholder.style.display = 'none'; }

        /* Listen for xAPI events from this specific activity.
           The shared dispatcher receives events from all H5P instances;
           we filter by xAPIObjectIRI to avoid cross-contamination. */
        window.H5P.externalDispatcher.on('xAPI', function (event) {
          var statement = (event.data && event.data.statement) ? event.data.statement : event;
          var objectId  = statement.object && statement.object.id;

          /* Only handle events that belong to this activity */
          if (objectId && objectId !== xapiIri) { return; }

          fetch(xapiUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(statement),
          }).catch(function (err) {
            console.warn('h5p-lesson.js: xAPI POST failed for activity', activityId, err);
          });
        });
      })
      .catch(function (err) {
        console.error('h5p-lesson.js: player init failed for activity', activityId, err);
        if (placeholder) {
          placeholder.querySelector('.lms-h5p-activity__loading').textContent =
            'Could not load activity.';
        }
      });
  }

  /* -----------------------------------------------------------------------
     Lazy-load via IntersectionObserver.

     Activities are observed and initialised when they are within 300px of
     the viewport, matching the progressive-reveal behaviour of Rise.
     ----------------------------------------------------------------------- */
  var containers = document.querySelectorAll('.lms-h5p-activity');

  if (!containers.length) { return; }

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          initActivity(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '300px' });

    containers.forEach(function (c) { observer.observe(c); });
  } else {
    /* Fallback for browsers without IntersectionObserver: init everything. */
    containers.forEach(initActivity);
  }
}());
