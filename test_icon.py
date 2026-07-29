from PIL import Image
import cairosvg

cairosvg.svg2png(url="assets/aircraft.svg", write_to="assets/aircraft.png")

img = Image.open("assets/aircraft.png")
img.show()
