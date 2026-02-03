#!/bin/bash
#
# CS (Conversation Search) Plugin Installer for Claude Code
#
# This script installs the cs plugin to make /cs:* commands available.
#
# Usage:
#   ./install.sh              # Install to default location (~/.claude/plugins/cs)
#   ./install.sh --uninstall  # Remove the plugin
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PLUGIN_NAME="cs"
CLAUDE_DIR="${HOME}/.claude"
PLUGINS_DIR="${CLAUDE_DIR}/plugins"
PLUGIN_DIR="${PLUGINS_DIR}/${PLUGIN_NAME}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         CS - Conversation Search Plugin v2.0               ║"
    echo "║       Navigate & Search Claude Code Chat History           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_prerequisites() {
    echo "Checking prerequisites..."

    # Check if Claude directory exists
    if [[ ! -d "${CLAUDE_DIR}" ]]; then
        print_error "Claude directory not found at ${CLAUDE_DIR}"
        echo "Please ensure Claude Code is installed and has been run at least once."
        exit 1
    fi
    print_success "Claude directory found"

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not found"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    print_success "Python ${PYTHON_VERSION} found"

    echo ""
}

install_plugin() {
    echo "Installing CS plugin..."
    echo ""

    # Create plugins directory if it doesn't exist
    if [[ ! -d "${PLUGINS_DIR}" ]]; then
        mkdir -p "${PLUGINS_DIR}"
        print_success "Created plugins directory"
    fi

    # Create plugin directory
    if [[ -d "${PLUGIN_DIR}" ]]; then
        print_warning "Plugin directory already exists, backing up..."
        mv "${PLUGIN_DIR}" "${PLUGIN_DIR}.backup.$(date +%Y%m%d%H%M%S)"
    fi

    mkdir -p "${PLUGIN_DIR}"
    mkdir -p "${PLUGIN_DIR}/.claude-plugin"
    mkdir -p "${PLUGIN_DIR}/commands"
    print_success "Created plugin directory structure"

    # Copy main script
    cp "${SCRIPT_DIR}/search_helper.py" "${PLUGIN_DIR}/"
    chmod +x "${PLUGIN_DIR}/search_helper.py"
    print_success "Installed search_helper.py"

    # Copy plugin manifest
    cp "${SCRIPT_DIR}/.claude-plugin/plugin.json" "${PLUGIN_DIR}/.claude-plugin/"
    print_success "Installed plugin.json"

    # Copy command files
    if [[ -d "${SCRIPT_DIR}/commands" ]]; then
        cp "${SCRIPT_DIR}/commands/"*.md "${PLUGIN_DIR}/commands/"
        print_success "Installed command definitions"
    fi

    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo -e "${CYAN}=== TELEPORTATION COMMANDS ===${NC}"
    echo "  /cs:top          - Jump to conversation start"
    echo "  /cs:pre-compact  - Show before last compaction"
    echo "  /cs:find <word>  - Quick keyword search"
    echo "  /cs:anchor [lbl] - Place a searchable marker"
    echo ""
    echo -e "${CYAN}=== SEARCH COMMANDS ===${NC}"
    echo "  /cs:search <query>   - Full search with filters"
    echo "  /cs:sessions         - List all sessions"
    echo "  /cs:show <id>        - View a specific session"
    echo "  /cs:recent           - Show recent activity"
    echo "  /cs:stats            - Show usage statistics"
    echo ""
    echo -e "${YELLOW}How to use:${NC}"
    echo "  1. Start Claude Code with the plugin:"
    echo "     claude --plugin-dir ${PLUGIN_DIR}"
    echo ""
    echo "  2. Or add to your shell profile for permanent use:"
    echo "     alias claude='claude --plugin-dir ${PLUGIN_DIR}'"
    echo ""
    echo -e "${YELLOW}Navigation tip:${NC}"
    echo "  After running a command, use Ctrl+Shift+F and search"
    echo "  'CS-ANCHOR' to find anchors in your terminal scrollback."
    echo ""
}

uninstall_plugin() {
    echo "Uninstalling CS plugin..."
    echo ""

    if [[ ! -d "${PLUGIN_DIR}" ]]; then
        print_warning "Plugin directory not found, nothing to uninstall"
        exit 0
    fi

    rm -rf "${PLUGIN_DIR}"
    print_success "Removed plugin directory"

    echo ""
    echo -e "${GREEN}Uninstallation complete!${NC}"
}

# Main
print_header

case "${1:-}" in
    --uninstall|-u)
        uninstall_plugin
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --uninstall, -u  Remove the plugin"
        echo "  --help, -h       Show this help message"
        echo ""
        echo "Installation location: ${PLUGIN_DIR}"
        echo ""
        ;;
    *)
        check_prerequisites
        install_plugin
        ;;
esac
