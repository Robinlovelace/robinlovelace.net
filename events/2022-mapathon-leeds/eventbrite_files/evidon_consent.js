/*global document, window */

var checkoutExternalUrls = [
    '/checkout-external',
    '/tickets-external',
    '/signin/checkout',
];

window.EB = window.EB || {};

window.EB.EvidonConsent = (function () {
    return {
        shouldDisableEvidon: function () {
            try {
                const evidonEligibleInCheckoutWeb = window.EB.evidonEligibleInCheckoutWeb;

                if (evidonEligibleInCheckoutWeb) {
                    return this.isInsideNonTldIframe();
                }

                return this.isCheckoutOrIframe();
            } catch (e) {
                return this.isCheckoutOrIframe();
            }
        },
        isCheckoutOrIframe: function () {
            return (
                checkoutExternalUrls.indexOf(window.location.pathname) >= 0 ||
                this.isInsideIframe()
            );
        },
        isInsideIframe: function () {
            try {
                return window.self !== window.top;
            } catch (e) {
                return true;
            }
        },
        isNonTld: function () {
            try {
                return !['evbdev', 'evbqa', 'eventbrite'].find(
                    (env) => window.parent.location.hostname.indexOf(env) >= 0,
                );
            } catch (e) {
                return true;
            }
        },
        isInsideNonTldIframe: function () {
            return this.isInsideIframe() && this.isNonTld();
        },
        pixelRenderHelper: function (comment, url, isProd, isValidTld) {
            var bodyComment, img;

            if (isProd === undefined) {
                isProd = false;
            }
            if (isValidTld === undefined) {
                isValidTld = true;
            }

            if (isValidTld) {
                if (isProd) {
                    bodyComment = document.createComment(comment);
                    img = document.createElement('img');
                    img.className = 'is-hidden-accessible';
                    img.src = url;
                    img.height = '1';
                    img.width = '1';
                    img.alt = '';
                    img.ariaHidden = 'true';

                    document.body.appendChild(bodyComment);
                    document.body.appendChild(img);
                } else {
                    bodyComment = document.createComment(
                        comment + '  PIXEL OMITTED :  ' + url,
                    );
                    document.body.appendChild(bodyComment);
                }
            }
        },
    };
})();
