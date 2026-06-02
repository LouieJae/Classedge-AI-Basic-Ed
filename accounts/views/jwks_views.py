from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import status

from accounts.utils.powersync_utils import generate_powersync_token

class JWKSView(APIView):
    """
    JWKS (JSON Web Key Set) endpoint for PowerSync and other JWT verification services.
    Exposes the RS256 public key in JWKS format.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Load the public key from settings
            public_key_pem = settings.RS256_PUBLIC_KEY
            
            # Parse the public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Get the public numbers from the RSA key
            public_numbers = public_key.public_numbers()
            
            # Convert to base64url format (required by JWKS spec)
            def int_to_base64url(num):
                """Convert integer to base64url encoded string"""
                # Convert to bytes
                num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
                # Base64url encode (no padding)
                return base64.urlsafe_b64encode(num_bytes).decode('utf-8').rstrip('=')
            
            # Extract modulus (n) and exponent (e)
            n = int_to_base64url(public_numbers.n)
            e = int_to_base64url(public_numbers.e)
            
            # Generate a key ID (kid) - using SHA256 hash of the modulus
            kid = hashlib.sha256(public_numbers.n.to_bytes(
                (public_numbers.n.bit_length() + 7) // 8, 
                byteorder='big'
            )).hexdigest()[:16]
            
            # Build the JWKS response
            jwks = {
                "keys": [
                    {
                        "kty": "RSA",           # Key Type
                        "use": "sig",           # Public key use (signature)
                        "alg": "RS256",         # Algorithm
                        "kid": kid,             # Key ID
                        "n": n,                 # Modulus
                        "e": e                  # Exponent
                    }
                ]
            }
            
            return Response(jwks)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate JWKS: {str(e)}"}, 
                status=500
            )


class PowerSyncTokenView(APIView):
    """
    PowerSync token generation endpoint.
    Generates a short-lived JWT token for PowerSync authentication.
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            token = generate_powersync_token(user_id=request.user.id, request=request)
            return Response({'token': token})
        except Exception as e:
            return Response(
                {'message': 'Internal server error', 'error': str(e)}, 
                status=500
            )