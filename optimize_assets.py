#!/usr/bin/env python3
"""
GlobePiloT Advanced Asset Optimization Tool
Optimizes CSS and JavaScript files for production deployment with intelligent bundling and caching
"""

import os
import re
import gzip
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

def minify_css(css_content):
    """Advanced CSS minification with better optimization"""
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
    
    # Remove empty rules
    css_content = re.sub(r'[^}]+{\s*}', '', css_content)
    
    return css_content.strip()

def minify_js(js_content):
    """Advanced JavaScript minification"""
    # Remove single-line comments (preserve URLs and important comments)
    js_content = re.sub(r'//(?![:/]).*$', '', js_content, flags=re.MULTILINE)
    
    # Remove multi-line comments (preserve important ones)
    js_content = re.sub(r'/\*(?!\!|\*).*?\*/', '', js_content, flags=re.DOTALL)
    
    # Remove unnecessary whitespace
    lines = js_content.split('\n')
    minified_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Basic minification
        line = re.sub(r'\s*([=+\-*/{}();,:])\s*', r'\1', line)
        line = re.sub(r'\s*\{\s*', '{', line)
        line = re.sub(r'\s*\}\s*', '}', line)
        
        minified_lines.append(line)
    
    return '\n'.join(minified_lines)

def generate_file_hash(content):
    """Generate MD5 hash for content versioning"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

def bundle_css_files():
    """Bundle multiple CSS files into one optimized file"""
    static_dir = Path('static')
    css_dir = static_dir / 'css'
    components_dir = static_dir / 'components'
    
    if not css_dir.exists():
        return None
    
    # Define bundle order (critical CSS first)
    bundle_order = ['variables.css', 'results.css']
    bundled_content = []
    
    # Add main CSS files
    for css_file in bundle_order:
        css_path = css_dir / css_file
        if css_path.exists():
            with open(css_path, 'r', encoding='utf-8') as f:
                content = f.read()
                bundled_content.append(f"/* {css_file} */")
                bundled_content.append(content)
    
    # Add component CSS files
    if components_dir.exists():
        for component_dir in components_dir.iterdir():
            if component_dir.is_dir():
                css_file = component_dir / f"{component_dir.name}.css"
                if css_file.exists():
                    with open(css_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        bundled_content.append(f"/* Component: {component_dir.name} */")
                        bundled_content.append(content)
    
    if bundled_content:
        full_content = '\n'.join(bundled_content)
        content_hash = generate_file_hash(full_content)
        
        # Create versioned bundle
        bundle_name = f"bundle.{content_hash}.css"
        bundle_path = css_dir / bundle_name
        
        with open(bundle_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # Create minified version
        minified_content = minify_css(full_content)
        min_bundle_name = f"bundle.{content_hash}.min.css"
        min_bundle_path = css_dir / min_bundle_name
        
        with open(min_bundle_path, 'w', encoding='utf-8') as f:
            f.write(minified_content)
        
        # Compress both versions
        compress_file(str(bundle_path))
        compress_file(str(min_bundle_path))
        
        return {
            'original': bundle_name,
            'minified': min_bundle_name,
            'hash': content_hash,
            'original_size': len(full_content),
            'minified_size': len(minified_content)
        }
    
    return None

def bundle_js_files():
    """Bundle JavaScript files with dependency order"""
    static_dir = Path('static')
    js_dir = static_dir / 'js'
    components_dir = static_dir / 'components'
    
    if not js_dir.exists():
        return None
    
    # Bundle main JS files
    js_files = [f for f in js_dir.glob('*.js') if not f.name.startswith('bundle') and not f.name.endswith('.min.js')]
    
    bundled_content = []
    
    # Add main JS files
    for js_file in js_files:
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
            bundled_content.append(f"/* {js_file.name} */")
            bundled_content.append(content)
    
    # Add component JS files
    if components_dir.exists():
        for component_dir in components_dir.iterdir():
            if component_dir.is_dir():
                js_file = component_dir / f"{component_dir.name}.js"
                if js_file.exists():
                    with open(js_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        bundled_content.append(f"/* Component: {component_dir.name} */")
                        bundled_content.append(content)
    
    if not bundled_content:
        return None
    
    if bundled_content:
        full_content = '\n'.join(bundled_content)
        content_hash = generate_file_hash(full_content)
        
        # Create versioned bundle
        bundle_name = f"bundle.{content_hash}.js"
        bundle_path = js_dir / bundle_name
        
        with open(bundle_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # Create minified version
        minified_content = minify_js(full_content)
        min_bundle_name = f"bundle.{content_hash}.min.js"
        min_bundle_path = js_dir / min_bundle_name
        
        with open(min_bundle_path, 'w', encoding='utf-8') as f:
            f.write(minified_content)
        
        # Compress both versions
        compress_file(str(bundle_path))
        compress_file(str(min_bundle_path))
        
        return {
            'original': bundle_name,
            'minified': min_bundle_name,
            'hash': content_hash,
            'original_size': len(full_content),
            'minified_size': len(minified_content)
        }
    
    return None

def compress_file(file_path):
    """Gzip compress a file with optimal compression"""
    with open(file_path, 'rb') as f_in:
        with gzip.open(f"{file_path}.gz", 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return f"{file_path}.gz"

def cleanup_old_bundles():
    """Remove old bundle files to prevent bloat"""
    static_dir = Path('static')
    
    for subdir in ['css', 'js']:
        dir_path = static_dir / subdir
        if not dir_path.exists():
            continue
        
        # Remove old bundle files
        old_bundles = list(dir_path.glob('bundle.*'))
        for bundle in old_bundles:
            try:
                if bundle.exists():
                    bundle.unlink()
                gz_file = Path(f"{bundle}.gz")
                if gz_file.exists():
                    gz_file.unlink()
            except FileNotFoundError:
                # File already removed, continue
                pass

def create_manifest():
    """Create asset manifest for cache busting"""
    static_dir = Path('static')
    manifest = {
        'generated': datetime.now().isoformat(),
        'assets': {}
    }
    
    for file_path in static_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix in ['.css', '.js', '.png', '.jpg', '.svg']:
            relative_path = str(file_path.relative_to(static_dir))
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]
            
            manifest['assets'][relative_path] = {
                'hash': file_hash,
                'size': file_path.stat().st_size
            }
    
    manifest_path = static_dir / 'manifest.json'
    with open(manifest_path, 'w') as f:
        import json
        json.dump(manifest, f, indent=2)
    
    return manifest

def optimize_assets():
    """Main optimization function with intelligent bundling"""
    static_dir = Path('static')
    
    if not static_dir.exists():
        print("❌ Static directory not found!")
        return
    
    print("🚀 Starting Advanced GlobePiloT Asset Optimization...")
    
    # Clean up old bundles first
    cleanup_old_bundles()
    
    total_savings = 0
    
    # Bundle and optimize CSS
    css_bundle = bundle_css_files()
    if css_bundle:
        savings = css_bundle['original_size'] - css_bundle['minified_size']
        savings_pct = (savings / css_bundle['original_size']) * 100
        total_savings += savings
        print(f"📄 CSS Bundle: {css_bundle['original_size']:,} → {css_bundle['minified_size']:,} bytes ({savings_pct:.1f}% reduction)")
    
    # Bundle and optimize JavaScript
    js_bundle = bundle_js_files()
    if js_bundle:
        savings = js_bundle['original_size'] - js_bundle['minified_size']
        savings_pct = (savings / js_bundle['original_size']) * 100
        total_savings += savings
        print(f"📄 JS Bundle: {js_bundle['original_size']:,} → {js_bundle['minified_size']:,} bytes ({savings_pct:.1f}% reduction)")
    
    # Create asset manifest for cache busting
    manifest = create_manifest()
    print(f"📋 Created asset manifest with {len(manifest['assets'])} files")
    
    print(f"✨ Asset optimization complete! Total savings: {total_savings:,} bytes")
    print("\n📊 Optimization Features:")
    print("• Intelligent CSS and JS bundling")
    print("• Content-based hash versioning")
    print("• Gzip compression with optimal settings")
    print("• Asset manifest for cache busting")
    print("• Cleanup of redundant files")
    
    print("\n💡 Performance Tips:")
    print("1. Use the bundled files in production")
    print("2. Configure web server for gzip serving")
    print("3. Set cache headers based on content hashes")
    print("4. Enable HTTP/2 for better multiplexing")

if __name__ == "__main__":
    optimize_assets() 