import qrcode
from io import BytesIO

def generate_upi_qr(upi_id, amount):
    data = f"upi://pay?pa={upi_id}&am={amount}&cu=INR"
    img = qrcode.make(data)
    bio = BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio
