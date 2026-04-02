const API_URL = "/services";

/* ================= STORAGE ================= */

function saveUserLocation(location) {
  localStorage.setItem("userLocation", JSON.stringify(location));
}

function getUserLocation() {
  const raw = localStorage.getItem("userLocation");
  return raw ? JSON.parse(raw) : null;
}

function saveSelectedCategory(category) {
  localStorage.setItem("selectedCategory", category);
}

function getSelectedCategory() {
  return localStorage.getItem("selectedCategory");
}

function saveSelectedService(service) {
  localStorage.setItem("selectedService", JSON.stringify(service));
}

function getSelectedService() {
  const raw = localStorage.getItem("selectedService");
  return raw ? JSON.parse(raw) : null;
}

/* ================= HELPERS ================= */

function formatProvider(name) {
  if (!name) return "Unknown";
  if (name === "homeless_england") return "Homeless England";
  if (name === "shelter") return "Shelter";
  if (name === "crisis") return "Crisis";
  if (name === "givefood") return "Give Food";
  if (name === "nhs_ods") return "NHS";
  return name;
}

function getDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) *
    Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function textIncludesAny(text, keywords) {
  const lower = (text || "").toLowerCase();
  return keywords.some(keyword => lower.includes(keyword));
}

function mapServiceToCategory(service) {
  const provider = (service.provider_name || "").toLowerCase();
  const type = (service.service_type || "").toLowerCase();
  const name = (service.name || "").toLowerCase();
  const description = (service.description || "").toLowerCase();
  const combined = `${type} ${name} ${description}`;

  if (provider === "givefood" || type === "food") return "food";
  if (provider === "crisis") return "crisis_support";
  if (type === "medical" || provider === "nhs_ods") return "medical";

  if (
    textIncludesAny(combined, [
      "food", "meal", "food bank", "foodbank", "community kitchen", "soup kitchen"
    ])
  ) return "food";

  if (
    textIncludesAny(combined, [
      "medical", "health", "healthcare", "doctor", "nurse", "hospital", "clinic",
      "mental health", "gp", "outreach health", "surgery", "walk-in", "urgent care"
    ])
  ) return "medical";

  if (
    textIncludesAny(combined, [
      "accommodation", "supported housing", "housing", "hostel", "foyer", "house", "residential"
    ])
  ) return "shelter";

  return "advice";
}

async function fetchServices() {
  const res = await fetch(API_URL);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

async function getCoordinatesFromPostcode(postcode) {
  const clean = postcode.trim().replace(/\s+/g, "");
  const res = await fetch(`https://api.postcodes.io/postcodes/${clean}`);

  if (!res.ok) throw new Error("Invalid postcode");

  const data = await res.json();
  if (!data.result) throw new Error("Invalid postcode");

  return {
    lat: data.result.latitude,
    lng: data.result.longitude
  };
}

function getBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("Geolocation is not supported on this device."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          reject(new Error("Location access was denied. You can still search by postcode."));
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          reject(new Error("Your location could not be found. Try again or use a postcode."));
        } else if (error.code === error.TIMEOUT) {
          reject(new Error("Location request timed out. Try again or use a postcode."));
        } else {
          reject(new Error("Could not get your location. Try again or use a postcode."));
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000
      }
    );
  });
}

function buildGoogleMapsDirectionsUrl(originLat, originLng, destLat, destLng, mode = "walking") {
  return `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLng}&destination=${destLat},${destLng}&travelmode=${mode}`;
}

function buildGoogleMapsSearchUrl(destLat, destLng) {
  return `https://www.google.com/maps/search/?api=1&query=${destLat},${destLng}`;
}

function geocodeMedicalServicesWithoutCoords(services) {
  const postcodeMap = {
    "MK6 5LD": { lat: 52.0262, lng: -0.7280 },
    "MK9 3QA": { lat: 52.0406, lng: -0.7594 },
    "NW1 0PE": { lat: 51.5357, lng: -0.1360 },
    "WC1N 3JH": { lat: 51.5226, lng: -0.1207 },
    "SE5 9RS": { lat: 51.4685, lng: -0.0910 }
  };

  return services.map(service => {
    if (service.latitude != null && service.longitude != null) return service;
    if (!service.postcode) return service;

    const match = postcodeMap[service.postcode.toUpperCase()];
    if (!match) return service;

    return {
      ...service,
      latitude: match.lat,
      longitude: match.lng
    };
  });
}

