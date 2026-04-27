import os
import sys
import datetime
from itemadapter import ItemAdapter

# Dynamically find the root 'Solution_Challenge' folder
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the root directory to Python's path so we can import vhash.py
sys.path.append(ROOT_DIR)
import vhash

class ScrapyLearnPipeline:
    def process_item(self, item, spider):
        if item.get('media_type') == 'video':
            spider.logger.info(f"🔍 Pipeline intercepted video: Running piracy check on {item['filename']}...")
            
            abs_file_path = os.path.abspath(item['file_path'])
            db_path = os.path.join(ROOT_DIR, "asset_registry.json")
            
            # Call your main verification engine
            match_record = vhash.check_against_registry(abs_file_path, db_path=db_path)
            
            if match_record:
                spider.logger.warning(f"🚨 PIRACY DETECTED in {item['filename']}!")
                item['is_pirated'] = True
                
                # --- NEW: Update Spider Stats ---
                if hasattr(spider, 'pirated_count'):
                    spider.pirated_count += 1
                    spider.pirated_files.append(item['filename'])
                
                # --- NEW: Write to a dedicated report file ---
                report_path = os.path.join(ROOT_DIR, "piracy_report.txt")
                with open(report_path, "a", encoding="utf-8") as f:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] 🚨 PIRATED VIDEO DETECTED\n")
                    f.write(f"   Suspect File: {item['filename']}\n")
                    f.write(f"   Matched Asset: {match_record['filename']}\n")
                    f.write(f"   Local Path: {abs_file_path}\n")
                    f.write(f"   Source URL: {item.get('source_url', 'Unknown')}\n\n")
            else:
                spider.logger.info(f"✅ {item['filename']} is completely clean.")
                item['is_pirated'] = False
                
                if hasattr(spider, 'clean_count'):
                    spider.clean_count += 1

        return item