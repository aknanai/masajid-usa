/**
 * Nearby Masajid Module
 * Finds and displays masajid near the user's location, sorted by distance
 */

const NearbyMasajid = {
    defaultRadius: 10, // miles
    currentRadius: 10,
    userLocation: null,
    allMasajid: [],
    initialized: false,

    /**
     * Convert degrees to radians
     */
    toRad(deg) {
        return deg * (Math.PI / 180);
    },

    /**
     * Calculate distance between two coordinates using Haversine formula
     * @returns distance in miles
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 3959; // Earth's radius in miles
        const dLat = this.toRad(lat2 - lat1);
        const dLon = this.toRad(lon2 - lon1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    },

    /**
     * Get user location - checks cache first, then requests if needed
     */
    async getLocation() {
        // Check localStorage cache first (same as prayer-times.js)
        const cached = localStorage.getItem('userLocation');
        if (cached) {
            try {
                const location = JSON.parse(cached);
                // Check if cache is less than 24 hours old
                if (location.timestamp && (Date.now() - location.timestamp) < 24 * 60 * 60 * 1000) {
                    this.userLocation = location;
                    return location;
                }
            } catch (e) {
                // Invalid cache, continue to request new location
            }
        }

        // Request new location
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const location = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        timestamp: Date.now()
                    };
                    // Cache the location
                    localStorage.setItem('userLocation', JSON.stringify(location));
                    this.userLocation = location;
                    resolve(location);
                },
                (error) => {
                    reject(error);
                },
                {
                    enableHighAccuracy: false,
                    timeout: 10000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        });
    },

    /**
     * Find masajid within radius, sorted by distance
     */
    findNearby(radius) {
        if (!this.userLocation || !this.allMasajid.length) {
            return [];
        }

        const nearby = [];
        const userLat = this.userLocation.lat;
        const userLon = this.userLocation.lon;

        for (const masjid of this.allMasajid) {
            if (masjid.coordinates && masjid.coordinates.lat && masjid.coordinates.lon) {
                const distance = this.calculateDistance(
                    userLat, userLon,
                    masjid.coordinates.lat, masjid.coordinates.lon
                );

                if (distance <= radius) {
                    nearby.push({
                        ...masjid,
                        distance: distance
                    });
                }
            }
        }

        // Sort by distance (closest first)
        nearby.sort((a, b) => a.distance - b.distance);

        return nearby;
    },

    /**
     * Format distance for display
     */
    formatDistance(miles) {
        if (miles < 0.1) {
            return '< 0.1 mi';
        } else if (miles < 1) {
            return miles.toFixed(1) + ' mi';
        } else {
            return miles.toFixed(1) + ' mi';
        }
    },

    /**
     * Render the nearby masajid list
     */
    render(nearbyList) {
        const container = document.getElementById('nearby-results');
        const section = document.getElementById('nearby-section');

        if (!container || !section) return;

        if (nearbyList.length === 0) {
            container.innerHTML = `
                <div class="no-nearby-message">
                    <p>${window.i18n?.no_nearby || 'No masajid found within ' + this.currentRadius + ' miles'}</p>
                </div>
            `;
            section.style.display = 'block';
            return;
        }

        let html = '<div class="masajid-grid">';

        for (const masjid of nearbyList) {
            const directionsUrl = masjid.coordinates ?
                `https://www.google.com/maps?q=${masjid.coordinates.lat},${masjid.coordinates.lon}` : '#';

            html += `
                <div class="masjid-card" data-id="${masjid.id}">
                    <div class="masjid-card-header">
                        <h3 class="masjid-name">${masjid.name}</h3>
                        <span class="distance-badge">${this.formatDistance(masjid.distance)}</span>
                    </div>
                    <div class="masjid-details">
                        ${masjid.address?.street ? `
                        <div class="masjid-detail">
                            <span class="icon">&#128205;</span>
                            ${masjid.address.street}
                        </div>
                        ` : ''}
                        <div class="masjid-detail">
                            <span class="icon">&#127961;</span>
                            ${masjid.address?.city || 'N/A'}, ${masjid.address?.state || ''} ${masjid.address?.zip || ''}
                        </div>
                        ${masjid.phone ? `
                        <div class="masjid-detail">
                            <span class="icon">&#128222;</span>
                            <a href="tel:${masjid.phone}">${masjid.phone}</a>
                        </div>
                        ` : ''}
                    </div>
                    <div class="masjid-actions">
                        <a href="${directionsUrl}" target="_blank" class="btn btn-primary">
                            &#128506; ${window.i18n?.directions || 'Directions'}
                        </a>
                        <button class="favorite-btn" data-id="${masjid.id}" onclick="NearbyMasajid.handleFavorite(this, ${JSON.stringify(masjid).replace(/"/g, '&quot;')})" title="${window.i18n?.save_to_favorites || 'Save to favorites'}">&#9825;</button>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
        section.style.display = 'block';

        // Update favorite buttons state
        this.updateFavoriteButtons();
    },

    /**
     * Handle favorite button click
     */
    handleFavorite(btn, masjidData) {
        if (typeof Favorites !== 'undefined') {
            Favorites.handleClick(btn, masjidData);
        }
    },

    /**
     * Update favorite buttons state based on localStorage
     */
    updateFavoriteButtons() {
        if (typeof Favorites === 'undefined') return;

        const buttons = document.querySelectorAll('#nearby-results .favorite-btn');
        buttons.forEach(btn => {
            const id = btn.dataset.id;
            if (Favorites.isFavorite(id)) {
                btn.innerHTML = '&#9829;';
                btn.classList.add('active');
            }
        });
    },

    /**
     * Show loading state
     */
    showLoading() {
        const container = document.getElementById('nearby-results');
        const section = document.getElementById('nearby-section');
        if (container && section) {
            container.innerHTML = `
                <div class="nearby-loading">
                    <p>${window.i18n?.finding_location || 'Finding your location...'}</p>
                </div>
            `;
            section.style.display = 'block';
        }
    },

    /**
     * Show location prompt
     */
    showLocationPrompt() {
        const container = document.getElementById('nearby-results');
        const section = document.getElementById('nearby-section');
        if (container && section) {
            container.innerHTML = `
                <div class="location-prompt">
                    <p>${window.i18n?.enable_location || 'Enable location to find nearby masajid'}</p>
                    <button class="btn btn-primary" onclick="NearbyMasajid.requestLocation()">
                        ${window.i18n?.enable_location_btn || 'Enable Location'}
                    </button>
                </div>
            `;
            section.style.display = 'block';
        }
    },

    /**
     * Request location and update display
     */
    async requestLocation() {
        this.showLoading();
        try {
            await this.getLocation();
            this.update();
        } catch (error) {
            const container = document.getElementById('nearby-results');
            if (container) {
                container.innerHTML = `
                    <div class="location-error">
                        <p>${window.i18n?.location_denied || 'Location access denied. Please enable location services.'}</p>
                    </div>
                `;
            }
        }
    },

    /**
     * Update the display with current radius
     */
    update() {
        if (!this.userLocation) {
            this.showLocationPrompt();
            return;
        }

        const nearbyList = this.findNearby(this.currentRadius);
        this.render(nearbyList);
    },

    /**
     * Handle radius change
     */
    onRadiusChange(newRadius) {
        this.currentRadius = parseInt(newRadius, 10);
        this.update();
    },

    /**
     * Initialize the module
     */
    async init(masajidData) {
        if (this.initialized) return;

        this.allMasajid = masajidData || [];
        this.initialized = true;

        // Set up radius selector event listener
        const radiusSelect = document.getElementById('radius-select');
        if (radiusSelect) {
            radiusSelect.addEventListener('change', (e) => {
                this.onRadiusChange(e.target.value);
            });
        }

        // Check if we have cached location
        const cached = localStorage.getItem('userLocation');
        if (cached) {
            try {
                const location = JSON.parse(cached);
                if (location.timestamp && (Date.now() - location.timestamp) < 24 * 60 * 60 * 1000) {
                    this.userLocation = location;
                    this.update();
                    return;
                }
            } catch (e) {
                // Invalid cache
            }
        }

        // Show location prompt if no cached location
        this.showLocationPrompt();
    }
};

// Export for global access
window.NearbyMasajid = NearbyMasajid;
