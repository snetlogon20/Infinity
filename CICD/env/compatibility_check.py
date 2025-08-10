import sys
import importlib.metadata

requirements = [
    "streamlit", "pandas", "numpy", "scipy",
    "scikit-learn", "matplotlib", "flask",
    "chromadb", "arch", "clickhouse-driver"
]

print(f"Python {sys.version}")
for pkg in requirements:
    try:
        version = importlib.metadata.version(pkg)
        print(f"✅ {pkg:20} {version}   GOOD")
    except:
        print(f"❌ {pkg:20} NOT INSTALLED")