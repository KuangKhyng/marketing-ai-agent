from PIL import Image
import sys

def remove_background(image_path, output_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()

        newData = []
        # Find the background color from top-left pixel
        bg_color = datas[0]
        
        # We also specifically target near-white 
        for item in datas:
            # If the pixel is very close to white or the bg_color, make it transparent
            is_bg = (abs(item[0] - bg_color[0]) < 20 and \
                     abs(item[1] - bg_color[1]) < 20 and \
                     abs(item[2] - bg_color[2]) < 20)
            
            is_white = item[0] > 240 and item[1] > 240 and item[2] > 240
            
            if is_bg or is_white:
                # Calculate alpha based on how close it is to white for anti-aliasing edges
                # Pure white becomes 0 alpha, darker becomes more opaque. Simple linear interpolation.
                avg_color = (item[0] + item[1] + item[2]) / 3
                if avg_color > 240:
                    alpha = int((255 - avg_color) * 17) # 240 -> ~255, 255 -> 0
                    newData.append((item[0], item[1], item[2], max(0, min(255, alpha))))
                else:
                    newData.append(item)
            else:
                newData.append(item)

        img.putdata(newData)
        
        # Resize it down so it's clean and small for a favicon
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        img.save(output_path, "PNG")
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

input_img = r"C:\Users\qhung\.gemini\antigravity\brain\06e43a6d-9049-4930-a08a-6ada90d1c667\super_cute_cat_1776533671265.png"
output_img = r"d:\ai-agent-mkt\web\public\favicon.png"
remove_background(input_img, output_img)
