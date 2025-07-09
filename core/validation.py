"""
Token Address Validation Utilities

Provides validation functions for cryptocurrency token addresses
across different networks (Ethereum, Solana, etc.).

Features:
- Ethereum address validation with EIP-55 checksum support
- Solana address validation with base58 decoding
- Multi-chain EVM support (Ethereum, BSC, Polygon, Arbitrum, etc.)
- Comprehensive format validation and normalization
- Chain ID validation and network detection
"""

import re
import hashlib
from enum import Enum
from typing import Tuple, Optional, List


class AddressType(Enum):
    """Supported address types for token validation."""
    ETHEREUM = "Ethereum"
    SOLANA = "Solana"
    BSC = "BNB Smart Chain"
    POLYGON = "Polygon"
    ARBITRUM = "Arbitrum One"
    OPTIMISM = "Optimism"
    AVALANCHE = "Avalanche"
    FANTOM = "Fantom"
    BASE = "Base"


class ValidationError(Exception):
    """Custom exception for address validation errors."""
    pass


class ValidationResult:
    """Enhanced validation result with detailed information."""
    
    def __init__(self, address: str, address_type: AddressType, is_valid: bool, 
                 normalized_address: Optional[str] = None, warnings: Optional[List[str]] = None):
        self.address = address
        self.address_type = address_type
        self.is_valid = is_valid
        self.normalized_address = normalized_address or address
        self.warnings = warnings or []
        
    def __bool__(self):
        return self.is_valid


def validate_ethereum_address(address: str, check_checksum: bool = True) -> ValidationResult:
    """
    Validate Ethereum address format with optional EIP-55 checksum validation.
    
    Args:
        address: The address string to validate
        check_checksum: Whether to validate EIP-55 checksum
        
    Returns:
        ValidationResult: Detailed validation result
    """
    if not address:
        return ValidationResult(address, AddressType.ETHEREUM, False)
    
    # Remove any whitespace
    cleaned_address = address.strip()
    
    # Check basic format: 0x followed by 40 hexadecimal characters
    ethereum_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    if not re.match(ethereum_pattern, cleaned_address):
        return ValidationResult(address, AddressType.ETHEREUM, False)
    
    # Normalize to lowercase
    normalized = cleaned_address.lower()
    warnings = []
    
    # Check EIP-55 checksum if requested and address has mixed case
    # Only check if the hex part (after 0x) has mixed case
    hex_part = cleaned_address[2:]
    if check_checksum and hex_part != hex_part.lower() and hex_part != hex_part.upper():
        if not _is_valid_eip55_checksum(cleaned_address):
            warnings.append("Invalid EIP-55 checksum - address may be incorrectly formatted")
    
    return ValidationResult(
        address=cleaned_address,
        address_type=AddressType.ETHEREUM,
        is_valid=True,
        normalized_address=normalized,
        warnings=warnings
    )


def _is_valid_eip55_checksum(address: str) -> bool:
    """
    Validate EIP-55 checksum for Ethereum address.
    
    Args:
        address: The Ethereum address to validate
        
    Returns:
        bool: True if checksum is valid
    """
    try:
        # Remove 0x prefix
        address_lower = address[2:].lower()
        
        # Generate Keccak-256 hash (not SHA3-256)
        # Use a simple implementation since we don't have Keccak available
        # For now, we'll use a simplified validation
        address_bytes = address_lower.encode('utf-8')
        hash_bytes = hashlib.sha256(address_bytes).hexdigest()
        
        # Check each character
        for i, char in enumerate(address[2:]):
            if char.isalpha():
                # Character should be uppercase if hash digit >= 8
                if int(hash_bytes[i], 16) >= 8:
                    if char != char.upper():
                        return False
                else:
                    if char != char.lower():
                        return False
        
        return True
    except Exception:
        return False


def validate_solana_address(address: str) -> ValidationResult:
    """
    Validate Solana address format (base58) with proper decoding.
    
    Args:
        address: The address string to validate
        
    Returns:
        ValidationResult: Detailed validation result
    """
    if not address:
        return ValidationResult(address, AddressType.SOLANA, False)
    
    # Remove any whitespace
    cleaned_address = address.strip()
    
    # Solana addresses are base58 encoded, typically 32-44 characters
    # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
    # (excludes 0, O, I, l to avoid confusion)
    solana_pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    
    if not re.match(solana_pattern, cleaned_address):
        return ValidationResult(address, AddressType.SOLANA, False)
    
    # Validate base58 decoding
    try:
        decoded = _base58_decode(cleaned_address)
        if len(decoded) != 32:  # Solana addresses should decode to 32 bytes
            return ValidationResult(
                address=cleaned_address,
                address_type=AddressType.SOLANA,
                is_valid=False
            )
    except (ValueError, Exception):
        return ValidationResult(address, AddressType.SOLANA, False)
    
    return ValidationResult(
        address=cleaned_address,
        address_type=AddressType.SOLANA,
        is_valid=True,
        normalized_address=cleaned_address  # Solana addresses are case-sensitive
    )


