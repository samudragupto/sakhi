"""Automated accessibility audit test suite for Sakhi frontend.

Verifies:
- lang="hi" on html element
- Strict absence of inline scripts or inline styles (CSP compliant)
- Absence of external CDN scripts
- Accessible names (aria-label or innerText) on all buttons
- alt or title on images
- Presence of keyboard skip link
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

INDEX_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "index.html"
LOCALE_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "locales" / "hi.json"
STYLE_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "css" / "style.css"


def _locale_value(key: str) -> str:
    """Return a translated Hindi string by dotted locale key."""
    value = json.loads(LOCALE_PATH.read_text(encoding="utf-8"))
    for part in key.split("."):
        value = value[part]
    return str(value)


def test_html_lang_attribute() -> None:
    """Verify primary language is set to Hindi (lang='hi')."""
    with open(INDEX_HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    html_tag = soup.find("html")
    assert html_tag is not None
    assert html_tag.get("lang") == "hi"


def test_no_inline_assets_or_external_cdns() -> None:
    """Verify strict CSP compatibility for scripts, styles, and handlers."""
    with open(INDEX_HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    scripts = soup.find_all("script")
    for s in scripts:
        src = s.get("src")
        assert src is not None, "Found inline script tag violating CSP"
        assert not src.startswith("http://") and not src.startswith("https://"), (
            f"External CDN detected: {src}"
        )
    for element in soup.find_all(True):
        assert not element.has_attr("style"), f"Inline style violates CSP: {element.name}"
        assert not any(attribute.lower().startswith("on") for attribute in element.attrs), (
            f"Inline event handler violates CSP: {element.name}"
        )


def test_buttons_have_accessible_names() -> None:
    """Verify every button has an accessible name via text content or aria-label."""
    with open(INDEX_HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    buttons = soup.find_all("button")
    assert len(buttons) > 0
    for b in buttons:
        has_text = bool(b.get_text(strip=True))
        has_aria = bool(b.get("aria-label"))
        has_localized_name = bool(b.get("data-i18n") and _locale_value(b["data-i18n"]))
        has_localized_aria = bool(
            b.get("data-i18n-aria-label") and _locale_value(b["data-i18n-aria-label"])
        )
        assert has_text or has_aria or has_localized_name or has_localized_aria, (
            f"Button without accessible name: {b}"
        )


def test_keyboard_skip_link_present() -> None:
    """Verify skip link exists for keyboard navigation."""
    with open(INDEX_HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    skip_link = soup.find("a", class_="skip-link")
    assert skip_link is not None
    assert skip_link.get("href") == "#main-content"
    assert soup.find(id="main-content").get("tabindex") == "-1"


def test_images_have_alt_text_and_inputs_have_labels() -> None:
    """Ensure images and form controls have programmatic labels."""
    soup = BeautifulSoup(INDEX_HTML_PATH.read_text(encoding="utf-8"), "html.parser")
    for image in soup.find_all("img"):
        assert image.get("alt") is not None or image.get("data-i18n-alt")
    for control in soup.find_all(["input", "select", "textarea"]):
        control_id = control.get("id")
        assert control_id and soup.find("label", attrs={"for": control_id})


def test_focus_indicators_and_text_contrast() -> None:
    """Check visible keyboard focus and WCAG AA contrast for key text pairs."""
    css = STYLE_PATH.read_text(encoding="utf-8")
    assert ":focus-visible" in css and "--focus-ring:" in css

    def luminance(color: str) -> float:
        """Calculate relative luminance for a six-digit hex color."""
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(foreground: str, background: str) -> float:
        """Calculate the WCAG contrast ratio for two hex colors."""
        light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

    css_colors = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", css))
    assert contrast(css_colors["--text"], css_colors["--bg"]) >= 4.5
    assert contrast("#ffffff", css_colors["--primary-dark"]) >= 4.5
    assert contrast("#2e7d32", "#e8f5e9") >= 4.5
    assert contrast("#c62828", "#ffebee") >= 4.5
