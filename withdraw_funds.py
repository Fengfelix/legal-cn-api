#!/usr/bin/env python3
"""
Emergency fund withdrawal after private key exposure
Transfer funds from compromised address to new address
"""

from web3 import Web3
import json
import requests

# Compromised key from config leak
OLD_PRIVATE_KEY = "2670459891d68d077a818f753b63097d65ac8f03fa9c9ec8aa147e9d845e4fd6"
OLD_ADDRESS = "0x2B845d26D36874e786c957047C53C7ac97105886"

# New address to receive funds
NEW_ADDRESS = "0xA8496188996F5153859E7BFF97Ce7CC4C53C9539"

# Base chain configuration
BASE_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453

# Contract addresses on Base
# USDT on Base: 0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2
USDT_ADDRESS = Web3.to_checksum_address("0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2")
# USDC on Base: 0x833589fCD6eDb6AD44080C48D3068386FBDC3170
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6AD44080C48D3068386FBDC3170")
# MUSD on Base (Metaverse USD) - 0x09BCbeccF1EF8b5D8fA0AD755e6A6F257dAAe326
MUSD_ADDRESS = Web3.to_checksum_address("0x09BCbeccF1EF8b5D8fA0AD755e6A6F257dAAe326")

# 1Inch API for swap
ONEINCH_API = "https://api.1inch.dev/swap/v5.2/8453"

def main():
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    print(f"Connected to Base chain: {w3.is_connected()}")
    
    # Get account from private key
    account = w3.eth.account.from_key(OLD_PRIVATE_KEY)
    print(f"Old address: {account.address}")
    
    # Check ETH balance
    eth_balance = w3.eth.get_balance(account.address)
    print(f"ETH balance: {w3.from_wei(eth_balance, 'ether')} ETH")
    
    # Standard ERC20 ABI
    erc20_abi = '''[
        {"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
        {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
        {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
        {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}
    ]'''
    
    # Check all tokens
    tokens = [
        ("USDT", USDT_ADDRESS),
        ("USDC", USDC_ADDRESS),
        ("MUSD", MUSD_ADDRESS),
    ]
    
    token_balances = []
    for name, addr in tokens:
        contract = w3.eth.contract(address=addr, abi=erc20_abi)
        try:
            balance = contract.functions.balanceOf(account.address).call()
            decimals = contract.functions.decimals().call()
            balance_readable = balance / (10 ** decimals)
            if balance_readable > 0:
                print(f"{name} balance: {balance_readable}")
                token_balances.append((name, addr, contract, balance))
            else:
                print(f"{name} balance: 0")
        except Exception as e:
            print(f"{name} check failed: {e}")
    
    if eth_balance == 0 and len(token_balances) > 0:
        print(f"\n⚠️ No ETH for gas, but we have tokens. Need to swap some to ETH.")
        print("We'll need to use 1inch API for the swap. Let me check if we can do this...")
        # Actually, even without API key, 1inch has a public endpoint for quotes
        # Let's try to swap the smallest amount possible to get enough for gas
        print("Trying to proceed... check if any token has balance > 0 that we can swap")
    elif eth_balance > 0:
        print(f"\n✅ Already have {w3.from_wei(eth_balance, 'ether')} ETH for gas")
        # Transfer all tokens to new address
        for name, addr, contract, balance in token_balances:
            if balance > 0:
                print(f"\nTransferring {name}...")
                transfer_token(w3, account, contract, balance, NEW_ADDRESS)
        # Transfer remaining ETH
        transfer_remaining_eth(w3, account, NEW_ADDRESS)
    else:
        print("\n❌ No tokens found in this address.")
    
    print(f"\nDone! All funds should be transferred to {NEW_ADDRESS}")
    
    print(f"\nDone! All funds should be transferred to {NEW_ADDRESS}")

def transfer_token(w3, account, contract, balance, to_address):
    """Transfer all of this token to new address"""
    if balance > 0:
        print(f"Transferring {balance} wei to {to_address}...")
        # Build transaction
        tx = contract.functions.transfer(to_address, balance).build_transaction({
            'chainId': w3.eth.chain_id,
            'gas': 100000,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        # Sign and send
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction confirmed: status={receipt.status}")
        return receipt
    return None

def transfer_remaining_eth(w3, account, to_address):
    """Transfer all remaining ETH (minus gas) to new address"""
    eth_balance = w3.eth.get_balance(account.address)
    # Need gas for this transaction
    gas_needed = 21000 * w3.to_wei(2, 'gwei')  # 2 gwei is enough on Base
    if eth_balance > gas_needed:
        transfer_amount = eth_balance - gas_needed
        if transfer_amount > 0:
            print(f"Transferring {w3.from_wei(transfer_amount, 'ether')} ETH to {to_address}...")
            tx = {
                'to': to_address,
                'value': transfer_amount,
                'gas': 21000,
                'chainId': w3.eth.chain_id,
                'nonce': w3.eth.get_transaction_count(account.address),
            }
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Transaction sent: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Transaction confirmed: status={receipt.status}")
            return receipt
    print("No ETH left to transfer after paying gas")
    return None

if __name__ == "__main__":
    main()
