window.wsc = (function() {
  let map;
  let infoWindow;

  const markers = {};

  // API utilities.
  const api = (function() {
    const telemetry = new URL(document.currentScript.src);
    const sprout = new URL('http://sola.gwilyn.bunnysites.com');

    // Generic fetch.
    async function get(base, uri, params = {}) {
      const query = new URLSearchParams(params);
      const search = query.toString();
      const url = `${base.protocol}//${base.host}/${uri}` + (search ? `?${search}` : '');

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
    async function getPaths(shortname) {
      return await get(telemetry, 'api/path/' + shortname);
    }

    // Fetch Sprout content managed data.
    async function getSproutData(event, team) {
      return await get(sprout, 'api/team', { event, team });
    }

    return {
      getPositions,
      getPaths,
      getSproutData,
    }
  })();

  // Create/update markers on the map, deduplicated by shortname.
  function updateMarkers(items) {
    for (let item of items) {

      if (!item.shortname) {
        console.warn('missing shortname:', item);
        continue;
      }

      if (
        typeof item.latitude !== 'number'
        || typeof item.latitude !== 'number'
      ) {
        console.warn('invalid position:', item);
        continue;
      }

      let marker = markers[item.shortname];

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
        title: item.shortname,
        position: {
          lat: item.latitude,
          lng: item.longitude,
        }
      });

      // Attach events.
      marker.addListener("click", () => openMarkerPopup(item, marker));

      markers[item.shortname] = marker;
    }
  }

  // Draw a path for a car.
  async function drawPath(shortname) {
    const path = await api.getPaths(shortname);

    const poly = new google.maps.Polyline({
      path: path.map(item => ({ lat: item.latitude, lng: item.longitude })),
      geodesic: true,
      strokeColor: '#FF0000',
      strokeOpacity: 1.0,
      strokeWeight: 2,
    });

    poly.setMap(map);
  }

  async function openMarkerPopup(data, marker) {
    const team = await api.getSproutData(data.event, data.team);

    const gps_when = new Date(data.time);
    const gps_age = (Date.now() - gps_when) / 1000;

    const html = [
      '<div class="map-popup">',
      `<p class="name"><img src="${team.flag_url}">`,
      `<a href="${team.site_url}" target="_blank">${team.name}</a></p>`,
      `<p><b>Latitude:</b><span>${data.latitude}</span></p>`,
      `<p><b>Longitude:</b><span>${data.longitude}</span></p>`,
      `<p><b>GPS last updated:</b><span>${gps_when.toLocaleString()} &nbsp; <i title="UTC + 9:30">Darwin time</i></span></p>`,
      `<p><b>GPS data age:</b><span>${gps_age} seconds</span></p>`,
    ];

    if (data.dist_adelaide > 1) {
      html.push(`<p><b>Geodesic dist from Darwin:</b><span>${data.dist_darwin} km</span></p>`);
      html.push(`<p><b>Geodesic dist from Adelaide:</b><span>${data.dist_adelaide} km</span></p>`);
    }

    if (data.trailered) {
      html.push('<p><br>This car has been trailered</p>');
    }

    html.push('</div>');

    infoWindow.close();
    infoWindow.setContent(html.join(''));
    infoWindow.open(marker.getMap(), marker);
  }

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

    const data = await api.getPositions();

    // Initial map position based on the mean of all positions.
    map.setCenter(data.center);
    updateMarkers(data.items);

    // Loop it.
    setInterval(async () => {
      const data = await api.getPositions();
      updateMarkers(data.items);
    }, 5000);
  }

  window.__wscinitMap = initMap;

  return {
    markers,
    updateMarkers,
    drawPath,
    initMap,
  }
})();
