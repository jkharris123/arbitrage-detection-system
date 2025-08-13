#!/usr/bin/env python3
"""
Quick TWS connection diagnostic
"""
import socket
import sys

def check_port(host, port):
    """Check if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

print("🔍 Checking TWS Connection Status...")
print("=" * 50)

# Check common TWS ports
ports = {
    7496: "Live Trading",
    7497: "Paper Trading", 
    4001: "IB Gateway Live",
    4002: "IB Gateway Paper"
}

tws_found = False
for port, desc in ports.items():
    if check_port("127.0.0.1", port):
        print(f"✅ Port {port} ({desc}) is OPEN")
        tws_found = True
    else:
        print(f"❌ Port {port} ({desc}) is CLOSED")

if not tws_found:
    print("\n⚠️ TWS/IB Gateway not detected!")
    print("\n📋 To fix:")
    print("1. Start TWS or IB Gateway")
    print("2. In TWS: File -> Global Configuration -> API -> Settings")
    print("3. Enable 'Enable ActiveX and Socket Clients'")
    print("4. Add '127.0.0.1' to 'Trusted IP Addresses'")
    print("5. Uncheck 'Read-Only API'")
    print("6. Port should be 7496 (live) or 7497 (paper)")
else:
    print("\n✅ TWS/IB Gateway is running and accessible!")
    print("Ready to run options test.")

print("\n" + "=" * 50)