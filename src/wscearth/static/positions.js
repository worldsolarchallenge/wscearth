window.wsc = (function() {
  // Map reference.
  let map;

  // Popup window for markers.
  let infoWindow;

  // Current positions data, updated on a loop.
  let data;

  // Marker references, these are indexed by the 'teamnum'.
  const markers = {};


  /**
   * API utilities.
   */
  const api = (function() {
    const telemetry = new URL(document.currentScript.baseURI);
    const sprout = new URL('https://worldsolarchallenge.org');

    // Generic fetch.
    async function get(base, uri, params = {}) {
      const query = new URLSearchParams(params);
      const search = query.toString();
      const url = `${base.href}/${uri}` + (search ? `?${search}` : '');

      const res = await fetch(url, {
        mode: 'cors',
      });

      if (!res.ok) {
        const message = `${res.status}: ` + await res.text();
        throw new Error(message);
      }

      const json = await res.json();
      return json;
    }

    // Fetch last positions for all cars.
    async function getPositions() {
      return await get(telemetry, 'api/positions');
    }

    // Fetch historical positions (path) for a car.
    async function getPath(teamnum) {
      return await get(telemetry, 'api/path/' + teamnum);
    }

    // Fetch Sprout content managed data.
    async function getSproutData(event, team) {
      return await get(sprout, 'api/team', { event, team });
    }

    return {
      getPositions,
      getPath,
      getSproutData,
    }
  })();


  /**
   * Looping utility.
   * This is triggered on the map init.
   */
  const loop = (function() {
    let timer = 0;

    function start(timeout = 5000) {
      clearInterval(timer);

      timer = setInterval(async () => {
        data = await api.getPositions();
        updateMarkers();
      }, timeout);
    }

    function stop() {
      clearInterval(timer);
    }

    return {
      start,
      stop,
    }
  })();


  /**
   * Live time-ago for fun and profit.
   */
  const timeago = (function() {
    function register() {
      const elements = document.querySelectorAll('[data-timeago]');
      for (const element of elements) {
        render(element);
      }
    }

    function render(element) {
      const when = parseInt(element.getAttribute('data-timeago'));
      element.removeAttribute('date-timeago');

      (function inner() {
        const seconds = Math.floor((Date.now() - when) / 1000);

        element.textContent = format(seconds);

        if (document.body.contains(element)) {
          setTimeout(inner, 1000);
        }
      })();
    }

    function format(seconds) {
      switch (true) {
        case seconds < 60: return `${seconds} seconds`;
        case seconds < 3600: return `${Math.floor(seconds / 60)} minutes`;
        case seconds < 86400: return `${Math.floor(seconds / 3600)} hours`;
        case seconds < 604800: return `${Math.floor(seconds / 86400)} days`;
        default: return `${Math.floor(seconds / 604800)} weeks`;
      }
    }

    return {
      register,
      render,
      format,
    }
  })();


  /**
   * Create/update markers on the map, deduplicated by teamnum.
   */
  function updateMarkers() {
    for (let item of data.items) {

      if (!item.teamnum) {
        console.warn('missing teamnum:', item);
        continue;
      }

      if (
        typeof item.latitude !== 'number'
        || typeof item.latitude !== 'number'
      ) {
        console.warn('invalid position:', item);
        continue;
      }

      let marker = markers[item.teamnum];

      // Update existing markers.
      if (marker) {
        marker.setPosition({
          lat: item.latitude,
          lng: item.longitude,
        });
        continue;
      }

      // It's a new marker.
      marker = new google.maps.Marker({
        map: map,
        title: item.team,
        position: {
          lat: item.latitude,
          lng: item.longitude,
        }
      });

      // Attach events.
      marker.addListener("click", () => openMarkerPopup(item.teamnum));

      // Register it for later updates.
      markers[item.teamnum] = marker;
    }
  }


  /**
   * Draw the path for a car.
   */
  async function drawPath(teamnum, options = {}) {
    const path = await api.getPath(teamnum);

    options = Object.assign({
      geodesic: true,
      strokeColor: '#FF0000',
      strokeOpacity: 1.0,
      strokeWeight: 2,
    }, options || {});

    options.path = path.map(item => ({ lat: item.latitude, lng: item.longitude }));

    const poly = new google.maps.Polyline(options);
    poly.setMap(map);
    return poly;
  }


  /**
   * Open the popup for a marker.
   */
  async function openMarkerPopup(teamnum) {
    infoWindow.close();

    const marker = markers[teamnum];
    const item = data.items.find(item => item.teamnum === teamnum);

    if (!marker || !item) {
      throw new Error('invalid teamnum');
    }

    // This is cached ~5 minutes.
    const team = await api.getSproutData(item.event, item.teamnum);

    const gps_when = new Date(item.time);
    const gps_age = (Date.now() - gps_when) / 1000;

    const html = [
      '<div class="map-popup">',
      `<p class="name"><img src="${team.flag_url}">`,
      `<a href="${team.site_url}" target="_blank">${team.name}</a></p>`,
      `<p><b>Latitude:</b><span>${item.latitude}</span></p>`,
      `<p><b>Longitude:</b><span>${item.longitude}</span></p>`,
      `<p><b>GPS last updated:</b><span>${gps_when.toLocaleString()} &nbsp; <i title="UTC + 9:30">Darwin time</i></span></p>`,
      `<p><b>GPS data age:</b><span data-timeago="${item.time}">${gps_age} seconds</span></p>`,
    ];

    // TODO not present in telemetry data (yet?).
    if (item.dist_adelaide > 1) {
      html.push(`<p><b>Geodesic dist from Darwin:</b><span>${item.dist_darwin} km</span></p>`);
      html.push(`<p><b>Geodesic dist from Adelaide:</b><span>${item.dist_adelaide} km</span></p>`);
    }

    // TODO not present in telemetry data.
    if (item.trailered) {
      html.push('<p><br>This car has been trailered</p>');
    }

    html.push('</div>');

    infoWindow.setContent(html.join(''));
    infoWindow.open(marker.getMap(), marker);

    // Keep the GPS age up-to-date.
    setTimeout(() => timeago.register(), 200);

    return marker;
  }


  /**
   * Entry point.
   */
  async function initMap() {
    if (map) {
      throw new Error('already initialized');
    }

    map = new google.maps.Map(document.getElementById("map"), {
      center: { lat: -25.0, lng: 133.0 },
      zoom: 4,
    });

    // Create an info window to share between markers.
    infoWindow = new google.maps.InfoWindow();

    data = await api.getPositions();

    // Initial map position based on the mean of all positions.
    map.setCenter(data.center);
    updateMarkers();

    // Loop it.
    loop.start();
  }

  // Something for the map to tell us it's ready.
  window.__wscinitMap = initMap;


  /**
   * Exports.
   */
  return {
    api,
    loop,
    markers,
    updateMarkers,
    drawPath,
    openMarkerPopup,
    initMap,
    getMap: () => map,
    getInfoWindow: () => infoWindow,
  }
})();
