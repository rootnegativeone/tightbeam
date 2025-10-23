#!/usr/bin/env python3
"""
Tightbeam Camera Demo: Real camera capture and QR code decoding
Demonstrates live QR-GIF capture and fountain decoding.
"""
import cv2
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
import sys
import numpy as np
import os

# Suppress OpenCV camera warnings
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.fountain.encoder import LTEncoder
from decoder.reassembler import LTDecoder

class TightbeamCameraDemo:
    def __init__(self, block_size=32):
        self.block_size = block_size
        self.qr_detector = cv2.QRCodeDetector()
        
    def generate_sample_log(self) -> bytes:
        """Generate a small realistic JSON log file for demo."""
        # Much smaller dataset for easier testing
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO", 
            "service": "auth-service", 
            "message": "User login successful", 
            "userId": "user123"
        }
        return json.dumps(log_entry).encode('utf-8')
    
    def create_looping_gif(self, symbols, output_path="qr_loop.gif"):
        """Create a looping GIF of QR codes with spatial diversity for phone display."""
        import qrcode
        from PIL import Image
        import imageio.v3 as iio
        
        print(f"Creating looping GIF with {len(symbols)} QR codes (with spatial diversity)...")
        
        frames = []
        for i, (idxs, payload) in enumerate(symbols):
            # Create main QR code data
            qr_data = f"{idxs[0]}:{payload.hex()}"
            
            # Create QR code with consistent sizing
            qr = qrcode.QRCode(version=3, box_size=8, border=4)  # Smaller box_size for faster scanning
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to RGB mode
            if qr_img.mode != 'RGB':
                qr_img = qr_img.convert('RGB')
            
            # Create spatial diversity - add out-of-phase QR code with larger phase difference
            phase_offset = len(symbols) // 3  # Use 1/3 offset instead of +1 for more pronounced diversity
            next_idx = (i + phase_offset) % len(symbols)
            next_idxs, next_payload = symbols[next_idx]
            next_qr_data = f"{next_idxs[0]}:{next_payload.hex()}"
            
            next_qr = qrcode.QRCode(version=3, box_size=8, border=4)
            next_qr.add_data(next_qr_data)
            next_qr.make(fit=True)
            
            next_qr_img = next_qr.make_image(fill_color="black", back_color="white")
            
            # Convert to RGB mode
            if next_qr_img.mode != 'RGB':
                next_qr_img = next_qr_img.convert('RGB')
            
            # Arrange side by side for spatial diversity
            total_width = qr_img.width + next_qr_img.width + 20
            total_height = max(qr_img.height, next_qr_img.height) + 60
            
            canvas = Image.new('RGB', (total_width, total_height), 'white')
            canvas.paste(qr_img, (0, 30))
            canvas.paste(next_qr_img, (qr_img.width + 20, 30))
            
            # Add text overlay
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            text1 = f"Primary: {i+1}/{len(symbols)} (Index: {idxs[0]})"
            text2 = f"Secondary: {next_idx+1}/{len(symbols)} (Index: {next_idxs[0]})"
            draw.text((10, 5), text1, fill='black', font=font)
            draw.text((10, total_height - 25), text2, fill='black', font=font)
            
            frames.append(np.array(canvas))
        
        # Create faster looping GIF (400ms per frame instead of 800ms)
        iio.imwrite(output_path, frames, duration=400, loop=0)
        print(f"Created looping GIF: {output_path}")
        print("Display this GIF on your phone and point laptop camera at it!")
        print("Spatial diversity: Each frame shows 2 QR codes for redundancy!")
        
        return output_path
    
    def encode_data(self, data: bytes):
        """Encode data using fountain codes."""
        print(f"Encoding {len(data)} bytes...")
        
        encoder = LTEncoder(data, self.block_size, systematic=True)
        k = len(encoder.blocks)
        
        # Use systematic symbols for reliable demo
        symbols = list(encoder.emit_systematic())
        
        print(f"Generated {len(symbols)} symbols for {k} blocks")
        print("Each symbol will be displayed as a QR code")
        print("Point your camera at the QR codes to capture them")
        
        return symbols, k
    
    def display_qr_sequence(self, symbols):
        """Display QR codes in sequence for camera capture."""
        import qrcode
        from PIL import Image
        
        print("\nDisplaying QR codes...")
        print("Press 'q' to quit, 'n' for next QR code, 'p' for previous")
        
        current_idx = 0
        
        while True:
            if current_idx >= len(symbols):
                print("All QR codes displayed!")
                break
                
            # Create QR code for current symbol
            idxs, payload = symbols[current_idx]
            
            # Create a simple data format: "idx:payload_hex"
            qr_data = f"{idxs[0]}:{payload.hex()}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL to OpenCV format
            qr_array = np.array(qr_img.convert('RGB'))
            qr_bgr = cv2.cvtColor(qr_array, cv2.COLOR_RGB2BGR)
            
            # Resize for better visibility
            height, width = qr_bgr.shape[:2]
            qr_large = cv2.resize(qr_bgr, (width*3, height*3), interpolation=cv2.INTER_NEAREST)
            
            # Add text overlay
            text = f"Symbol {current_idx+1}/{len(symbols)} - Index: {idxs[0]}"
            cv2.putText(qr_large, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            cv2.imshow('QR Code Display', qr_large)
            
            key = cv2.waitKey(0) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('n') or key == ord(' '):
                current_idx += 1
            elif key == ord('p') and current_idx > 0:
                current_idx -= 1
        
        cv2.destroyAllWindows()
    
    def capture_qr_codes(self, expected_count):
        """Capture QR codes using laptop camera."""
        print(f"\nStarting laptop camera capture...")
        print(f"Looking for {expected_count} QR codes")
        print("Press 'q' to quit")
        
        # Try different camera indices to find laptop camera
        cap = None
        for camera_idx in [0, 1, 2]:
            test_cap = cv2.VideoCapture(camera_idx)
            if test_cap.isOpened():
                # Test if it's working
                ret, frame = test_cap.read()
                if ret:
                    print(f"Using camera {camera_idx}")
                    cap = test_cap
                    break
                else:
                    test_cap.release()
            else:
                test_cap.release()
        
        if cap is None:
            print("Error: Could not open any camera")
            return []
        
        captured_symbols = {}
        
        while len(captured_symbols) < expected_count:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break
            
            # Detect QR codes
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            
            # Draw bounding box if QR code detected
            if bbox is not None:
                bbox = bbox.astype(int)
                cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
                
                if data:
                    # Parse QR data: "idx:payload_hex"
                    try:
                        idx_str, payload_hex = data.split(':', 1)
                        idx = int(idx_str)
                        payload = bytes.fromhex(payload_hex)
                        
                        if idx not in captured_symbols:
                            captured_symbols[idx] = payload
                            print(f"✅ Captured symbol {idx} ({len(captured_symbols)}/{expected_count})")
                        
                        # Show captured status
                        status_text = f"Captured: {len(captured_symbols)}/{expected_count}"
                        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.putText(frame, f"Current: {idx}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                        
                    except (ValueError, IndexError):
                        cv2.putText(frame, "Invalid QR format", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Show progress
            progress_text = f"Progress: {len(captured_symbols)}/{expected_count}"
            cv2.putText(frame, progress_text, (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Laptop Camera - Point at Phone QR GIF', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Convert to list format expected by decoder
        symbols = []
        for idx in sorted(captured_symbols.keys()):
            symbols.append(([idx], captured_symbols[idx]))
        
        print(f"Captured {len(symbols)} symbols")
        return symbols
    
    def decode_symbols(self, symbols, original_length, k):
        """Decode captured symbols."""
        print("Decoding symbols...")
        
        decoder = LTDecoder(self.block_size, k, original_length)
        
        for idxs, payload in symbols:
            decoder.add_symbol(idxs, payload)
        
        print(f"Added {len(decoder.symbols)} symbols, need {k}")
        
        result = decoder.decode()
        
        if result:
            print(f"Successfully decoded {len(result)} bytes")
        else:
            print("Decoding failed - insufficient symbols")
        
        return result
    
    def run_demo(self):
        """Run the complete camera demo."""
        print("=== Tightbeam Camera Demo (Simplified) ===\n")
        
        # 1. Generate sample log
        print("1. Generating sample log file...")
        log_data = self.generate_sample_log()
        log_hash = hashlib.sha256(log_data).hexdigest()[:8]
        print(f"Generated log: {len(log_data)} bytes")
        print(f"Data: {log_data.decode()}")
        print(f"Hash: {log_hash}\n")
        
        # 2. Encode data
        print("2. Encoding data...")
        symbols, k = self.encode_data(log_data)
        print()
        
        # 3. Create looping GIF
        print("3. Creating QR-GIF for phone display...")
        gif_path = self.create_looping_gif(symbols)
        print()
        
        # 4. Instructions
        print("4. Setup Instructions:")
        print(f"   a) Open {gif_path} on your phone")
        print("   b) Make sure it's looping/animating")
        print("   c) Hold phone steady in good lighting")
        print("   d) Press Enter when ready...")
        input()
        
        # 5. Capture QR codes with laptop camera
        print("5. Starting laptop camera capture...")
        captured_symbols = self.capture_qr_codes(k)
        
        if len(captured_symbols) < k:
            print(f"Warning: Only captured {len(captured_symbols)}/{k} symbols")
            if len(captured_symbols) == 0:
                print("No symbols captured. Try again with better lighting/positioning.")
                return
        
        # 6. Decode
        print("\n6. Decoding...")
        decoded_data = self.decode_symbols(captured_symbols, len(log_data), k)
        
        # 7. Verify
        print("\n7. Verification...")
        if decoded_data and decoded_data == log_data:
            decoded_hash = hashlib.sha256(decoded_data).hexdigest()[:8]
            print("✅ SUCCESS: Decoded data matches original!")
            print(f"Original hash: {log_hash}")
            print(f"Decoded hash:  {decoded_hash}")
            print(f"Decoded data:  {decoded_data.decode()}")
            print("Camera-based QR capture and fountain decoding successful!")
        else:
            print("❌ FAILED: Decoded data doesn't match original")
            if decoded_data:
                decoded_hash = hashlib.sha256(decoded_data).hexdigest()[:8]
                print(f"Original: {len(log_data)} bytes, hash: {log_hash}")
                print(f"Decoded:  {len(decoded_data)} bytes, hash: {decoded_hash}")
                print(f"Decoded data: {decoded_data}")

if __name__ == "__main__":
    demo = TightbeamCameraDemo(block_size=8)  # Even smaller blocks for tiny dataset
    demo.run_demo()
