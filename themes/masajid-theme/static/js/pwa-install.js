// Masajid USA - PWA Install Banner
// Shows install instructions on iOS (Safari) and native install button on Android (Chrome)

(function() {
    'use strict';

    // Don't show if already installed as PWA
    if (window.matchMedia('(display-mode: standalone)').matches ||
        window.matchMedia('(display-mode: fullscreen)').matches ||
        window.matchMedia('(display-mode: minimal-ui)').matches ||
        window.navigator.standalone === true) {
        return;
    }

    // Don't show if previously dismissed
    if (localStorage.getItem('pwa-banner-dismissed')) {
        return;
    }

    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isAndroid = /android/i.test(navigator.userAgent);
    const isChrome = /chrome/i.test(navigator.userAgent);
    const isDesktop = !isIOS && !isAndroid;

    // Only show on mobile devices
    if (isDesktop) return;

    // Wait for page to load, then show banner after a short delay
    window.addEventListener('load', function() {
        setTimeout(showBanner, 3000);
    });

    // Store the beforeinstallprompt event for Android
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
        // If we haven't shown the banner yet, show Android version
        const banner = document.querySelector('.pwa-install-banner');
        if (banner && !banner.classList.contains('visible')) {
            showBanner(true);
        }
    });

    function showBanner(forceAndroid) {
        // Check if already installed (double-check)
        if (window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true) {
            return;
        }

        const banner = document.getElementById('pwa-install-banner');
        if (!banner) return;

        // Determine banner type
        if (forceAndroid || (isAndroid && deferredPrompt)) {
            showAndroidBanner(banner);
        } else if (isIOS) {
            showIOSBanner(banner);
        } else if (isAndroid) {
            showAndroidBanner(banner);
        } else {
            return; // Don't show on other platforms
        }

        // Animate in
        requestAnimationFrame(function() {
            banner.classList.add('visible');
        });

        // Close button
        const closeBtn = banner.querySelector('.banner-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                dismissBanner(banner);
            });
        }

        // Dismiss button
        const dismissBtn = banner.querySelector('.btn-dismiss');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', function() {
                dismissBanner(banner);
            });
        }

        // Install button (Android)
        const installBtn = banner.querySelector('.btn-install');
        if (installBtn) {
            installBtn.addEventListener('click', function() {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    deferredPrompt.userChoice.then(function(choiceResult) {
                        if (choiceResult.outcome === 'accepted') {
                            console.log('User installed the PWA');
                        }
                        deferredPrompt = null;
                        dismissBanner(banner);
                    });
                }
            });
        }
    }

    function showIOSBanner(banner) {
        banner.classList.remove('android');
        banner.querySelector('.banner-icon').textContent = '📲';
        banner.querySelector('.banner-title').textContent = 'Install Masajid USA';
        banner.querySelector('.banner-subtitle').textContent = 'Add to your home screen for the best experience — full-screen, offline, and faster!';
        
        const stepsContainer = banner.querySelector('.banner-steps');
        stepsContainer.innerHTML = ''; // Clear any existing steps
        
        // Step 1: Share button
        const step1 = document.createElement('span');
        step1.className = 'step';
        step1.innerHTML = '<span class="step-icon">⎙</span> Tap Share';
        stepsContainer.appendChild(step1);
        
        // Arrow
        const arrow1 = document.createElement('span');
        arrow1.className = 'step-arrow';
        arrow1.textContent = '›';
        stepsContainer.appendChild(arrow1);
        
        // Step 2: Add to Home Screen
        const step2 = document.createElement('span');
        step2.className = 'step';
        step2.innerHTML = '<span class="step-icon">➕</span> Add to Home Screen';
        stepsContainer.appendChild(step2);
        
        // Arrow
        const arrow2 = document.createElement('span');
        arrow2.className = 'step-arrow';
        arrow2.textContent = '›';
        stepsContainer.appendChild(arrow2);
        
        // Step 3: Done
        const step3 = document.createElement('span');
        step3.className = 'step';
        step3.innerHTML = '<span class="step-icon">✅</span> Done!';
        stepsContainer.appendChild(step3);

        // Hide Android action buttons
        const actions = banner.querySelector('.banner-actions');
        if (actions) actions.style.display = 'none';
    }

    function showAndroidBanner(banner) {
        banner.classList.add('android');
        banner.querySelector('.banner-icon').textContent = '📱';
        banner.querySelector('.banner-title').textContent = 'Install Masajid USA';
        banner.querySelector('.banner-subtitle').textContent = 'Install as an app for full-screen browsing, offline access, and faster loading!';
        
        const stepsContainer = banner.querySelector('.banner-steps');
        stepsContainer.innerHTML = '';
        
        const step = document.createElement('span');
        step.className = 'step';
        step.innerHTML = '<span class="step-icon">⚡</span> One tap install';
        stepsContainer.appendChild(step);

        // Show Android action buttons
        const actions = banner.querySelector('.banner-actions');
        if (actions) actions.style.display = 'flex';
    }

    function dismissBanner(banner) {
        banner.classList.remove('visible');
        // Remember dismissal for 30 days
        localStorage.setItem('pwa-banner-dismissed', Date.now().toString());
        setTimeout(function() {
            banner.style.display = 'none';
        }, 400);
    }

})();
