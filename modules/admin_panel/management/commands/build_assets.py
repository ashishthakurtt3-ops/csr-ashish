import os
import re
import sys
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

def minify_css(css_text: str) -> str:
    # 1. Remove comments
    css_text = re.sub(r'/\*[\s\S]*?\*/', '', css_text)
    # 2. Collapse whitespace
    css_text = re.sub(r'\s+', ' ', css_text)
    # 3. Remove space around symbols
    css_text = re.sub(r'\s*([\{\}\:\;\,])\s*', r'\1', css_text)
    css_text = css_text.replace(';}', '}')
    return css_text.strip()

def minify_js(js_text: str) -> str:
    # Safe JS minification preserving strings and regexes
    lines = []
    in_multiline_comment = False
    for line in js_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if in_multiline_comment:
            if '*/' in trimmed:
                in_multiline_comment = False
                trimmed = trimmed.split('*/', 1)[1].strip()
            else:
                continue
        if trimmed.startswith('/*') and '*/' not in trimmed:
            in_multiline_comment = True
            continue
        if trimmed.startswith('//'):
            continue
        # Remove trailing single line comments if safe (not inside string)
        if '//' in trimmed and not ('http://' in trimmed or 'https://' in trimmed or '"' in trimmed or "'" in trimmed or '`' in trimmed):
            trimmed = trimmed.split('//')[0].strip()
        if trimmed:
            lines.append(trimmed)
    return '\n'.join(lines)

class Command(BaseCommand):
    help = "Builds and verifies minified static assets (app.min.js, style.min.css)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Fails with non-zero exit code if source assets are newer than minified files',
        )

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        app_js = base_dir / 'static' / 'js' / 'app.js'
        app_min_js = base_dir / 'static' / 'js' / 'app.min.js'
        style_css = base_dir / 'static' / 'css' / 'style.css'
        style_min_css = base_dir / 'static' / 'css' / 'style.min.css'

        if not app_js.exists() or not style_css.exists():
            raise CommandError("Source files static/js/app.js or static/css/style.css not found.")

        is_check = options.get('check', False)

        if is_check:
            errors = []
            if not app_min_js.exists():
                errors.append("app.min.js does not exist.")
            elif app_js.stat().st_mtime > app_min_js.stat().st_mtime:
                errors.append(f"app.js ({app_js.stat().st_mtime}) is newer than app.min.js ({app_min_js.stat().st_mtime})")

            if not style_min_css.exists():
                errors.append("style.min.css does not exist.")
            elif style_css.stat().st_mtime > style_min_css.stat().st_mtime:
                errors.append(f"style.css ({style_css.stat().st_mtime}) is newer than style.min.css ({style_min_css.stat().st_mtime})")

            if errors:
                for err in errors:
                    self.stderr.write(self.style.ERROR(f"[ASSET CHECK FAILED] {err}"))
                raise CommandError("Minified assets are outdated. Run 'python manage.py build_assets' to rebuild.")
            self.stdout.write(self.style.SUCCESS("[OK] All minified static assets are up-to-date."))
            return

        # Regenerate minified files
        self.stdout.write("Minifying static/css/style.css -> static/css/style.min.css...")
        with open(style_css, 'r', encoding='utf-8') as f:
            css_content = f.read()
        min_css = minify_css(css_content)
        with open(style_min_css, 'w', encoding='utf-8') as f:
            f.write(min_css)

        self.stdout.write("Minifying static/js/app.js -> static/js/app.min.js...")
        with open(app_js, 'r', encoding='utf-8') as f:
            js_content = f.read()
        min_js = minify_js(js_content)
        with open(app_min_js, 'w', encoding='utf-8') as f:
            f.write(min_js)

        # Ensure timestamps on minified files are strictly greater than sources
        now = max(app_js.stat().st_mtime, style_css.stat().st_mtime) + 5
        os.utime(app_min_js, (now, now))
        os.utime(style_min_css, (now, now))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully built minified assets:\n"
            f"  style.min.css: {len(min_css):,} bytes (saved {len(css_content)-len(min_css):,} bytes)\n"
            f"  app.min.js:    {len(min_js):,} bytes (saved {len(js_content)-len(min_js):,} bytes)"
        ))
