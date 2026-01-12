
import os
import sys
from datetime import timedelta
from jose import jwt

# Add project root to sys.path
sys.path.append("/home/dustin/stock/FinanceAICrews")

# Mock the environment for security.py
os.environ["JWT_SECRET_KEY"] = "your-super-secret-key-change-in-production"

from backend.app.security import create_access_token

token = create_access_token(data={"sub": "1"})
print(token)
