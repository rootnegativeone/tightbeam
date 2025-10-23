# Tightbeam Encoder - Deployment Guide

This package contains a standalone encoder demonstration for Tightbeam, a burst-resilient data transmission system using QR-GIFs.

## Quick Start

### 1. Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### 2. Installation
```bash
# Clone or extract the tightbeam package
cd tightbeam

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Demo
```bash
# Run the standalone encoder demo
python demo/standalone_encoder.py
```

## What the Demo Does

1. **Generates Realistic Log Data**: Creates ~150 realistic JSON log entries simulating various services (auth, payments, database, etc.)

2. **Fountain Encoding**: Uses fountain codes to encode the log data into redundant symbols for burst-error resilience

3. **QR-GIF Creation**: Converts encoded symbols into an animated GIF of QR codes

4. **Output Files**:
   - `tightbeam_demo.gif` - The main QR-GIF for display/scanning
   - `sample_log.json` - Sample of the encoded log data for inspection

## Using the Output

### Display the QR-GIF
- Open `tightbeam_demo.gif` in any image viewer, browser, or presentation software
- Display on any screen (phone, tablet, monitor, projector)
- The GIF loops automatically with 800ms per frame (optimal for scanning)

### Scanning/Capturing
- Use any QR code scanner app or camera
- Each QR code contains data in format: `index:hex_payload`
- Collect all QR codes to reconstruct the original log data
- The system is designed to work even with some missing frames (burst resilience)

## Technical Details

- **Fountain Codes**: Provides redundancy and error resilience
- **Systematic Encoding**: Original data blocks are sent first for efficiency
- **Block Size**: 64 bytes per block (configurable)
- **QR Error Correction**: Medium level for good balance of size/reliability
- **Frame Rate**: 800ms per frame for reliable camera capture

## Use Cases

- **Air-gapped Systems**: Transfer logs from isolated systems
- **Secure Environments**: One-way data exfiltration via visual channel
- **Demonstrations**: Show fountain coding and QR-based data transfer
- **Testing**: Evaluate optical data transmission in various conditions

## Troubleshooting

### Installation Issues
```bash
# If opencv-python fails to install
pip install --upgrade pip
pip install opencv-python-headless  # Use headless version if GUI issues

# If Pillow fails
pip install --upgrade Pillow

# Alternative: Use conda
conda install opencv pillow numpy imageio qrcode
```

### Runtime Issues
- **"Module not found"**: Ensure you're running from the tightbeam directory
- **"Permission denied"**: Check file permissions in output directory
- **QR codes too small**: Increase `box_size` parameter in the code
- **Scanning issues**: Try better lighting, steady camera, closer distance

## Customization

Edit `demo/standalone_encoder.py` to customize:
- `num_entries`: Number of log entries to generate
- `block_size`: Size of fountain code blocks
- `duration`: Frame duration in GIF (milliseconds)
- Log content and format

## File Structure
```
tightbeam/
├── demo/
│   ├── standalone_encoder.py    # Main demo script
│   ├── demo_rig.py             # Original demo
│   └── camera_demo.py          # Camera capture demo
├── common/
│   ├── fountain/               # Fountain coding implementation
│   └── shared/                 # Shared utilities
├── decoder/                    # Decoding components
├── requirements.txt            # Python dependencies
└── DEPLOYMENT_README.md        # This file
```

## Support

For issues or questions:
1. Check that all dependencies are installed correctly
2. Verify Python version compatibility (3.7+)
3. Test with a simple QR scanner app first
4. Review the technical documentation in the main README.md
