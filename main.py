import os
import sys
import time
import requests
import json
import re
from fpdf import FPDF

# Constants
SCRYFALL_API_URL = "https://api.scryfall.com/cards/named"
SCRYFALL_SYMBOLOGY_URL = "https://api.scryfall.com/symbology"
CACHE_FILE = "card_cache.json"
SYMBOLS_CACHE_FILE = "symbols_cache.json"
SYMBOLS_DIR = "cache/symbols"
CARD_WIDTH_MM = 62
CARD_HEIGHT_MM = 87
MARGIN_MM = 10
SPACING_MM = 2
CARDS_PER_ROW = 3
CARDS_PER_COL = 3
FONT_SIZE_TITLE = 10
FONT_SIZE_ITEM = 8
LINE_HEIGHT = 4
SYMBOL_SIZE = 3 # mm

def ensure_dirs():
    if not os.path.exists(SYMBOLS_DIR):
        os.makedirs(SYMBOLS_DIR)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def get_symbology_map():
    """
    Returns a dict mapping symbol text (e.g., '{R}') to its SVG URI.
    """
    cache = load_json(SYMBOLS_CACHE_FILE)
    if cache:
        return cache

    print("Fetching symbology from Scryfall...")
    try:
        response = requests.get(SCRYFALL_SYMBOLOGY_URL)
        if response.status_code == 200:
            data = response.json()
            mapping = {item["symbol"]: item["svg_uri"] for item in data["data"]}
            save_json(SYMBOLS_CACHE_FILE, mapping)
            return mapping
    except Exception as e:
        print(f"Error fetching symbology: {e}")
    
    return {}

def get_symbol_image_path(symbol, uri):
    """
    Downloads the symbol SVG if not present. Returns path to local file.
    """
    safe_name = symbol.replace("{", "").replace("}", "").replace("/", "")
    filename = os.path.join(SYMBOLS_DIR, f"{safe_name}.svg")
    
    if os.path.exists(filename):
        return filename
        
    print(f"Downloading symbol {symbol}...")
    try:
        response = requests.get(uri)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Error downloading symbol {symbol}: {e}")
    
    return None

def get_card_data(card_name, cache):
    """
    Fetches the card mana cost and type from Scryfall or loads it from cache.
    Returns a dict with 'name', 'mana_cost', and 'type_line'.
    """
    key = card_name.lower().strip()
    if key in cache:
        # Backward compatibility for cache without type_line
        if 'type_line' not in cache[key]:
             pass # Force re-fetch
        else:
            return cache[key]

    print(f"Fetching data for {card_name}...")
    try:
        time.sleep(0.1) 
        response = requests.get(SCRYFALL_API_URL, params={"exact": card_name})
        
        if response.status_code == 404:
            response = requests.get(SCRYFALL_API_URL, params={"fuzzy": card_name})
        
        if response.status_code != 200:
            # Check for Basic Land variants (e.g., "Plains Appa")
            basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"]
            for land in basic_lands:
                if card_name.startswith(land):
                    print(f"Assuming '{card_name}' is a variant of {land}")
                    return {"name": card_name, "mana_cost": "", "type_line": f"Basic Land — {land}"}

            print(f"Error: Could not find card '{card_name}'")
            return {"name": card_name, "mana_cost": "???", "type_line": "Unknown"}

        data = response.json()
        
        mana_cost = ""
        type_line = ""
        
        if "mana_cost" in data:
            mana_cost = data["mana_cost"]
        elif "card_faces" in data and "mana_cost" in data["card_faces"][0]:
            mana_cost = data["card_faces"][0]["mana_cost"]
            
        if "type_line" in data:
            type_line = data["type_line"]
        elif "card_faces" in data and "type_line" in data["card_faces"][0]:
            type_line = data["card_faces"][0]["type_line"]
            
        result = {"name": data.get("name", card_name), "mana_cost": mana_cost, "type_line": type_line}
        cache[key] = result
        return result

    except Exception as e:
        print(f"Exception fetching '{card_name}': {e}")
        return {"name": card_name, "mana_cost": "Error", "type_line": "Error"}