/* ================= HOME ================= */

function initHomePage() {
  const cards = document.querySelectorAll(".category-card[data-category]");
  if (!cards.length) return;

  const useLocationBtn = document.getElementById("useLocationBtn");
  const homePostcodeInput = document.getElementById("homePostcodeInput");
  const homePostcodeBtn = document.getElementById("homePostcodeBtn");
  const homeLocationStatus = document.getElementById("homeLocationStatus");

  if (useLocationBtn) {
    useLocationBtn.addEventListener("click", async () => {
      homeLocationStatus.textContent = "Getting your location...";
      try {
        const coords = await getBrowserLocation();
        saveUserLocation(coords);
        homeLocationStatus.textContent = "Location saved. Now choose a category.";
      } catch (error) {
        console.error(error);
        homeLocationStatus.textContent = error.message;
      }
    });
  }

  if (homePostcodeBtn && homePostcodeInput) {
    homePostcodeBtn.addEventListener("click", async () => {
      const postcode = homePostcodeInput.value.trim();
      if (!postcode) {
        homeLocationStatus.textContent = "Enter a postcode first.";
        return;
      }

      homeLocationStatus.textContent = "Finding postcode...";
      try {
        const coords = await getCoordinatesFromPostcode(postcode);
        saveUserLocation(coords);
        homeLocationStatus.textContent = "Postcode saved. Now choose a category.";
      } catch (error) {
        console.error(error);
        homeLocationStatus.textContent = "Invalid postcode.";
      }
    });
  }

  cards.forEach(card => {
    card.addEventListener("click", () => {
      saveSelectedCategory(card.dataset.category);
      window.location.href = "./results.html";
    });
  });
}

/* ================= RESULTS ================= */

function initResultsPage() {
  const list = document.getElementById("resultsList");
  if (!list) return;

  const status = document.getElementById("resultsStatus");
  const input = document.getElementById("postcodeInput");
  const button = document.getElementById("searchBtn");
  const resultsUseLocationBtn = document.getElementById("resultsUseLocationBtn");

  const category = getSelectedCategory() || "advice";

  async function loadResults() {
    list.innerHTML = "";

    const userLocation = getUserLocation();
    if (!userLocation) {
      status.textContent = "Use your current location or enter a postcode.";
      return;
    }

    let services = await fetchServices();
    services = geocodeMedicalServicesWithoutCoords(services);

    let all = services
      .filter(s => s.latitude != null && s.longitude != null)
      .filter(s => {
        const name = (s.name || "").toLowerCase();
        return !(
          name.includes("get help") ||
          name.includes("help if") ||
          name.length < 3
        );
      });

    all.forEach(s => {
      s.distance = getDistanceKm(
        userLocation.lat,
        userLocation.lng,
        s.latitude,
        s.longitude
      );
    });

    all.sort((a, b) => a.distance - b.distance);

    let filtered = all.filter(s => mapServiceToCategory(s) === category);

    if (!filtered.length) {
      status.textContent =
        `No ${category.replace("_", " ")} services found yet — showing nearest services instead.`;
      filtered = all;
    } else {
      status.textContent = `${filtered.length} services shown`;
    }

    filtered.slice(0, 10).forEach(service => {
      const card = document.createElement("div");
      card.className = "result-card";

      card.innerHTML = `
        <h3>${service.name || "Unknown service"}</h3>
        <p>${service.postcode || ""}</p>
        <p>${service.distance.toFixed(2)} km away</p>
        <button class="primary-btn view-btn">View route</button>
      `;

      card.querySelector(".view-btn").addEventListener("click", () => {
        saveSelectedService(service);
        window.location.href = "./service.html";
      });

      list.appendChild(card);
    });
  }

  if (button && input) {
    button.addEventListener("click", async () => {
      const postcode = input.value.trim();

      if (!postcode) {
        status.textContent = "Enter a postcode.";
        return;
      }

      try {
        status.textContent = "Finding postcode...";
        const coords = await getCoordinatesFromPostcode(postcode);
        saveUserLocation(coords);
        status.textContent = "Loading services...";
        await loadResults();
      } catch (error) {
        console.error(error);
        status.textContent = "Invalid postcode.";
      }
    });
  }

  if (resultsUseLocationBtn) {
    resultsUseLocationBtn.addEventListener("click", async () => {
      status.textContent = "Getting your location...";
      try {
        const coords = await getBrowserLocation();
        saveUserLocation(coords);
        status.textContent = "Loading nearby services...";
        await loadResults();
      } catch (error) {
        console.error(error);
        status.textContent = error.message;
      }
    });
  }

  const existingLocation = getUserLocation();
  if (existingLocation) {
    loadResults().catch((error) => {
      console.error(error);
      status.textContent = "Could not load services.";
    });
  }
}

