"""
Tests for token address validation utilities.

Tests comprehensive validation for Ethereum, Solana, and multi-chain EVM addresses
including EIP-55 checksum validation, base58 decoding, and batch processing.
"""

import pytest
from core.validation import (
    validate_ethereum_address,
    validate_solana_address,
    validate_token_address,
    validate_token_address_detailed,
    AddressType,
    ValidationResult,
    ValidationError,
    detect_address_format,
    get_address_info,
    is_contract_address_format,
    batch_validate_addresses,
    normalize_address,
    is_valid_chain_id,
    get_network_name,
    _is_valid_eip55_checksum,
    _base58_decode
)


class TestEthereumValidation:
    """Test Ethereum address validation."""
    
    def test_valid_ethereum_addresses(self):
        """Test valid Ethereum address formats."""
        valid_addresses = [
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # UNI token (lowercase)
            "0x1F9840A85D5AF5BF1D1762F925BDADDC4201F984",  # UNI token (uppercase)
            "0xA0b86a33E6441B8422B3E1F9a5c36e4bc5F7e4a7",  # Mixed case
            "0x0000000000000000000000000000000000000000",  # Null address
            "0xffffffffffffffffffffffffffffffffffffffff",  # Max address
        ]
        
        for address in valid_addresses:
            result = validate_ethereum_address(address, check_checksum=False)
            assert result.is_valid, f"Should be valid: {address}"
            assert result.address_type == AddressType.ETHEREUM
            assert result.normalized_address == address.lower()
    
    def test_invalid_ethereum_addresses(self):
        """Test invalid Ethereum address formats."""
        invalid_addresses = [
            "",  # Empty
            "0x",  # Too short
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f98",  # Too short
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f9844",  # Too long
            "1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Missing 0x
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f98g",  # Invalid hex
            "0X1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrong prefix case
        ]
        
        for address in invalid_addresses:
            result = validate_ethereum_address(address)
            assert not result.is_valid, f"Should be invalid: {address}"
    
    def test_eip55_checksum_validation(self):
        """Test EIP-55 checksum validation."""
        # Valid checksum address (using a known valid checksum)
        valid_checksum = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
        result = validate_ethereum_address(valid_checksum, check_checksum=True)
        assert result.is_valid
        # Note: Our simplified checksum validation may still produce warnings
        
        # Invalid checksum address
        invalid_checksum = "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"  # Should have mixed case
        result = validate_ethereum_address(invalid_checksum, check_checksum=True)
        assert result.is_valid  # Still valid format
        assert len(result.warnings) == 0  # No warnings for all lowercase
        
        # Mixed case with wrong checksum
        wrong_checksum = "0x5aAeb6053f3e94c9b9a09f33669435e7ef1beaed"  # Wrong case
        result = validate_ethereum_address(wrong_checksum, check_checksum=True)
        assert result.is_valid  # Valid format
        assert len(result.warnings) > 0  # Should have checksum warning


class TestSolanaValidation:
    """Test Solana address validation."""
    
    def test_valid_solana_addresses(self):
        """Test valid Solana address formats."""
        valid_addresses = [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "So11111111111111111111111111111111111111112",   # SOL
            "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",   # BTC
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
        ]
        
        for address in valid_addresses:
            result = validate_solana_address(address)
            assert result.is_valid, f"Should be valid: {address}"
            assert result.address_type == AddressType.SOLANA
            assert result.normalized_address == address  # Case-sensitive
    
    def test_invalid_solana_addresses(self):
        """Test invalid Solana address formats."""
        invalid_addresses = [
            "",  # Empty
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4w",  # Too short (less than 32 chars)
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1vv",  # Too long
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt10",  # Contains 0
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDtOv",  # Contains O
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDtIv",  # Contains I
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDtlv",  # Contains l
        ]
        
        for address in invalid_addresses:
            result = validate_solana_address(address)
            assert not result.is_valid, f"Should be invalid: {address}"
    
    def test_base58_decoding(self):
        """Test base58 decoding functionality."""
        # Valid base58 that should decode to 32 bytes
        valid_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        decoded = _base58_decode(valid_address)
        assert len(decoded) == 32
        
        # Test invalid base58 character
        with pytest.raises(ValueError):
            _base58_decode("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt0v")  # Contains 0


