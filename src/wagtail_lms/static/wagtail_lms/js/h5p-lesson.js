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
  var H5P_STANDALONE_API = window.H5PStandalone;
  var H5P_INIT_TIMEOUT_MS = 20000;
  var h5pLazyDisabled = window.location.search.indexOf('h5pLazy=0') !== -1;

  /* -----------------------------------------------------------------------
     CSRF token — read from the hidden input Django injects via {% csrf_token %}.
     ----------------------------------------------------------------------- */
  function getCsrfToken() {
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  if (!H5P_STANDALONE_API || typeof H5P_STANDALONE_API.H5P !== 'function') {
    console.error('h5p-lesson.js: H5PStandalone API unavailable at script startup.');
    return;
  }

  function setPlaceholderMessage(placeholder, message) {
    if (!placeholder) { return; }
    var loadingEl = placeholder.querySelector('.lms-h5p-activity__loading');
    if (loadingEl) { loadingEl.textContent = message; }
  }

  function promiseWithTimeout(promise, timeoutMs, timeoutErrorFactory) {
    return new Promise(function (resolve, reject) {
      var settled = false;
      var timer = window.setTimeout(function () {
        if (settled) { return; }
        settled = true;
        reject(timeoutErrorFactory());
      }, timeoutMs);

      Promise.resolve(promise).then(function (value) {
        if (settled) { return; }
        settled = true;
        window.clearTimeout(timer);
        resolve(value);
      }).catch(function (err) {
        if (settled) { return; }
        settled = true;
        window.clearTimeout(timer);
        reject(err);
      });
    });
  }

  /* -----------------------------------------------------------------------
     Minimal EventDispatcher shim.

     When H5P content uses an "iframe" embed type, the frame code forwards
     events to window.parent.H5P.externalDispatcher. We pre-create this
     object so the forwarding doesn't throw, and so our synchronous
     .on('xAPI', ...) listener continues to work.
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

  /* Track which xAPI IRIs already have a dispatcher listener registered.
     When the same H5PActivity snippet is embedded more than once in a
     lesson, each container is initialised separately but they share the
     same xapiIri.  Without this guard every block would register its own
     listener and a single xAPI event would generate duplicate POSTs. */
  var registeredXApiIris = {};

  /* -----------------------------------------------------------------------
     Sequential initialisation queue.

     H5PStandalone.H5P() modifies shared global state (window.H5P,
     window.H5PIntegration, the preventInit flag, H5P.init()) in ways that
     are not safe when two instances initialise concurrently.  On a first
     page load the network fetches for activity 1 can still be in flight
     when the user scrolls activity 2 into view, causing the second promise
     to hang indefinitely.

     Solution: enqueue containers as the IntersectionObserver fires and run
     one H5P initialisation at a time.  The observer still fires lazily —
     we just defer the actual init until the previous one settles.
     ----------------------------------------------------------------------- */
  var h5pInitQueue  = [];
  var h5pInitBusy   = false;

  function processH5PQueue() {
    if (h5pInitBusy || h5pInitQueue.length === 0) { return; }
    h5pInitBusy = true;
    var container = h5pInitQueue.shift();
    var activityId = container.dataset.activityId;
    Promise.resolve().then(function () {
      return runInitActivity(container);
    }).catch(function (err) {
      console.error('h5p-lesson.js: queue item failed for activity', activityId, err);
    }).then(function () {
      h5pInitBusy = false;
      processH5PQueue();
    });
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
     H5P activity initialisation.

     initActivity()    — called by IntersectionObserver; registers the xAPI
                         listener and enqueues the container.
     runInitActivity() — dequeued by processH5PQueue() and runs one at a
                         time; returns a Promise so the next item only starts
                         after the current one settles.

     Each container carries:
       data-activity-id  Django H5PActivity PK
       data-content-url  base URL for h5p-standalone (h5pJsonPath)
       data-xapi-url     POST endpoint for xAPI statements
       data-xapi-iri     unique IRI used to filter shared dispatcher events
     ----------------------------------------------------------------------- */
  function initActivity(container) {
    if (container.dataset.initialized) { return; }
    container.dataset.initialized = 'true';

    /* Register the xAPI listener synchronously — before entering the queue
       — so that if two containers with the same xapiIri enter the observer
       callback in the same batch, the second one sees the guard already set
       and skips registration. */
    var xapiIri = container.dataset.xapiIri;
    var xapiUrl = container.dataset.xapiUrl;
    var activityId = container.dataset.activityId;
    if (!registeredXApiIris[xapiIri]) {
      registeredXApiIris[xapiIri] = true;
      window.H5P.externalDispatcher.on('xAPI', function (event) {
        var statement = (event.data && event.data.statement) ? event.data.statement : event;
        var objectId  = statement.object && statement.object.id;
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
    }

    h5pInitQueue.push(container);
    processH5PQueue();
  }

  /* Perform the actual H5PStandalone initialisation; returns a Promise. */
  function runInitActivity(container) {
    var activityId  = container.dataset.activityId;
    var contentUrl  = container.dataset.contentUrl;
    var xapiIri     = container.dataset.xapiIri;
    var playerEl    = container.querySelector('.lms-h5p-activity__player');
    var placeholder = container.querySelector('.lms-h5p-activity__placeholder');

    if (!playerEl) {
      console.warn('h5p-lesson.js: player element not found for activity', activityId);
      return Promise.resolve();
    }

    ensureH5PCss();

    var options = {
      h5pJsonPath:   contentUrl,
      frameJs:       FRAME_JS,
      frameCss:      FRAME_CSS,
      xAPIObjectIRI: xapiIri,
    };

    /* frame.bundle.js overwrites window.H5PStandalone with undefined.
       Keep the original API alive and restore global if needed. */
    if (!window.H5PStandalone) {
      window.H5PStandalone = H5P_STANDALONE_API;
    }

    var initPromise;
    try {
      initPromise = new H5P_STANDALONE_API.H5P(playerEl, options);
    } catch (err) {
      initPromise = Promise.reject(err);
    }

    return promiseWithTimeout(initPromise, H5P_INIT_TIMEOUT_MS, function () {
      return new Error('Timed out after ' + H5P_INIT_TIMEOUT_MS + 'ms');
    })
      .then(function () {
        if (placeholder) { placeholder.style.display = 'none'; }
      })
      .catch(function (err) {
        console.error('h5p-lesson.js: player init failed for activity', activityId, err);
        setPlaceholderMessage(placeholder, 'Could not load activity.');
      });
  }

  /* -----------------------------------------------------------------------
     Lazy-load via IntersectionObserver.

     Activities are observed and initialised when they are within 300px of
     the viewport, matching the progressive-reveal behaviour of Rise.
     ----------------------------------------------------------------------- */
  var containers = document.querySelectorAll('.lms-h5p-activity');

  if (!containers.length) { return; }

  if (h5pLazyDisabled) {
    containers.forEach(initActivity);
    return;
  }

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
