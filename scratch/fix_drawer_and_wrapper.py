import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Update .mobile-nav-drawer to have visibility hidden by default
drawer_old = """.mobile-nav-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  max-width: 90vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-color);
  z-index: 2200;
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}
.mobile-nav-drawer.show {
  transform: translateX(0);
}"""

drawer_new = """.mobile-nav-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  max-width: 90vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-color);
  z-index: 2200;
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  visibility: hidden;
  pointer-events: none;
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.32s;
  overflow: hidden;
}
.mobile-nav-drawer.show {
  transform: translateX(0);
  visibility: visible;
  pointer-events: auto;
}"""

if drawer_old in css:
    css = css.replace(drawer_old, drawer_new)
    print("Updated .mobile-nav-drawer with visibility: hidden when closed.")
else:
    print("WARNING: drawer_old not matched.")

extra_rules = """
.main-wrapper {
  max-width: 100vw !important;
  width: 100% !important;
  overflow-x: hidden !important;
}
"""
css += "\n" + extra_rules

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Saved static/css/style.css successfully.")

