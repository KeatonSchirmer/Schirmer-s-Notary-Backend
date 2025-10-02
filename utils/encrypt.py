from cryptography.fernet import Fernet
import os
import base64

class EncryptionManager:
    def __init__(self):
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            print(f"Generated new encryption key: {key.decode()}")
            print("Store this key securely in your environment variables!")
        else:
            key = key.encode()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data):
        """Encrypt sensitive data"""
        if not data:
            return None
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data):
        """Decrypt sensitive data"""
        if not encrypted_data:
            return None
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Global instance
encryption_manager = EncryptionManager()