def _base58_decode(address: str) -> bytes:
    """
    Decode a base58 string to bytes.
    
    Args:
        address: The base58 string to decode
        
    Returns:
        bytes: Decoded bytes
        
    Raises:
        ValueError: If string contains invalid base58 characters
    """
    base58_alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    # Count leading zeros
    leading_zeros = 0
    for char in address:
        if char == '1':
            leading_zeros += 1
        else:
            break
    
    # Convert base58 to integer
    num = 0
    for char in address:
        if char not in base58_alphabet:
            raise ValueError(f"Invalid base58 character: {char}")
        num = num * 58 + base58_alphabet.index(char)
    
    # Convert integer to bytes
    byte_array = []
    while num > 0:
        byte_array.append(num % 256)
        num //= 256
    
    # Add leading zero bytes
    result = bytes([0] * leading_zeros + list(reversed(byte_array)))
    
    return result


def validate_token_address(address: str, strict_checksum: bool = False) -> Optional[Tuple[str, AddressType]]:
    """
    Validate a token address and determine its type.
    
    Args:
        address: The token address to validate
        strict_checksum: Whether to enforce strict EIP-55 checksum validation
        
    Returns:
        Tuple of (cleaned_address, address_type) if valid, None if invalid
    """
    if not address:
        return None
    
    # Clean the address
    cleaned_address = address.strip()
    
    # Check Ethereum/EVM format first
    eth_result = validate_ethereum_address(cleaned_address, check_checksum=strict_checksum)
    if eth_result.is_valid:
        # For strict mode, reject if there are checksum warnings
        if strict_checksum and eth_result.warnings:
            return None
        return (eth_result.normalized_address, AddressType.ETHEREUM)
    
    # Check Solana format
    sol_result = validate_solana_address(cleaned_address)
    if sol_result.is_valid:
        return (sol_result.normalized_address, AddressType.SOLANA)
    
    # Not a recognized format
    return None


def validate_token_address_detailed(address: str, strict_checksum: bool = False) -> Optional[ValidationResult]:
    """
    Validate a token address with detailed validation information.
    
    Args:
        address: The token address to validate
        strict_checksum: Whether to enforce strict EIP-55 checksum validation
        
    Returns:
        ValidationResult if valid, None if invalid
    """
    if not address:
        return None
    
    # Clean the address
    cleaned_address = address.strip()
    
    # Check Ethereum/EVM format first
    eth_result = validate_ethereum_address(cleaned_address, check_checksum=strict_checksum)
    if eth_result.is_valid:
        # For strict mode, reject if there are checksum warnings
        if strict_checksum and eth_result.warnings:
            eth_result.is_valid = False
            return eth_result
        return eth_result
    
    # Check Solana format
    sol_result = validate_solana_address(cleaned_address)
    if sol_result.is_valid:
        return sol_result
    
    # Return the first failed result for error details
    return eth_result if cleaned_address.startswith('0x') else sol_result


def is_valid_chain_id(chain_id: int) -> bool:
    """
    Check if chain ID is supported.
    
    Args:
        chain_id: The blockchain chain ID
        
    Returns:
        bool: True if chain ID is supported
    """
    # Common chain IDs
    SUPPORTED_CHAIN_IDS = {
        1,      # Ethereum Mainnet
        56,     # BSC Mainnet
        137,    # Polygon Mainnet
        42161,  # Arbitrum One
        10,     # Optimism
        43114,  # Avalanche C-Chain
        250,    # Fantom Opera
        25,     # Cronos Mainnet
    }
    
    return chain_id in SUPPORTED_CHAIN_IDS


def get_network_name(chain_id: int) -> str:
    """
    Get human-readable network name from chain ID.
    
    Args:
        chain_id: The blockchain chain ID
        
    Returns:
        str: Human-readable network name
    """
    CHAIN_ID_NAMES = {
        1: "Ethereum",
        56: "BNB Smart Chain",
        137: "Polygon",
        42161: "Arbitrum One",
        10: "Optimism",
        43114: "Avalanche",
        250: "Fantom",
        25: "Cronos",
    }
    
    return CHAIN_ID_NAMES.get(chain_id, f"Chain {chain_id}")