/* ================= SERVICE ================= */

function initServicePage() {
  const mapEl = document.getElementById("serviceMap");
  if (!mapEl) return;

  const service = getSelectedService();
  const userLocation = getUserLocation();
  const mapsButton = document.getElementById("openMapsBtn");

  if (!service) {
    document.getElementById("serviceName").textContent = "No service selected.";
    document.getElementById("serviceOrg").textContent = "No service selected.";
    document.getElementById("routeStatus").textContent = "Go back and choose a service first.";
    if (mapsButton) mapsButton.style.display = "none";
    return;
  }

  document.getElementById("serviceName").textContent = service.name || "N/A";
  document.getElementById("serviceOrg").textContent = service.name || "N/A";
  document.getElementById("serviceProvider").textContent = formatProvider(service.provider_name);
  document.getElementById("serviceType").textContent = service.service_type || "N/A";
  document.getElementById("servicePostcode").textContent = service.postcode || "N/A";
  document.getElementById("servicePhone").textContent = service.phone_number || "N/A";
  document.getElementById("serviceAddress").textContent = service.physical_address || "N/A";
  document.getElementById("serviceOpening").textContent = service.opening_times || "N/A";
  document.getElementById("serviceDescription").textContent = service.description || "N/A";
  document.getElementById("serviceSource").href = service.source_url || "#";

  if (service.latitude == null || service.longitude == null) {
    document.getElementById("routeStatus").textContent = "Location not available for this service.";
    if (mapsButton) mapsButton.style.display = "none";
    return;
  }

  const map = L.map("serviceMap").setView([service.latitude, service.longitude], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19
  }).addTo(map);

  const destinationMarker = L.marker([service.latitude, service.longitude]).addTo(map);
  destinationMarker.bindPopup(service.name || "Destination");

  if (userLocation) {
    const userMarker = L.marker([userLocation.lat, userLocation.lng]).addTo(map);
    userMarker.bindPopup("Start point");

    const line = L.polyline(
      [
        [userLocation.lat, userLocation.lng],
        [service.latitude, service.longitude]
      ],
      {
        color: "#2563eb",
        weight: 4,
        opacity: 0.8
      }
    ).addTo(map);

    map.fitBounds(line.getBounds(), { padding: [30, 30] });

    const distance = getDistanceKm(
      userLocation.lat,
      userLocation.lng,
      service.latitude,
      service.longitude
    );

    document.getElementById("routeStatus").textContent =
      `Approximate distance: ${distance.toFixed(2)} km`;

    if (mapsButton) {
      mapsButton.href = buildGoogleMapsDirectionsUrl(
        userLocation.lat,
        userLocation.lng,
        service.latitude,
        service.longitude,
        "walking"
      );
      mapsButton.style.display = "inline-block";
    }
  } else {
    document.getElementById("routeStatus").textContent =
      "Use your location or postcode first to see directions.";

    if (mapsButton) {
      mapsButton.href = buildGoogleMapsSearchUrl(service.latitude, service.longitude);
      mapsButton.style.display = "inline-block";
    }
  }
}

/* ================= INIT ================= */

document.addEventListener("DOMContentLoaded", () => {
  initHomePage();
  initResultsPage();
  initServicePage();
});