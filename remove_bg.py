from PIL import Image
import sys

def remove_background(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()

        # Giả định pixel ở góc trên cùng bên trái là màu nền
        bg_color = datas[0]
        
        newData = []
        tolerance = 25 # Độ sai lệch cho phép
        
        for item in datas:
            # Nếu màu pixel gần giống màu nền, thay bằng trong suốt
            if abs(item[0] - bg_color[0]) < tolerance and \
               abs(item[1] - bg_color[1]) < tolerance and \
               abs(item[2] - bg_color[2]) < tolerance:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)

        img.putdata(newData)
        img.save(image_path, "PNG")
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

remove_background("web/public/favicon.png")
