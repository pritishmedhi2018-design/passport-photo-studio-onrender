import io
import pandas as pd
from PIL import Image, ImageOps, ImageEnhance
from modules.bg_removal import remove_background
from modules.layout_generator import (
    generate_layout,
    create_preview
)
from modules.pricing import calculate_total
from modules.database import (
    create_database,
    save_order,
    get_total_orders,
    get_total_revenue,
    get_today_orders,
    get_today_revenue
)

# -----------------------------------
# DATABASE INIT
# -----------------------------------
create_database()

# -----------------------------------
# CACHE BG REMOVAL (Simple function)
# -----------------------------------
def cached_bg_remove(file_bytes):
    file_obj = io.BytesIO(file_bytes)
    return remove_background(file_obj)
    print("=" * 50)
print("📸 Smart Passport Photo Studio")
print("AI Background Removal • Crop • Zoom • Rotate")
print("=" * 50)

# ===================================
# SETTINGS
# ===================================
print("\n⚙️ Photo Settings")

photo_type = input("Photo Type (Passport / ID Card): ").strip() or "Passport"

remove_bg_input = input("Remove Background? (Yes/No): ").strip().capitalize()
remove_bg = "Yes" if remove_bg_input == "Yes" else "No"

crop_option = input("Crop Option (No Crop / Manual Crop / Passport Crop): ").strip() or "No Crop"

bg_option = input("Background Color (Original/White/Blue/Red/Light Grey/Green): ").strip() or "Original"

photos_per_row_input = input("Photos Per Row (6/7): ").strip()
photos_per_row = int(photos_per_row_input) if photos_per_row_input in ["6", "7"] else 6

print("\n📊 Statistics")
print(f"Total Orders     : {get_total_orders()}")
print(f"Today's Orders   : {get_today_orders()}")
print(f"Total Revenue    : ₹{get_total_revenue()}")
print(f"Today's Revenue  : ₹{get_today_revenue()}")

# -----------------------------------
# FILE INPUT
# -----------------------------------
file_paths = []
print("\nEnter full paths of image files (one per line). Type 'done' when finished:")
while True:
    path = input("> ").strip()
    if path.lower() == "done":
        break
    if path:
        file_paths.append(path)

if not file_paths:
    print("No files provided. Exiting.")
    exit()

# -----------------------------------
# PROCESS STORAGE
# -----------------------------------
processed_photos = []
copies = []

# -----------------------------------
# PHOTO PROCESSING
# -----------------------------------
for idx, file_path in enumerate(file_paths):
    print(f"\n--- Processing Photo {idx + 1} ---")
    
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        continue

    # Background Removal
    try:
        if remove_bg == "Yes":
            print("Removing background...")
            image = cached_bg_remove(file_bytes)
        else:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    except Exception:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")

    # Background Color Change
    if bg_option != "Original":
        colors = {
            "White": (255, 255, 255),
            "Blue": (135, 206, 235),
            "Red": (255, 0, 0),
            "Light Grey": (220, 220, 220),
            "Green": (0, 150, 0)
        }
        bg = Image.new("RGBA", image.size, colors[bg_option])
        bg.paste(image, (0, 0), image)
        image = bg

    # Convert to RGB
    if image.mode == "RGBA":
        image = image.convert("RGB")

    # Manual Crop - Skipped (Hard to do in console). Using original for now.
    cropped_img = image

    # Get adjustments from user
    try:
        zoom = int(input("Zoom % (50-200, default 100): ") or 100)
        rotation = int(input("Rotate (-180 to 180, default 0): ") or 0)
        brightness = int(input("Brightness (50-200, default 100): ") or 100)
    except:
        zoom, rotation, brightness = 100, 0, 100

    # Zoom
    scale = zoom / 100
    w, h = cropped_img.size
    cropped_img = cropped_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    cropped_img = ImageOps.fit(cropped_img, (w, h), Image.LANCZOS)

    # Rotate
    cropped_img = cropped_img.rotate(rotation, expand=True, fillcolor="white")

    # Brightness
    enhancer = ImageEnhance.Brightness(cropped_img)
    cropped_img = enhancer.enhance(brightness / 100)

    # Save processed image
    processed_photos.append(cropped_img.convert("RGB"))

    # Copies
    try:
        qty = int(input(f"Copies for Photo {idx+1} (min 3): ") or 3)
        qty = max(3, qty)
    except:
        qty = 3
    copies.append(qty)

print("\nAll photos processed successfully!")

# --------------------------------
# BILLING
# --------------------------------
total_photos = sum(copies)
total_amount = calculate_total(total_photos)

print("\n" + "="*40)
print("BILLING")
print("="*40)
print(f"Total Photos : {total_photos}")
print(f"Rate         : ₹5 per photo")
print(f"Total Amount : ₹{total_amount}")
print("="*40)

proceed = input("\nGenerate A4 Sheet? (yes/no): ").strip().lower()
if proceed != "yes":
    print("Process cancelled.")
    exit()

# --------------------------------
# GENERATE SHEET
# --------------------------------
print("\nGenerating print sheet...")
sheet = generate_layout(
    photos=processed_photos,
    copies=copies,
    photos_per_row=photos_per_row,
    photo_type=photo_type
)

preview = create_preview(sheet)

# --------------------------------
# SAVE & DOWNLOAD (Save files locally)
# --------------------------------
png_buffer = io.BytesIO()
sheet.save(png_buffer, format="PNG", dpi=(300, 300))
png_buffer.seek(0)

pdf_buffer = io.BytesIO()
sheet.convert("RGB").save(pdf_buffer, format="PDF", resolution=300.0)
pdf_buffer.seek(0)

with open("passport_sheet.png", "wb") as f:
    f.write(png_buffer.getvalue())

with open("passport_sheet.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

print("\n✅ Sheet generated successfully!")
print("📁 Files saved as:")
print("   - passport_sheet.png")
print("   - passport_sheet.pdf")

# --------------------------------
# ORDER SUMMARY
# --------------------------------
print("\nOrder Summary:")
summary = {
    "Photo Type": photo_type,
    "Layout": f"{photos_per_row} per row",
    "Total Photos": total_photos,
    "Rate": "₹5",
    "Amount": f"₹{total_amount}"
}

for key, value in summary.items():
    print(f"  {key:15}: {value}")

# Save to Database
try:
    save_order(photo_type, photos_per_row, total_photos, total_amount)
    print("✅ Order saved to database.")
except Exception as e:
    print(f"⚠️ Database Error: {e}")

print("\nThank you for using Smart Passport Photo Studio!")
