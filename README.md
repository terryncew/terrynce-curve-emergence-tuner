[![OpenLine-compatible](https://img.shields.io/static/v1?label=OpenLine&message=compatible%20v0.1&color=1f6feb)](https://github.com/terryncew/openline-core)
![Schema check](https://github.com/terryncew/openline-core/actions/workflows/validate.yml/badge.svg)

**Live hub:** https://terryncew.github.io/openline-hub/

# 🛡️ Emergence Guard

**Real-time safety monitoring for AI systems using dual κ/ε metrics**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

**Private kernel**: Real κ/ε math ships only as a compiled plug-in. This repo runs fine without it but falls back to demo logic.

-----

## 🎯 What Is This?

Emergence Guard is a **real-time safety monitor** that watches AI systems for dangerous emergent behavior using two key metrics:

- **κ (kappa)**: System stress/load indicator (0-1 scale)
- **ε (epsilon)**: Entropy/unpredictability indicator (0-1 scale)

**🔒 IP Protection Model:**

- **Public**: Monitoring framework, logging, CLI interface
- **Private**: Real Terrynce Curve κ/ε computations (compiled plugin only)
- **Demo-Ready**: Includes fallback math so it runs out-of-the-box

When either metric exceeds safe thresholds, the system triggers emergency protocols to prevent runaway AI behavior.

-----

## 🚀 Quick Start

```bash
# 1 – Clone
git clone https://github.com/terryncew/emergence-guard.git
cd emergence-guard

# 2 – (OPTIONAL) drop your proprietary kernel:
#     cp /path/to/emergence_kernel.so emergence-guard/

# 3 – Run
python3 emergence_guard.py
```

### 3. Watch the Output

```
🛡️  Emergence Guard started
Thresholds → κ≤0.8, ε≤0.7
⚠️  Private kernel not found – using fallback toy math
κ=0.234, ε=0.156  →  SAFE
κ=0.445, ε=0.289  →  SAFE  
κ=0.876, ε=0.234  →  CRITICAL – HIGH STRESS
🚨 EMERGENCY SHUTDOWN triggered
```

-----

## 📊 How It Works

### The κ/ε Safety Model

**κ (Kappa) - Stress Metric**

- CPU load (30%)
- Memory usage (30%)
- Network I/O (20%)
- Error rate (20%)

**ε (Epsilon) - Entropy Metric**

- Response variance (40%)
- Token entropy (30%)
- Pattern deviation (20%)
- Recursion depth (10%)

### Safety Thresholds

- **κ > 0.8**: System under extreme stress
- **ε > 0.7**: Chaotic/emergent behavior detected
- **Either condition**: Triggers emergency shutdown

### IP Protection Architecture

```
┌─────────────────────┐    ┌──────────────────────┐
│   PUBLIC REPO       │    │   PRIVATE KERNEL     │
│                     │    │                      │
│ • Monitor loop      │◄───┤ • Terrynce Curve     │
│ • Logging system    │    │ • Real κ/ε math     │
│ • CLI interface     │    │ • emergence_kernel.* │
│ • Fallback demos    │    │   (.so/.pyd/.wasm)   │
└─────────────────────┘    └──────────────────────┘
```

-----

## ⚙️ Configuration

### Using Your Private Kernel

```bash
# Compile your proprietary κ/ε algorithm to:
emergence_kernel.so     # Linux/macOS
emergence_kernel.pyd    # Windows  
emergence_kernel.wasm   # WebAssembly

# Drop it in the repo folder - auto-detected on startup
```

### Fallback vs Production

```python
# With private kernel:
🔒 Loaded private kernel: emergence_kernel

# Without (demo mode):
⚠️  Private kernel not found – using fallback toy math
```

-----

## 📁 Files Generated

- **`emergency_[timestamp].json`**: Detailed logs when emergency shutdown occurs
- **Console logs**: Real-time κ/ε values and system status

## 🛠️ Requirements

- **Python 3.7+** (uses dataclasses, type hints)
- **Standard library only** (no external dependencies)
- **Optional**: Your compiled `emergence_kernel.*` for production use

-----

## 🔬 Example Use Cases

### AI Training Monitoring

```python
# Monitor training runs for instability  
python3 emergence_guard.py  # Uses your private kernel if available
```

### Production Deployment

```bash
# 1. Compile your proprietary algorithm
gcc -shared -fPIC terrynce_curve.c -o emergence_kernel.so

# 2. Deploy with private kernel
cp emergence_kernel.so /production/emergence-guard/
python3 emergence_guard.py  # Now uses real math
```

-----

## 📈 Status Reports

Get detailed system status:

```python
report = guard.get_status_report()
print(json.dumps(report, indent=2))
```

Output:

```json
{
  "current_status": "SAFE - NORMAL OPERATION",
  "current_kappa": 0.234,
  "current_epsilon": 0.156,
  "avg_kappa_10": 0.267,
  "avg_epsilon_10": 0.198,
  "uptime_samples": 1247,
  "thresholds": {
    "kappa": 0.8,
    "epsilon": 0.7
  }
}
```

-----

## 🎭 Demo Mode vs Production

### Current Version (Demo)

- Simulates random sensor data
- Safe for testing and demonstration
- No external dependencies

### Production Ready

- Replace `sense_environment()` with real APIs
- Add database logging
- Integrate with alerting systems
- Connect to actual shutdown mechanisms

-----

## 🔒 Safety Philosophy

**“Better safe than sorry”** - Emergence Guard errs on the side of caution. A false positive (unnecessary shutdown) is infinitely preferable to a false negative (missed dangerous emergence).

The κ/ε model provides:

- **Early warning** before critical failures
- **Dual validation** (both stress AND chaos must be low)
- **Interpretable metrics** for human operators
- **Fail-safe design** with automatic cutoffs

-----

## 📜 License

```
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

-----

## 🤝 Contributing

1. Fork the repository
1. Create your feature branch (`git checkout -b feature/amazing-feature`)
1. Commit your changes (`git commit -m 'Add amazing feature'`)
1. Push to the branch (`git push origin feature/amazing-feature`)
1. Open a Pull Request

-----

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/[your-username]/emergence-guard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/[your-username]/emergence-guard/discussions)
- **Security**: Report vulnerabilities via GitHub Security tab

-----

**⚡ “When emergence threatens, the Guard protects.”**
