import string
import base64
from uuid import uuid4


def generate_uuid() -> str:
  return uuid4().hex

def hash_string(content: str) -> str:
  # Encode the string to bytes using UTF-8, then base64 encode it
  encoded_bytes = base64.urlsafe_b64encode(content.encode('utf-8'))
  return encoded_bytes.decode('utf-8')

def dehash_string(content: str) -> str:
  # Decode the base64 string back to the original string
  decoded_bytes = base64.urlsafe_b64decode(content.encode('utf-8'))
  return decoded_bytes.decode('utf-8')


# Base62 character set (62 characters: 0-9, A-Z, a-z)
BASE62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase

def base62_encode(num):
    """Encode a number into Base62 string"""
    if num == 0:
        return BASE62_ALPHABET[0]
    base62 = []
    while num > 0:
        num, rem = divmod(num, 62)
        base62.append(BASE62_ALPHABET[rem])
    return ''.join(reversed(base62))

def base62_decode(s):
    """Decode a Base62 string into number"""
    num = 0
    for char in s:
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num

def text_to_base62(text):
    """Encode arbitrary text to Base62 string"""
    # Convert to bytes, then to integer
    byte_data = text.encode('utf-8')
    num = int.from_bytes(byte_data, byteorder='big')
    return base62_encode(num)

def base62_to_text(encoded):
    """Decode Base62 string back to text"""
    num = base62_decode(encoded)
    # Convert integer back to bytes, then decode
    # Estimate minimum number of bytes needed
    byte_length = (num.bit_length() + 7) // 8
    byte_data = num.to_bytes(byte_length, byteorder='big')
    return byte_data.decode('utf-8')

