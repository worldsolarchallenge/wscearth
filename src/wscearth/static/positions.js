window.wsc = (function() {
  let map;
  const markers = {};

  // API utilities.
  const api = (function() {
    const base = new URL(document.currentScript.src);

    // Generic fetch.
    async function get(url) {
      const res = await fetch(`${base.protocol}//${base.host}/${url}`, {
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
      return await get('api/positions');
    }

    // Fetch historical positions (path) for a car.
    async function getPaths(shortname) {
      return await get('api/path/' + shortname);
    }

    return {
      getPositions,
      getPaths,
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
      markers[item.shortname] = new google.maps.Marker({
        map: map,
        title: item.shortname,
        position: {
          lat: item.latitude,
          lng: item.longitude,
        }
      });
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

  async function initMap() {
    if (map) {
      throw new Error('already initialized');
    }

    map = new google.maps.Map(document.getElementById("map"), {
      center: { lat: -25.0, lng: 133.0 },
      zoom: 4,
    });

    // Create an info window to share between markers.
    const infoWindow = new google.maps.InfoWindow();

    const data = await api.getPositions();

    // Initial map position based on the mean of all positions.
    map.setCenter(data.center);
    updateMarkers(data.items);

    // Add a click listener for each marker, and set up the info window.
    for (let marker of Object.values(markers)) {
      marker.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(marker.getTitle());
        infoWindow.open(marker.getMap(), marker);
      })
    }

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
