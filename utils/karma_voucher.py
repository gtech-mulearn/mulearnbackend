from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

image_location = './api/dashboard/karma_voucher/assets/karmacard.png'
font_location =  './api/dashboard/karma_voucher/fonts/Roboto-Light.ttf'

def generate_karma_voucher(name, hashtag, karma, muid, month):
    """
    Generate a karma voucher for the given users
    :param name:
    :param hashtag:
    :param karma:
    :param muid:
    :param month:
    :return:
    """   


    image = Image.open(image_location)
    image = image.convert('RGB')

    draw = ImageDraw.Draw(image)
    x = 135
    y = 250
    font1 = ImageFont.truetype(font_location, size=60)
    draw.text((x, y), name, fill=(255, 255, 255), font=font1)

    x1 = 135
    y1 = 450
    font2 = ImageFont.truetype(font_location, size=45)
    draw.text((x1, y1), hashtag, fill=(255, 255, 255), font=font2)

    x2 = 920
    y2 = 135
    font3 = ImageFont.truetype(font_location, size=45)
    draw.text((x2, y2), karma, fill=(255, 255, 255), font=font3)

    x3 = 135
    y3 = 135
    font3 = ImageFont.truetype(font_location, size=20)
    draw.text((x3, y3), muid, fill=(255, 255, 255), font=font3)

    x3 = 135
    y3 = 375
    font3 = ImageFont.truetype(font_location, size=30)
    draw.text((x3, y3), month, fill=(255, 255, 255), font=font3)

    image_data = BytesIO()
    image.save(image_data, format='JPEG')
    return image_data