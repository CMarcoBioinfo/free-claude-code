import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# ---------------------------------------------------------
# 1. Récupérer le dossier où se trouve l'exécutable
# ---------------------------------------------------------
def get_executable_dir():
    """Retourne le dossier où se trouve l'exécutable ou le script."""
    if getattr(sys, 'frozen', False):
        # Exécutable PyInstaller
        return Path(sys.executable).parent
    else:
        # Mode script
        return Path(__file__).parent

# ---------------------------------------------------------
# 2. Charger configs/.env à côté de l'exécutable
# ---------------------------------------------------------
def load_config():
    exe_dir = get_executable_dir()
    config_file = exe_dir / "configs" / ".env"

    if not config_file.exists():
        print("ERREUR : Le fichier configs/.env est introuvable.")
        print(f"Chemin attendu : {config_file}")
        sys.exit(1)

    env = {}
    for line in config_file.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

    return env

# ---------------------------------------------------------
# 3. Sélection du dossier de travail
# ---------------------------------------------------------
def selectionner_dossier():
    root = tk.Tk()
    root.withdraw()
    dossier = filedialog.askdirectory(title="Sélectionnez votre dossier de travail")
    if not dossier:
        print("Aucun dossier sélectionné, fermeture.")
        sys.exit()
    return dossier

# ---------------------------------------------------------
# 4. Lancement du système
# ---------------------------------------------------------
def lancer_systeme():
    # Charger la configuration
    env = load_config()
    port = env.get("PORT", "8082")

    dossier_travail = selectionner_dossier()

    # Redirection de Claude Code vers ton proxy
    os.environ["ANTHROPIC_BASE_URL"] = f"http://localhost:{port}"
    os.environ["ANTHROPIC_API_KEY"] = "fake-key-pour-passer-les-verifications"

    # Lancement du proxy
    print(f"Démarrage du proxy local sur le port {port}...")

    python_cmd = "python3" if sys.platform != "win32" else "python"

    try:
        proxy_process = subprocess.Popen(
            ["fcc-server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        chemin_serveur = os.path.join(os.path.dirname(os.path.realpath(__file__)), "server.py")
        if not os.path.exists(chemin_serveur):
            chemin_serveur = "server.py"

        proxy_process = subprocess.Popen(
            [python_cmd, chemin_serveur],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    time.sleep(2)

    print(f"Ouverture de Claude Code dans : {dossier_travail}")

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["cmd", "/c", "start", "/wait", "cmd", "/c", "fcc-claude"],
                cwd=dossier_travail
            )
        else:
            try:
                subprocess.run(["x-terminal-emulator", "-e", "fcc-claude"], cwd=dossier_travail)
            except FileNotFoundError:
                subprocess.run(["fcc-claude"], cwd=dossier_travail)

    except FileNotFoundError:
        if sys.platform == "win32":
            subprocess.run(
                ["cmd", "/c", "start", "/wait", "cmd", "/c", "npx @anthropic-ai/claude-code"],
                cwd=dossier_travail
            )
        else:
            try:
                subprocess.run(["x-terminal-emulator", "-e", "npx @anthropic-ai/claude-code"], cwd=dossier_travail)
            except FileNotFoundError:
                subprocess.run(["npx", "@anthropic-ai/claude-code"], cwd=dossier_travail)

    finally:
        print("\nFermeture du proxy et nettoyage en cours...")
        proxy_process.kill()
        print("Système arrêté proprement.")

# ---------------------------------------------------------
# 5. Main
# ---------------------------------------------------------
if __name__ == "__main__":
    lancer_systeme()
