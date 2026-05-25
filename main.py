import sys
import os

# Add the project directory to sys.path to ensure correct imports
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

from gui import DownloaderApp

def main():
    try:
        app = DownloaderApp()
        app.mainloop()
    except Exception as e:
        print(f"Erro fatal ao iniciar a aplicação: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
