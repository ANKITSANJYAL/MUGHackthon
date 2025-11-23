"""
URL Encode MongoDB Password Helper

Use this to encode your MongoDB password if it contains special characters.
"""

from urllib.parse import quote_plus

print("=" * 70)
print("  MongoDB Password URL Encoder")
print("=" * 70)

# Get password from user
password = input("\nEnter your MongoDB password: ")

# Encode it
encoded_password = quote_plus(password)

print(f"\n✅ Original password: {password}")
print(f"✅ URL-encoded password: {encoded_password}")

print("\n" + "=" * 70)
print("Copy the ENCODED password and paste it in your .env file!")
print("=" * 70)

# Show example
print("\nExample:")
print("If your password is: mypass@1234")
print("Use in .env file: mypass%401234")
print("\nYour connection string should look like:")
print(f"mongodb+srv://username:{encoded_password}@cluster0.xxxxx.mongodb.net/...")
