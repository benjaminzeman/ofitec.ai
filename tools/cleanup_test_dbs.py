#!/usr/bin/env python3
"""
Database cleanup script for OFITEC.AI project.
Removes old test databases and maintains project cleanliness.
"""

import time
import argparse
from pathlib import Path


def cleanup_test_databases(data_dir="data", max_age_hours=24, dry_run=False):
    """Clean up old test databases."""
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ Data directory '{data_dir}' does not exist")
        return 0
    
    current_time = time.time()
    cutoff_time = current_time - (max_age_hours * 3600)
    
    cleaned_count = 0
    total_size = 0
    
    # Patterns for test databases
    patterns = ["test_*.db", "tmp_*.db"]
    
    print(f"🔍 Scanning for test databases older than {max_age_hours} hours...")
    
    for pattern in patterns:
        for db_file in data_path.glob(pattern):
            try:
                file_stat = db_file.stat()
                file_age_hours = (current_time - file_stat.st_mtime) / 3600
                
                if file_stat.st_mtime < cutoff_time:
                    file_size = file_stat.st_size
                    total_size += file_size
                    
                    if dry_run:
                        print(f"[DRY RUN] Would remove: {db_file.name} ({file_size:,} bytes, {file_age_hours:.1f}h old)")
                    else:
                        db_file.unlink()
                        print(f"✅ Removed: {db_file.name} ({file_size:,} bytes, {file_age_hours:.1f}h old)")
                    
                    cleaned_count += 1
                    
            except OSError as e:
                print(f"⚠️  Error processing {db_file.name}: {e}")
    
    if cleaned_count > 0:
        size_mb = total_size / (1024 * 1024)
        action = "Would free" if dry_run else "Freed"
        print(f"🧹 {action} {size_mb:.2f} MB by cleaning {cleaned_count} test databases")
    else:
        print("✨ No old test databases found to clean")
    
    return cleaned_count


def show_database_stats(data_dir="data"):
    """Show current database statistics."""
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ Data directory '{data_dir}' does not exist")
        return
    
    print("\n📊 DATABASE STATISTICS:")
    print("=" * 50)
    
    # Count by type
    stats = {}
    total_size = 0
    
    for db_file in data_path.glob("*.db"):
        file_size = db_file.stat().st_size
        total_size += file_size
        
        if db_file.name.startswith("test_"):
            db_type = "test_" + db_file.name.split("_")[1]
        elif db_file.name.startswith("tmp_"):
            db_type = "temporary"
        else:
            db_type = "production"
        
        if db_type not in stats:
            stats[db_type] = {"count": 0, "size": 0}
        
        stats[db_type]["count"] += 1
        stats[db_type]["size"] += file_size
    
    # Display stats
    for db_type, data in sorted(stats.items()):
        size_mb = data["size"] / (1024 * 1024)
        print(f"{db_type:20}: {data['count']:4d} files ({size_mb:8.2f} MB)")
    
    print("-" * 50)
    total_mb = total_size / (1024 * 1024)
    print(f"{'TOTAL':20}: {sum(s['count'] for s in stats.values()):4d} files ({total_mb:8.2f} MB)")
    
    # Show recent production databases
    print("\n📁 PRODUCTION DATABASES:")
    prod_dbs = [f for f in data_path.glob("*.db") 
                if not f.name.startswith(("test_", "tmp_"))]
    
    for db in sorted(prod_dbs, key=lambda x: x.stat().st_mtime, reverse=True):
        size_mb = db.stat().st_size / (1024 * 1024)
        mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(db.stat().st_mtime))
        print(f"  {db.name:20} - {size_mb:6.2f} MB - {mod_time}")


def main():
    parser = argparse.ArgumentParser(description="Clean up test databases")
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    parser.add_argument("--max-age", type=int, default=24, help="Max age in hours")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--force", action="store_true", help="Clean all test databases regardless of age")
    
    args = parser.parse_args()
    
    # Show stats if requested
    if args.stats:
        show_database_stats(args.data_dir)
    
    # Perform cleanup
    max_age = 0 if args.force else args.max_age
    cleaned = cleanup_test_databases(args.data_dir, max_age, args.dry_run)
    
    # Show final stats if any cleaning was done
    if cleaned > 0 and not args.dry_run:
        print()
        show_database_stats(args.data_dir)


if __name__ == "__main__":
    main()