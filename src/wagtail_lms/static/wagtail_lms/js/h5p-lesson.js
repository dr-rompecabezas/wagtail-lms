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
 *   data-user-name  current learner display name for H5P user-data API
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
  var USER_NAME = loaderScript.dataset.userName || 'Learner';
  var H5P_STANDALONE_API = window.H5PStandalone;
  var H5P_INIT_TIMEOUT_MS = 20000;
  var h5pLazyDisabled = window.location.search.indexOf('h5pLazy=0') !== -1;
  var h5pDebugEnabled = window.location.search.indexOf('h5pDebug=1') !== -1;

  function debugLog() {
    if (!h5pDebugEnabled) { return; }
    var args = Array.prototype.slice.call(arguments);
    args.unshift('h5p-lesson.js:');
    console.log.apply(console, args);
  }

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

  function toAbsoluteUrl(url) {
    if (!url) { return ''; }
    if (/^https?:\/\//i.test(url)) { return url; }
    if (url.charAt(0) === '/') { return window.location.origin + url; }
    return window.location.origin + '/' + url;
  }

  function statementMatchesActivity(statement, xapiIri, contentUrl) {
    if (!statement) { return true; }

    var objectId = statement.object && statement.object.id;
    var contentAbs = toAbsoluteUrl(contentUrl);

    if (!objectId) { return true; }

    if (xapiIri && objectId === xapiIri) { return true; }

    /* Some content types append anchors/query/path segments to object.id. */
    if (xapiIri && (
      objectId.indexOf(xapiIri + '#') === 0 ||
      objectId.indexOf(xapiIri + '?') === 0 ||
      objectId.indexOf(xapiIri + '/') === 0
    )) {
      return true;
    }

    /* Many H5P libraries emit object.id based on content URL instead of our IRI. */
    if (contentAbs && (
      objectId === contentAbs ||
      objectId.indexOf(contentAbs + '#') === 0 ||
      objectId.indexOf(contentAbs + '?') === 0 ||
      objectId.indexOf(contentAbs + '/') === 0
    )) {
      return true;
    }

    /* Fallback: accept if xapiIri is listed in context activities. */
    var context = statement.context && statement.context.contextActivities;
    if (context && xapiIri) {
      var buckets = ['parent', 'grouping', 'category'];
      for (var i = 0; i < buckets.length; i++) {
        var key = buckets[i];
        var raw = context[key];
        if (!raw) { continue; }
        var arr = Array.isArray(raw) ? raw : [raw];
        for (var j = 0; j < arr.length; j++) {
          if (arr[j] && arr[j].id === xapiIri) {
            return true;
          }
        }
      }
    }

    return false;
  }

  function setPlaceholderMessage(placeholder, message) {
    if (!placeholder) { return; }
    var loadingEl = placeholder.querySelector('.lms-h5p-activity__loading');
    if (loadingEl) { loadingEl.textContent = message; }
  }

  function buildUserDataUrl(userDataTemplate, dataType, subContentId) {
    if (!userDataTemplate) { return ''; }
    return userDataTemplate
      .replace(':dataType', encodeURIComponent(dataType))
      .replace(':subContentId', encodeURIComponent(String(subContentId)));
  }

  function fetchPreloadedUserState(activityId, userDataTemplate) {
    if (!userDataTemplate) { return Promise.resolve(null); }
    var stateUrl = buildUserDataUrl(userDataTemplate, 'state', 0);
    if (!stateUrl) { return Promise.resolve(null); }

    return fetch(stateUrl, { method: 'GET' })
      .then(function (response) {
        if (!response.ok) {
          debugLog('resume preload GET non-OK', {
            activityId: activityId,
            status: response.status
          });
          return null;
        }
        return response.json();
      })
      .then(function (payload) {
        if (!payload || payload.success !== true || payload.data === false || !payload.data) {
          debugLog('resume preload empty state', { activityId: activityId });
          return null;
        }
        debugLog('resume preload state found', {
          activityId: activityId,
          bytes: String(payload.data).length
        });
        return {
          0: {
            state: payload.data
          }
        };
      })
      .catch(function (err) {
        console.warn(
          'h5p-lesson.js: failed to preload resume state for activity',
          activityId,
          err
        );
        return null;
      });
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
      off: function (name, fn) {
        if (!listeners[name]) { return; }
        if (!fn) {
          listeners[name] = [];
          return;
        }
        listeners[name] = listeners[name].filter(function (f) { return f !== fn; });
      },
      trigger: function (event, data) {
        var evt;
        if (typeof event === 'string') {
          evt = { type: event };
          if (typeof data !== 'undefined') {
            evt.data = data;
          }
        } else if (event && typeof event === 'object') {
          evt = event;
          if (typeof data !== 'undefined' && typeof evt.data === 'undefined') {
            evt.data = data;
          }
        } else {
          evt = { type: '' };
        }
        var name = evt.type || ((typeof event === 'string') ? event : '');
        var fns = (listeners[name] || []).concat(listeners['*'] || []);
        for (var i = 0; i < fns.length; i++) {
          fns[i].call(this, evt);
        }
      }
    };
  }

  /* Ensure window.H5P.externalDispatcher exists before any player loads. */
  window.H5P = window.H5P || {};
  if (!window.H5P.externalDispatcher) {
    window.H5P.externalDispatcher = createEventDispatcher();
  }

  /* Per-activity xAPI routing table. Keyed by xapiIri so duplicated snippet
     embeds don't trigger duplicate POSTs. */
  var xapiSubscriptions = {};
  var activeExternalDispatcher = null;
  var externalDispatcherHookInstalled = false;

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

  function postXApiStatement(subscription, statement) {
    fetch(subscription.xapiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(statement),
    }).then(function (response) {
      debugLog('xAPI POST response', {
        activityId: subscription.activityId,
        status: response.status
      });
      if (!response.ok) {
        console.warn(
          'h5p-lesson.js: xAPI POST returned non-OK status for activity',
          subscription.activityId,
          response.status
        );
      }
    }).catch(function (err) {
      console.warn(
        'h5p-lesson.js: xAPI POST failed for activity',
        subscription.activityId,
        err
      );
    });
  }

  function handleExternalXApiEvent(event) {
    var statement = (event && event.data && event.data.statement) ? event.data.statement : event;
    var objectId = statement && statement.object && statement.object.id;
    var verbId = statement && statement.verb && statement.verb.id;
    debugLog('received xAPI event', { verbId: verbId, objectId: objectId });

    var keys = Object.keys(xapiSubscriptions);
    if (!keys.length) {
      debugLog('received xAPI event but no subscriptions are registered yet');
    }
    for (var i = 0; i < keys.length; i++) {
      var subscription = xapiSubscriptions[keys[i]];
      if (!subscription) { continue; }
      var isMatch = statementMatchesActivity(
        statement,
        subscription.xapiIri,
        subscription.contentUrl
      );
      if (!isMatch) {
        debugLog('xAPI event filtered out for activity', subscription.activityId);
        continue;
      }
      debugLog('posting xAPI for activity', subscription.activityId);
      postXApiStatement(subscription, statement);
    }
  }

  function ensureExternalDispatcherListener() {
    var dispatcher = window.H5P && window.H5P.externalDispatcher;
    if (!dispatcher || typeof dispatcher.on !== 'function') {
      debugLog('externalDispatcher unavailable for xAPI listener');
      return;
    }
    if (dispatcher === activeExternalDispatcher) { return; }
    if (activeExternalDispatcher && typeof activeExternalDispatcher.off === 'function') {
      activeExternalDispatcher.off('xAPI', handleExternalXApiEvent);
    }
    activeExternalDispatcher = dispatcher;
    activeExternalDispatcher.on('xAPI', handleExternalXApiEvent);
    debugLog('attached xAPI listener to externalDispatcher');
  }

  function installExternalDispatcherHook() {
    if (externalDispatcherHookInstalled) { return; }
    if (!window.H5P) { return; }

    var descriptor;
    try {
      descriptor = Object.getOwnPropertyDescriptor(window.H5P, 'externalDispatcher');
    } catch (err) {
      debugLog('could not inspect externalDispatcher descriptor', err);
    }

    if (descriptor && descriptor.configurable === false) {
      debugLog('externalDispatcher property is not configurable; fallback to manual reattach');
      ensureExternalDispatcherListener();
      return;
    }

    var currentDispatcher = window.H5P.externalDispatcher;
    try {
      Object.defineProperty(window.H5P, 'externalDispatcher', {
        configurable: true,
        enumerable: true,
        get: function () {
          return currentDispatcher;
        },
        set: function (value) {
          currentDispatcher = value;
          debugLog('externalDispatcher replaced; reattaching xAPI listener');
          ensureExternalDispatcherListener();
        }
      });
      externalDispatcherHookInstalled = true;
      debugLog('installed externalDispatcher hook');
      ensureExternalDispatcherListener();
    } catch (err) {
      debugLog('failed to install externalDispatcher hook', err);
      ensureExternalDispatcherListener();
    }
  }

  installExternalDispatcherHook();

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
       data-user-data-url endpoint for H5P resume/progress state
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
    debugLog('initActivity', {
      activityId: activityId,
      xapiIri: xapiIri,
      xapiUrl: xapiUrl,
      contentUrl: container.dataset.contentUrl
    });
    xapiSubscriptions[xapiIri] = {
      xapiIri: xapiIri,
      xapiUrl: xapiUrl,
      contentUrl: container.dataset.contentUrl,
      activityId: activityId
    };
    ensureExternalDispatcherListener();

    h5pInitQueue.push(container);
    processH5PQueue();
  }

  /* Perform the actual H5PStandalone initialisation; returns a Promise. */
  function runInitActivity(container) {
    var activityId  = container.dataset.activityId;
    var contentUrl  = container.dataset.contentUrl;
    var xapiIri     = container.dataset.xapiIri;
    var userDataUrl = container.dataset.userDataUrl;
    var playerEl    = container.querySelector('.lms-h5p-activity__player');
    var placeholder = container.querySelector('.lms-h5p-activity__placeholder');

    if (!playerEl) {
      console.warn('h5p-lesson.js: player element not found for activity', activityId);
      return Promise.resolve();
    }

    ensureH5PCss();

    return fetchPreloadedUserState(activityId, userDataUrl).then(function (preloadedState) {
      var options = {
        h5pJsonPath:   contentUrl,
        frameJs:       FRAME_JS,
        frameCss:      FRAME_CSS,
        xAPIObjectIRI: xapiIri,
      };
      if (userDataUrl) {
        options.user = { name: USER_NAME };
        options.saveFreq = 5;
        options.ajax = {
          contentUserDataUrl: userDataUrl,
        };
        if (preloadedState) {
          options.contentUserData = preloadedState;
        }
      }

      /* frame.bundle.js overwrites window.H5PStandalone with undefined.
         Keep the original API alive and restore global if needed. */
      if (!window.H5PStandalone) {
        window.H5PStandalone = H5P_STANDALONE_API;
      }
      ensureExternalDispatcherListener();

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
          ensureExternalDispatcherListener();
          if (placeholder) { placeholder.style.display = 'none'; }
        })
        .catch(function (err) {
          console.error('h5p-lesson.js: player init failed for activity', activityId, err);
          setPlaceholderMessage(placeholder, 'Could not load activity.');
        });
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
