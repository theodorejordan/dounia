/**
 * Utility functions for DOM manipulation and security
 */
/**
 * Escapes HTML to prevent XSS attacks
 * @param text - Text to escape
 * @returns Escaped HTML string
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
/**
 * Gets the CSRF token from the page for Django forms
 * @returns CSRF token or empty string if not found
 */
export function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}
//# sourceMappingURL=helpers.js.map