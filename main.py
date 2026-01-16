import sys
import os

# Ensure the current directory is in sys.path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import PortfolioApp

if __name__ == "__main__":
    app = PortfolioApp()
    sys.exit(app.run(sys.argv))
