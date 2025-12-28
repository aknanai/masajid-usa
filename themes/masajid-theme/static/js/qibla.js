/**
 * Qibla Direction Finder
 * Calculates the direction to the Kaaba from the user's location
 */

const Qibla = {
    // Kaaba coordinates (Mecca, Saudi Arabia)
    KAABA: {
        lat: 21.4225,
        lon: 39.8262
    },

    // Get i18n strings (fallback to English if not available)
    getI18n() {
        return window.qiblaI18n || {
            direction: "Direction",
            distance: "Distance to Kaaba",
            note: "Point the arrow towards magnetic North to find the Qibla direction.",
            finding_location: "Finding your location...",
            retry: "Retry",
            location_denied: "Location access denied. Please enable location services.",
            geolocation_unsupported: "Geolocation not supported by your browser"
        };
    },

    /**
     * Initialize the Qibla finder
     */
    async init() {
        const container = document.getElementById('qibla-container');
        if (!container) return;

        this.container = container;
        this.showLoading();

        try {
            const location = await this.getLocation();
            const qiblaData = this.calculateQibla(location.lat, location.lon);
            this.displayQibla(qiblaData, location.city);
        } catch (error) {
            this.showError(error.message);
        }
    },

    /**
     * Get user's location
     */
    async getLocation() {
        const i18n = this.getI18n();

        // Check localStorage cache
        const cached = localStorage.getItem('userLocation');
        if (cached) {
            const data = JSON.parse(cached);
            if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
                return data;
            }
        }

        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(i18n.geolocation_unsupported));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const { latitude: lat, longitude: lon } = position.coords;

                    // Get city name
                    let city = 'Your Location';
                    try {
                        const response = await fetch(
                            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
                        );
                        const data = await response.json();
                        city = data.address.city || data.address.town || data.address.village || 'Your Location';
                    } catch (e) {
                        console.log('Could not get city name');
                    }

                    const locationData = { lat, lon, city, timestamp: Date.now() };
                    localStorage.setItem('userLocation', JSON.stringify(locationData));
                    resolve(locationData);
                },
                (error) => {
                    reject(new Error(i18n.location_denied));
                },
                { timeout: 10000 }
            );
        });
    },

    /**
     * Calculate Qibla direction using spherical geometry
     * Returns bearing in degrees from North (0-360)
     */
    calculateQibla(userLat, userLon) {
        const toRad = deg => deg * Math.PI / 180;
        const toDeg = rad => rad * 180 / Math.PI;

        const lat1 = toRad(userLat);
        const lon1 = toRad(userLon);
        const lat2 = toRad(this.KAABA.lat);
        const lon2 = toRad(this.KAABA.lon);

        // Calculate bearing
        const dLon = lon2 - lon1;
        const y = Math.sin(dLon) * Math.cos(lat2);
        const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
        let bearing = toDeg(Math.atan2(y, x));

        // Normalize to 0-360
        bearing = (bearing + 360) % 360;

        // Calculate distance using Haversine formula
        const R = 6371; // Earth's radius in km
        const dLat = lat2 - lat1;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1) * Math.cos(lat2) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;

        // Get compass direction name
        const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                           'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
        const index = Math.round(bearing / 22.5) % 16;
        const compassDirection = directions[index];

        return {
            bearing: bearing.toFixed(1),
            distance: distance.toFixed(0),
            distanceMiles: (distance * 0.621371).toFixed(0),
            compassDirection
        };
    },

    /**
     * Display the Qibla direction
     */
    displayQibla(data, city) {
        const i18n = this.getI18n();

        this.container.innerHTML = `
            <div class="qibla-content">
                <div class="compass-wrapper">
                    <div class="compass">
                        <div class="compass-cardinal north">N</div>
                        <div class="compass-cardinal east">E</div>
                        <div class="compass-cardinal south">S</div>
                        <div class="compass-cardinal west">W</div>
                        <div class="qibla-arrow" id="qibla-arrow" style="transform: translate(-50%, -100%) rotate(${data.bearing}deg);"></div>
                        <div class="compass-center"></div>
                    </div>
                </div>

                <div class="qibla-info">
                    <h3>${city}</h3>
                    <div class="qibla-stat">
                        <span class="qibla-stat-label">${i18n.direction}</span>
                        <span class="qibla-stat-value">${data.bearing}&deg; ${data.compassDirection}</span>
                    </div>
                    <div class="qibla-stat">
                        <span class="qibla-stat-label">${i18n.distance}</span>
                        <span class="qibla-stat-value">${Number(data.distance).toLocaleString()} km (${Number(data.distanceMiles).toLocaleString()} mi)</span>
                    </div>
                </div>

                <p class="qibla-note" style="margin-top: 1.5rem; font-size: 0.875rem; color: var(--text-light); text-align: center;">
                    ${i18n.note}
                </p>
            </div>
        `;

        // Animate the arrow
        setTimeout(() => {
            const arrow = document.getElementById('qibla-arrow');
            if (arrow) {
                arrow.style.transition = 'transform 1s ease-out';
            }
        }, 100);
    },

    /**
     * Show loading state
     */
    showLoading() {
        const i18n = this.getI18n();

        this.container.innerHTML = `
            <div class="qibla-loading">
                <div class="loading-spinner"></div>
                <p>${i18n.finding_location}</p>
            </div>
        `;
    },

    /**
     * Show error state
     */
    showError(message) {
        const i18n = this.getI18n();

        this.container.innerHTML = `
            <div class="qibla-error">
                <p>${message}</p>
                <button onclick="Qibla.init()" class="btn btn-primary">${i18n.retry}</button>
            </div>
        `;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Qibla.init();
});
