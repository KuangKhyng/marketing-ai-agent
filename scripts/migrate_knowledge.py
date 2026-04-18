"""
Migration script: Single-brand knowledge_base → Multi-brand structure.

Copies (not moves) files from old structure to new structure.
Safe to run multiple times — uses exist_ok.

Old:
  knowledge_base/brand/         → brands/tuvionline/
  knowledge_base/products/      → brands/tuvionline/products/
  knowledge_base/audience/      → brands/tuvionline/audience/
  knowledge_base/policies/      → _global/policies/ + brands/tuvionline/policies/
  knowledge_base/platforms/     → _global/platforms/
  voice_profiles/default.json   → brands/tuvionline/voice_profile.json

New:
  knowledge_base/
  ├── _global/
  │   ├── platforms/
  │   └── policies/
  └── brands/
      └── tuvionline/
          ├── brand.json
          ├── identity.md
          ├── tone_of_voice.md
          ├── visual_guidelines.md
          ├── voice_profile.json
          ├── products/
          ├── audience/
          └── policies/
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KB / "brands"
GLOBAL_DIR = KB / "_global"
VOICE_DIR = PROJECT_ROOT / "voice_profiles"


def migrate():
    print("=" * 60)
    print("  Knowledge Base Migration: Single -> Multi-Brand")
    print("=" * 60)

    # === 1. Create _global structure ===
    print("\n[1/5] Creating _global/ structure...")
    (GLOBAL_DIR / "platforms").mkdir(parents=True, exist_ok=True)
    (GLOBAL_DIR / "policies").mkdir(parents=True, exist_ok=True)

    # Copy platforms → _global/platforms/
    src_platforms = KB / "platforms"
    if src_platforms.exists():
        for f in src_platforms.glob("*.md"):
            dest = GLOBAL_DIR / "platforms" / f.name
            shutil.copy2(f, dest)
            print(f"  ✓ {f.name} → _global/platforms/")

    # Copy policies → _global/policies/
    src_policies = KB / "policies"
    if src_policies.exists():
        for f in src_policies.glob("*.md"):
            dest = GLOBAL_DIR / "policies" / f.name
            shutil.copy2(f, dest)
            print(f"  ✓ {f.name} → _global/policies/")

    # === 2. Create tuvionline brand ===
    print("\n[2/5] Creating brands/tuvionline/ structure...")
    brand_dir = BRANDS_DIR / "tuvionline"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "products").mkdir(exist_ok=True)
    (brand_dir / "audience").mkdir(exist_ok=True)
    (brand_dir / "policies").mkdir(exist_ok=True)

    # === 3. Copy brand files ===
    print("\n[3/5] Copying brand files...")
    src_brand = KB / "brand"
    if src_brand.exists():
        file_map = {
            "brand_identity.md": "identity.md",
            "tone_of_voice.md": "tone_of_voice.md",
            "visual_guidelines.md": "visual_guidelines.md",
        }
        for old_name, new_name in file_map.items():
            src = src_brand / old_name
            if src.exists():
                shutil.copy2(src, brand_dir / new_name)
                print(f"  ✓ brand/{old_name} → brands/tuvionline/{new_name}")

    # Copy products
    src_products = KB / "products"
    if src_products.exists():
        for f in src_products.glob("*.md"):
            shutil.copy2(f, brand_dir / "products" / f.name)
            print(f"  ✓ products/{f.name} → brands/tuvionline/products/")

    # Copy audience
    src_audience = KB / "audience"
    if src_audience.exists():
        for f in src_audience.glob("*.md"):
            shutil.copy2(f, brand_dir / "audience" / f.name)
            print(f"  ✓ audience/{f.name} → brands/tuvionline/audience/")

    # Copy policies (brand-specific copy)
    if src_policies.exists():
        for f in src_policies.glob("*.md"):
            shutil.copy2(f, brand_dir / "policies" / f.name)
            print(f"  ✓ policies/{f.name} → brands/tuvionline/policies/")

    # === 4. Voice profile ===
    print("\n[4/5] Copying voice profile...")
    voice_src = VOICE_DIR / "default.json"
    if voice_src.exists():
        shutil.copy2(voice_src, brand_dir / "voice_profile.json")
        print(f"  ✓ voice_profiles/default.json → brands/tuvionline/voice_profile.json")

    # === 5. Create brand.json ===
    print("\n[5/5] Creating brand.json metadata...")
    brand_meta = {
        "id": "tuvionline",
        "name": "TửViOnline",
        "description": "Nền tảng xem tử vi online cho Gen Z",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "color": "#6c5ce7",
        "icon": "✦",
        "default_channels": ["facebook", "instagram"],
        "default_goal": "awareness",
        "forbidden_claims": [
            "cam kết kết quả chắc chắn",
            "tiên tri tương lai"
        ],
        "mandatory_terms": [],
    }
    meta_path = brand_dir / "brand.json"
    meta_path.write_text(
        json.dumps(brand_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ Created brand.json")

    # === Summary ===
    print("\n" + "=" * 60)
    print("  Migration Complete!")
    print("=" * 60)
    print(f"\n  New structure created at: {KB}")
    print(f"  Brand 'tuvionline' files: {sum(1 for _ in brand_dir.rglob('*') if _.is_file())}")
    print(f"  Global files: {sum(1 for _ in GLOBAL_DIR.rglob('*') if _.is_file())}")
    print(f"\n  Old folders (brand/, products/, audience/, platforms/, policies/)")
    print(f"  are still intact — delete manually after verifying.\n")


if __name__ == "__main__":
    migrate()
