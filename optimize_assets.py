#!/usr/bin/env python3
"""
GlobePiloT Asset Optimization Tool
Optimizes CSS and JavaScript files for production deployment
"""

import os
import re
import gzip
import shutil
from pathlib import Path

def minify_css(css_content):
    """Basic CSS minification"""
    # Remove comments
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    # Remove unnecessary whitespace
    css_content = re.sub(r'\s+', ' ', css_content)
    css_content = re.sub(r';\s*}', '}', css_content)
    css_content = re.sub(r'{\s*', '{', css_content)
    css_content = re.sub(r'}\s*', '}', css_content)
    css_content = re.sub(r':\s*', ':', css_content)
    css_content = re.sub(r';\s*', ';', css_content)
    css_content = re.sub(r',\s*', ',', css_content)
    
    # Remove trailing semicolons before }
    css_content = re.sub(r';+}', '}', css_content)
    
    return css_content.strip()

def minify_js(js_content):
    """Basic JavaScript minification"""
    # Remove single-line comments (but preserve URLs)
    js_content = re.sub(r'//(?![:/]).*$', '', js_content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
    
    # Remove unnecessary whitespace but preserve string literals
    lines = js_content.split('\n')
    minified_lines = []
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Basic minification - remove leading/trailing spaces
        line = line.strip()
        
        # Remove spaces around operators (simple approach)
        line = re.sub(r'\s*=\s*', '=', line)
        line = re.sub(r'\s*\+\s*', '+', line)
        line = re.sub(r'\s*\{\s*', '{', line)
        line = re.sub(r'\s*\}\s*', '}', line)
        line = re.sub(r'\s*;\s*', ';', line)
        
        minified_lines.append(line)
    
    return '\n'.join(minified_lines)

def compress_file(file_path):
    """Gzip compress a file"""
    with open(file_path, 'rb') as f_in:
        with gzip.open(f"{file_path}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return f"{file_path}.gz"

def optimize_assets():
    """Main optimization function"""
    static_dir = Path('static')
    
    if not static_dir.exists():
        print("❌ Static directory not found!")
        return
    
    print("🚀 Starting GlobePiloT Asset Optimization...")
    
    # Optimize CSS files
    css_files = list(static_dir.glob('**/*.css'))
    for css_file in css_files:
        print(f"📄 Processing CSS: {css_file}")
        
        with open(css_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Create minified version
        minified_content = minify_css(original_content)
        minified_file = css_file.with_suffix('.min.css')
        
        with open(minified_file, 'w', encoding='utf-8') as f:
            f.write(minified_content)
        
        # Compress both versions
        compress_file(str(css_file))
        compress_file(str(minified_file))
        
        original_size = len(original_content)
        minified_size = len(minified_content)
        savings = ((original_size - minified_size) / original_size) * 100
        
        print(f"  ✅ Minified: {original_size} → {minified_size} bytes ({savings:.1f}% reduction)")
    
    # Optimize JavaScript files
    js_files = list(static_dir.glob('**/*.js'))
    for js_file in js_files:
        if js_file.suffix == '.min.js':  # Skip already minified files
            continue
            
        print(f"📄 Processing JS: {js_file}")
        
        with open(js_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Create minified version
        minified_content = minify_js(original_content)
        minified_file = js_file.with_suffix('.min.js')
        
        with open(minified_file, 'w', encoding='utf-8') as f:
            f.write(minified_content)
        
        # Compress both versions
        compress_file(str(js_file))
        compress_file(str(minified_file))
        
        original_size = len(original_content)
        minified_size = len(minified_content)
        savings = ((original_size - minified_size) / original_size) * 100
        
        print(f"  ✅ Minified: {original_size} → {minified_size} bytes ({savings:.1f}% reduction)")
    
    print("✨ Asset optimization complete!")
    print("\n📊 Optimization Summary:")
    print("• Created .min.css and .min.js versions")
    print("• Generated .gz compressed versions for all files")
    print("• Ready for production deployment with proper headers")
    print("\n💡 Server Configuration Tip:")
    print("Configure your web server to:")
    print("1. Serve .gz files when Accept-Encoding: gzip")
    print("2. Set cache headers for static assets")
    print("3. Use .min versions in production")

def show_file_sizes():
    """Show current file sizes for analysis"""
    static_dir = Path('static')
    if not static_dir.exists():
        return
    
    print("\n📏 Current Asset Sizes:")
    
    for file_path in static_dir.glob('**/*'):
        if file_path.is_file() and file_path.suffix in ['.css', '.js']:
            size = file_path.stat().st_size
            print(f"  {file_path}: {size:,} bytes")

if __name__ == "__main__":
    show_file_sizes()
    optimize_assets() 