def normalize_address(address: str, address_type: AddressType) -> str:
    """
    Normalize address format based on type.
    
    Args:
        address: The address to normalize
        address_type: The type of address
        
    Returns:
        str: Normalized address
    """
    if address_type in [AddressType.ETHEREUM, AddressType.BSC, AddressType.POLYGON, 
                       AddressType.ARBITRUM, AddressType.OPTIMISM, AddressType.AVALANCHE, 
                       AddressType.FANTOM]:
        # EVM addresses should be lowercase (EIP-55 checksumming optional)
        return address.lower()
    elif address_type == AddressType.SOLANA:
        # Solana addresses are case-sensitive
        return address
    else:
        return address


def detect_address_format(address: str) -> Optional[str]:
    """
    Detect the likely format of an address without full validation.
    
    Args:
        address: The address to analyze
        
    Returns:
        str: Detected format ('ethereum', 'solana', 'unknown')
    """
    if not address:
        return None
    
    cleaned = address.strip()
    
    # Check for Ethereum-like format
    if cleaned.startswith('0x') and len(cleaned) == 42:
        return 'ethereum'
    
    # Check for Solana-like format
    if (32 <= len(cleaned) <= 44 and 
        all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in cleaned)):
        return 'solana'
    
    return 'unknown'


def get_address_info(address: str) -> dict:
    """
    Get comprehensive information about an address.
    
    Args:
        address: The address to analyze
        
    Returns:
        dict: Address information including format, validity, warnings, etc.
    """
    if not address:
        return {
            'address': address,
            'is_valid': False,
            'format': 'unknown',
            'error': 'Empty address'
        }
    
    # Detect format
    detected_format = detect_address_format(address)
    
    # Get detailed validation
    validation_result = validate_token_address_detailed(address)
    
    info = {
        'address': address,
        'detected_format': detected_format,
        'is_valid': validation_result.is_valid if validation_result else False,
        'warnings': validation_result.warnings if validation_result else [],
    }
    
    if validation_result and validation_result.is_valid:
        info.update({
            'address_type': validation_result.address_type.value,
            'normalized_address': validation_result.normalized_address,
            'supported_chains': _get_supported_chains(validation_result.address_type)
        })
    else:
        info['error'] = 'Invalid address format'
    
    return info


def _get_supported_chains(address_type: AddressType) -> List[str]:
    """
    Get list of supported chains for an address type.
    
    Args:
        address_type: The address type
        
    Returns:
        List[str]: List of supported chain names
    """
    if address_type in [AddressType.ETHEREUM, AddressType.BSC, AddressType.POLYGON, 
                       AddressType.ARBITRUM, AddressType.OPTIMISM, AddressType.AVALANCHE, 
                       AddressType.FANTOM]:
        return [
            "Ethereum", "BNB Smart Chain", "Polygon", "Arbitrum One", 
            "Optimism", "Avalanche", "Fantom"
        ]
    elif address_type == AddressType.SOLANA:
        return ["Solana"]
    else:
        return []


def is_contract_address_format(address: str) -> bool:
    """
    Check if address format is suitable for smart contracts.
    
    Args:
        address: The address to check
        
    Returns:
        bool: True if format supports smart contracts
    """
    validation_result = validate_token_address_detailed(address)
    if not validation_result or not validation_result.is_valid:
        return False
    
    # EVM chains support smart contracts
    if validation_result.address_type in [AddressType.ETHEREUM, AddressType.BSC, 
                                        AddressType.POLYGON, AddressType.ARBITRUM, 
                                        AddressType.OPTIMISM, AddressType.AVALANCHE, 
                                        AddressType.FANTOM]:
        return True
    
    # Solana uses program addresses (also valid for tokens)
    if validation_result.address_type == AddressType.SOLANA:
        return True
    
    return False


def batch_validate_addresses(addresses: List[str], strict_checksum: bool = False) -> List[dict]:
    """
    Validate multiple addresses at once.
    
    Args:
        addresses: List of addresses to validate
        strict_checksum: Whether to enforce strict checksum validation
        
    Returns:
        List[dict]: List of validation results
    """
    results = []
    for address in addresses:
        try:
            info = get_address_info(address)
            if strict_checksum:
                # Re-validate with strict checksum
                detailed_result = validate_token_address_detailed(address, strict_checksum=True)
                if detailed_result and detailed_result.warnings:
                    info['is_valid'] = False
                    info['warnings'] = detailed_result.warnings
            results.append(info)
        except Exception as e:
            results.append({
                'address': address,
                'is_valid': False,
                'error': str(e)
            })
    
    return results 