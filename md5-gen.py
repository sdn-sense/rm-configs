#!/usr/bin/env python3
"""Generate MD5 from provided str"""
import sys
import hashlib

def generateMD5(inText):
    """Generate MD5 from provided str"""
    hashObj = hashlib.md5(inText.encode())
    print(f"INPUT: {inText} MD5: {hashObj.hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        generateMD5(sys.argv[1])
    else:
        print('Usage: python3 <script_name> <hostname>')

