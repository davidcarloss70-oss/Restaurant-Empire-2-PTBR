import os
import subprocess
import sys
import platform

def build_app():
    print("Iniciando o empacotamento com PyInstaller usando UV...")
    
    # Using uv run with dependencies directly
    command = [
        "uv", "run", 
        "--with", "pyinstaller",
        "--with", "customtkinter",
        "--with", "deep-translator",
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name", "RE2_Tradutor_UI",
        "app.py"
    ]
    
    try:
        # Use shell=True on Windows to resolve "uv" executable if it's not in direct PATH but in alias
        use_shell = platform.system() == "Windows"
        subprocess.check_call(command, shell=use_shell)
        print("\n=== COMPILAÇÃO CONCLUÍDA! ===")
        print("Você encontrará o seu arquivo executável (.exe) dentro da nova pasta 'dist/' que foi criada.")
    except Exception as e:
        print(f"\nERRO DURANTE O EMPACOTAMENTO: {e}")

if __name__ == "__main__":
    build_app()
