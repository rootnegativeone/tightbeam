#!/usr/bin/env python3
"""
Tightbeam Standalone Encoder Demo
Generates realistic log data and creates QR-GIF for demonstration.
Self-contained script for easy deployment.
"""

import json
import time
import random
from datetime import datetime, timedelta
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
from common.shared.metrics import FountainMetrics


class StandaloneEncoder:
    def __init__(self, block_size: int = 32, integrity_check: bool = True):
        self.block_size = block_size
        self.integrity_check = integrity_check
        self.metrics: FountainMetrics | None = None

    def generate_realistic_logs(self, num_entries=100) -> bytes:
        """Generate substantial realistic JSON log data for demo."""
        logs = []
        base_time = datetime.now() - timedelta(hours=24)

        # Realistic service names and log patterns
        services = [
            "auth-service",
            "payment-gateway",
            "user-service",
            "notification-service",
            "database",
            "api-gateway",
            "cache-service",
            "file-service",
            "analytics-service",
        ]

        log_templates = [
            {
                "level": "INFO",
                "message": "Request processed successfully",
                "status": 200,
            },
            {
                "level": "INFO",
                "message": "User authentication successful",
                "method": "POST",
            },
            {
                "level": "WARN",
                "message": "High memory usage detected",
                "memory_percent": lambda: random.randint(75, 95),
            },
            {
                "level": "WARN",
                "message": "Slow query detected",
                "query_time_ms": lambda: random.randint(1000, 5000),
            },
            {
                "level": "ERROR",
                "message": "Database connection timeout",
                "timeout_ms": lambda: random.randint(5000, 30000),
            },
            {
                "level": "ERROR",
                "message": "Failed to process payment",
                "error_code": lambda: f"PAY_{random.randint(1000, 9999)}",
            },
            {
                "level": "INFO",
                "message": "Cache hit",
                "cache_key": lambda: f"user_{random.randint(1000, 9999)}",
            },
            {
                "level": "INFO",
                "message": "File uploaded successfully",
                "file_size_mb": lambda: round(random.uniform(0.1, 50.0), 2),
            },
            {
                "level": "DEBUG",
                "message": "API rate limit check",
                "requests_per_minute": lambda: random.randint(10, 100),
            },
            {
                "level": "WARN",
                "message": "Unusual traffic pattern detected",
                "requests_spike": lambda: random.randint(200, 1000),
            },
        ]

        user_ids = [f"user_{i:04d}" for i in range(1, 501)]
        endpoints = [
            "/api/users",
            "/api/payments",
            "/api/files",
            "/api/auth",
            "/api/analytics",
            "/health",
        ]

        for i in range(num_entries):
            # Generate timestamp with some realistic spacing
            timestamp = base_time + timedelta(
                minutes=random.randint(0, 1440),  # Within 24 hours
                seconds=random.randint(0, 59),
            )

            # Pick random service and log template
            service = random.choice(services)
            template = random.choice(log_templates).copy()

            # Resolve any lambda functions in template
            for key, value in template.items():
                if callable(value):
                    template[key] = value()

            # Build log entry
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "requestId": f"req-{i:06d}",
                "service": service,
                "userId": random.choice(user_ids) if random.random() > 0.3 else None,
                "endpoint": random.choice(endpoints) if random.random() > 0.4 else None,
                **template,
            }

            # Add some service-specific fields
            if service == "payment-gateway":
                log_entry["transaction_id"] = f"txn_{random.randint(100000, 999999)}"
                log_entry["amount"] = round(random.uniform(1.0, 1000.0), 2)
            elif service == "database":
                log_entry["table"] = random.choice(
                    ["users", "payments", "sessions", "logs"]
                )
                log_entry["operation"] = random.choice(
                    ["SELECT", "INSERT", "UPDATE", "DELETE"]
                )
            elif service == "api-gateway":
                log_entry["ip_address"] = (
                    f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
                )
                log_entry["user_agent"] = random.choice(
                    ["Chrome/91.0", "Firefox/89.0", "Safari/14.1", "Mobile/15.0"]
                )

            # Remove None values
            log_entry = {k: v for k, v in log_entry.items() if v is not None}

            logs.append(json.dumps(log_entry, separators=(",", ":")))  # Compact JSON

        log_data = "\n".join(logs)

        # Add some metadata header
        metadata = {
            "log_format": "json_lines",
            "generated_at": datetime.now().isoformat(),
            "total_entries": len(logs),
            "services": services,
            "demo_version": "1.0",
        }

        full_log = json.dumps(metadata, separators=(",", ":")) + "\n" + log_data
        return full_log.encode("utf-8")

    def create_enhanced_qr_frame(
        self, symbol_data: bytes, frame_id: int, total_frames: int, symbol_index: int
    ) -> Image.Image:
        """Create QR code frame with enhanced metadata and styling."""
        # Create QR code with optimal settings for camera capture
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction
            box_size=6,  # Good balance of size and scannability
            border=4,  # Adequate border for detection
        )

        # Format data for QR: index:hex_payload
        qr_data = f"{symbol_index}:{symbol_data.hex()}"
        qr.add_data(qr_data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to RGB
        if qr_img.mode != "RGB":
            qr_img = qr_img.convert("RGB")

        # Create canvas with space for metadata
        canvas_width = qr_img.width + 40
        canvas_height = qr_img.height + 80
        canvas = Image.new("RGB", (canvas_width, canvas_height), "white")

        # Center the QR code
        qr_x = (canvas_width - qr_img.width) // 2
        qr_y = 40
        canvas.paste(qr_img, (qr_x, qr_y))

        # Add informative text
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.load_default()
        except:
            font = None

        # Header text
        header_text = f"Tightbeam Demo - Symbol {frame_id + 1}/{total_frames}"
        draw.text((10, 10), header_text, fill="black", font=font)

        # Footer text with symbol info
        footer_text = f"Index: {symbol_index} | Size: {len(symbol_data)} bytes"
        draw.text((10, canvas_height - 25), footer_text, fill="black", font=font)

        return canvas

    def create_demo_qr_gif(self, data: bytes, output_path: str = "tightbeam_demo.gif"):
        """Create demonstration QR-GIF with fountain encoding."""
        print(f"🔧 Encoding {len(data)} bytes of log data...")

        # Fountain encode the data
        self.metrics = FountainMetrics()
        encoder = LTEncoder(
            data,
            self.block_size,
            systematic=True,
            integrity_check=self.integrity_check,
            metrics=self.metrics,
        )
        k = len(encoder.blocks)

        # Generate systematic symbols (most reliable for demo)
        symbols = list(encoder.emit_systematic())

        print(f"📊 Generated {len(symbols)} fountain-coded symbols for {k} blocks")
        print(f"📱 Creating QR-GIF with enhanced frames...")

        # Create QR frames
        frames = []
        for i, (idxs, payload) in enumerate(symbols):
            # Use the first index for display (systematic symbols have single indices)
            symbol_index = idxs[0] if isinstance(idxs, (list, tuple)) else idxs

            frame = self.create_enhanced_qr_frame(
                payload, i, len(symbols), symbol_index
            )
            frames.append(frame)

            if (i + 1) % 10 == 0:
                print(f"   Created {i + 1}/{len(symbols)} frames...")

        # Save as animated GIF with optimal settings
        if frames:
            frame_arrays = [np.array(frame) for frame in frames]
            iio.imwrite(
                output_path,
                frame_arrays,
                duration=800,  # 800ms per frame for easy scanning
                loop=0,  # Infinite loop
            )
            print(f"✅ Created QR-GIF: {output_path}")
            print(f"📺 Display this GIF on a screen and scan with camera!")

        if self.metrics:
            summary = self.metrics.summary()
            print("📈 Fountain metrics:")
            print(f"   • Symbols generated: {summary['total_symbols']}")
            print(f"   • Average degree: {summary['average_degree']:.2f}")
            if summary["rejected_symbols"]:
                print(f"   • Rejected symbols: {summary['rejected_symbols']}")
            if summary["decode_attempts"]:
                print(
                    f"   • Decode success rate: {summary['decode_success_rate'] * 100:.1f}% "
                    f"across {summary['decode_attempts']} attempts"
                )

        return symbols, output_path

    def save_log_sample(self, data: bytes, output_path: str = "sample_log.json"):
        """Save a sample of the log data for inspection."""
        # Save first few lines for user to see what was encoded
        lines = data.decode("utf-8").split("\n")
        sample_lines = lines[:10] if len(lines) > 10 else lines

        sample_data = {
            "sample_note": "This is a sample of the encoded log data",
            "total_size_bytes": len(data),
            "total_lines": len(lines),
            "sample_lines": sample_lines,
        }

        with open(output_path, "w") as f:
            json.dump(sample_data, f, indent=2)

        print(f"📄 Saved log sample: {output_path}")

    def run_demo(self):
        """Run the complete standalone encoder demo."""
        print("=" * 60)
        print("🚀 TIGHTBEAM STANDALONE ENCODER DEMO")
        print("=" * 60)
        print()

        # 1. Generate realistic log data
        print("1️⃣  Generating realistic log data...")
        log_data = self.generate_realistic_logs(num_entries=150)  # Substantial dataset
        print(f"   📊 Generated {len(log_data):,} bytes of log data")
        print(f"   📝 Contains {len(log_data.decode().split())} lines")
        print()

        # 2. Save sample for inspection
        print("2️⃣  Saving log sample for inspection...")
        self.save_log_sample(log_data)
        print()

        # 3. Encode to QR-GIF
        print("3️⃣  Encoding to QR-GIF...")
        symbols, gif_path = self.create_demo_qr_gif(log_data)
        print()

        # 4. Demo summary
        print("4️⃣  Demo Summary:")
        print(f"   📊 Original data: {len(log_data):,} bytes")
        print(f"   🔢 Fountain symbols: {len(symbols)}")
        print(f"   🎬 QR-GIF created: {gif_path}")
        print(f"   ⏱️  Frame duration: 800ms (optimal for scanning)")
        print()

        print("=" * 60)
        print("✅ DEMO COMPLETE!")
        print("=" * 60)
        print()
        print("📱 Next Steps:")
        print(f"   1. Open {gif_path} in any image viewer or browser")
        print("   2. Display it on a screen (phone, tablet, monitor)")
        print("   3. Use any QR scanner app to capture the codes")
        print("   4. Each QR contains: 'index:hex_payload' format")
        print("   5. Collect all symbols to reconstruct original data")
        print()
        print("🔍 Technical Details:")
        print("   • Uses fountain codes for burst-error resilience")
        print("   • Systematic encoding (original blocks first)")
        print("   • Each QR code is one fountain symbol")
        print("   • Designed for air-gapped data transfer")
        print()


if __name__ == "__main__":
    print("Initializing Tightbeam Standalone Encoder...")
    demo = StandaloneEncoder(block_size=64)  # Larger blocks for efficiency
    demo.run_demo()
