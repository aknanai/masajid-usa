/**
 * Favorites/Bookmarks System
 * Uses localStorage to save and manage favorite masajid
 */

const Favorites = {
    STORAGE_KEY: 'favoriteMasajid',

    /**
     * Get all favorites from localStorage
     */
    getAll() {
        const stored = localStorage.getItem(this.STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    },

    /**
     * Save favorites to localStorage
     */
    save(favorites) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(favorites));
    },

    /**
     * Check if a masjid is favorited
     */
    isFavorite(masjidId) {
        const favorites = this.getAll();
        return favorites.some(f => f.id === masjidId);
    },

    /**
     * Add a masjid to favorites
     */
    add(masjid) {
        const favorites = this.getAll();
        if (!favorites.some(f => f.id === masjid.id)) {
            favorites.push({
                id: masjid.id,
                name: masjid.name,
                address: masjid.address,
                coordinates: masjid.coordinates,
                phone: masjid.phone,
                website: masjid.website,
                addedAt: Date.now()
            });
            this.save(favorites);
        }
    },

    /**
     * Remove a masjid from favorites
     */
    remove(masjidId) {
        let favorites = this.getAll();
        favorites = favorites.filter(f => f.id !== masjidId);
        this.save(favorites);
    },

    /**
     * Toggle favorite status
     */
    toggle(masjid) {
        if (this.isFavorite(masjid.id)) {
            this.remove(masjid.id);
            return false;
        } else {
            this.add(masjid);
            return true;
        }
    },

    /**
     * Initialize favorite buttons on the page
     */
    initButtons() {
        // This will be called after masjid cards are rendered
        document.querySelectorAll('.favorite-btn').forEach(btn => {
            const masjidId = btn.dataset.id;
            if (this.isFavorite(masjidId)) {
                btn.classList.add('active');
                btn.innerHTML = '&#10084;'; // Filled heart
            }
        });
    },

    /**
     * Handle favorite button click
     */
    handleClick(btn, masjidData) {
        const isNowFavorite = this.toggle(masjidData);

        if (isNowFavorite) {
            btn.classList.add('active');
            btn.innerHTML = '&#10084;'; // Filled heart
        } else {
            btn.classList.remove('active');
            btn.innerHTML = '&#9825;'; // Empty heart
        }
    },

    /**
     * Render favorites on the favorites page
     */
    renderFavoritesPage() {
        const container = document.getElementById('favorites-list');
        if (!container) return;

        const favorites = this.getAll();

        // Get i18n strings (fallback to English if not available)
        const i18n = window.favoritesI18n || {
            no_favorites: "You haven't saved any masajid yet.",
            browse_masajid: "Browse Masajid",
            saved_count: "{count} saved masajid",
            directions: "Directions",
            visit_website: "Visit Website"
        };

        if (favorites.length === 0) {
            container.innerHTML = `
                <div class="empty-favorites">
                    <p>${i18n.no_favorites}</p>
                    <a href="${window.BASE_URL || '/'}" class="btn btn-primary">${i18n.browse_masajid}</a>
                </div>
            `;
            return;
        }

        // Sort by most recently added
        favorites.sort((a, b) => b.addedAt - a.addedAt);

        container.innerHTML = favorites.map(m => `
            <div class="masjid-card" data-id="${m.id}">
                <div class="masjid-card-header">
                    <h3 class="masjid-name">${m.name}</h3>
                    <button class="favorite-btn active" data-id="${m.id}" onclick="Favorites.removeFromPage('${m.id}')">&#10084;</button>
                </div>
                <div class="masjid-details">
                    ${m.address.street ? `<div class="masjid-detail"><span class="icon">&#128205;</span>${m.address.street}</div>` : ''}
                    <div class="masjid-detail"><span class="icon">&#127961;</span>${m.address.city || 'N/A'}, ${m.address.state || 'N/A'} ${m.address.zip || ''}</div>
                    ${m.phone ? `<div class="masjid-detail"><span class="icon">&#128222;</span><a href="tel:${m.phone}">${m.phone}</a></div>` : ''}
                    ${m.website ? `<div class="masjid-detail"><span class="icon">&#127760;</span><a href="${m.website}" target="_blank">${i18n.visit_website}</a></div>` : ''}
                </div>
                <div class="masjid-actions">
                    ${m.coordinates && m.coordinates.lat && m.coordinates.lon ? `
                        <a href="https://www.google.com/maps?q=${m.coordinates.lat},${m.coordinates.lon}" target="_blank" class="btn btn-primary">
                            &#128506; ${i18n.directions}
                        </a>
                    ` : ''}
                </div>
            </div>
        `).join('');

        // Update count
        const countEl = document.getElementById('favorites-count');
        if (countEl) {
            countEl.textContent = i18n.saved_count.replace('{count}', favorites.length);
        }
    },

    /**
     * Remove from favorites page and re-render
     */
    removeFromPage(masjidId) {
        this.remove(masjidId);
        this.renderFavoritesPage();
    }
};

// Initialize favorites when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Favorites.initButtons();

    // If on favorites page, render the list
    if (document.getElementById('favorites-list')) {
        Favorites.renderFavoritesPage();
    }
});
