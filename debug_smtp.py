#!/usr/bin/env python3
"""
Simple SMTP Debug Server
Muestra todos los emails que recibe en la terminal
"""

import asyncio
import email
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message

class DebugHandler(Message):
    def handle_message(self, message):
        print("\n" + "="*50)
        print("📧 EMAIL RECIBIDO 📧")
        print("="*50)
        print(f"From: {message.get('From', 'Unknown')}")
        print(f"To: {message.get('To', 'Unknown')}")
        print(f"Subject: {message.get('Subject', 'No Subject')}")
        print(f"Date: {message.get('Date', 'Unknown')}")
        print("-" * 50)
        
        # Get the body
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    print("Body:")
                    print(part.get_payload(decode=True).decode('utf-8'))
                    break
        else:
            print("Body:")
            try:
                body = message.get_payload(decode=True)
                if body:
                    print(body.decode('utf-8'))
                else:
                    print(message.get_payload())
            except:
                print(message.get_payload())
        
        print("="*50)

def main():
    handler = DebugHandler()
    controller = Controller(handler, hostname='localhost', port=1025)
    
    print("🚀 Starting SMTP Debug Server...")
    print("📧 Listening on localhost:1025")
    print("💡 Press Ctrl+C to stop")
    print("="*50)
    
    controller.start()
    
    try:
        # Keep the server running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping SMTP server...")
        controller.stop()

if __name__ == "__main__":
    main()