def get_card_group(type_line):
    type_line = type_line.lower()
    if "creature" in type_line: return "Creatures", 1
    if "planeswalker" in type_line: return "Planeswalkers", 2
    if "instant" in type_line: return "Instants", 3
    if "sorcery" in type_line: return "Sorceries", 4
    if "artifact" in type_line: return "Artifacts", 5
    if "enchantment" in type_line: return "Enchantments", 6
    if "land" in type_line: return "Lands", 7
    return "Others", 8

class ProxyPDF(FPDF):
    def header(self):
        pass
    def footer(self):
        pass

def create_pdf(card_lists, list_names, output_filename="checklist_cards.pdf"):
    ensure_dirs()
    symbology = get_symbology_map()
    
    pdf = ProxyPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(False)
    pdf.add_page()
    
    cache = load_json(CACHE_FILE)
    
    col = 0
    row = 0
    
    x_start_base = MARGIN_MM
    y_start_base = MARGIN_MM
    
    for list_idx, card_list in enumerate(card_lists):
        list_name = list_names[list_idx]
        
        # 1. Fetch Data
        fetched_items = []
        for entry in card_list:
            quantity, card_name = entry
            if not card_name.strip(): continue
            data = get_card_data(card_name, cache)
            data_with_qty = data.copy()
            data_with_qty['quantity'] = quantity
            fetched_items.append(data_with_qty)
            
        # 2. Group Items
        grouped_items = {}
        for item in fetched_items:
            group_name, order = get_card_group(item.get('type_line', ''))
            if group_name not in grouped_items:
                grouped_items[group_name] = {'order': order, 'items': []}
            grouped_items[group_name]['items'].append(item)
            
        # 3. Flatten with Headers
        display_items = []
        sorted_groups = sorted(grouped_items.items(), key=lambda x: x[1]['order'])
        
        for group_name, group_data in sorted_groups:
            display_items.append({'type': 'header', 'name': group_name})
            # Sort items within group by name
            sorted_cards = sorted(group_data['items'], key=lambda x: x['name'])
            for card in sorted_cards:
                card['type'] = 'card'
                display_items.append(card)
        
        # 4. Calculate Layout & Scaling
        # Available height for items = Card Height - Title Height - Padding
        # Title takes ~6mm + 2mm padding = 8mm. Let's say 10mm to be safe.
        available_height = CARD_HEIGHT_MM - 12 
        total_items = len(display_items)
        
        current_line_height = LINE_HEIGHT
        current_font_size = FONT_SIZE_ITEM
        current_symbol_size = SYMBOL_SIZE
        
        required_height = total_items * LINE_HEIGHT
        
        if required_height > available_height and total_items > 0:
            scale_factor = available_height / required_height
            current_line_height = LINE_HEIGHT * scale_factor
            current_font_size = FONT_SIZE_ITEM * scale_factor
            current_symbol_size = SYMBOL_SIZE * scale_factor
            # Optional: Set a minimum font size limit if needed, but user asked to fit it.
        
        # 5. Draw Card
        x = x_start_base + (col * (CARD_WIDTH_MM + SPACING_MM))
        y = y_start_base + (row * (CARD_HEIGHT_MM + SPACING_MM))
        
        # Draw Card Border
        pdf.rect(x, y, CARD_WIDTH_MM, CARD_HEIGHT_MM)
        
        # Draw Title
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("Arial", 'B', FONT_SIZE_TITLE)
        pdf.cell(CARD_WIDTH_MM - 4, 6, list_name, align='C', ln=1)
        
        # Draw Items
        current_y = y + 10 # Start below title
        
        for item in display_items:
            pdf.set_xy(x + 2, current_y)
            
            if item.get('type') == 'header':
                pdf.set_font("Arial", 'B', current_font_size)
                pdf.cell(CARD_WIDTH_MM - 4, current_line_height, f"{item['name']}:", ln=1)
                current_y += current_line_height
                continue
            
            # It's a card
            pdf.set_font("Arial", '', current_font_size)
            
            # Prepare Mana Symbols
            mana_cost = item['mana_cost']
            symbols = []
            if mana_cost:
                symbols = re.findall(r'\{.*?\}', mana_cost)
            
            # Calculate width needed for symbols
            symbol_padding = 0.5 * (current_symbol_size / SYMBOL_SIZE) # Scale padding too
            total_symbol_width = 0
            valid_symbols = []
            
            for sym in symbols:
                if sym in symbology:
                        total_symbol_width += current_symbol_size + symbol_padding
                        valid_symbols.append({'type': 'img', 'val': sym})
                else:
                        w = pdf.get_string_width(sym)
                        total_symbol_width += w + symbol_padding
                        valid_symbols.append({'type': 'text', 'val': sym})

            # Draw Symbols Right-Aligned
            draw_x = x + CARD_WIDTH_MM - 2 - total_symbol_width
            
            for sym_data in valid_symbols:
                if sym_data['type'] == 'img':
                    img_path = get_symbol_image_path(sym_data['val'], symbology[sym_data['val']])
                    if img_path:
                        img_y = current_y + (current_line_height - current_symbol_size) / 2
                        pdf.image(img_path, x=draw_x, y=img_y, w=current_symbol_size, h=current_symbol_size)
                    draw_x += current_symbol_size + symbol_padding
                else:
                    pdf.set_xy(draw_x, current_y)
                    pdf.cell(pdf.get_string_width(sym_data['val']), current_line_height, sym_data['val'])
                    draw_x += pdf.get_string_width(sym_data['val']) + symbol_padding

            # Draw Quantity and Name (Left Aligned)
            qty = item['quantity']
            name = item['name']
            text_str = f"{qty}x {name}"
            
            max_text_width = CARD_WIDTH_MM - 4 - total_symbol_width - 1
            
            if pdf.get_string_width(text_str) > max_text_width:
                while pdf.get_string_width(text_str + "...") > max_text_width and len(text_str) > 0:
                    text_str = text_str[:-1]
                text_str += "..."
            
            pdf.set_xy(x + 2, current_y)
            pdf.cell(max_text_width, current_line_height, text_str)
                        
            current_y += current_line_height
        
        col += 1
        if col >= CARDS_PER_ROW:
            col = 0
            row += 1
            
        if row >= CARDS_PER_COL:
            pdf.add_page()
            col = 0
            row = 0
    
    save_json(CACHE_FILE, cache)
    pdf.output(output_filename)
    print(f"PDF generated: {output_filename}")

def main():
    input_dir = "files"
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"Created '{input_dir}' directory. Please put your .txt files there and run again.")
        return

    input_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".txt")]
    
    if not input_files:
        print(f"No .txt files found in '{input_dir}' directory.")
        return

    all_lists = []
    list_names = []
    
    print(f"Found {len(input_files)} files in '{input_dir}':")
    for file_path in input_files:
        print(f" - {os.path.basename(file_path)}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            parsed_list = []
            for line in f:
                line = line.strip()
                if not line: continue
                
                # Remove bracketed content like [12345]
                line = re.sub(r'\[.*?\]', '', line).strip()
                
                # Parse quantity: "3x Mountain" or "7 Island" or "Mountain"
                match = re.match(r'^(\d+)(?:x)?\s+(.*)$', line)
                if match:
                    qty = int(match.group(1))
                    name = match.group(2).strip()
                else:
                    qty = 1
                    name = line
                
                parsed_list.append((qty, name))
            
            all_lists.append(parsed_list)
            list_names.append(os.path.basename(file_path).replace(".txt", ""))

    if all_lists:
        create_pdf(all_lists, list_names)
    else:
        print("No valid lists found.")

if __name__ == "__main__":
    main()
