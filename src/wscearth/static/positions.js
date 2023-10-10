window.wsc = (function() {
  let map;
  const markers = {};

  async function getPositions() {
    const res = await fetch('api/positions');

    if (!res.ok) {
      const message = `${res.status}: ` + await res.text();
      throw new Error(message);
    }

    const json = await res.json();
    return json;
  }

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

    const data = await getPositions();

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
      const data = await getPositions();
      updateMarkers(data.items);
    }, 5000);
  }

  window.__wscinitMap = initMap;

  return {
    map,
    markers,
    getPositions,
    updateMarkers,
    initMap,
  }
})();