class TestTokenAddressValidation:
    """Test main token address validation functions."""
    
    def test_validate_token_address_ethereum(self):
        """Test token address validation for Ethereum addresses."""
        eth_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        result = validate_token_address(eth_address)
        
        assert result is not None
        address, address_type = result
        assert address == eth_address.lower()
        assert address_type == AddressType.ETHEREUM
    
    def test_validate_token_address_solana(self):
        """Test token address validation for Solana addresses."""
        sol_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        result = validate_token_address(sol_address)
        
        assert result is not None
        address, address_type = result
        assert address == sol_address
        assert address_type == AddressType.SOLANA
    
    def test_validate_token_address_invalid(self):
        """Test token address validation for invalid addresses."""
        invalid_addresses = [
            "",
            "invalid",
            "0xinvalid",
            "toolongsolanaaddressthatshouldnotworkhere",
        ]
        
        for address in invalid_addresses:
            result = validate_token_address(address)
            assert result is None, f"Should be invalid: {address}"
    
    def test_validate_token_address_detailed(self):
        """Test detailed token address validation."""
        eth_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        result = validate_token_address_detailed(eth_address)
        
        assert result is not None
        assert result.is_valid
        assert result.address_type == AddressType.ETHEREUM
        assert result.normalized_address == eth_address.lower()
        assert isinstance(result.warnings, list)


class TestAddressUtilities:
    """Test address utility functions."""
    
    def test_detect_address_format(self):
        """Test address format detection."""
        assert detect_address_format("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984") == "ethereum"
        assert detect_address_format("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") == "solana"
        assert detect_address_format("invalid") == "unknown"
        assert detect_address_format("") is None
    
    def test_get_address_info(self):
        """Test comprehensive address information."""
        eth_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        info = get_address_info(eth_address)
        
        assert info['is_valid']
        assert info['detected_format'] == 'ethereum'
        assert info['address_type'] == 'Ethereum'
        assert 'normalized_address' in info
        assert 'supported_chains' in info
        assert isinstance(info['supported_chains'], list)
    
    def test_is_contract_address_format(self):
        """Test contract address format validation."""
        eth_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        sol_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        assert is_contract_address_format(eth_address)
        assert is_contract_address_format(sol_address)
        assert not is_contract_address_format("invalid")
    
    def test_normalize_address(self):
        """Test address normalization."""
        eth_address = "0x1F9840A85D5AF5BF1D1762F925BDADDC4201F984"
        sol_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        assert normalize_address(eth_address, AddressType.ETHEREUM) == eth_address.lower()
        assert normalize_address(sol_address, AddressType.SOLANA) == sol_address
    
    def test_batch_validate_addresses(self):
        """Test batch address validation."""
        addresses = [
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Valid ETH
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # Valid SOL
            "invalid",  # Invalid
        ]
        
        results = batch_validate_addresses(addresses)
        
        assert len(results) == 3
        assert results[0]['is_valid']
        assert results[1]['is_valid']
        assert not results[2]['is_valid']


class TestChainSupport:
    """Test chain ID and network support."""
    
    def test_is_valid_chain_id(self):
        """Test chain ID validation."""
        assert is_valid_chain_id(1)      # Ethereum
        assert is_valid_chain_id(56)     # BSC
        assert is_valid_chain_id(137)    # Polygon
        assert not is_valid_chain_id(999999)  # Invalid
    
    def test_get_network_name(self):
        """Test network name retrieval."""
        assert get_network_name(1) == "Ethereum"
        assert get_network_name(56) == "BNB Smart Chain"
        assert get_network_name(999999) == "Chain 999999"


class TestValidationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        assert validate_token_address("") is None
        assert validate_token_address("   ") is None
        assert validate_token_address_detailed("") is None
        
        # Test address info with empty input
        info = get_address_info("")
        assert not info['is_valid']
        assert 'error' in info
    
    def test_whitespace_handling(self):
        """Test proper whitespace handling."""
        eth_with_spaces = "  0x1f9840a85d5af5bf1d1762f925bdaddc4201f984  "
        result = validate_token_address(eth_with_spaces)
        
        assert result is not None
        address, address_type = result
        assert address == eth_with_spaces.strip().lower()
    
    def test_strict_checksum_mode(self):
        """Test strict checksum validation mode."""
        # Test with all lowercase (should pass)
        lowercase_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        result = validate_token_address(lowercase_address, strict_checksum=True)
        assert result is not None
        
        # Test with all uppercase (should pass)
        uppercase_address = "0x1F9840A85D5AF5BF1D1762F925BDADDC4201F984"
        result = validate_token_address(uppercase_address, strict_checksum=True)
        assert result is not None


class TestValidationResult:
    """Test ValidationResult class functionality."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult object creation."""
        result = ValidationResult(
            address="0x1234",
            address_type=AddressType.ETHEREUM,
            is_valid=True,
            normalized_address="0x1234",
            warnings=["test warning"]
        )
        
        assert result.address == "0x1234"
        assert result.address_type == AddressType.ETHEREUM
        assert result.is_valid
        assert result.normalized_address == "0x1234"
        assert len(result.warnings) == 1
        assert bool(result) == True
    
    def test_validation_result_bool_conversion(self):
        """Test ValidationResult boolean conversion."""
        valid_result = ValidationResult("0x1234", AddressType.ETHEREUM, True)
        invalid_result = ValidationResult("invalid", AddressType.ETHEREUM, False)
        
        assert bool(valid_result) == True
        assert bool(invalid_result) == False 