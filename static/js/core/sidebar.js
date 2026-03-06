/**
 * Sidebar toggle functionality with localStorage persistence
 */
// SVG icon paths
const COLLAPSED_ICON = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />';
const EXPANDED_ICON = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />';
/**
 * Applies the sidebar state (collapsed or expanded)
 * @param sidebar - Sidebar element
 * @param toggleIcon - Toggle button icon SVG element
 * @param isCollapsed - Whether sidebar should be collapsed
 */
function applySidebarState(sidebar, toggleIcon, isCollapsed) {
    sidebar.classList.toggle('collapsed', isCollapsed);
    document.body.classList.toggle('sidebar-collapsed', isCollapsed);
    // Update icon
    toggleIcon.innerHTML = isCollapsed ? COLLAPSED_ICON : EXPANDED_ICON;
}
/**
 * Initializes the sidebar toggle functionality
 * Sets up event listeners and loads saved state from localStorage
 */
export function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar');
    const toggleIcon = document.getElementById('toggle-icon');
    if (!sidebar || !toggleBtn || !toggleIcon) {
        console.warn('Sidebar elements not found');
        return;
    }
    // Remove initial loading class
    document.documentElement.classList.remove('sidebar-collapsed-initial');
    // Load saved state from localStorage
    const sidebarState = localStorage.getItem('sidebarCollapsed');
    if (sidebarState === 'true') {
        applySidebarState(sidebar, toggleIcon, true);
    }
    // Handle toggle clicks
    toggleBtn.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.contains('collapsed');
        const newState = !isCollapsed;
        applySidebarState(sidebar, toggleIcon, newState);
        localStorage.setItem('sidebarCollapsed', String(newState));
    });
}
//# sourceMappingURL=sidebar.js.map