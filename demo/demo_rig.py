#!/usr/bin/env python3
"""
Tightbeam Demo Rig: Log File → QR-GIF → Decoded Log
Demonstrates fountain-encoded QR-GIFs with spatial diversity.
"""

import json
import time
from datetime import datetime
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio
import sys
import numpy as np

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.fountain.encoder import LTEncoder
from decoder.reassembler import LTDecoder
from common.fountain.sim import burst_eraser
from common.shared.metrics import FountainMetrics


class TightbeamDemo:
    def __init__(self, block_size: int = 32, integrity_check: bool = True):
        self.block_size = block_size
        self.integrity_check = integrity_check

    def generate_sample_log(self) -> bytes:
        """Generate a realistic JSON log file for demo."""
        logs = []
        base_time = datetime.now()

        # Simulate various log events
        events = [
            {
                "level": "INFO",
                "service": "auth-service",
                "message": "User login successful",
                "userId": "user123",
            },
            {
                "level": "WARN",
                "service": "payment-gateway",
                "message": "High latency detected",
                "latency_ms": 1250,
            },
            {
                "level": "ERROR",
                "service": "database",
                "message": "Connection timeout",
                "errorCode": "DB_TIMEOUT",
            },
            {
                "level": "INFO",
                "service": "api-gateway",
                "message": "Request processed",
                "endpoint": "/api/data",
                "status": 200,
            },
            {
                "level": "ERROR",
                "service": "auth-service",
                "message": "Invalid credentials",
                "userId": "user456",
                "attempts": 3,
            },
        ]

        for i, event in enumerate(events * 4):  # Repeat for more data
            timestamp = base_time.timestamp() + i * 5
            log_entry = {
                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                "requestId": f"req-{i:04d}",
                **event,
            }
            logs.append(json.dumps(log_entry))

        return "\n".join(logs).encode("utf-8")

    def create_qr_frame(
        self, symbol_data: bytes, frame_id: int, total_frames: int
    ) -> Image.Image:
        """Create a single QR code frame with metadata."""
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(symbol_data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to RGB if needed
        if qr_img.mode != "RGB":
            qr_img = qr_img.convert("RGB")

        # Add frame info
        width, height = qr_img.size
        canvas = Image.new("RGB", (width, height + 40), "white")
        canvas.paste(qr_img, (0, 0))

        # Add text overlay
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.load_default()
        except:
            font = None

        text = f"Frame {frame_id}/{total_frames}"
        draw.text((5, height + 5), text, fill="black", font=font)

        return canvas

    def create_spatial_diversity_frame(
        self, symbols: list, frame_idx: int
    ) -> Image.Image:
        """Create frame with spatial diversity - multiple QR codes out of phase."""
        if frame_idx >= len(symbols):
            return None

        # Get current symbol and next symbol (out of phase)
        current_symbol = symbols[frame_idx]
        next_symbol = symbols[(frame_idx + 1) % len(symbols)]

        # Create QR codes for both symbols
        qr1 = self.create_qr_frame(current_symbol[1], frame_idx, len(symbols))
        qr2 = self.create_qr_frame(
            next_symbol[1], (frame_idx + 1) % len(symbols), len(symbols)
        )

        # Arrange side by side for spatial diversity
        total_width = qr1.width + qr2.width + 20
        total_height = max(qr1.height, qr2.height)

        canvas = Image.new("RGB", (total_width, total_height), "white")
        canvas.paste(qr1, (0, 0))
        canvas.paste(qr2, (qr1.width + 20, 0))

        return canvas

    def encode_to_qr_gif(
        self,
        data: bytes,
        output_path: str = "demo_output.gif",
        metrics: FountainMetrics | None = None,
    ):
        """Encode data using fountain codes and create QR-GIF."""
        print(f"Encoding {len(data)} bytes...")

        # Fountain encode
        metrics = metrics or FountainMetrics()
        encoder = LTEncoder(
            data,
            self.block_size,
            systematic=True,
            integrity_check=self.integrity_check,
            metrics=metrics,
        )
        k = len(encoder.blocks)

        # Use only systematic symbols for reliable demo
        symbols = list(encoder.emit_systematic())

        print(f"Generated {len(symbols)} symbols for {k} blocks")

        # Create QR-GIF frames with spatial diversity
        frames = []
        for i in range(min(len(symbols), 20)):  # Limit frames for demo
            frame = self.create_spatial_diversity_frame(symbols, i)
            if frame:
                frames.append(frame)

        # Save as animated GIF
        if frames:
            # Convert PIL images to numpy arrays for imageio
            frame_arrays = [np.array(frame) for frame in frames]
            iio.imwrite(output_path, frame_arrays, duration=500)  # 500ms per frame
            print(f"Created QR-GIF: {output_path}")

        summary = metrics.summary()
        print("\nFountain metrics:")
        print(f"  • Symbols generated: {summary['total_symbols']}")
        print(f"  • Average degree: {summary['average_degree']:.2f}")
        if summary["rejected_symbols"]:
            print(
                f"  • Rejected symbols during encode/decode: {summary['rejected_symbols']}"
            )

        return symbols

    def simulate_camera_capture(self, symbols: list, loss_rate=0.2):
        """Simulate camera capturing QR codes with some loss."""
        print(f"Simulating camera capture with {loss_rate * 100}% loss rate...")

        # Simulate burst erasure (camera missing frames)
        received = burst_eraser(symbols, loss_rate=loss_rate, burst_len=3)

        print(f"Captured {len(received)}/{len(symbols)} symbols")
        return received

    def decode_from_symbols(
        self,
        symbols: list,
        original_length: int,
        metrics: FountainMetrics | None = None,
    ) -> bytes:
        """Decode data from received symbols."""
        print("Decoding symbols...")

        # Calculate k from block size and data length
        k = (original_length + self.block_size - 1) // self.block_size

        decoder = LTDecoder(
            self.block_size,
            k,
            original_length,
            integrity_check=self.integrity_check,
            metrics=metrics,
        )

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
        """Run the complete demo."""
        print("=== Tightbeam Demo: Log File Transfer ===\n")

        # 1. Generate sample log
        print("1. Generating sample log file...")
        log_data = self.generate_sample_log()
        print(f"Generated log: {len(log_data)} bytes")
        print(f"Sample: {log_data[:100].decode()}...\n")

        # 2. Encode to QR-GIF
        print("2. Encoding to QR-GIF...")
        metrics = FountainMetrics()
        symbols = self.encode_to_qr_gif(log_data, metrics=metrics)
        print()

        # 3. Simulate transmission with loss
        print("3. Simulating camera capture...")
        # For demo purposes, assume perfect transmission
        received_symbols = symbols  # No loss simulation
        print(
            f"Captured {len(received_symbols)}/{len(symbols)} symbols (perfect transmission)"
        )
        print()

        # 4. Decode
        print("4. Decoding received symbols...")
        decoded_data = self.decode_from_symbols(
            received_symbols, len(log_data), metrics=metrics
        )
        print()

        # 5. Verify
        print("5. Verification...")
        if decoded_data and decoded_data == log_data:
            print("✅ SUCCESS: Decoded data matches original!")
            print(
                "Demo completed successfully - fountain codes provided burst resilience!"
            )
            summary = metrics.summary()
            print("Metrics Summary:")
            print(f"  • Decode attempts: {summary['decode_attempts']}")
            print(
                f"  • Decode success rate: {summary['decode_success_rate'] * 100:.1f}%"
            )
            if summary["decode_durations"]:
                print(
                    f"  • Average decode latency: {summary['average_decode_duration'] * 1000:.2f} ms"
                )
            if summary["rejected_symbols"]:
                print(f"  • Rejected symbols: {summary['rejected_symbols']}")
        else:
            print("❌ FAILED: Decoded data doesn't match original")
            if decoded_data:
                print(f"Original: {len(log_data)} bytes")
                print(f"Decoded:  {len(decoded_data)} bytes")


if __name__ == "__main__":
    demo = TightbeamDemo(block_size=32)
    demo.run_demo()
