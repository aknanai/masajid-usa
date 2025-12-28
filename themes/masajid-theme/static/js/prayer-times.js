/**
 * Prayer Times Widget
 * Uses the Aladhan API to fetch accurate prayer times based on user location
 */

const PrayerTimes = {
    // Aladhan API endpoint
    API_BASE: 'https://api.aladhan.com/v1',

    // Prayer names
    PRAYERS: ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha'],

    // Cache key
    CACHE_KEY: 'prayerTimesData',
    LOCATION_KEY: 'userLocation',

    /**
     * Initialize the prayer times widget
     */
    async init() {
        const widget = document.getElementById('prayer-times-widget');
        if (!widget) return;

        this.widget = widget;
        this.showLoading();

        try {
            const location = await this.getLocation();
            const times = await this.fetchPrayerTimes(location.lat, location.lon);
            this.displayTimes(times, location.city);
            this.startCountdown(times);
        } catch (error) {
            this.showError(error.message);
        }
    },

    /**
     * Get user's location (with caching)
     */
    async getLocation() {
        // Check cache first
        const cached = localStorage.getItem(this.LOCATION_KEY);
        if (cached) {
            const data = JSON.parse(cached);
            // Cache valid for 24 hours
            if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
                return data;
            }
        }

        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const { latitude: lat, longitude: lon } = position.coords;

                    // Get city name from coordinates
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
                    localStorage.setItem(this.LOCATION_KEY, JSON.stringify(locationData));
                    resolve(locationData);
                },
                (error) => {
                    reject(new Error('Location access denied. Please enable location services.'));
                },
                { timeout: 10000 }
            );
        });
    },

    /**
     * Fetch prayer times from Aladhan API
     */
    async fetchPrayerTimes(lat, lon) {
        const today = new Date();
        const dateStr = `${today.getDate()}-${today.getMonth() + 1}-${today.getFullYear()}`;

        // Check cache
        const cacheKey = `${this.CACHE_KEY}_${dateStr}_${lat.toFixed(2)}_${lon.toFixed(2)}`;
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
            return JSON.parse(cached);
        }

        const response = await fetch(
            `${this.API_BASE}/timings/${dateStr}?latitude=${lat}&longitude=${lon}&method=2`
        );

        if (!response.ok) {
            throw new Error('Failed to fetch prayer times');
        }

        const data = await response.json();
        const timings = data.data.timings;

        // Cache the result
        localStorage.setItem(cacheKey, JSON.stringify(timings));

        return timings;
    },

    /**
     * Display prayer times in the widget
     */
    displayTimes(times, city) {
        const now = new Date();
        const currentMinutes = now.getHours() * 60 + now.getMinutes();

        let nextPrayer = null;
        let nextPrayerTime = null;

        const prayerHTML = this.PRAYERS.map(prayer => {
            const time = times[prayer];
            const [hours, minutes] = time.split(':').map(Number);
            const prayerMinutes = hours * 60 + minutes;

            // Check if this is the next prayer
            if (!nextPrayer && prayerMinutes > currentMinutes) {
                nextPrayer = prayer;
                nextPrayerTime = time;
            }

            const isNext = prayer === nextPrayer;
            const isPast = prayerMinutes < currentMinutes;

            return `
                <div class="prayer-time ${isNext ? 'next-prayer' : ''} ${isPast ? 'past' : ''}">
                    <span class="prayer-name">${prayer}</span>
                    <span class="prayer-value">${this.formatTime(time)}</span>
                </div>
            `;
        }).join('');

        // If no next prayer found today, it's Fajr tomorrow
        if (!nextPrayer) {
            nextPrayer = 'Fajr';
            nextPrayerTime = times.Fajr;
        }

        this.widget.innerHTML = `
            <div class="prayer-header">
                <h3>Prayer Times</h3>
                <span class="location">${city}</span>
            </div>
            <div class="prayer-grid">
                ${prayerHTML}
            </div>
            <div class="next-prayer-countdown">
                <span class="countdown-label">Next: ${nextPrayer} in</span>
                <span class="countdown-value" id="countdown"></span>
            </div>
        `;

        this.nextPrayer = nextPrayer;
        this.nextPrayerTime = nextPrayerTime;
    },

    /**
     * Format 24h time to 12h format
     */
    formatTime(time24) {
        const [hours, minutes] = time24.split(':');
        const h = parseInt(hours);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        return `${h12}:${minutes} ${ampm}`;
    },

    /**
     * Start countdown to next prayer
     */
    startCountdown(times) {
        const updateCountdown = () => {
            const now = new Date();
            const [hours, minutes] = this.nextPrayerTime.split(':').map(Number);

            let target = new Date(now);
            target.setHours(hours, minutes, 0, 0);

            // If the prayer time has passed, it's tomorrow's Fajr
            if (target <= now) {
                target.setDate(target.getDate() + 1);
                target.setHours(times.Fajr.split(':')[0], times.Fajr.split(':')[1], 0, 0);
            }

            const diff = target - now;
            const h = Math.floor(diff / (1000 * 60 * 60));
            const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const s = Math.floor((diff % (1000 * 60)) / 1000);

            const countdown = document.getElementById('countdown');
            if (countdown) {
                countdown.textContent = `${h}h ${m}m ${s}s`;
            }
        };

        updateCountdown();
        setInterval(updateCountdown, 1000);
    },

    /**
     * Show loading state
     */
    showLoading() {
        this.widget.innerHTML = `
            <div class="prayer-loading">
                <div class="loading-spinner"></div>
                <p>Loading prayer times...</p>
            </div>
        `;
    },

    /**
     * Show error state
     */
    showError(message) {
        this.widget.innerHTML = `
            <div class="prayer-error">
                <p>${message}</p>
                <button onclick="PrayerTimes.init()" class="btn btn-primary">Retry</button>
            </div>
        `;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    PrayerTimes.init();
});
