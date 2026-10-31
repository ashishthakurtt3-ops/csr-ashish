import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

def minify_js(content: str) -> str:
    # Remove single-line comments that don't look like URLs
    content = re.sub(r'^[ \t]*//.*$', '', content, flags=re.MULTILINE)
    # Remove multi-line comments
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    # Compress consecutive whitespace
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return '\n'.join(lines)

def minify_css(content: str) -> str:
    # Remove CSS comments
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    # Remove newlines and compress whitespace around selectors/braces
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([\{\}\:\;\,])\s*', r'\1', content)
    return content.strip()

class Command(BaseCommand):
    help = "Minify static assets (app.js and style.css)"

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        js_src = base_dir / 'static' / 'js' / 'app.js'
        js_dst = base_dir / 'static' / 'js' / 'app.min.js'
        css_src = base_dir / 'static' / 'css' / 'style.css'
        css_dst = base_dir / 'static' / 'css' / 'style.min.css'

        if js_src.exists():
            orig_size = js_src.stat().st_size
            min_js = minify_js(js_src.read_text(encoding='utf-8'))
            js_dst.write_text(min_js, encoding='utf-8')
            new_size = js_dst.stat().st_size
            self.stdout.write(self.style.SUCCESS(f"Minified {js_src.name}: {orig_size/1024:.1f} KB -> {new_size/1024:.1f} KB"))

        if css_src.exists():
            orig_size = css_src.stat().st_size
            min_css = minify_css(css_src.read_text(encoding='utf-8'))
            css_dst.write_text(min_css, encoding='utf-8')
            new_size = css_dst.stat().st_size
            self.stdout.write(self.style.SUCCESS(f"Minified {css_src.name}: {orig_size/1024:.1f} KB -> {new_size/1024:.1f} KB"))
